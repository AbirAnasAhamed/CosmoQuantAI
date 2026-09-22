import pandas as pd
import numpy as np
from .base_feature import BaseCandlePsychologyFeature

class BodyEffortResult(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        body = np.where(body == 0, 0.00001, body)
        effort = tick_vol / body
        return pd.DataFrame({'body_effort_result': effort.fillna(0)}, index=df_ohlcv.index)

class IntraCandleDisplacementMomentum(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        momentum = (df_ohlcv['close'] - df_ohlcv['open']) * tick_count
        return pd.DataFrame({'intra_candle_displacement_momentum': momentum.fillna(0)}, index=df_ohlcv.index)

class BodyFillTickAsymmetry(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        
        asymmetry = (df_ohlcv['close'] - df_ohlcv['open']) / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001) * tick_delta
        return pd.DataFrame({'body_fill_tick_asymmetry': asymmetry.fillna(0)}, index=df_ohlcv.index)

class CandleCloseSurge(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        surge = tick_vol / (tick_vol.shift(1) + 1)
        return pd.DataFrame({'candle_close_surge': surge.fillna(0)}, index=df_ohlcv.index)

class OpenDriveTickVelocity(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        velocity = abs(df_ohlcv['open'] - df_ohlcv['close'].shift(1)) * tick_count
        return pd.DataFrame({'open_drive_tick_velocity': velocity.fillna(0)}, index=df_ohlcv.index)

class RealBodyTickSaturationIndex(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        saturation = tick_vol.rolling(5).sum() / (abs(df_ohlcv['close'] - df_ohlcv['open']).rolling(5).sum() + 0.00001)
        return pd.DataFrame({'real_body_tick_saturation_index': saturation.fillna(0)}, index=df_ohlcv.index)
