import pandas as pd
import numpy as np
from .base_feature import BaseCandlePsychologyFeature

class WickRejectionIntensity(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        
        upper_wick = df_ohlcv['high'] - df_ohlcv[['open', 'close']].max(axis=1)
        lower_wick = df_ohlcv[['open', 'close']].min(axis=1) - df_ohlcv['low']
        tr = df_ohlcv['high'] - df_ohlcv['low']
        tr = np.where(tr == 0, 0.00001, tr)
        
        # Now use real tick counts/volume instead of OHLCV volume
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        intensity = ((upper_wick + lower_wick) / tr) * tick_vol
        return pd.DataFrame({'wick_rejection_intensity': intensity.fillna(0)}, index=df_ohlcv.index)

class UpperWickTickDensity(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        
        upper_wick = df_ohlcv['high'] - df_ohlcv[['open', 'close']].max(axis=1)
        upper_wick = np.where(upper_wick == 0, 0.00001, upper_wick)
        
        # Density = Tick Count in that candle / Wick Size
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        density = tick_count / upper_wick
        return pd.DataFrame({'upper_wick_tick_density': density.fillna(0)}, index=df_ohlcv.index)

class LowerWickTickDensity(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        
        lower_wick = df_ohlcv[['open', 'close']].min(axis=1) - df_ohlcv['low']
        lower_wick = np.where(lower_wick == 0, 0.00001, lower_wick)
        
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        density = tick_count / lower_wick
        return pd.DataFrame({'lower_wick_tick_density': density.fillna(0)}, index=df_ohlcv.index)

class WickToBodyTickTurnover(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        
        upper_wick = df_ohlcv['high'] - df_ohlcv[['open', 'close']].max(axis=1)
        lower_wick = df_ohlcv[['open', 'close']].min(axis=1) - df_ohlcv['low']
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        body = np.where(body == 0, 0.00001, body)
        
        turnover = (upper_wick + lower_wick) / body
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        return pd.DataFrame({'wick_to_body_tick_turnover': turnover * tick_vol}, index=df_ohlcv.index)

class ExtremePriceTickReversalVelocity(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        velocity = (df_ohlcv['high'] - df_ohlcv['low']) * tick_count / (abs(df_ohlcv['close'] - df_ohlcv['open']) + 0.00001)
        return pd.DataFrame({'extreme_price_tick_reversal_velocity': velocity.fillna(0)}, index=df_ohlcv.index)

class WickSponsoringDelta(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Proxy: delta applied to wick ratios
        delta = ( (df_ohlcv['high'] - df_ohlcv['close']) - (df_ohlcv['close'] - df_ohlcv['low']) ) * tick_delta
        return pd.DataFrame({'wick_sponsoring_delta': delta.fillna(0)}, index=df_ohlcv.index)

class ShadowTrappingDuration(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        duration = tick_count / (tick_count.rolling(5).max() + 0.00001)
        return pd.DataFrame({'shadow_trapping_duration': duration.fillna(0)}, index=df_ohlcv.index)

class HiddenRejectionBlock(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        
        wick = (df_ohlcv['high'] - df_ohlcv[['open', 'close']].max(axis=1)) + (df_ohlcv[['open', 'close']].min(axis=1) - df_ohlcv['low'])
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        block = np.where((wick < wick.rolling(10).mean()) & (tick_vol > tick_vol.rolling(10).mean()), tick_vol, 0)
        return pd.DataFrame({'hidden_rejection_block': block}, index=df_ohlcv.index)
