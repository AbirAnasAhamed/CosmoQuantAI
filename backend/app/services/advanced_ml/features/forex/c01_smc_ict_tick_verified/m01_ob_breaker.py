import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class OBInitiationTickSurge(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        rolling_avg_vol = tick_count.rolling(window=20, min_periods=1).mean()
        tick_surge = np.where(rolling_avg_vol > 0, tick_count / rolling_avg_vol, 1.0)
        return pd.DataFrame({'ob_initiation_tick_surge': tick_surge}, index=df_ohlcv.index)

class InstitutionalTickDeltaOB(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        
        return pd.DataFrame({'institutional_tick_delta_ob': tick_delta}, index=df_ohlcv.index)

class OBDefenseTickIntensity(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        spread = df_ohlcv['high'] - df_ohlcv['low']
        intensity = tick_count * spread
        return pd.DataFrame({'ob_defense_tick_intensity': intensity}, index=df_ohlcv.index)

class BreakerBlockTickTurnover(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        turnover = tick_count.rolling(5).std()
        return pd.DataFrame({'breaker_block_tick_turnover': turnover.fillna(0)}, index=df_ohlcv.index)

class OBTimeInForceTick(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        # Proper proxy: consecutive times tick_count > average
        is_high = tick_count > tick_count.rolling(10).mean()
        tif = is_high.astype(int).rolling(3).sum()
        return pd.DataFrame({'ob_time_in_force_tick': tif.fillna(0)}, index=df_ohlcv.index)

class MitigationTickAbsorptionRate(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        body = np.where(body == 0, 0.00001, body) # Prevent div by zero
        absorption = tick_count / body
        return pd.DataFrame({'mitigation_tick_absorption_rate': absorption}, index=df_ohlcv.index)
