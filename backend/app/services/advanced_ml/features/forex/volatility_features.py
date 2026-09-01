import numpy as np
import pandas as pd
import pandas_ta as ta
import logging
from typing import Dict

class VolatilityFeatures:
    """
    Forex ML Intelligence Studio - Category 4: Volatility Indicators
    74 Advanced Hedge-Fund Grade Quant Metrics.
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
        roll = series.rolling(window)
        return self._safe_divide(series - roll.mean(), roll.std())

    def generate_legacy_metrics(self) -> pd.DataFrame:
        """Phase 0: 12 Legacy Retail Metrics"""
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']
        
        features: Dict[str, pd.Series] = {}
        
        # 1. TR
        try: features['true_range'] = ta.true_range(high, low, close)
        except: features['true_range'] = 0.0
        
        # 2. ATR
        try: features['atr'] = ta.atr(high, low, close, length=14)
        except: features['atr'] = 0.0
        
        # 3-6. Bollinger Bands
        try:
            bb = ta.bbands(close, length=20, std=2)
            features['bb_lower'] = bb[bb.columns[0]]
            features['bb_upper'] = bb[bb.columns[2]]
            features['bb_width'] = bb[bb.columns[3]]
            features['bb_pct_b'] = bb[bb.columns[4]]
        except:
            for col in ['bb_lower', 'bb_upper', 'bb_width', 'bb_pct_b']: features[col] = 0.0
            
        # 7-8. Keltner Channels
        try:
            kc = ta.kc(high, low, close, length=20)
            features['keltner_lower'] = kc[kc.columns[0]]
            features['keltner_upper'] = kc[kc.columns[2]]
        except:
            features['keltner_lower'], features['keltner_upper'] = 0.0, 0.0
            
        # 9-10. Donchian Channels
        try:
            dc = ta.donchian(high, low, lower_length=20, upper_length=20)
            features['donchian_lower'] = dc[dc.columns[0]]
            features['donchian_upper'] = dc[dc.columns[2]]
        except:
            features['donchian_lower'], features['donchian_upper'] = 0.0, 0.0
            
        # 11. Historical Volatility
        try:
            log_ret = ta.log_return(close)
            features['historical_volatility'] = log_ret.rolling(20).std() * np.sqrt(252) # Annualized
        except: features['historical_volatility'] = 0.0
        
        # 12. Choppiness Index
        try: features['choppiness_index'] = ta.chop(high, low, close, length=14)
        except: features['choppiness_index'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_stationary_distances(self, legacy: pd.DataFrame) -> pd.DataFrame:
        """Phase 1: Stationary Band Distances"""
        close = self.df['close']
        features: Dict[str, pd.Series] = {}
        
        # 13-14. BB Distances
        features['vol_bb_upper_dist'] = self._safe_divide(legacy.get('bb_upper', 0) - close, close)
        features['vol_bb_lower_dist'] = self._safe_divide(close - legacy.get('bb_lower', 0), close)
        
        # 15. BB %B Z-Score
        features['vol_bb_pct_b_z_score'] = self._z_score(legacy.get('bb_pct_b', pd.Series(0, index=close.index)))
        
        # 16-18. KC Distances
        kc_upper = legacy.get('keltner_upper', pd.Series(0, index=close.index))
        kc_lower = legacy.get('keltner_lower', pd.Series(0, index=close.index))
        kc_mid = (kc_upper + kc_lower) / 2
        
        features['vol_kc_upper_dist'] = self._safe_divide(kc_upper - close, close)
        features['vol_kc_lower_dist'] = self._safe_divide(close - kc_lower, close)
        features['vol_kc_mid_dist'] = self._safe_divide(kc_mid - close, close)
        
        # 19-21. Donchian Distances & Expansion
        dc_upper = legacy.get('donchian_upper', pd.Series(0, index=close.index))
        dc_lower = legacy.get('donchian_lower', pd.Series(0, index=close.index))
        dc_width = dc_upper - dc_lower
        
        features['vol_dc_upper_dist'] = self._safe_divide(dc_upper - close, close)
        features['vol_dc_lower_dist'] = self._safe_divide(close - dc_lower, close)
        features['vol_dc_width_roc'] = ta.roc(dc_width, length=5).fillna(0.0)
        
        # 22-23. Acceleration Bands
        try:
            acc = ta.accbands(self.df['high'], self.df['low'], close, length=20)
            features['vol_accband_lower_dist'] = self._safe_divide(close - acc[acc.columns[0]], close)
            features['vol_accband_upper_dist'] = self._safe_divide(acc[acc.columns[2]] - close, close)
        except:
            features['vol_accband_lower_dist'] = 0.0
            features['vol_accband_upper_dist'] = 0.0
            
        return pd.DataFrame(features, index=self.df.index)

    def generate_atr_derivatives(self, legacy: pd.DataFrame) -> pd.DataFrame:
        """Phase 2: ATR & True Range Derivatives"""
        features: Dict[str, pd.Series] = {}
        atr = legacy.get('atr', pd.Series(0, index=self.df.index))
        tr = legacy.get('true_range', pd.Series(0, index=self.df.index))
        
        # 24-25. ATR Velocity & Accel
        features['vol_atr_velocity'] = atr.diff(1).fillna(0.0)
        features['vol_atr_acceleration'] = features['vol_atr_velocity'].diff(1).fillna(0.0)
        
        # 26. ATR Ratio 14/50
        try:
            atr_50 = ta.atr(self.df['high'], self.df['low'], self.df['close'], length=50)
            features['vol_atr_ratio_14_50'] = self._safe_divide(atr, atr_50)
        except: features['vol_atr_ratio_14_50'] = 0.0
        
        # 27. NATR
        try: features['vol_natr'] = ta.natr(self.df['high'], self.df['low'], self.df['close'])
        except: features['vol_natr'] = 0.0
        
        # 28. TR Z-Score
        features['vol_tr_z_score'] = self._z_score(tr)
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_squeeze_dynamics(self, legacy: pd.DataFrame) -> pd.DataFrame:
        """Phase 3: Squeeze & Standard Deviation Dynamics"""
        features: Dict[str, pd.Series] = {}
        close = self.df['close']
        
        bb_width = legacy.get('bb_width', pd.Series(0, index=close.index))
        kc_upper = legacy.get('keltner_upper', pd.Series(1, index=close.index))
        kc_lower = legacy.get('keltner_lower', pd.Series(0, index=close.index))
        kc_width = kc_upper - kc_lower
        
        # 29-30. Squeeze Proxy & True TTM Squeeze Momentum
        features['vol_bb_kc_squeeze_ratio'] = self._safe_divide(bb_width, kc_width)
        
        try:
            sqz = ta.squeeze(self.df['high'], self.df['low'], close)
            # First column of ta.squeeze is the momentum histogram
            features['vol_squeeze_momentum'] = sqz[sqz.columns[0]].fillna(0.0)
        except: features['vol_squeeze_momentum'] = 0.0
        
        # 31. DC Width Z-Score
        dc_width = legacy.get('donchian_upper', pd.Series(0, index=close.index)) - legacy.get('donchian_lower', pd.Series(0, index=close.index))
        features['vol_dc_width_z_score'] = self._z_score(dc_width)
            
        # 32-33. StdDev Dynamics
        try:
            std_dev = close.rolling(20).std()
            features['vol_std_dev_velocity'] = std_dev.diff(1).fillna(0.0)
            features['vol_std_dev_acceleration'] = features['vol_std_dev_velocity'].diff(1).fillna(0.0)
        except:
            features['vol_std_dev_velocity'] = 0.0
            features['vol_std_dev_acceleration'] = 0.0
            
        return pd.DataFrame(features, index=self.df.index)

    def generate_hedge_fund_estimators(self) -> pd.DataFrame:
        """Phase 4: Advanced Hedge-Fund Estimators"""
        features: Dict[str, pd.Series] = {}
        o, h, l, c = self.df['open'], self.df['high'], self.df['low'], self.df['close']
        
        # 34. Yang-Zhang Proxy (Simplified robust approximation)
        try:
            log_ho = np.log(self._safe_divide(h, o))
            log_lo = np.log(self._safe_divide(l, o))
            log_co = np.log(self._safe_divide(c, o))
            log_oc_prev = np.log(self._safe_divide(o, c.shift(1)))
            rs_vol = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
            open_vol = log_oc_prev ** 2
            close_vol = log_co ** 2
            features['vol_yang_zhang'] = np.sqrt(open_vol.rolling(20).mean() + 0.164 * close_vol.rolling(20).mean() + 0.836 * rs_vol.rolling(20).mean()).fillna(0.0)
        except: features['vol_yang_zhang'] = 0.0
        
        # 35. Garman-Klass
        try:
            gk = 0.5 * (np.log(self._safe_divide(h, l)) ** 2) - (2 * np.log(2) - 1) * (np.log(self._safe_divide(c, o)) ** 2)
            features['vol_garman_klass'] = np.sqrt(gk.rolling(20).mean()).fillna(0.0)
        except: features['vol_garman_klass'] = 0.0
        
        # 36. Parkinson
        try:
            park = (1.0 / (4.0 * np.log(2.0))) * (np.log(self._safe_divide(h, l)) ** 2)
            features['vol_parkinson'] = np.sqrt(park.rolling(20).mean()).fillna(0.0)
        except: features['vol_parkinson'] = 0.0
        
        # 37. Hodges-Tompkins (Proxy via overlapping log returns variance)
        try:
            features['vol_hodges_tompkins'] = ta.stdev(ta.log_return(c), length=20).fillna(0.0)
        except: features['vol_hodges_tompkins'] = 0.0
        
        # 38. Ulcer Index
        try: features['vol_ulcer_index'] = ta.ui(c, length=14).fillna(0.0)
        except: features['vol_ulcer_index'] = 0.0
        
        # 39. Mass Index
        try: features['vol_mass_index'] = ta.massi(h, l, fast=9, slow=25).fillna(0.0)
        except: features['vol_mass_index'] = 0.0
        
        # 40. RVI (Relative Volatility Index)
        try:
            rvi = ta.rvi(c, h, l, length=14)
            features['vol_rvi_volatility'] = rvi if isinstance(rvi, pd.Series) else rvi[rvi.columns[0]]
        except: features['vol_rvi_volatility'] = 0.0
        
        # 41. HV Ratio 10/30
        try:
            hv10 = ta.stdev(ta.log_return(c), length=10)
            hv30 = ta.stdev(ta.log_return(c), length=30)
            features['vol_hv_ratio_10_30'] = self._safe_divide(hv10, hv30)
        except: features['vol_hv_ratio_10_30'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_vortex_statistical(self, legacy: pd.DataFrame) -> pd.DataFrame:
        """Phase 5: Vortex & Statistical Extremes"""
        features: Dict[str, pd.Series] = {}
        h, l, c = self.df['high'], self.df['low'], self.df['close']
        atr = legacy.get('atr', pd.Series(0, index=c.index))
        
        # 42-44. Vortex Indicator
        try:
            vtx = ta.vortex(h, l, c, length=14)
            features['vol_vortex_pos'] = vtx[vtx.columns[0]]
            features['vol_vortex_neg'] = vtx[vtx.columns[1]]
            features['vol_vortex_diff'] = features['vol_vortex_pos'] - features['vol_vortex_neg']
        except:
            features['vol_vortex_pos'] = 0.0
            features['vol_vortex_neg'] = 0.0
            features['vol_vortex_diff'] = 0.0
            
        # 45-46. ATR Skewness & Kurtosis
        try:
            features['vol_atr_skewness'] = atr.rolling(20).skew().fillna(0.0)
            features['vol_atr_kurtosis'] = atr.rolling(20).kurt().fillna(0.0)
        except:
            features['vol_atr_skewness'] = 0.0
            features['vol_atr_kurtosis'] = 0.0
            
        # 47-48. Chandelier Exits Distances
        try:
            chd = ta.chandelier_exit(h, l, c, length=22, mult=3.0)
            chd_long = chd[chd.columns[0]]
            chd_short = chd[chd.columns[1]]
            features['vol_chandelier_long_dist'] = self._safe_divide(c - chd_long, c)
            features['vol_chandelier_short_dist'] = self._safe_divide(chd_short - c, c)
        except:
            features['vol_chandelier_long_dist'] = 0.0
            features['vol_chandelier_short_dist'] = 0.0
            
        return pd.DataFrame(features, index=self.df.index)

    def generate_mtf_dsp_envelopes(self, legacy: pd.DataFrame) -> pd.DataFrame:
        """Phase 6: MTF & DSP Envelopes"""
        features: Dict[str, pd.Series] = {}
        c = self.df['close']
        atr = legacy.get('atr', pd.Series(0, index=c.index))
        
        # 49. MTF ATR Proxy
        try: features['vol_mtf_atr_proxy'] = ta.sma(atr, length=50).fillna(0.0)
        except: features['vol_mtf_atr_proxy'] = 0.0
        
        # 50-52. Holt-Winter Channel
        try:
            hwc = ta.hwc(c)
            # Typically HWC has 3 cols. Wait, the docs say it has 3 columns but the exact names may vary.
            # We'll robustly grab mid, upper, lower. Mid is 0, Upper is 1, Lower is 2 if 3 columns exist.
            hwc_lower = hwc.iloc[:, -1] if len(hwc.columns) >= 3 else hwc.iloc[:, 0]
            hwc_upper = hwc.iloc[:, 1] if len(hwc.columns) >= 2 else hwc.iloc[:, 0]
            
            features['vol_hw_channel_lower_dist'] = self._safe_divide(c - hwc_lower, c)
            features['vol_hw_channel_upper_dist'] = self._safe_divide(hwc_upper - c, c)
            features['vol_hw_channel_width'] = self._safe_divide(hwc_upper - hwc_lower, c)
        except:
            features['vol_hw_channel_lower_dist'] = 0.0
            features['vol_hw_channel_upper_dist'] = 0.0
            features['vol_hw_channel_width'] = 0.0
            
        # 53-54. STARC Bands Proxy (SMA + 2*ATR)
        try:
            sma = ta.sma(c, length=15)
            starc_upper = sma + (2 * atr)
            starc_lower = sma - (2 * atr)
            features['vol_starbands_upper_dist'] = self._safe_divide(starc_upper - c, c)
            features['vol_starbands_lower_dist'] = self._safe_divide(c - starc_lower, c)
        except:
            features['vol_starbands_upper_dist'] = 0.0
            features['vol_starbands_lower_dist'] = 0.0
            
        # 55-56. KAMA-ATR Bands
        try:
            kama = ta.kama(c, length=10)
            kama_upper = kama + (1.5 * atr)
            kama_lower = kama - (1.5 * atr)
            features['vol_kama_atr_upper_dist'] = self._safe_divide(kama_upper - c, c)
            features['vol_kama_atr_lower_dist'] = self._safe_divide(c - kama_lower, c)
        except:
            features['vol_kama_atr_upper_dist'] = 0.0
            features['vol_kama_atr_lower_dist'] = 0.0
            
        return pd.DataFrame(features, index=self.df.index)

    def generate_asymmetric_volatility(self, legacy: pd.DataFrame) -> pd.DataFrame:
        """Phase 7: Asymmetric Volatility"""
        features: Dict[str, pd.Series] = {}
        c, o = self.df['close'], self.df['open']
        tr = legacy.get('true_range', pd.Series(0, index=c.index))
        ret = c.diff(1)
        
        # 57-59. Asymmetric TR
        up_tr = pd.Series(np.where(c > o, tr, 0.0), index=c.index)
        down_tr = pd.Series(np.where(c < o, tr, 0.0), index=c.index)
        features['vol_up_day_tr'] = up_tr
        features['vol_down_day_tr'] = down_tr
        
        # Smooth the TR to get a meaningful ratio instead of binary 0/1
        up_tr_sma = up_tr.rolling(14, min_periods=1).mean()
        down_tr_sma = down_tr.rolling(14, min_periods=1).mean()
        features['vol_tr_asymmetry_ratio'] = self._safe_divide(up_tr_sma, up_tr_sma + down_tr_sma)
        
        # 60-62. Asymmetric StdDev
        try:
            up_ret = pd.Series(np.where(ret > 0, ret, np.nan), index=c.index)
            down_ret = pd.Series(np.where(ret < 0, ret, np.nan), index=c.index)
            # Use min_periods=2 because NaNs will make the default rolling(20) evaluate to NaN everywhere
            features['vol_std_dev_up'] = up_ret.rolling(20, min_periods=2).std().fillna(0.0)
            features['vol_std_dev_down'] = down_ret.rolling(20, min_periods=2).std().fillna(0.0)
            features['vol_std_dev_asymmetry'] = features['vol_std_dev_up'] - features['vol_std_dev_down']
        except:
            features['vol_std_dev_up'] = 0.0
            features['vol_std_dev_down'] = 0.0
            features['vol_std_dev_asymmetry'] = 0.0
            
        return pd.DataFrame(features, index=self.df.index)

    def generate_high_low_dsp(self, legacy: pd.DataFrame) -> pd.DataFrame:
        """Phase 8: High-Low Spread & DSP"""
        features: Dict[str, pd.Series] = {}
        o, h, l, c = self.df['open'], self.df['high'], self.df['low'], self.df['close']
        atr = legacy.get('atr', pd.Series(0, index=c.index))
        
        # 63. Fractal Dimension Index (Proxy)
        try:
            tr_sum = legacy.get('true_range', pd.Series(0.0001, index=c.index)).rolling(20).sum()
            features['vol_fractal_dimension_proxy'] = self._safe_divide(np.log(tr_sum), np.log(pd.Series(20, index=c.index)))
        except: features['vol_fractal_dimension_proxy'] = 0.0
        
        # 64. Choppiness Z-Score
        features['vol_choppiness_z_score'] = self._z_score(legacy.get('choppiness_index', pd.Series(0, index=c.index)))
        
        # 65. Ehlers ATR (EMA smoothed ATR)
        try: features['vol_ehlers_atr'] = ta.ema(atr, length=5).fillna(0.0)
        except: features['vol_ehlers_atr'] = 0.0
        
        # 66. StdDev Log
        try:
            std_dev = c.rolling(20).std()
            features['vol_std_dev_log'] = np.log(std_dev + 1e-9).fillna(0.0)
        except: features['vol_std_dev_log'] = 0.0
        
        # 67-68. HL Spread
        hl_spread = h - l
        features['vol_hl_spread'] = hl_spread
        features['vol_hl_spread_z_score'] = self._z_score(hl_spread)
        
        # 69-70. Body & Range Ratios
        body = (c - o).abs()
        features['vol_open_close_spread'] = body
        features['vol_body_to_range_ratio'] = self._safe_divide(body, hl_spread)
        
        # 71. Volatility Breakout Proxy (Expansion Outside Bar)
        features['vol_volatility_breakout_proxy'] = np.where((h > h.shift(1)) & (l < l.shift(1)), 1.0, 0.0)
        
        # 72-74. Price BB Z-Scores
        try:
            bb = ta.bbands(c, length=20, std=2)
            bb_lower, bb_mid, bb_upper = bb[bb.columns[0]], bb[bb.columns[1]], bb[bb.columns[2]]
            features['vol_price_bb_upper_z_score'] = self._z_score(c - bb_upper)
            features['vol_price_bb_lower_z_score'] = self._z_score(c - bb_lower)
            features['vol_price_bb_mid_z_score'] = self._z_score(c - bb_mid)
        except:
            features['vol_price_bb_upper_z_score'] = 0.0
            features['vol_price_bb_lower_z_score'] = 0.0
            features['vol_price_bb_mid_z_score'] = 0.0
            
        return pd.DataFrame(features, index=self.df.index)

    def generate_all_features(self) -> pd.DataFrame:
        """Execute all phases and combine"""
        p0 = self.generate_legacy_metrics()
        p1 = self.generate_stationary_distances(p0)
        p2 = self.generate_atr_derivatives(p0)
        p3 = self.generate_squeeze_dynamics(p0)
        p4 = self.generate_hedge_fund_estimators()
        p5 = self.generate_vortex_statistical(p0)
        p6 = self.generate_mtf_dsp_envelopes(p0)
        p7 = self.generate_asymmetric_volatility(p0)
        p8 = self.generate_high_low_dsp(p0)
        
        # Concatenate all 9 phases
        all_features = pd.concat([p0, p1, p2, p3, p4, p5, p6, p7, p8], axis=1)
        
        # Ensure 100% Neural Network Safety (No NaNs, No Infs)
        all_features = all_features.replace([np.inf, -np.inf], np.nan)
        all_features = all_features.ffill().fillna(0.0)
        
        # Protect against Gradient Explosions (e.g., Holt-Winter mathematical instability)
        # Most indicators are percentages or index values (0-100), so clamping at -1000 to 1000 is 100% safe
        all_features = all_features.clip(-1000.0, 1000.0)
        
        return all_features

    @staticmethod
    def calculate_all(df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Graceful Degradation Wrapper. 
        Returns original df concatenated with the new 74 features.
        """
        df_safe = df_raw.copy()
        try:
            extractor = VolatilityFeatures(df_safe)
            new_features = extractor.generate_all_features()
            
            # Prevent duplicate column concatenation
            cols_to_use = new_features.columns.difference(df_safe.columns)
            result = pd.concat([df_safe, new_features[cols_to_use]], axis=1)
            return result
        except Exception as e:
            logging.error(f"Error calculating Volatility Features: {e}")
            return df_raw
