import pandas as pd
import numpy as np
from .base_feature import BaseCandlePsychologyFeature

class DojiIndecisionTickDensity(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        is_doji = abs(df_ohlcv['close'] - df_ohlcv['open']) <= (df_ohlcv['high'] - df_ohlcv['low']) * 0.1
        density = np.where(is_doji, tick_count / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001), 0)
        return pd.DataFrame({'doji_indecision_tick_density': density}, index=df_ohlcv.index)

class EngulfingImbalanceRatio(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        prev_body = abs(df_ohlcv['close'].shift(1) - df_ohlcv['open'].shift(1))
        is_engulf = body > prev_body
        ratio = np.where(is_engulf, tick_delta / (agg_ticks['volume'].shift(1) + 1 if 'volume' in agg_ticks else 1), 0)
        return pd.DataFrame({'engulfing_imbalance_ratio': ratio}, index=df_ohlcv.index)

class PinBarTrappingVolume(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        tr = df_ohlcv['high'] - df_ohlcv['low']
        tr = np.where(tr == 0, 0.00001, tr)
        upper = df_ohlcv['high'] - df_ohlcv[['open', 'close']].max(axis=1)
        lower = df_ohlcv[['open', 'close']].min(axis=1) - df_ohlcv['low']
        is_pin = (upper / tr > 0.6) | (lower / tr > 0.6)
        trap = np.where(is_pin, tick_vol, 0)
        return pd.DataFrame({'pin_bar_trapping_volume': trap}, index=df_ohlcv.index)

class HammerTickAcceleration(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        lower = df_ohlcv[['open', 'close']].min(axis=1) - df_ohlcv['low']
        tr = df_ohlcv['high'] - df_ohlcv['low']
        tr = np.where(tr == 0, 0.00001, tr)
        is_hammer = (lower / tr > 0.6) & (df_ohlcv['close'] > df_ohlcv['open'])
        accel = np.where(is_hammer, tick_count * (df_ohlcv['close'] - df_ohlcv['open']), 0)
        return pd.DataFrame({'hammer_tick_acceleration': accel}, index=df_ohlcv.index)

class StarValidationShift(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        
        shift = tick_delta.diff() * np.sign(df_ohlcv['close'] - df_ohlcv['open'])
        return pd.DataFrame({'star_validation_shift': shift.fillna(0)}, index=df_ohlcv.index)

class ShootingStarExhaustionSignature(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        upper = df_ohlcv['high'] - df_ohlcv[['open', 'close']].max(axis=1)
        tr = df_ohlcv['high'] - df_ohlcv['low']
        tr = np.where(tr == 0, 0.00001, tr)
        is_shooting = (upper / tr > 0.6) & (df_ohlcv['close'] < df_ohlcv['open'])
        exh = np.where(is_shooting, tick_count / (tick_count.rolling(5).mean() + 1), 0)
        return pd.DataFrame({'shooting_star_exhaustion_signature': exh}, index=df_ohlcv.index)

class InsideBarTickCompression(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        is_inside = (df_ohlcv['high'] < df_ohlcv['high'].shift(1)) & (df_ohlcv['low'] > df_ohlcv['low'].shift(1))
        comp = np.where(is_inside, tick_count / (tick_count.shift(1) + 1), 0)
        return pd.DataFrame({'inside_bar_tick_compression': comp}, index=df_ohlcv.index)

class MarubozuInstitutionalCommitment(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        tr = df_ohlcv['high'] - df_ohlcv['low']
        tr = np.where(tr == 0, 0.00001, tr)
        is_marubozu = (body / tr) > 0.9
        commit = np.where(is_marubozu, tick_vol * body, 0)
        return pd.DataFrame({'marubozu_institutional_commitment': commit}, index=df_ohlcv.index)
