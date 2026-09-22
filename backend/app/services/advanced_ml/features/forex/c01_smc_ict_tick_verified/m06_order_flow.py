import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class CumulativeTickDeltaDivergence(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # CTD Divergence Proxy: Volume * Price Direction Divergence
        price_dir = np.sign(df_ohlcv['close'] - df_ohlcv['open'])
        vol_dir = tick_vol.diff()
        ctd = price_dir * vol_dir
        return pd.DataFrame({'cumulative_tick_delta_divergence': ctd.fillna(0)}, index=df_ohlcv.index)

class InstitutionalSponsoringSignature(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Sponsoring: Huge volume with tiny price movement
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        body = np.where(body == 0, 0.00001, body)
        sig = tick_vol / body
        return pd.DataFrame({'institutional_sponsoring_signature': sig}, index=df_ohlcv.index)

class TickSpreadWideningIndicator(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Spread Proxy: High - Low relative to volume
        spread = df_ohlcv['high'] - df_ohlcv['low']
        spread_indicator = spread * tick_vol
        return pd.DataFrame({'tick_spread_widening_indicator': spread_indicator}, index=df_ohlcv.index)

class TickAccelDecelAtPOI(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Accel/Decel: 2nd derivative of Volume
        accel = tick_vol.diff().diff().fillna(0)
        return pd.DataFrame({'tick_accel_decel_at_poi': accel}, index=df_ohlcv.index)

class TickImbalanceSequenceIndex(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Sequence Index: Consecutive same-direction volume surges
        dir_val = np.sign(df_ohlcv['close'] - df_ohlcv['open'])
        sequence = (dir_val == dir_val.shift(1)).astype(int) * tick_vol
        return pd.DataFrame({'tick_imbalance_sequence_index': sequence.fillna(0)}, index=df_ohlcv.index)

class SMCLevelExhaustionRate(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Exhaustion: Volume drop off at extremes
        exhaustion = tick_vol / (tick_vol.rolling(5).mean() + 1)
        return pd.DataFrame({'smc_level_exhaustion_rate': exhaustion.fillna(0)}, index=df_ohlcv.index)

class LiquidityVoidTickTraverseTime(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Traverse time proxy: Range / Volume
        rng = df_ohlcv['high'] - df_ohlcv['low']
        traverse = tick_vol / (rng + 0.00001)
        return pd.DataFrame({'liquidity_void_tick_traverse_time': traverse}, index=df_ohlcv.index)

class CompositeSMCTickScore(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Composite score
        score = (tick_vol / (tick_vol.rolling(20).mean() + 1)) * ((df_ohlcv['close'] - df_ohlcv['open']) / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001))
        return pd.DataFrame({'composite_smc_tick_score': score.fillna(0)}, index=df_ohlcv.index)
