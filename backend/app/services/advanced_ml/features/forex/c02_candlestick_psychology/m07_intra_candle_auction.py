import pandas as pd
import numpy as np
from .base_feature import BaseCandlePsychologyFeature

class POCTickGravity(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        poc_proxy = (df_ohlcv['high'] + df_ohlcv['low'] + df_ohlcv['close']) / 3
        gravity = abs(df_ohlcv['close'] - poc_proxy) * tick_count
        return pd.DataFrame({'poc_tick_gravity': gravity.fillna(0)}, index=df_ohlcv.index)

class VAHTickRejection(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        vah_proxy = df_ohlcv['high'] - (df_ohlcv['high'] - df_ohlcv['low']) * 0.2
        rej = np.where(df_ohlcv['close'] < vah_proxy, tick_count, 0)
        return pd.DataFrame({'vah_tick_rejection': rej}, index=df_ohlcv.index)

class VALTickRejection(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        val_proxy = df_ohlcv['low'] + (df_ohlcv['high'] - df_ohlcv['low']) * 0.2
        rej = np.where(df_ohlcv['close'] > val_proxy, tick_count, 0)
        return pd.DataFrame({'val_tick_rejection': rej}, index=df_ohlcv.index)

class IntraCandleVolumeProfileSkewness(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        
        skew = (df_ohlcv['close'] - df_ohlcv['open']) / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001) * tick_delta
        return pd.DataFrame({'intra_candle_volume_profile_skewness': skew}, index=df_ohlcv.index)

class SinglePrintTickAnomalies(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        anomaly = np.where(tick_count < tick_count.rolling(20).mean() * 0.1, 1, 0)
        return pd.DataFrame({'single_print_tick_anomalies': anomaly}, index=df_ohlcv.index)

class AuctionImbalanceShift(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        
        shift = tick_delta.diff() * df_ohlcv['close'].diff()
        return pd.DataFrame({'auction_imbalance_shift': shift.fillna(0)}, index=df_ohlcv.index)

class ValueAreaTickDensity(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        density = tick_count / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001) * 0.7
        return pd.DataFrame({'value_area_tick_density': density}, index=df_ohlcv.index)
