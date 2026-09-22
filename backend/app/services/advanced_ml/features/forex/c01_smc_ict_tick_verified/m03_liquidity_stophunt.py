import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class BSLSSLSweepTickVelocity(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Sweep Velocity: (High - High.shift(1)) / Volume (proxy)
        high_diff = df_ohlcv['high'].diff()
        low_diff = df_ohlcv['low'].diff()
        sweep = np.where(high_diff > 0, high_diff, np.where(low_diff < 0, abs(low_diff), 0))
        velocity = sweep * tick_vol
        return pd.DataFrame({'bsl_ssl_sweep_tick_velocity': velocity.fillna(0)}, index=df_ohlcv.index)

class LiquidityGrabRejectionDelta(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Rejection Delta: Wick size vs Body size * Volume
        upper_wick = df_ohlcv['high'] - df_ohlcv[['open', 'close']].max(axis=1)
        lower_wick = df_ohlcv[['open', 'close']].min(axis=1) - df_ohlcv['low']
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        body = np.where(body == 0, 0.00001, body)
        rejection = ((upper_wick + lower_wick) / body) * tick_vol
        return pd.DataFrame({'liquidity_grab_rejection_delta': rejection}, index=df_ohlcv.index)

class StopRunTickExhaustionIndex(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Exhaustion Index: Volume spike on extreme highs/lows
        roll_vol_max = tick_vol.rolling(20).max()
        roll_vol_max = np.where(roll_vol_max == 0, 1, roll_vol_max)
        exhaustion = tick_vol / roll_vol_max
        return pd.DataFrame({'stop_run_tick_exhaustion_index': exhaustion.fillna(0)}, index=df_ohlcv.index)

class InducementLevelTickClustering(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Clustering: Local minimal price movement with high volume
        spread = df_ohlcv['high'] - df_ohlcv['low']
        spread = np.where(spread == 0, 0.00001, spread)
        clustering = tick_vol / spread
        return pd.DataFrame({'inducement_level_tick_clustering': clustering}, index=df_ohlcv.index)

class SweepVsBOSTickRatio(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Ratio of body (BOS) vs wicks (Sweep)
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        wicks = df_ohlcv['high'] - df_ohlcv['low'] - body
        wicks = np.where(wicks == 0, 0.00001, wicks)
        ratio = body / wicks
        return pd.DataFrame({'sweep_vs_bos_tick_ratio': ratio}, index=df_ohlcv.index)
