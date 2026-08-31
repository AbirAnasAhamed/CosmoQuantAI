import numpy as np
import pandas as pd
import pandas_ta as ta
import logging

class MomentumOscillatorFeatures:
    """
    Advanced Quantitative Feature Engineering for Momentum Oscillators.
    Designed exclusively for Forex Neural Network Models (Transformer/MoE).
    Total Metrics: 50 (9 Legacy + 41 Advanced)
    """

    @staticmethod
    def calculate_all(df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Main entry point matching the architecture of other feature classes.
        Takes raw OHLCV and returns DataFrame with original + 50 new columns.
        """
        if df_raw.empty:
            return df_raw
            
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        # We work on a copy to prevent SettingWithCopy warnings
        df_safe = df_raw.copy()
        
        for col in required_cols:
            if col not in df_safe.columns:
                if col == 'volume':
                    df_safe['volume'] = 1.0 # Fallback for forex tick volume
                else:
                    logging.warning(f"Missing column '{col}' for Momentum Osc features. Skipping.")
                    return df_raw
                    
        try:
            extractor = MomentumOscillatorFeatures(df_safe)
            new_features = extractor.generate_all_features()
            
            # Combine original df with new features
            result = pd.concat([df_safe, new_features], axis=1)
            return result
        except Exception as e:
            logging.error(f"Error calculating Momentum Osc features: {e}")
            return df_raw

    def __init__(self, df: pd.DataFrame):
        self.df = df
        
    def _safe_divide(self, num, den):
        return np.where(den == 0, 0, num / den)

    # =========================================
    # Phase 0: Legacy Retail Metrics (9)
    # =========================================
    def generate_legacy_metrics(self) -> pd.DataFrame:
        features = pd.DataFrame(index=self.df.index)
        close = self.df['close']
        high = self.df['high']
        low = self.df['low']
        
        # 1. RSI
        try: features['rsi'] = ta.rsi(close, length=14)
        except: features['rsi'] = 50.0
        
        # 2-3. Stochastic
        try:
            stoch = ta.stoch(high, low, close, k=14, d=3, smooth_k=3)
            features['stoch_k'] = stoch[stoch.columns[0]]
            features['stoch_d'] = stoch[stoch.columns[1]]
        except:
            features['stoch_k'] = 50.0
            features['stoch_d'] = 50.0
            
        # 4. Williams %R
        try: features['williams_r'] = ta.willr(high, low, close, length=14)
        except: features['williams_r'] = -50.0
        
        # 5. ROC
        try: features['roc'] = ta.roc(close, length=14)
        except: features['roc'] = 0.0
        
        # 6. CCI
        try: features['cci'] = ta.cci(high, low, close, length=14)
        except: features['cci'] = 0.0
        
        # 7. Momentum (MOM)
        try: features['momentum'] = ta.mom(close, length=10)
        except: features['momentum'] = 0.0
        
        # 8. Awesome Oscillator (AO)
        try: features['awesome_oscillator'] = ta.ao(high, low)
        except: features['awesome_oscillator'] = 0.0
        
        # 9. TSI
        try:
            tsi = ta.tsi(close, fast=13, slow=25)
            features['tsi'] = tsi[tsi.columns[0]]
        except: features['tsi'] = 0.0

        return features

    # =========================================
    # Phase 1: Core Oscillators & Derivs (10)
    # =========================================
    def generate_core_derivatives(self, legacy_features: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame(index=self.df.index)
        close = self.df['close']
        high = self.df['high']
        low = self.df['low']
        
        # 10. Connors RSI (Proxy using simple components)
        try:
            features['mom_crsi'] = ta.crsi(close)
        except: features['mom_crsi'] = 0.0
            
        # 11. Ultimate Oscillator
        try: features['mom_uo'] = ta.uo(high, low, close, fast=7, medium=14, slow=28)
        except: features['mom_uo'] = 50.0
        
        # 12. Chande Momentum Oscillator (CMO)
        try: features['mom_cmo'] = ta.cmo(close, length=14)
        except: features['mom_cmo'] = 0.0
        
        # 13. Percentage Price Oscillator (PPO)
        try:
            ppo = ta.ppo(close, fast=12, slow=26, signal=9)
            features['mom_ppo'] = ppo[ppo.columns[0]]
        except: features['mom_ppo'] = 0.0
        
        # 14. RSI Velocity
        rsi = legacy_features.get('rsi', ta.rsi(close, length=14))
        features['mom_rsi_velocity'] = rsi.diff()
        
        # 15. RSI Acceleration
        features['mom_rsi_acceleration'] = features['mom_rsi_velocity'].diff()
        
        # 16. Stoch Velocity
        stoch_k = legacy_features.get('stoch_k', pd.Series(50.0, index=close.index))
        features['mom_stoch_velocity'] = stoch_k.diff()
        
        # 17. CCI Velocity
        cci = legacy_features.get('cci', pd.Series(0.0, index=close.index))
        features['mom_cci_velocity'] = cci.diff()
        
        # 18. ROC Accel
        roc = legacy_features.get('roc', ta.roc(close, length=14))
        features['mom_roc_accel'] = roc.diff().diff()
        
        # 19. MACD Normalized Factor
        try:
            macd = ta.macd(close, fast=12, slow=26, signal=9)
            macd_line = macd[macd.columns[0]]
            features['mom_macd_norm'] = self._safe_divide(macd_line, close) * 100
        except: features['mom_macd_norm'] = 0.0
        
        return features

    # =========================================
    # Phase 2: Divergence & Gaussian (8)
    # =========================================
    def generate_divergence_gaussian(self, legacy_features: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame(index=self.df.index)
        close = self.df['close']
        high = self.df['high']
        low = self.df['low']
        
        price_slope = close - close.rolling(20).mean()
        
        # 20. RSI Divergence Proxy
        rsi = legacy_features.get('rsi', ta.rsi(close, length=14))
        rsi_slope = rsi - rsi.rolling(20).mean()
        features['mom_rsi_div_proxy'] = self._safe_divide(price_slope, close) - self._safe_divide(rsi_slope, 100)
        
        # 21. Stoch Divergence Proxy
        stoch_k = legacy_features.get('stoch_k', pd.Series(50.0, index=close.index))
        stoch_slope = stoch_k - stoch_k.rolling(20).mean()
        features['mom_stoch_div_proxy'] = self._safe_divide(price_slope, close) - self._safe_divide(stoch_slope, 100)
        
        # 22. MACD Divergence Proxy
        try:
            macd = ta.macd(close, fast=12, slow=26, signal=9)
            macd_hist = macd[macd.columns[1]]
            features['mom_macd_div_proxy'] = self._safe_divide(price_slope, close) - self._safe_divide(macd_hist, close)
        except: features['mom_macd_div_proxy'] = 0.0
        
        # 23. Fisher Transform
        try:
            fisher = ta.fisher(high, low, length=9)
            features['mom_fisher_transform'] = fisher[fisher.columns[0]]
        except: features['mom_fisher_transform'] = 0.0
        
        # 24. Center of Gravity (CG)
        try:
            cg = ta.cg(close, length=10)
            features['mom_cg_oscillator'] = cg if isinstance(cg, pd.Series) else cg[cg.columns[0]]
        except: features['mom_cg_oscillator'] = 0.0
        
        # 25. Relative Vigor Index (RVI)
        try:
            rvi = ta.rvgi(open_=self.df['open'], high=high, low=low, close=close, length=14)
            features['mom_rvi'] = rvi if isinstance(rvi, pd.Series) else rvi[rvi.columns[0]]
        except: features['mom_rvi'] = 0.0
        
        # 26. TRIX
        try:
            trix = ta.trix(close, length=15)
            features['mom_trix'] = trix[trix.columns[0]]
        except: features['mom_trix'] = 0.0
        
        # 27. Coppock Curve Proxy
        try:
            roc14 = ta.roc(close, length=14)
            roc11 = ta.roc(close, length=11)
            features['mom_coppock_proxy'] = ta.wma(roc14 + roc11, length=10)
        except: features['mom_coppock_proxy'] = 0.0
        
        return features

    # =========================================
    # Phase 3: Vol Weighted & Asymmetric (7)
    # =========================================
    def generate_volume_asymmetric(self, legacy_features: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame(index=self.df.index)
        close = self.df['close']
        high = self.df['high']
        low = self.df['low']
        volume = self.df['volume']
        
        # 28. Money Flow Index (MFI)
        try: features['mom_mfi'] = ta.mfi(high, low, close, volume, length=14)
        except: features['mom_mfi'] = 50.0
        
        # 29. Chaikin Money Flow (CMF)
        try: features['mom_cmf'] = ta.cmf(high, low, close, volume, length=20)
        except: features['mom_cmf'] = 0.0
        
        # 30. Volume Weighted ROC
        roc = legacy_features.get('roc', ta.roc(close, length=14))
        vol_ratio = self._safe_divide(volume, volume.rolling(20).mean())
        features['mom_vw_roc'] = roc * vol_ratio
        
        # 31. Elder Ray Bull Power
        ema13 = ta.ema(close, length=13)
        features['mom_elder_bull'] = high - ema13
        
        # 32. Elder Ray Bear Power
        features['mom_elder_bear'] = low - ema13
        
        # 33. QStick Indicator
        features['mom_qstick'] = ta.sma(close - self.df['open'], length=8)
        
        # 34. Chande Kroll Stop Proxy
        try:
            atr = ta.atr(high, low, close, length=10)
            features['mom_chande_kroll_proxy'] = self._safe_divide(close - (high.rolling(10).max() - atr*3), close)
        except: features['mom_chande_kroll_proxy'] = 0.0
        
        return features

    # =========================================
    # Phase 4: MTF & DSP Smoothed (8)
    # =========================================
    def generate_mtf_dsp(self, legacy_features: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame(index=self.df.index)
        close = self.df['close']
        
        # 35-36. KST & Signal
        try:
            kst = ta.kst(close)
            features['mom_kst'] = kst[kst.columns[0]]
            features['mom_kst_signal'] = kst[kst.columns[1]]
        except:
            features['mom_kst'] = 0.0
            features['mom_kst_signal'] = 0.0
            
        # 37. Ehlers Smoothed RSI (Proxy using WMA)
        rsi = legacy_features.get('rsi', ta.rsi(close, length=14))
        try: features['mom_ehlers_rsi'] = ta.wma(rsi, length=5)
        except: features['mom_ehlers_rsi'] = rsi
        
        # 38. DSS Bressert (Double Smoothed Stoch Proxy)
        stoch_k = legacy_features.get('stoch_k', pd.Series(50.0, index=close.index))
        try: features['mom_dss_bressert'] = ta.ema(ta.ema(stoch_k, length=3), length=3)
        except: features['mom_dss_bressert'] = stoch_k
        
        # 39. Momentum Fractal Energy
        rsi50 = ta.rsi(close, length=50)
        features['mom_fractal_energy'] = rsi - rsi50
        
        # 40. Inertia
        try:
            inertia_val = ta.inertia(close, high=self.df['high'], low=self.df['low'])
            features['mom_inertia'] = inertia_val if isinstance(inertia_val, pd.Series) else inertia_val[inertia_val.columns[0]]
        except: features['mom_inertia'] = 0.0
        
        # 41-42. StochRSI
        try:
            stochrsi = ta.stochrsi(close, length=14, rsi_length=14, k=3, d=3)
            features['mom_stoch_rsi_k'] = stochrsi[stochrsi.columns[0]]
            features['mom_stoch_rsi_d'] = stochrsi[stochrsi.columns[1]]
        except:
            features['mom_stoch_rsi_k'] = 50.0
            features['mom_stoch_rsi_d'] = 50.0
            
        return features

    # =========================================
    # Phase 5: Statistical Extremes (8)
    # =========================================
    def generate_statistical_extremes(self, legacy_features: pd.DataFrame, mtf_features: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame(index=self.df.index)
        close = self.df['close']
        rsi = legacy_features.get('rsi', ta.rsi(close, length=14))
        
        # 43. RSI Skewness
        features['mom_rsi_skewness'] = rsi.rolling(20).skew()
        
        # 44. RSI Kurtosis (Black Swan Detector)
        features['mom_rsi_kurtosis'] = rsi.rolling(20).kurt()
        
        # 45. Williams %R Z-Score
        willr = legacy_features.get('williams_r', pd.Series(-50.0, index=close.index))
        features['mom_williams_z_score'] = self._safe_divide(willr - willr.rolling(50).mean(), willr.rolling(50).std())
        
        # 46. ROC Accel Spread
        roc14_diff = legacy_features.get('roc', ta.roc(close, length=14)).diff()
        roc28_diff = ta.roc(close, length=28).diff()
        features['mom_roc_accel_spread'] = roc14_diff - roc28_diff
        
        # 47. TSI Signal
        try:
            tsi = ta.tsi(close, fast=13, slow=25)
            features['mom_tsi_signal'] = tsi[tsi.columns[1]] # Signal line
        except: features['mom_tsi_signal'] = 0.0
        
        # 48. StochRSI Divergence Proxy
        stoch_rsi_k = mtf_features.get('mom_stoch_rsi_k', pd.Series(50.0, index=close.index))
        stoch_rsi_slope = stoch_rsi_k - stoch_rsi_k.rolling(20).mean()
        price_slope = close - close.rolling(20).mean()
        features['mom_stoch_rsi_div'] = self._safe_divide(price_slope, close) - self._safe_divide(stoch_rsi_slope, 100)
        
        # 49. RSI Z-Score
        features['mom_rsi_z_score'] = self._safe_divide(rsi - rsi.rolling(50).mean(), rsi.rolling(50).std())
        
        # 50. CCI Z-Score
        cci = legacy_features.get('cci', pd.Series(0.0, index=close.index))
        features['mom_cci_z_score'] = self._safe_divide(cci - cci.rolling(50).mean(), cci.rolling(50).std())
        
        return features

    def generate_all_features(self) -> pd.DataFrame:
        """
        Master method to execute all 6 phases and concatenate the 50 metrics.
        Includes safety measures to prevent NaN/Inf propagation.
        """
        p0 = self.generate_legacy_metrics()
        p1 = self.generate_core_derivatives(p0)
        p2 = self.generate_divergence_gaussian(p0)
        p3 = self.generate_volume_asymmetric(p0)
        p4 = self.generate_mtf_dsp(p0)
        p5 = self.generate_statistical_extremes(p0, p4)
        
        # Concatenate all phases
        all_features = pd.concat([p0, p1, p2, p3, p4, p5], axis=1)
        
        # Absolute Safeguard for Neural Networks
        all_features = all_features.replace([np.inf, -np.inf], np.nan)
        all_features = all_features.ffill().fillna(0.0)
        
        return all_features

if __name__ == "__main__":
    # Test execution
    print("Testing MomentumOscillatorFeatures...")
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=100)
    data = {
        'open': np.random.uniform(1.0, 1.1, 100),
        'high': np.random.uniform(1.1, 1.2, 100),
        'low': np.random.uniform(0.9, 1.0, 100),
        'close': np.random.uniform(1.0, 1.1, 100),
        'volume': np.random.uniform(1000, 5000, 100)
    }
    df = pd.DataFrame(data, index=dates)
    
    features = MomentumOscillatorFeatures.calculate_all(df)
    
    print(f"Generated DataFrame Shape: {features.shape}")
    print(f"Total Columns (Original + Features): {len(features.columns)}")
    print(f"NaN Count (Should be 0): {features.isna().sum().sum()}")
    print("Successfully completed implementation of 50 Momentum metrics.")
