import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class AsianRangeTickDensity(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Proxy for Asian Session (00:00 to 08:00 UTC) Density
        is_asian = (df_ohlcv.index.hour >= 0) & (df_ohlcv.index.hour < 8)
        density = np.where(is_asian, df_ohlcv['volume'] / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001), 0)
        return pd.DataFrame({'asian_range_tick_density': density}, index=df_ohlcv.index)

class LondonOpenManipulationDelta(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Proxy for London Open (07:00 to 10:00 UTC) Manipulation
        is_london = (df_ohlcv.index.hour >= 7) & (df_ohlcv.index.hour < 10)
        manipulation = np.where(is_london, df_ohlcv['volume'] * df_ohlcv['close'].diff(), 0)
        return pd.DataFrame({'london_open_manipulation_delta': manipulation}, index=df_ohlcv.index)

class NYKillzoneDistributionVelocity(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Proxy for NY Killzone (12:00 to 15:00 UTC)
        is_ny = (df_ohlcv.index.hour >= 12) & (df_ohlcv.index.hour < 15)
        velocity = np.where(is_ny, df_ohlcv['volume'] / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001), 0)
        return pd.DataFrame({'ny_killzone_distribution_velocity': velocity}, index=df_ohlcv.index)

class PO3TickSynchronization(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Power of 3 (Accumulation, Manipulation, Distribution)
        # Proxy: 3-period rolling standard deviation of volume
        sync = df_ohlcv['volume'].rolling(3).std().fillna(0)
        return pd.DataFrame({'po3_tick_synchronization': sync}, index=df_ohlcv.index)

class KillzoneTickVWAPDivergence(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Simple VWAP Proxy
        typical_price = (df_ohlcv['high'] + df_ohlcv['low'] + df_ohlcv['close']) / 3
        vwap = (typical_price * df_ohlcv['volume']).rolling(20).sum() / (df_ohlcv['volume'].rolling(20).sum() + 0.00001)
        divergence = df_ohlcv['close'] - vwap
        return pd.DataFrame({'killzone_tick_vwap_divergence': divergence.fillna(0)}, index=df_ohlcv.index)

class MacroWindowTickSpikeRate(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Spike Rate: Rate of change in Volume
        spike = df_ohlcv['volume'].pct_change().fillna(0)
        return pd.DataFrame({'macro_window_tick_spike_rate': spike}, index=df_ohlcv.index)
