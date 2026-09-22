import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class CumulativeTickDeltaDivergence(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # CTD Divergence Proxy: Volume * Price Direction Divergence
        price_dir = np.sign(df_ohlcv['close'] - df_ohlcv['open'])
        vol_dir = df_ohlcv['volume'].diff()
        ctd = price_dir * vol_dir
        return pd.DataFrame({'cumulative_tick_delta_divergence': ctd.fillna(0)}, index=df_ohlcv.index)

class InstitutionalSponsoringSignature(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Sponsoring: Huge volume with tiny price movement
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        body = np.where(body == 0, 0.00001, body)
        sig = df_ohlcv['volume'] / body
        return pd.DataFrame({'institutional_sponsoring_signature': sig}, index=df_ohlcv.index)

class TickSpreadWideningIndicator(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Spread Proxy: High - Low relative to volume
        spread = df_ohlcv['high'] - df_ohlcv['low']
        spread_indicator = spread * df_ohlcv['volume']
        return pd.DataFrame({'tick_spread_widening_indicator': spread_indicator}, index=df_ohlcv.index)

class TickAccelDecelAtPOI(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Accel/Decel: 2nd derivative of Volume
        accel = df_ohlcv['volume'].diff().diff().fillna(0)
        return pd.DataFrame({'tick_accel_decel_at_poi': accel}, index=df_ohlcv.index)

class TickImbalanceSequenceIndex(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Sequence Index: Consecutive same-direction volume surges
        dir_val = np.sign(df_ohlcv['close'] - df_ohlcv['open'])
        sequence = (dir_val == dir_val.shift(1)).astype(int) * df_ohlcv['volume']
        return pd.DataFrame({'tick_imbalance_sequence_index': sequence.fillna(0)}, index=df_ohlcv.index)

class SMCLevelExhaustionRate(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Exhaustion: Volume drop off at extremes
        exhaustion = df_ohlcv['volume'] / (df_ohlcv['volume'].rolling(5).mean() + 1)
        return pd.DataFrame({'smc_level_exhaustion_rate': exhaustion.fillna(0)}, index=df_ohlcv.index)

class LiquidityVoidTickTraverseTime(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Traverse time proxy: Range / Volume
        rng = df_ohlcv['high'] - df_ohlcv['low']
        traverse = df_ohlcv['volume'] / (rng + 0.00001)
        return pd.DataFrame({'liquidity_void_tick_traverse_time': traverse}, index=df_ohlcv.index)

class CompositeSMCTickScore(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Composite score
        score = (df_ohlcv['volume'] / (df_ohlcv['volume'].rolling(20).mean() + 1)) * ((df_ohlcv['close'] - df_ohlcv['open']) / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001))
        return pd.DataFrame({'composite_smc_tick_score': score.fillna(0)}, index=df_ohlcv.index)
