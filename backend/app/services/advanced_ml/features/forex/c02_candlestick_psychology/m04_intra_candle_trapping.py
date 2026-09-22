import pandas as pd
import numpy as np
from .base_feature import BaseCandlePsychologyFeature

class IntraCandleStopHuntCascade(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        sweep_high = df_ohlcv['high'] > df_ohlcv['high'].shift(1)
        sweep_low = df_ohlcv['low'] < df_ohlcv['low'].shift(1)
        cascade = np.where(sweep_high | sweep_low, tick_count * tick_count.diff(), 0)
        return pd.DataFrame({'intra_candle_stop_hunt_cascade': cascade}, index=df_ohlcv.index)

class LateJoinerTrappingIndex(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        # Reversal after high volume
        trap = df_ohlcv['close'].diff() * tick_vol.shift(1)
        return pd.DataFrame({'late_joiner_trapping_index': trap.fillna(0)}, index=df_ohlcv.index)

class FakeoutTickVelocity(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        fakeout = np.where(df_ohlcv['close'].diff() != np.sign(df_ohlcv['close'].diff().shift(1)), tick_count, 0)
        return pd.DataFrame({'fakeout_tick_velocity': fakeout}, index=df_ohlcv.index)

class SqueezeImbalanceRatio(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        
        ratio = (df_ohlcv['close'] - df_ohlcv['open']) / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001) * tick_delta
        return pd.DataFrame({'squeeze_imbalance_ratio': ratio}, index=df_ohlcv.index)

class WrongSidedTickAccumulation(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        
        # Price goes one way, volume diverges
        wrong = tick_delta * -np.sign(df_ohlcv['close'] - df_ohlcv['open'])
        return pd.DataFrame({'wrong_sided_tick_accumulation': wrong}, index=df_ohlcv.index)

class ExhaustionTickGap(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        gap = (df_ohlcv['high'] - df_ohlcv['low']) / (tick_count + 1)
        return pd.DataFrame({'exhaustion_tick_gap': gap}, index=df_ohlcv.index)

class ConsecutivePressure(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        sign = np.sign(df_ohlcv['close'] - df_ohlcv['open'])
        pressure = (sign == sign.shift(1)).astype(int) * tick_vol
        return pd.DataFrame({'consecutive_pressure': pressure.fillna(0)}, index=df_ohlcv.index)
