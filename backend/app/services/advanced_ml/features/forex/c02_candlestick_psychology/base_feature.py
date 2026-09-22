import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

class BaseCandlePsychologyFeature(ABC):
    """
    Abstract base class for all Candlestick Psychology & Micro-anatomy features.
    Requires both standard OHLCV data and high-frequency L1 Tick Data.
    """
    
    @abstractmethod
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        pass
    
    def _validate_inputs(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame):
        if df_ohlcv is None or df_tick is None:
            raise ValueError("Both df_ohlcv and df_tick must be provided.")
        if df_ohlcv.empty:
            raise ValueError("df_ohlcv cannot be empty.")
            
    def _aggregate_ticks_to_ohlcv(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregates L1 tick data to match the OHLCV timeframe.
        Calculates tick buy/sell volumes, tick count, and tick-level delta.
        """
        if df_tick.empty or df_ohlcv.empty:
            return pd.DataFrame(index=df_ohlcv.index)
            
        freq = pd.infer_freq(df_ohlcv.index) or '5min'
        
        # Handle potential NaNs in real-world streaming ticks
        df_tick['bid'] = df_tick['bid'].ffill().bfill()
        df_tick['ask'] = df_tick['ask'].ffill().bfill()
        
        # Approximate Tick Price and Direction
        df_tick['mid_price'] = (df_tick['bid'] + df_tick['ask']) / 2
        df_tick['price_change'] = df_tick['mid_price'].diff()
        
        # Categorize Tick Volumes
        df_tick['buy_vol'] = np.where(df_tick['price_change'] > 0, df_tick['volume'], 0)
        df_tick['sell_vol'] = np.where(df_tick['price_change'] < 0, df_tick['volume'], 0)
        
        # Resample to OHLCV frequency
        agg_ticks = df_tick.resample(freq).agg({
            'volume': 'sum',
            'buy_vol': 'sum',
            'sell_vol': 'sum',
            'mid_price': 'count' # Proxy for tick count (speed/velocity)
        }).rename(columns={'mid_price': 'tick_count'})
        
        # Align with OHLCV index (Timezone Safe for Production)
        if hasattr(agg_ticks.index, 'tz') and hasattr(df_ohlcv.index, 'tz'):
            if agg_ticks.index.tz != df_ohlcv.index.tz:
                if agg_ticks.index.tz is None:
                    agg_ticks.index = agg_ticks.index.tz_localize(df_ohlcv.index.tz)
                else:
                    agg_ticks.index = agg_ticks.index.tz_convert(df_ohlcv.index.tz)
                    
        agg_ticks = agg_ticks.reindex(df_ohlcv.index, fill_value=0)
        agg_ticks['tick_delta'] = agg_ticks['buy_vol'] - agg_ticks['sell_vol']
        
        return agg_ticks
