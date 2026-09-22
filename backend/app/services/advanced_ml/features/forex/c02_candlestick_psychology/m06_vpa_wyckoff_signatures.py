import pandas as pd
import numpy as np
from .base_feature import BaseCandlePsychologyFeature

class ClimaxVolumeTickFootprint(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        climax = np.where(tick_count > tick_count.rolling(20).mean() * 3, tick_count, 0)
        return pd.DataFrame({'climax_volume_tick_footprint': climax}, index=df_ohlcv.index)

class ChurningTickIndex(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        churn = tick_count / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001)
        return pd.DataFrame({'churning_tick_index': churn}, index=df_ohlcv.index)

class StoppingVolumeIntensity(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        stop = tick_vol * abs(df_ohlcv['close'] - df_ohlcv['close'].shift(1))
        return pd.DataFrame({'stopping_volume_intensity': stop.fillna(0)}, index=df_ohlcv.index)

class NoDemandSupplyTickValidation(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        no_ds = np.where(tick_count < tick_count.rolling(20).mean() * 0.3, tick_count, 0)
        return pd.DataFrame({'no_demand_supply_tick_validation': no_ds}, index=df_ohlcv.index)

class AbsorptionVsInitiationTickRatio(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        wick = (df_ohlcv['high'] - df_ohlcv['low']) - body
        ratio = (wick + 0.00001) / (body + 0.00001) * abs(tick_delta)
        return pd.DataFrame({'absorption_vs_initiation_tick_ratio': ratio}, index=df_ohlcv.index)

class EffortWithoutResultTickAnomaly(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        anomaly = tick_count / (abs(df_ohlcv['close'] - df_ohlcv['open']) + 0.00001)
        return pd.DataFrame({'effort_without_result_tick_anomaly': anomaly}, index=df_ohlcv.index)

class AnomalousSpreadVolumeDivergence(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        div = (df_ohlcv['high'] - df_ohlcv['low']) - tick_vol.pct_change()
        return pd.DataFrame({'anomalous_spread_volume_divergence': div.fillna(0)}, index=df_ohlcv.index)
