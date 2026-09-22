import pandas as pd
import numpy as np
from .base_feature import BaseCandlePsychologyFeature

class GapFillVelocity(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        gap = abs(df_ohlcv['open'] - df_ohlcv['close'].shift(1))
        vel = np.where(gap > 0, tick_count / gap, 0)
        return pd.DataFrame({'gap_fill_velocity': vel}, index=df_ohlcv.index)

class VWAPDivergenceWithinCandle(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        typical = (df_ohlcv['high'] + df_ohlcv['low'] + df_ohlcv['close']) / 3
        vwap = (typical * tick_vol).rolling(5).sum() / (tick_vol.rolling(5).sum() + 1)
        div = df_ohlcv['close'] - vwap
        return pd.DataFrame({'vwap_divergence_within_candle': div.fillna(0)}, index=df_ohlcv.index)

class TickInterArrivalTimeVariance(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        var = 1 / (tick_count.rolling(5).var() + 0.00001)
        return pd.DataFrame({'tick_inter_arrival_time_variance': var.fillna(0)}, index=df_ohlcv.index)

class PriceTraverseTime(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        traverse = tick_count / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001)
        return pd.DataFrame({'price_traverse_time': traverse}, index=df_ohlcv.index)

class HighFrequencyMicroTrendReversals(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        rev = tick_count * (abs(df_ohlcv['high'] - df_ohlcv['close']) + abs(df_ohlcv['close'] - df_ohlcv['low']))
        return pd.DataFrame({'high_frequency_micro_trend_reversals': rev}, index=df_ohlcv.index)

class TimeWeightedTickAbsorption(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        twta = tick_count.rolling(3).apply(lambda x: np.sum(x * np.arange(1, 4))/6, raw=True)
        return pd.DataFrame({'time_weighted_tick_absorption': twta.fillna(0)}, index=df_ohlcv.index)
