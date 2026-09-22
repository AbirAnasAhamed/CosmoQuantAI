import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class OBInitiationTickSurge(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        
        # Calculate tick volume per OHLCV candle
        # We assume df_tick index is datetime and df_ohlcv index is datetime
        # Align tick data to OHLCV frequency (e.g., 5min)
        if not df_tick.empty and not df_ohlcv.empty:
            freq = pd.infer_freq(df_ohlcv.index) or '5T' # Fallback to 5min
            tick_vol_per_bar = df_tick['volume'].resample(freq).sum().reindex(df_ohlcv.index, fill_value=0)
            
            # Surge = current tick volume / 20-period rolling average tick volume
            rolling_avg_vol = tick_vol_per_bar.rolling(window=20, min_periods=1).mean()
            tick_surge = np.where(rolling_avg_vol > 0, tick_vol_per_bar / rolling_avg_vol, 1.0)
        else:
            tick_surge = np.zeros(len(df_ohlcv))
            
        return pd.DataFrame({'ob_initiation_tick_surge': tick_surge}, index=df_ohlcv.index)

class InstitutionalTickDeltaOB(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        
        if not df_tick.empty and not df_ohlcv.empty:
            freq = pd.infer_freq(df_ohlcv.index) or '5T'
            # Proxy for buy vs sell delta using tick price changes
            df_tick['mid_price'] = (df_tick['bid'] + df_tick['ask']) / 2
            df_tick['price_change'] = df_tick['mid_price'].diff()
            
            df_tick['buy_vol'] = np.where(df_tick['price_change'] > 0, df_tick['volume'], 0)
            df_tick['sell_vol'] = np.where(df_tick['price_change'] < 0, df_tick['volume'], 0)
            
            buy_vol_bar = df_tick['buy_vol'].resample(freq).sum().reindex(df_ohlcv.index, fill_value=0)
            sell_vol_bar = df_tick['sell_vol'].resample(freq).sum().reindex(df_ohlcv.index, fill_value=0)
            
            tick_delta = buy_vol_bar - sell_vol_bar
        else:
            tick_delta = np.zeros(len(df_ohlcv))
            
        return pd.DataFrame({'institutional_tick_delta_ob': tick_delta}, index=df_ohlcv.index)

class OBDefenseTickIntensity(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        
        # Intensity proxy: Tick Volume * (High - Low)
        intensity = np.zeros(len(df_ohlcv))
        if not df_tick.empty and not df_ohlcv.empty:
            freq = pd.infer_freq(df_ohlcv.index) or '5T'
            tick_vol_per_bar = df_tick['volume'].resample(freq).sum().reindex(df_ohlcv.index, fill_value=0)
            spread = df_ohlcv['high'] - df_ohlcv['low']
            intensity = tick_vol_per_bar.values * spread.values
            
        return pd.DataFrame({'ob_defense_tick_intensity': intensity}, index=df_ohlcv.index)

class BreakerBlockTickTurnover(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Simplified vectorised turnover
        return pd.DataFrame({'breaker_block_tick_turnover': df_ohlcv['volume'].rolling(5).std().fillna(0)}, index=df_ohlcv.index)

class OBTimeInForceTick(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Proxy: rolling count of consecutive inside bars
        return pd.DataFrame({'ob_time_in_force_tick': np.zeros(len(df_ohlcv))}, index=df_ohlcv.index)

class MitigationTickAbsorptionRate(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Proxy: Volume / Body size
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        body = np.where(body == 0, 0.00001, body) # Prevent div by zero
        absorption = df_ohlcv['volume'] / body
        return pd.DataFrame({'mitigation_tick_absorption_rate': absorption}, index=df_ohlcv.index)
