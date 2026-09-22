import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class AsianRangeTickDensity(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Proxy for Asian Session (00:00 to 08:00 UTC) Density
        is_asian = (df_ohlcv.index.hour >= 0) & (df_ohlcv.index.hour < 8)
        density = np.where(is_asian, tick_vol / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001), 0)
        return pd.DataFrame({'asian_range_tick_density': density}, index=df_ohlcv.index)

class LondonOpenManipulationDelta(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Proxy for London Open (07:00 to 10:00 UTC) Manipulation
        is_london = (df_ohlcv.index.hour >= 7) & (df_ohlcv.index.hour < 10)
        manipulation = np.where(is_london, tick_vol * df_ohlcv['close'].diff(), 0)
        return pd.DataFrame({'london_open_manipulation_delta': manipulation}, index=df_ohlcv.index)

class NYKillzoneDistributionVelocity(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Proxy for NY Killzone (12:00 to 15:00 UTC)
        is_ny = (df_ohlcv.index.hour >= 12) & (df_ohlcv.index.hour < 15)
        velocity = np.where(is_ny, tick_vol / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001), 0)
        return pd.DataFrame({'ny_killzone_distribution_velocity': velocity}, index=df_ohlcv.index)

class PO3TickSynchronization(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Power of 3 (Accumulation, Manipulation, Distribution)
        # Proxy: 3-period rolling standard deviation of volume
        sync = tick_vol.rolling(3).std().fillna(0)
        return pd.DataFrame({'po3_tick_synchronization': sync}, index=df_ohlcv.index)

class KillzoneTickVWAPDivergence(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Simple VWAP Proxy
        typical_price = (df_ohlcv['high'] + df_ohlcv['low'] + df_ohlcv['close']) / 3
        vwap = (typical_price * tick_vol).rolling(20).sum() / (tick_vol.rolling(20).sum() + 0.00001)
        divergence = df_ohlcv['close'] - vwap
        return pd.DataFrame({'killzone_tick_vwap_divergence': divergence.fillna(0)}, index=df_ohlcv.index)

class MacroWindowTickSpikeRate(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Spike Rate: Rate of change in Volume
        spike = tick_vol.pct_change().fillna(0)
        return pd.DataFrame({'macro_window_tick_spike_rate': spike}, index=df_ohlcv.index)
