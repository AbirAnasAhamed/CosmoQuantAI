import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class TOFIDecay(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # TOFI Decay: Exponential moving average of volume changes
        decay = df_ohlcv['volume'].ewm(span=5).mean()
        return pd.DataFrame({'tofi_decay': decay}, index=df_ohlcv.index)

class STBProbability(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # STB Prob: Probability of next tick continuing trend based on rolling sum
        prob = df_ohlcv['close'].pct_change().rolling(3).sum() * df_ohlcv['volume']
        return pd.DataFrame({'stb_probability': prob.fillna(0)}, index=df_ohlcv.index)

class BSLSSLTickTrapRatio(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Tick Trap Ratio
        ratio = (df_ohlcv['high'] - df_ohlcv['close']) / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001) * df_ohlcv['volume']
        return pd.DataFrame({'bsl_ssl_tick_trap_ratio': ratio}, index=df_ohlcv.index)

class TLFVDeviation(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Fair Value Deviation
        ma = df_ohlcv['close'].rolling(10).mean()
        dev = (df_ohlcv['close'] - ma) * df_ohlcv['volume']
        return pd.DataFrame({'tlfv_deviation': dev.fillna(0)}, index=df_ohlcv.index)

class HFMV(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # High-Frequency Mitigation Velocity
        hfmv = df_ohlcv['volume'] / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001)
        return pd.DataFrame({'hfmv': hfmv}, index=df_ohlcv.index)

class TWTA(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Time-Weighted Tick Absorption
        twta = df_ohlcv['volume'].rolling(5).apply(lambda x: np.sum(x * np.arange(1, 6))/15, raw=True)
        return pd.DataFrame({'twta': twta.fillna(0)}, index=df_ohlcv.index)

class StealthMitigationIndex(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Stealth Mitigation: Small price moves, large volume
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        stealth = np.where(body < body.rolling(10).mean(), df_ohlcv['volume'], 0)
        return pd.DataFrame({'stealth_mitigation_index': stealth}, index=df_ohlcv.index)

class TCDAtPDArrays(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Tick Cluster Density
        tcd = df_ohlcv['volume'].rolling(3).sum() / (df_ohlcv['high'].rolling(3).max() - df_ohlcv['low'].rolling(3).min() + 0.00001)
        return pd.DataFrame({'tcd_at_pd_arrays': tcd.fillna(0)}, index=df_ohlcv.index)

class VSTS(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Volume-Synchronized Tick Sequences
        vsts = df_ohlcv['volume'] * np.sign(df_ohlcv['close'] - df_ohlcv['open'])
        return pd.DataFrame({'vsts': vsts}, index=df_ohlcv.index)

class IcebergOrderTickFootprint(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Iceberg Proxy: Sustained volume over multiple periods with no price change
        price_change = abs(df_ohlcv['close'].diff())
        iceberg = np.where(price_change < price_change.rolling(10).mean(), df_ohlcv['volume'].rolling(3).sum(), 0)
        return pd.DataFrame({'iceberg_order_tick_footprint': iceberg}, index=df_ohlcv.index)
