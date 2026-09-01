import numpy as np
import pandas as pd
import pandas_ta as ta
import logging
from typing import Dict

class TickVolumeFeatures:
    """
    Forex ML Intelligence Studio - Category 5: Tick Volume Metrics
    59 Advanced Hedge-Fund Grade Quant Metrics.
    """
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        
        # Ensure required columns exist
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in self.df.columns:
                if col == 'volume':
                    self.df['volume'] = 1.0
                else:
                    raise ValueError(f"Missing required column: {col}")

    def _safe_divide(self, num, den) -> pd.Series:
        """Zero-division safe division that preserves the index."""
        den_arr = np.asarray(den)
        num_arr = np.asarray(num)
        with np.errstate(divide='ignore', invalid='ignore'):
            result = np.where(den_arr == 0, 0.0, num_arr / den_arr)
        return pd.Series(result, index=self.df.index)

    def _z_score(self, series: pd.Series, window: int = 20) -> pd.Series:
        """Rolling Z-Score calculation."""
        roll = series.rolling(window, min_periods=2)
        return self._safe_divide(series - roll.mean(), roll.std())

    def generate_legacy_metrics(self) -> pd.DataFrame:
        """Phase 0: 6 Legacy Retail Metrics"""
        features: Dict[str, pd.Series] = {}
        h, l, c, v = self.df['high'], self.df['low'], self.df['close'], self.df['volume']
        
        # 1. OBV
        try: features['obv'] = ta.obv(c, v)
        except: features['obv'] = 0.0
        
        # 2. Volume SMA
        try: features['volume_sma'] = ta.sma(v, length=20)
        except: features['volume_sma'] = 0.0
        
        # 3. VROC
        try: features['vroc'] = ta.roc(v, length=10)
        except: features['vroc'] = 0.0
        
        # 4. MFI
        try: features['mfi'] = ta.mfi(h, l, c, v, length=14)
        except: features['mfi'] = 50.0
        
        # 5. Force Index
        try: features['force_index'] = (c - c.shift(1)) * v
        except: features['force_index'] = 0.0
        
        # 6. CMF
        try: features['cmf'] = ta.cmf(h, l, c, v, length=20)
        except: features['cmf'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_volume_momentum(self) -> pd.DataFrame:
        """Phase 1: Volume Momentum & Trend"""
        features: Dict[str, pd.Series] = {}
        c, v = self.df['close'], self.df['volume']
        
        # 7. Volume EMA
        try: features['vol_volume_ema'] = ta.ema(v, length=20)
        except: features['vol_volume_ema'] = 0.0
        
        # 8. Volume Oscillator (Fast EMA - Slow EMA of Volume)
        try: features['vol_volume_oscillator'] = ta.ema(v, length=5) - ta.ema(v, length=20)
        except: features['vol_volume_oscillator'] = 0.0
        
        # 9. PVI
        try:
            pvi = ta.pvi(c, v)
            features['vol_pvi'] = pvi[pvi.columns[0]] if isinstance(pvi, pd.DataFrame) else pvi
        except: features['vol_pvi'] = 0.0
        
        # 10. NVI
        try: features['vol_nvi'] = ta.nvi(c, v)
        except: features['vol_nvi'] = 0.0
        
        # 11. VPT (Volume Price Trend)
        try:
            vpt = v * ta.roc(c, length=1) / 100.0
            features['vol_vpt'] = vpt.cumsum()
        except: features['vol_vpt'] = 0.0
        
        # 12. ADI
        try: features['vol_adi'] = ta.ad(self.df['high'], self.df['low'], c, v)
        except: features['vol_adi'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_statistical_anomalies(self) -> pd.DataFrame:
        """Phase 2: Statistical Volume Anomalies"""
        features: Dict[str, pd.Series] = {}
        v = self.df['volume']
        
        # 13. Relative Volume (RVOL)
        try: features['vol_rel_vol'] = self._safe_divide(v, ta.sma(v, length=20))
        except: features['vol_rel_vol'] = 0.0
        
        # 14. Volume Z-Score
        features['vol_volume_z_score'] = self._z_score(v)
        
        # 15-17. Volume StdDev, Skewness, Kurtosis
        try:
            features['vol_volume_std_dev'] = v.rolling(20, min_periods=2).std()
            features['vol_volume_skewness'] = v.rolling(20, min_periods=2).skew()
            features['vol_volume_kurtosis'] = v.rolling(20, min_periods=2).kurt()
        except:
            features['vol_volume_std_dev'] = 0.0
            features['vol_volume_skewness'] = 0.0
            features['vol_volume_kurtosis'] = 0.0
            
        return pd.DataFrame(features, index=self.df.index)

    def generate_demand_supply(self) -> pd.DataFrame:
        """Phase 3: Demand/Supply & Money Flow"""
        features: Dict[str, pd.Series] = {}
        h, l, c, v = self.df['high'], self.df['low'], self.df['close'], self.df['volume']
        
        # 18. KVO
        try:
            kvo = ta.kvo(h, l, c, v)
            features['vol_kvo'] = kvo[kvo.columns[0]]
        except: features['vol_kvo'] = 0.0
        
        # 19. EOM
        try:
            eom = ta.eom(h, l, c, v)
            features['vol_eom'] = eom[eom.columns[0]] if isinstance(eom, pd.DataFrame) else eom
        except: features['vol_eom'] = 0.0
        
        # 20. VWMA
        try: features['vol_vwma'] = ta.vwma(c, v, length=20)
        except: features['vol_vwma'] = 0.0
        
        # 21. VWMA Dist
        features['vol_vwma_dist'] = self._safe_divide(c - features.get('vol_vwma', c), c)
        
        # 22. Rolling VWAP Proxy
        try:
            tp = (h + l + c) / 3
            features['vol_vwap_proxy'] = self._safe_divide((tp * v).rolling(20).sum(), v.rolling(20).sum())
        except: features['vol_vwap_proxy'] = tp
        
        # 23. TWAP Proxy
        try: features['vol_twap_proxy'] = tp.rolling(20).mean()
        except: features['vol_twap_proxy'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_directional_asymmetry(self) -> pd.DataFrame:
        """Phase 4: Directional Volume Asymmetry"""
        features: Dict[str, pd.Series] = {}
        c, o, v = self.df['close'], self.df['open'], self.df['volume']
        
        # 24-25. Up/Down Volume
        up_v = pd.Series(np.where(c > o, v, 0.0), index=v.index)
        down_v = pd.Series(np.where(c < o, v, 0.0), index=v.index)
        features['vol_up_day_volume'] = up_v
        features['vol_down_day_volume'] = down_v
        
        # 26. Asymmetry Ratio (Smoothed)
        up_v_sma = up_v.rolling(14, min_periods=1).mean()
        down_v_sma = down_v.rolling(14, min_periods=1).mean()
        features['vol_volume_asymmetry_ratio'] = self._safe_divide(up_v_sma, up_v_sma + down_v_sma)
        
        # 27. CVD Proxy
        body_spread = (c - o)
        cvd = (body_spread * v).cumsum()
        features['vol_cvd_proxy'] = cvd
        
        # 28. EFI_13
        try: features['vol_efi_13'] = ta.ema((c - c.shift(1)) * v, length=13)
        except: features['vol_efi_13'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_price_volume_divergence(self) -> pd.DataFrame:
        """Phase 5: Price-Volume Divergence"""
        features: Dict[str, pd.Series] = {}
        h, l, c, v = self.df['high'], self.df['low'], self.df['close'], self.df['volume']
        
        # 29. Price vs Volume Trend
        p_mom = ta.mom(c, length=5)
        v_mom = ta.mom(v, length=5)
        features['vol_price_vol_trend'] = p_mom * v_mom
        
        # 30. CLV
        features['vol_clv'] = self._safe_divide((c - l) - (h - c), h - l)
        
        # 31. Efficiency Ratio Vol
        try:
            v_change = (v - v.shift(10)).abs()
            v_volatility = v.diff(1).abs().rolling(10, min_periods=2).sum()
            features['vol_eff_ratio_vol'] = self._safe_divide(v_change, v_volatility)
        except: features['vol_eff_ratio_vol'] = 0.0
        
        # 32. Vortex Vol Adjusted
        try:
            vtx = ta.vortex(h, l, c, length=14)
            vtx_diff = vtx[vtx.columns[0]] - vtx[vtx.columns[1]]
            features['vol_vortex_vol_adjusted'] = vtx_diff * self._safe_divide(v, ta.sma(v, length=14))
        except: features['vol_vortex_vol_adjusted'] = 0.0
        
        # 33. PVO
        try:
            pvo = ta.pvo(v)
            features['vol_pvo'] = pvo[pvo.columns[0]] if isinstance(pvo, pd.DataFrame) else pvo
        except: features['vol_pvo'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_volume_envelopes(self) -> pd.DataFrame:
        """Phase 6: Volume Envelopes & Squeeze"""
        features: Dict[str, pd.Series] = {}
        v = self.df['volume']
        
        # 34-36. Volume BB
        try:
            v_bb = ta.bbands(v, length=20, std=2)
            features['vol_volume_bb_lower'] = v_bb[v_bb.columns[0]]
            features['vol_volume_bb_upper'] = v_bb[v_bb.columns[2]]
            features['vol_volume_bb_width'] = self._safe_divide(features['vol_volume_bb_upper'] - features['vol_volume_bb_lower'], ta.sma(v, length=20))
        except:
            features['vol_volume_bb_lower'] = 0.0
            features['vol_volume_bb_upper'] = 0.0
            features['vol_volume_bb_width'] = 0.0
            
        # 37-38. Volume KC
        try:
            # We construct manual Keltner for volume (SMA +/- ATR proxy of volume)
            v_sma = ta.sma(v, length=20)
            v_atr = v.diff().abs().rolling(20, min_periods=2).mean()
            features['vol_volume_kc_upper'] = v_sma + (2 * v_atr)
            features['vol_volume_kc_lower'] = v_sma - (2 * v_atr)
        except:
            features['vol_volume_kc_upper'] = 0.0
            features['vol_volume_kc_lower'] = 0.0
            
        # 39. Volume Squeeze Proxy
        v_kc_width = features.get('vol_volume_kc_upper', 0) - features.get('vol_volume_kc_lower', 0)
        features['vol_volume_squeeze'] = self._safe_divide(features.get('vol_volume_bb_width', 0) * ta.sma(v, length=20), v_kc_width)
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_vw_advanced(self, legacy: pd.DataFrame) -> pd.DataFrame:
        """Phase 7: Volume-Weighted Advanced Indicators (VWI)"""
        features: Dict[str, pd.Series] = {}
        c, v = self.df['close'], self.df['volume']
        
        # 40-42. VWMACD
        try:
            vwma_fast = ta.vwma(c, v, length=12)
            vwma_slow = ta.vwma(c, v, length=26)
            features['vol_vwmacd'] = vwma_fast - vwma_slow
            features['vol_vwmacd_signal'] = ta.ema(features['vol_vwmacd'], length=9)
            features['vol_vwmacd_hist'] = features['vol_vwmacd'] - features['vol_vwmacd_signal']
        except:
            features['vol_vwmacd'] = 0.0
            features['vol_vwmacd_signal'] = 0.0
            features['vol_vwmacd_hist'] = 0.0
            
        # 43. StochMFI
        mfi = legacy.get('mfi', pd.Series(50, index=c.index))
        mfi_min = mfi.rolling(14, min_periods=2).min()
        mfi_max = mfi.rolling(14, min_periods=2).max()
        features['vol_mfi_stochastic'] = self._safe_divide(mfi - mfi_min, mfi_max - mfi_min) * 100.0
        
        # 44. Price ROC / Vol ROC Ratio
        p_roc = ta.roc(c, length=10)
        v_roc = ta.roc(v, length=10)
        features['vol_price_roc_vol_roc_ratio'] = self._safe_divide(p_roc, v_roc)
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_log_normal_extremes(self, legacy: pd.DataFrame) -> pd.DataFrame:
        """Phase 8: Log-Normal Statistical Extremes"""
        features: Dict[str, pd.Series] = {}
        v = self.df['volume']
        obv = legacy.get('obv', pd.Series(0, index=v.index))
        mfi = legacy.get('mfi', pd.Series(50, index=v.index))
        cmf = legacy.get('cmf', pd.Series(0, index=v.index))
        
        # 45-46. Log Volume
        log_v = np.log(v + 1.0)
        features['vol_log_volume'] = log_v
        features['vol_log_volume_z_score'] = self._z_score(log_v)
        
        # 47-49. OBV Dynamics
        features['vol_obv_z_score'] = self._z_score(obv)
        features['vol_obv_acceleration'] = obv.diff(1).diff(1)
        obv_sma = ta.sma(obv, length=20)
        features['vol_obv_sma_crossover'] = self._safe_divide(obv - obv_sma, obv_sma.abs() + 1e-9)
        
        # 50-52. MFI & CMF Z-Scores & Momentum
        features['vol_mfi_z_score'] = self._z_score(mfi)
        features['vol_cmf_z_score'] = self._z_score(cmf)
        features['vol_cmf_momentum'] = ta.mom(cmf, length=5)
        
        # 53. Tick Volume Fractal Dimension Proxy
        v_sum = v.rolling(20, min_periods=2).sum()
        features['vol_tick_volume_fractal_dimension'] = self._safe_divide(np.log(v_sum), np.log(pd.Series(20.0, index=v.index)))
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_pressure_oscillators(self) -> pd.DataFrame:
        """Phase 9: Buying & Selling Pressure"""
        features: Dict[str, pd.Series] = {}
        h, l, c, v = self.df['high'], self.df['low'], self.df['close'], self.df['volume']
        
        # 54-56. True Pressure
        bp = (c - l) * v
        sp = (h - c) * v
        features['vol_buying_pressure'] = bp
        features['vol_selling_pressure'] = sp
        
        bp_sma = ta.sma(bp, length=14)
        sp_sma = ta.sma(sp, length=14)
        features['vol_net_pressure_oscillator'] = self._safe_divide(bp_sma - sp_sma, bp_sma + sp_sma)
        
        # 57-58. Volume ROCs
        features['vol_volume_roc_10'] = ta.roc(v, length=10)
        features['vol_volume_roc_20'] = ta.roc(v, length=20)
        
        # 59. Macro VWAP Proxy
        tp = (h + l + c) / 3.0
        features['vol_mtf_vwap_proxy'] = self._safe_divide((tp * v).rolling(100, min_periods=2).sum(), v.rolling(100, min_periods=2).sum())
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_all_features(self) -> pd.DataFrame:
        """Execute all phases and combine"""
        p0 = self.generate_legacy_metrics()
        p1 = self.generate_volume_momentum()
        p2 = self.generate_statistical_anomalies()
        p3 = self.generate_demand_supply()
        p4 = self.generate_directional_asymmetry()
        p5 = self.generate_price_volume_divergence()
        p6 = self.generate_volume_envelopes()
        p7 = self.generate_vw_advanced(p0)
        p8 = self.generate_log_normal_extremes(p0)
        p9 = self.generate_pressure_oscillators()
        
        # Concatenate all 10 phases
        all_features = pd.concat([p0, p1, p2, p3, p4, p5, p6, p7, p8, p9], axis=1)
        
        # Ensure 100% Neural Network Safety (No NaNs, No Infs)
        all_features = all_features.replace([np.inf, -np.inf], np.nan)
        all_features = all_features.ffill().fillna(0.0)
        
        # Protect against Gradient Explosions (Safety Clamp)
        all_features = all_features.clip(-1000.0, 1000.0)
        
        return all_features

    @staticmethod
    def calculate_all(df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Graceful Degradation Wrapper. 
        Returns original df concatenated with the new 59 features.
        """
        df_safe = df_raw.copy()
        try:
            extractor = TickVolumeFeatures(df_safe)
            new_features = extractor.generate_all_features()
            
            # Prevent duplicate column concatenation
            cols_to_use = new_features.columns.difference(df_safe.columns)
            result = pd.concat([df_safe, new_features[cols_to_use]], axis=1)
            return result
        except Exception as e:
            logging.error(f"Error calculating Tick Volume Features: {e}")
            return df_raw
