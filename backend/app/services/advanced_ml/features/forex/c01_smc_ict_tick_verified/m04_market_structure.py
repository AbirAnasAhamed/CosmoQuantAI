import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class BOSTickConfirmationRatio(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # BOS Confirmation: Rolling volume / 20-period average volume during a breakout
        roll_vol = tick_vol.rolling(20).mean()
        roll_vol = np.where(roll_vol == 0, 1, roll_vol)
        ratio = tick_vol / roll_vol
        return pd.DataFrame({'bos_tick_confirmation_ratio': ratio.fillna(0)}, index=df_ohlcv.index)

class MSSDisplacementTickMomentum(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Displacement Momentum: (Close - Open) * Volume
        momentum = (df_ohlcv['close'] - df_ohlcv['open']) * tick_vol
        return pd.DataFrame({'mss_displacement_tick_momentum': momentum}, index=df_ohlcv.index)

class DisplacementCandleGiniCoef(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Gini Coef Proxy: Standard Deviation of returns over 10 periods
        returns = df_ohlcv['close'].pct_change().fillna(0)
        gini_proxy = returns.rolling(10).std().fillna(0)
        return pd.DataFrame({'displacement_candle_gini_coef': gini_proxy}, index=df_ohlcv.index)

class FractalBOSTickValidation(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Fractal BOS: Multi-period high/low breakout confirmed by volume
        high_5 = df_ohlcv['high'].rolling(5).max().shift(1)
        low_5 = df_ohlcv['low'].rolling(5).min().shift(1)
        breakout = np.where(df_ohlcv['close'] > high_5, 1, np.where(df_ohlcv['close'] < low_5, -1, 0))
        validation = breakout * tick_vol
        return pd.DataFrame({'fractal_bos_tick_validation': validation}, index=df_ohlcv.index)

class OTETickConfluence(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # OTE (Optimal Trade Entry): Price retracement to 62-79% Fibonacci area
        high_20 = df_ohlcv['high'].rolling(20).max()
        low_20 = df_ohlcv['low'].rolling(20).min()
        range_20 = high_20 - low_20
        range_20 = np.where(range_20 == 0, 0.00001, range_20)
        
        retracement = (df_ohlcv['close'] - low_20) / range_20
        ote = np.where((retracement >= 0.62) & (retracement <= 0.79), tick_vol, 0)
        return pd.DataFrame({'ote_tick_confluence': ote}, index=df_ohlcv.index)
