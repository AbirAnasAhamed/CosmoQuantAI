import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class TickVolumeFVGMagnitude(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        
        # FVG Magnitude = (Low[i] - High[i-2]) * Volume
        high_shift_2 = df_ohlcv['high'].shift(2)
        low_current = df_ohlcv['low']
        fvg_gap = np.where(low_current > high_shift_2, low_current - high_shift_2, 0)
        
        # Bearish FVG
        low_shift_2 = df_ohlcv['low'].shift(2)
        high_current = df_ohlcv['high']
        fvg_gap_bear = np.where(high_current < low_shift_2, low_shift_2 - high_current, 0)
        
        fvg_magnitude = (fvg_gap + fvg_gap_bear) * tick_vol
        return pd.DataFrame({'tick_volume_fvg_magnitude': fvg_magnitude}, index=df_ohlcv.index)

class FVGFillVelocity(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        
        # Velocity of price movement during FVG creation
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        body = np.where(body == 0, 0.00001, body)
        velocity = tick_vol / body
        
        return pd.DataFrame({'fvg_fill_velocity': velocity}, index=df_ohlcv.index)

class TickImbalanceRatioFVG(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        
        # Imbalance proxy: (High - Low) / Volume
        spread = df_ohlcv['high'] - df_ohlcv['low']
        volume = np.where(tick_vol == 0, 1, tick_vol)
        ratio = spread / volume
        
        return pd.DataFrame({'tick_imbalance_ratio_fvg': ratio}, index=df_ohlcv.index)

class FVGMitigationTickDensity(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Tick Density: Rolling sum of volume over rolling max spread
        roll_vol = tick_vol.rolling(3).sum()
        roll_spread = (df_ohlcv['high'] - df_ohlcv['low']).rolling(3).max()
        roll_spread = np.where(roll_spread == 0, 0.00001, roll_spread)
        density = roll_vol / roll_spread
        return pd.DataFrame({'fvg_mitigation_tick_density': density.fillna(0)}, index=df_ohlcv.index)

class UnmitigatedFVGGravityIndex(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        agg_ticks = self._aggregate_ticks_to_ohlcv(df_ohlcv, df_tick)
        tick_vol = agg_ticks['volume'] if 'volume' in agg_ticks else df_ohlcv['volume']
        tick_count = agg_ticks['tick_count'] if 'tick_count' in agg_ticks else np.ones(len(df_ohlcv))
        tick_delta = agg_ticks['tick_delta'] if 'tick_delta' in agg_ticks else np.zeros(len(df_ohlcv))
        # Gravity Index: Distance from current close to 20-period moving average * volume
        ma_20 = df_ohlcv['close'].rolling(20).mean()
        gravity = abs(df_ohlcv['close'] - ma_20) * tick_vol
        return pd.DataFrame({'unmitigated_fvg_gravity_index': gravity.fillna(0)}, index=df_ohlcv.index)
