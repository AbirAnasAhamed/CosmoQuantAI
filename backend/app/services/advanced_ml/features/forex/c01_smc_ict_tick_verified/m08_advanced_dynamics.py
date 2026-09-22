import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class InternalVsExternalLiquidityTickDelta(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Delta between internal (close to open) vs external (high to low)
        internal = abs(df_ohlcv['close'] - df_ohlcv['open'])
        external = df_ohlcv['high'] - df_ohlcv['low']
        external = np.where(external == 0, 0.00001, external)
        delta = (internal / external) * tick_vol
        return pd.DataFrame({'internal_vs_external_liquidity_tick_delta': delta}, index=df_ohlcv.index)

class LiquidityVoidTickSpreadCoefficient(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Void Coefficient: True Range scaled by Volume
        tr = np.maximum(df_ohlcv['high'] - df_ohlcv['low'], 
                        np.maximum(abs(df_ohlcv['high'] - df_ohlcv['close'].shift(1)), 
                                   abs(df_ohlcv['low'] - df_ohlcv['close'].shift(1))))
        coef = tr * tick_vol
        return pd.DataFrame({'liquidity_void_tick_spread_coefficient': coef.fillna(0)}, index=df_ohlcv.index)

class StopRunCascadingTickMultiplier(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Cascading: Volume multiplier on consecutive sweeps
        is_sweep = (df_ohlcv['high'] > df_ohlcv['high'].shift(1)) | (df_ohlcv['low'] < df_ohlcv['low'].shift(1))
        cascade = is_sweep.astype(int).rolling(3).sum() * tick_vol
        return pd.DataFrame({'stop_run_cascading_tick_multiplier': cascade.fillna(0)}, index=df_ohlcv.index)

class KillzoneTickVolatilitySkew(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Skewness of volume
        skew = tick_vol.rolling(10).skew().fillna(0)
        return pd.DataFrame({'killzone_tick_volatility_skew': skew}, index=df_ohlcv.index)

class MacroTimeTickEntropy(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Entropy Proxy: Variance of volume
        entropy = tick_vol.rolling(10).var().fillna(0)
        return pd.DataFrame({'macro_time_tick_entropy': entropy}, index=df_ohlcv.index)

class DisplacementTickFractalDimension(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Fractal Dimension Proxy: Log(Path Length) / Log(Time)
        path_length = abs(df_ohlcv['close'].diff()).rolling(10).sum()
        net_dist = abs(df_ohlcv['close'] - df_ohlcv['close'].shift(10))
        net_dist = np.where(net_dist == 0, 0.00001, net_dist)
        fd = np.log(path_length + 1) / np.log(net_dist + 1)
        return pd.DataFrame({'displacement_tick_fractal_dimension': fd.fillna(0)}, index=df_ohlcv.index)

class TickWeightedSMTDivergence(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # SMT Divergence Proxy
        smt = df_ohlcv['close'].pct_change() * tick_vol.pct_change()
        return pd.DataFrame({'tick_weighted_smt_divergence': smt.fillna(0)}, index=df_ohlcv.index)

class FVGInversionTickThreshold(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Inversion threshold: volume required to invert a gap
        threshold = tick_vol.rolling(20).mean() * 1.5
        return pd.DataFrame({'fvg_inversion_tick_threshold': threshold.fillna(0)}, index=df_ohlcv.index)

class BreakerBlockResonanceIndex(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Resonance: Harmonic combination of volume and price movement
        resonance = (tick_vol * df_ohlcv['close'].diff()).rolling(5).sum()
        return pd.DataFrame({'breaker_block_resonance_index': resonance.fillna(0)}, index=df_ohlcv.index)

class InstitutionalOrderLayering(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Layering: Gradual increase in volume over time
        layering = tick_vol.diff().rolling(3).apply(lambda x: 1 if all(x > 0) else 0, raw=True)
        return pd.DataFrame({'institutional_order_layering': layering.fillna(0)}, index=df_ohlcv.index)
