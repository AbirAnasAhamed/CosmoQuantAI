from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Union

class BaseTickVerifiedFeature(ABC):
    """
    Abstract base class for all Tick-Verified SMC & ICT metrics.
    Ensures a standardized, dynamic, and modular interface for feature calculation.
    Designed for high-frequency tick data combined with standard OHLCV.
    """

    @abstractmethod
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Calculates the advanced metric.
        
        Args:
            df_ohlcv (pd.DataFrame): Standard OHLCV data.
            df_tick (pd.DataFrame): High-frequency L1 tick data.
            **kwargs: Dynamic parameters for the specific metric.
            
        Returns:
            pd.DataFrame: A DataFrame containing the calculated feature(s), aligned with df_ohlcv index.
        """
        pass

    def _validate_inputs(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame):
        """
        Basic validation to ensure required columns exist and data is not empty.
        """
        if df_ohlcv.empty or df_tick.empty:
            raise ValueError(f"{self.__class__.__name__}: Input DataFrames cannot be empty.")
            
        required_ohlcv = {'open', 'high', 'low', 'close', 'volume'}
        if not required_ohlcv.issubset(set(df_ohlcv.columns)):
            raise ValueError(f"{self.__class__.__name__}: df_ohlcv missing required columns.")
            
        required_tick = {'bid', 'ask', 'volume'} # L1 Tick Data
        if not required_tick.issubset(set(df_tick.columns)):
            # Warning or fallback based on provider
            pass

    def _aggregate_ticks_to_ohlcv(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame) -> pd.DataFrame:
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
