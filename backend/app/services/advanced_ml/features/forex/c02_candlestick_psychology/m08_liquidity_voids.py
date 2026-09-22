import pandas as pd
import numpy as np
from .base_feature import BaseCandlePsychologyFeature

class IntraCandleLiquidityVoidTraverse(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        traverse = tick_count / (abs(df_ohlcv['open'] - df_ohlcv['close']) + 0.00001)
        return pd.DataFrame({'intra_candle_liquidity_void_traverse': traverse}, index=df_ohlcv.index)

class MagnetZoneTickAcceleration(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        accel = tick_count.diff() * abs(df_ohlcv['close'].diff())
        return pd.DataFrame({'magnet_zone_tick_acceleration': accel.fillna(0)}, index=df_ohlcv.index)

class ZeroTickSpreadExpansions(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        exp = np.where(tick_count < tick_count.rolling(20).mean() * 0.2, df_ohlcv['high'] - df_ohlcv['low'], 0)
        return pd.DataFrame({'zero_tick_spread_expansions': exp}, index=df_ohlcv.index)

class SlippageProxyIndex(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        
        slip = (df_ohlcv['high'] - df_ohlcv['low']) / (tick_count + 1)
        return pd.DataFrame({'slippage_proxy_index': slip}, index=df_ohlcv.index)

class VoidFillAsymmetry(BaseCandlePsychologyFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        
        asym = np.where(df_ohlcv['close'] > df_ohlcv['open'], tick_vol * 1.5, tick_vol * 0.5)
        return pd.DataFrame({'void_fill_asymmetry': asym}, index=df_ohlcv.index)
