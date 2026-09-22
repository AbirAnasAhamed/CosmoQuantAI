import pandas as pd
import numpy as np
from .base_feature import BaseTickVerifiedFeature

class TickVolumeFVGMagnitude(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        
        # FVG Magnitude = (Low[i] - High[i-2]) * Volume
        high_shift_2 = df_ohlcv['high'].shift(2)
        low_current = df_ohlcv['low']
        fvg_gap = np.where(low_current > high_shift_2, low_current - high_shift_2, 0)
        
        # Bearish FVG
        low_shift_2 = df_ohlcv['low'].shift(2)
        high_current = df_ohlcv['high']
        fvg_gap_bear = np.where(high_current < low_shift_2, low_shift_2 - high_current, 0)
        
        fvg_magnitude = (fvg_gap + fvg_gap_bear) * df_ohlcv['volume']
        return pd.DataFrame({'tick_volume_fvg_magnitude': fvg_magnitude}, index=df_ohlcv.index)

class FVGFillVelocity(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        
        # Velocity of price movement during FVG creation
        body = abs(df_ohlcv['close'] - df_ohlcv['open'])
        body = np.where(body == 0, 0.00001, body)
        velocity = df_ohlcv['volume'] / body
        
        return pd.DataFrame({'fvg_fill_velocity': velocity}, index=df_ohlcv.index)

class TickImbalanceRatioFVG(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        
        # Imbalance proxy: (High - Low) / Volume
        spread = df_ohlcv['high'] - df_ohlcv['low']
        volume = np.where(df_ohlcv['volume'] == 0, 1, df_ohlcv['volume'])
        ratio = spread / volume
        
        return pd.DataFrame({'tick_imbalance_ratio_fvg': ratio}, index=df_ohlcv.index)

class FVGMitigationTickDensity(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Tick Density: Rolling sum of volume over rolling max spread
        roll_vol = df_ohlcv['volume'].rolling(3).sum()
        roll_spread = (df_ohlcv['high'] - df_ohlcv['low']).rolling(3).max()
        roll_spread = np.where(roll_spread == 0, 0.00001, roll_spread)
        density = roll_vol / roll_spread
        return pd.DataFrame({'fvg_mitigation_tick_density': density.fillna(0)}, index=df_ohlcv.index)

class UnmitigatedFVGGravityIndex(BaseTickVerifiedFeature):
    def calculate(self, df_ohlcv: pd.DataFrame, df_tick: pd.DataFrame, **kwargs) -> pd.DataFrame:
        self._validate_inputs(df_ohlcv, df_tick)
        # Gravity Index: Distance from current close to 20-period moving average * volume
        ma_20 = df_ohlcv['close'].rolling(20).mean()
        gravity = abs(df_ohlcv['close'] - ma_20) * df_ohlcv['volume']
        return pd.DataFrame({'unmitigated_fvg_gravity_index': gravity.fillna(0)}, index=df_ohlcv.index)
