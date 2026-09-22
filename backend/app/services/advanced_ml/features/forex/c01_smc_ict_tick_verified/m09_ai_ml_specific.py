import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class EigenStructureTickCovariance(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Covariance proxy between price and volume
        cov = df_ohlcv['close'].rolling(20).cov(tick_vol)
        return pd.DataFrame({'eigen_structure_tick_covariance': cov.fillna(0)}, index=df_ohlcv.index)

class PDFTickInterArrivalTimes(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Proxy: 1 / Volume (as higher volume implies shorter inter-arrival)
        pdf_proxy = 1 / (tick_vol + 0.00001)
        return pd.DataFrame({'pdf_tick_inter_arrival_times': pdf_proxy}, index=df_ohlcv.index)

class TickVolumeWeightedHurst(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Hurst Exponent Proxy: scaled standard deviation of log returns
        log_ret = np.log(df_ohlcv['close'] / df_ohlcv['close'].shift(1)).fillna(0)
        hurst = log_ret.rolling(20).std() * tick_vol.rolling(20).mean()
        return pd.DataFrame({'tick_volume_weighted_hurst': hurst.fillna(0)}, index=df_ohlcv.index)

class RLRewardSignalProxy(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # RL Reward Signal: Forward return proxy scaled by current volume
        reward = df_ohlcv['close'].pct_change().shift(-1) * tick_vol
        return pd.DataFrame({'rl_reward_signal_proxy': reward.fillna(0)}, index=df_ohlcv.index)
