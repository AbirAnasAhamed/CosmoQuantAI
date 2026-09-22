import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class TOFIDecay(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # TOFI Decay: Exponential moving average of volume changes
        decay = tick_vol.ewm(span=5).mean()
        return pd.DataFrame({'tofi_decay': decay}, index=df_ohlcv.index)

class STBProbability(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # STB Prob: Probability of next tick continuing trend based on rolling sum
        prob = df_ohlcv['close'].pct_change().rolling(3).sum() * tick_vol
        return pd.DataFrame({'stb_probability': prob.fillna(0)}, index=df_ohlcv.index)

class BSLSSLTickTrapRatio(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Tick Trap Ratio
        ratio = (df_ohlcv['high'] - df_ohlcv['close']) / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001) * tick_vol
        return pd.DataFrame({'bsl_ssl_tick_trap_ratio': ratio}, index=df_ohlcv.index)

class TLFVDeviation(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Fair Value Deviation
        ma = df_ohlcv['close'].rolling(10).mean()
        dev = (df_ohlcv['close'] - ma) * tick_vol
        return pd.DataFrame({'tlfv_deviation': dev.fillna(0)}, index=df_ohlcv.index)

class HFMV(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # High-Frequency Mitigation Velocity
        hfmv = tick_vol / (df_ohlcv['high'] - df_ohlcv['low'] + 0.00001)
        return pd.DataFrame({'hfmv': hfmv}, index=df_ohlcv.index)

class TWTA(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Time-Weighted Tick Absorption
        twta = tick_vol.rolling(5).apply(lambda x: np.sum(x * np.arange(1, 6))/15, raw=True)
        return pd.DataFrame({'twta': twta.fillna(0)}, index=df_ohlcv.index)

class StealthMitigationIndex(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Stealth Mitigation: Small price moves, large volume
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        stealth = np.where(body < body.rolling(10).mean(), tick_vol, 0)
        return pd.DataFrame({'stealth_mitigation_index': stealth}, index=df_ohlcv.index)

class TCDAtPDArrays(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Tick Cluster Density
        tcd = tick_vol.rolling(3).sum() / (df_ohlcv['high'].rolling(3).max() - df_ohlcv['low'].rolling(3).min() + 0.00001)
        return pd.DataFrame({'tcd_at_pd_arrays': tcd.fillna(0)}, index=df_ohlcv.index)

class VSTS(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Volume-Synchronized Tick Sequences
        vsts = tick_vol * np.sign(df_ohlcv['close'] - df_ohlcv['open'])
        return pd.DataFrame({'vsts': vsts}, index=df_ohlcv.index)

class IcebergOrderTickFootprint(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Iceberg Proxy: Sustained volume over multiple periods with no price change
        price_change = abs(df_ohlcv['close'].diff())
        iceberg = np.where(price_change < price_change.rolling(10).mean(), tick_vol.rolling(3).sum(), 0)
        return pd.DataFrame({'iceberg_order_tick_footprint': iceberg}, index=df_ohlcv.index)
