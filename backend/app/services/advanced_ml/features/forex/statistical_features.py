import numpy as np
import pandas as pd
import pandas_ta as ta
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class StatisticalFeatures:
    """
    Forex ML Intelligence Studio - Category 6: Statistical & Time-Series
    73 Advanced Hedge-Fund Grade Quant Metrics with granular fail-safes.
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
        den_arr = np.asarray(den)
        num_arr = np.asarray(num)
        with np.errstate(divide='ignore', invalid='ignore'):
            result = np.where(den_arr == 0, 0.0, num_arr / den_arr)
        return pd.Series(result, index=self.df.index)

    def _z_score(self, series: pd.Series, window: int = 20) -> pd.Series:
        roll = series.rolling(window, min_periods=2)
        return self._safe_divide(series - roll.mean(), roll.std())

    def generate_legacy_metrics(self) -> pd.DataFrame:
        """Phase 0: Legacy Statistical Metrics (3 Metrics)"""
        features: Dict[str, pd.Series] = {}
        c = self.df['close']
        
        try: features['rolling_std'] = c.rolling(window=20, min_periods=2).std().fillna(0.0)
        except: features['rolling_std'] = 0.0
        
        try:
            ret = np.log(self._safe_divide(c, c.shift(1)))
            features['rolling_skewness'] = ret.rolling(window=20, min_periods=2).skew().fillna(0.0)
        except: features['rolling_skewness'] = 0.0
        
        try: features['rolling_kurtosis'] = ret.rolling(window=20, min_periods=2).kurt().fillna(0.0)
        except: features['rolling_kurtosis'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_distribution_moments(self, legacy: pd.DataFrame) -> pd.DataFrame:
        """Phase 1: Distribution Moments (5 Metrics)"""
        features: Dict[str, pd.Series] = {}
        c = self.df['close']
        ret = np.log(self._safe_divide(c, c.shift(1)))
        
        try: features['stat_rolling_variance'] = ret.rolling(20, min_periods=2).var().fillna(0.0)
        except: features['stat_rolling_variance'] = 0.0
        
        try: features['stat_rolling_skewness_adj'] = legacy.get('rolling_skewness', pd.Series(0, index=c.index)).rolling(5, min_periods=1).mean().fillna(0.0)
        except: features['stat_rolling_skewness_adj'] = 0.0
        
        try: features['stat_rolling_kurtosis_adj'] = legacy.get('rolling_kurtosis', pd.Series(0, index=c.index)).rolling(5, min_periods=1).mean().fillna(0.0)
        except: features['stat_rolling_kurtosis_adj'] = 0.0
        
        try:
            s = legacy.get('rolling_skewness', pd.Series(0, index=c.index))
            k = legacy.get('rolling_kurtosis', pd.Series(0, index=c.index))
            features['stat_jarque_bera_proxy'] = ((s**2)/6 + (k**2)/24).fillna(0.0)
        except: features['stat_jarque_bera_proxy'] = 0.0
        
        try: features['stat_z_score_close'] = self._z_score(c)
        except: features['stat_z_score_close'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_autocorrelation(self) -> pd.DataFrame:
        """Phase 2: Autocorrelation (5 Metrics)"""
        features: Dict[str, pd.Series] = {}
        ret = np.log(self._safe_divide(self.df['close'], self.df['close'].shift(1)))
        
        var_ret = ret.rolling(20, min_periods=2).var()
        
        def roll_autocorr(lag):
            try:
                cov = ret.rolling(20, min_periods=2).cov(ret.shift(lag))
                return self._safe_divide(cov, var_ret).fillna(0.0)
            except: return pd.Series(0.0, index=ret.index)
            
        features['stat_autocorr_lag1'] = roll_autocorr(1)
        features['stat_autocorr_lag3'] = roll_autocorr(3)
        features['stat_autocorr_lag5'] = roll_autocorr(5)
        features['stat_autocorr_lag10'] = roll_autocorr(10)
        
        try:
            features['stat_ljung_box_q_proxy'] = (
                features['stat_autocorr_lag1']**2 + 
                features['stat_autocorr_lag3']**2 + 
                features['stat_autocorr_lag5']**2
            ) * 20
        except: features['stat_ljung_box_q_proxy'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_stationarity(self) -> pd.DataFrame:
        """Phase 3: Stationarity & Random Walk Analysis (4 Metrics)"""
        features: Dict[str, pd.Series] = {}
        c = self.df['close']
        
        try:
            diff = c.diff()
            high_roll = c.rolling(20, min_periods=2).max()
            low_roll = c.rolling(20, min_periods=2).min()
            rs = self._safe_divide(high_roll - low_roll, diff.rolling(20, min_periods=2).std())
            features['stat_hurst_exponent'] = self._safe_divide(np.log(rs), np.log(pd.Series(20, index=c.index))).fillna(0.5)
        except: features['stat_hurst_exponent'] = 0.5
            
        try:
            ret_1 = c.diff()
            ret_5 = c.diff(5)
            features['stat_variance_ratio'] = self._safe_divide(ret_5.rolling(20, min_periods=2).var(), 5 * ret_1.rolling(20, min_periods=2).var()).fillna(1.0)
        except: features['stat_variance_ratio'] = 1.0
        
        try:
            delta_y = c.diff()
            y_t1 = c.shift(1)
            cov_delta_y_yt1 = delta_y.rolling(20, min_periods=2).cov(y_t1)
            var_yt1 = y_t1.rolling(20, min_periods=2).var()
            features['stat_adf_statistic_proxy'] = self._safe_divide(cov_delta_y_yt1, var_yt1).fillna(0.0)
        except: features['stat_adf_statistic_proxy'] = 0.0
        
        try:
            lam = -features['stat_adf_statistic_proxy']
            hl = np.where(lam > 0.0001, np.log(2) / lam, 0.0)
            features['stat_half_life_mean_reversion'] = pd.Series(hl, index=c.index).fillna(0.0)
        except: features['stat_half_life_mean_reversion'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_entropy(self) -> pd.DataFrame:
        """Phase 4: Entropy & Information Theory (3 Metrics)"""
        features: Dict[str, pd.Series] = {}
        ret = np.log(self._safe_divide(self.df['close'], self.df['close'].shift(1)))
        
        try:
            vol = ret.rolling(20, min_periods=2).std()
            kurt = ret.rolling(20, min_periods=2).kurt()
            features['stat_shannon_entropy'] = vol * np.exp(-self._safe_divide(kurt, 10)).fillna(0.0)
        except: features['stat_shannon_entropy'] = 0.0
        
        try: features['stat_approximate_entropy'] = self._safe_divide(ret.rolling(20, min_periods=2).std(), ret.rolling(10, min_periods=2).std()).fillna(1.0)
        except: features['stat_approximate_entropy'] = 1.0
        
        try: features['stat_sample_entropy'] = self._safe_divide(ret.diff().rolling(20, min_periods=2).std(), ret.rolling(20, min_periods=2).std()).fillna(1.0)
        except: features['stat_sample_entropy'] = 1.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_transformations(self) -> pd.DataFrame:
        """Phase 5: Time-Series Transformation (4 Metrics)"""
        features: Dict[str, pd.Series] = {}
        c = self.df['close']
        
        try:
            features['stat_fractional_differencing_d0_5'] = (
                c - 0.5 * c.shift(1) - 0.125 * c.shift(2) - 0.0625 * c.shift(3)
            ).fillna(0.0)
        except: features['stat_fractional_differencing_d0_5'] = 0.0
        
        try:
            log_ret = np.log(self._safe_divide(c, c.shift(1)))
            features['stat_log_returns'] = log_ret.fillna(0.0)
            features['stat_cumulative_log_returns'] = log_ret.rolling(20, min_periods=1).sum().fillna(0.0)
            features['stat_log_return_momentum'] = log_ret.diff(3).fillna(0.0)
        except:
            features['stat_log_returns'] = 0.0
            features['stat_cumulative_log_returns'] = 0.0
            features['stat_log_return_momentum'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_risk_adjusted(self) -> pd.DataFrame:
        """Phase 6: Risk-Adjusted Return Statistics (4 Metrics)"""
        features: Dict[str, pd.Series] = {}
        ret = np.log(self._safe_divide(self.df['close'], self.df['close'].shift(1)))
        
        roll_mean = ret.rolling(20, min_periods=2).mean()
        roll_std = ret.rolling(20, min_periods=2).std()
        
        try: features['stat_sharpe_ratio_rolling'] = self._safe_divide(roll_mean, roll_std).fillna(0.0)
        except: features['stat_sharpe_ratio_rolling'] = 0.0
        
        try:
            downside_ret = np.where(ret < 0, ret, 0)
            downside_std = pd.Series(downside_ret).rolling(20, min_periods=2).std()
            features['stat_sortino_ratio_rolling'] = self._safe_divide(roll_mean, downside_std).fillna(0.0)
        except: features['stat_sortino_ratio_rolling'] = 0.0
        
        try:
            max_c = self.df['close'].rolling(20, min_periods=2).max()
            dd = self._safe_divide(max_c - self.df['close'], max_c)
            max_dd = dd.rolling(20, min_periods=2).max()
            features['stat_calmar_ratio_proxy'] = self._safe_divide(roll_mean, max_dd).fillna(0.0)
        except: features['stat_calmar_ratio_proxy'] = 0.0
        
        try:
            up_sum = np.where(ret > 0, ret, 0)
            dn_sum = np.abs(np.where(ret < 0, ret, 0))
            features['stat_omega_ratio_proxy'] = self._safe_divide(pd.Series(up_sum).rolling(20, min_periods=2).sum(), pd.Series(dn_sum).rolling(20, min_periods=2).sum()).fillna(1.0)
        except: features['stat_omega_ratio_proxy'] = 1.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_linear_regression(self) -> pd.DataFrame:
        """Phase 7: Linear Regression & Trend Statistics (5 Metrics)"""
        features: Dict[str, pd.Series] = {}
        c = self.df['close']
        
        try:
            features['stat_linear_regression_slope'] = ta.slope(c, length=20).fillna(0.0)
            features['stat_linear_regression_intercept'] = ta.linreg(c, length=20, append=False).fillna(0.0) - (features['stat_linear_regression_slope'] * 19)
        except:
            features['stat_linear_regression_slope'] = 0.0
            features['stat_linear_regression_intercept'] = 0.0
            
        try:
            t = pd.Series(np.arange(len(c)), index=c.index)
            features['stat_r_squared_trend'] = c.rolling(20, min_periods=2).corr(t).pow(2).fillna(0.0)
            features['stat_standard_error'] = c.rolling(20, min_periods=2).std() * np.sqrt(1 - features['stat_r_squared_trend'])
        except:
            features['stat_r_squared_trend'] = 0.0
            features['stat_standard_error'] = 0.0
                
        try:
            ma = c.rolling(50, min_periods=2).mean()
            ret_c = c.pct_change()
            ret_ma = ma.pct_change()
            features['stat_beta_vs_ma'] = self._safe_divide(ret_c.rolling(20, min_periods=2).cov(ret_ma), ret_ma.rolling(20, min_periods=2).var()).fillna(1.0)
        except: features['stat_beta_vs_ma'] = 1.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_tail_risk(self) -> pd.DataFrame:
        """Phase 8: Tail Risk & Extreme Events (5 Metrics)"""
        features: Dict[str, pd.Series] = {}
        c = self.df['close']
        ret = np.log(self._safe_divide(c, c.shift(1)))
        
        try:
            mean = ret.rolling(20, min_periods=2).mean()
            std = ret.rolling(20, min_periods=2).std()
            features['stat_value_at_risk_95'] = (mean - 1.645 * std).fillna(0.0)
            features['stat_expected_shortfall_95'] = (mean - 2.06 * std).fillna(0.0)
        except:
            features['stat_value_at_risk_95'] = 0.0
            features['stat_expected_shortfall_95'] = 0.0
        
        try:
            max_c = c.rolling(50, min_periods=2).max()
            features['stat_max_drawdown_rolling'] = self._safe_divide(max_c - c, max_c).fillna(0.0)
            is_dd = (features['stat_max_drawdown_rolling'] > 0.01).astype(float)
            features['stat_drawdown_duration'] = is_dd.rolling(20, min_periods=1).sum().fillna(0.0)
        except:
            features['stat_max_drawdown_rolling'] = 0.0
            features['stat_drawdown_duration'] = 0.0
        
        try:
            var_pos = np.where(ret > 0, ret, 0)
            var_neg = np.abs(np.where(ret < 0, ret, 0))
            features['stat_tail_ratio'] = self._safe_divide(pd.Series(var_pos).rolling(20, min_periods=2).max(), pd.Series(var_neg).rolling(20, min_periods=2).max()).fillna(1.0)
        except: features['stat_tail_ratio'] = 1.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_kinematics(self, st_feat: pd.DataFrame) -> pd.DataFrame:
        """Phase 9: Physics-Based Kinematic Statistics (8 Metrics)"""
        features: Dict[str, pd.Series] = {}
        c = self.df['close']
        
        try:
            mean_log = np.log(self._safe_divide(c, c.shift(1))).rolling(20, min_periods=2).mean()
            features['stat_geometric_mean_return'] = (np.exp(mean_log) - 1).fillna(0.0)
        except: features['stat_geometric_mean_return'] = 0.0
        
        try: features['stat_harmonic_mean_proxy'] = self._safe_divide(20, (1/c).rolling(20, min_periods=2).sum()).fillna(0.0)
        except: features['stat_harmonic_mean_proxy'] = 0.0
        
        try:
            v = c.diff().fillna(0.0)
            a = v.diff().fillna(0.0)
            j = a.diff().fillna(0.0)
            s = j.diff().fillna(0.0)
            features['stat_price_velocity'] = v
            features['stat_price_acceleration'] = a
            features['stat_jerk_metric'] = j
            features['stat_snap_metric'] = s
        except:
            for feat in ['stat_price_velocity', 'stat_price_acceleration', 'stat_jerk_metric', 'stat_snap_metric']:
                features[feat] = 0.0
        
        try:
            features['stat_hurst_derivative'] = st_feat.get('stat_hurst_exponent', pd.Series(0.5, index=c.index)).diff().fillna(0.0)
            features['stat_entropy_velocity'] = st_feat.get('stat_shannon_entropy', pd.Series(0.0, index=c.index)).diff().fillna(0.0)
        except:
            features['stat_hurst_derivative'] = 0.0
            features['stat_entropy_velocity'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_spectral(self) -> pd.DataFrame:
        """Phase 10: Spectral & Frequency Domain (5 Metrics)"""
        features: Dict[str, pd.Series] = {}
        c = self.df['close']
        
        try:
            detrended = c - ta.ema(c, length=20)
            crossings = np.where(detrended * detrended.shift(1) < 0, 1.0, 0.0)
            cross_count = pd.Series(crossings).rolling(20, min_periods=2).sum()
            features['stat_dominant_cycle_period'] = self._safe_divide(20, cross_count).fillna(0.0)
        except: features['stat_dominant_cycle_period'] = 0.0
        
        try: features['stat_phase_angle'] = np.arctan2(detrended, detrended.diff()).fillna(0.0)
        except: features['stat_phase_angle'] = 0.0
        
        try:
            signal = np.abs(c - c.shift(20))
            noise = c.diff().abs().rolling(20, min_periods=2).sum()
            features['stat_signal_to_noise_ratio'] = self._safe_divide(signal, noise).fillna(0.0)
        except: features['stat_signal_to_noise_ratio'] = 0.0
        
        try:
            features['stat_hilbert_transform_sine'] = np.sin(features['stat_phase_angle'])
            features['stat_hilbert_transform_cosine'] = np.cos(features['stat_phase_angle'])
        except:
            features['stat_hilbert_transform_sine'] = 0.0
            features['stat_hilbert_transform_cosine'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_chaos(self, st_feat: pd.DataFrame) -> pd.DataFrame:
        """Phase 11: Non-linear Dynamics & Chaos Theory (3 Metrics)"""
        features: Dict[str, pd.Series] = {}
        ret = np.log(self._safe_divide(self.df['close'], self.df['close'].shift(1)))
        
        try:
            div = np.abs(ta.ema(self.df['close'], length=5) - ta.ema(self.df['close'], length=20))
            features['stat_lyapunov_exponent_proxy'] = np.log(self._safe_divide(div, div.shift(5))).fillna(0.0)
        except: features['stat_lyapunov_exponent_proxy'] = 0.0
        
        try: features['stat_correlation_dimension_proxy'] = (2.0 - st_feat.get('stat_hurst_exponent', pd.Series(0.5, index=ret.index))).fillna(0.0)
        except: features['stat_correlation_dimension_proxy'] = 0.0
        
        try:
            integrated = ret.cumsum()
            local_trend = integrated.rolling(10, min_periods=2).mean()
            fluct = integrated - local_trend
            features['stat_dfa'] = fluct.rolling(10, min_periods=2).var().fillna(0.0)
        except: features['stat_dfa'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_markov(self) -> pd.DataFrame:
        """Phase 12: Probability & Markov Chain Proxies (4 Metrics)"""
        features: Dict[str, pd.Series] = {}
        c, o = self.df['close'], self.df['open']
        
        try:
            is_up_bool = (c >= o)
            is_dn_bool = (c < o)
            is_up = is_up_bool.astype(float)
            is_dn = is_dn_bool.astype(float)
            
            up_sum = is_up.shift(1).rolling(20, min_periods=1).sum()
            dn_sum = is_dn.shift(1).rolling(20, min_periods=1).sum()
            
            up_up = (is_up_bool & is_up_bool.shift(1)).astype(float).rolling(20, min_periods=1).sum()
            dn_dn = (is_dn_bool & is_dn_bool.shift(1)).astype(float).rolling(20, min_periods=1).sum()
            reversals = (is_up_bool != is_up_bool.shift(1)).astype(float).rolling(20, min_periods=1).sum()
            
            features['stat_transition_prob_up_up'] = self._safe_divide(up_up, up_sum).fillna(0.0)
            features['stat_transition_prob_down_down'] = self._safe_divide(dn_dn, dn_sum).fillna(0.0)
            features['stat_transition_prob_reversal'] = self._safe_divide(reversals, 20.0).fillna(0.0)
        except:
            features['stat_transition_prob_up_up'] = 0.0
            features['stat_transition_prob_down_down'] = 0.0
            features['stat_transition_prob_reversal'] = 0.0
            
        try:
            vol = c.pct_change().rolling(20, min_periods=2).std()
            vol_mean = vol.rolling(100, min_periods=2).mean()
            features['stat_markov_regime_state'] = (vol > vol_mean).astype(float)
        except: features['stat_markov_regime_state'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_higher_order(self, st_feat: pd.DataFrame) -> pd.DataFrame:
        """Phase 13: Higher Order Return Statistics (3 Metrics)"""
        features: Dict[str, pd.Series] = {}
        
        try:
            ac1 = np.abs(st_feat.get('stat_autocorr_lag1', pd.Series(1.0, index=self.df.index)))
            ac5 = np.abs(st_feat.get('stat_autocorr_lag5', pd.Series(0.0, index=self.df.index)))
            features['stat_autocorr_decay_rate'] = self._safe_divide(ac1 - ac5, 4.0).fillna(0.0)
        except: features['stat_autocorr_decay_rate'] = 0.0
        
        try:
            features['stat_partial_autocorr_lag1'] = st_feat.get('stat_autocorr_lag1', pd.Series(0.0, index=self.df.index))
            features['stat_partial_autocorr_lag3'] = st_feat.get('stat_autocorr_lag3', pd.Series(0.0, index=self.df.index)) - (st_feat.get('stat_autocorr_lag1', pd.Series(0.0, index=self.df.index)) ** 3)
        except:
            features['stat_partial_autocorr_lag1'] = 0.0
            features['stat_partial_autocorr_lag3'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_geometry(self) -> pd.DataFrame:
        """Phase 14: Distance & Geometry Metrics (4 Metrics)"""
        features: Dict[str, pd.Series] = {}
        c = self.df['close']
        
        try:
            diff_20 = np.abs(c - c.shift(20))
            features['stat_euclidean_distance_rolling'] = np.sqrt(diff_20**2 + 20**2).fillna(0.0)
        except: features['stat_euclidean_distance_rolling'] = 0.0
        
        try:
            path_len = c.diff().abs().rolling(20, min_periods=2).sum()
            features['stat_path_length_rolling'] = path_len.fillna(0.0)
            features['stat_efficiency_ratio_kaufman'] = self._safe_divide(diff_20, path_len).fillna(0.0)
        except:
            features['stat_path_length_rolling'] = 0.0
            features['stat_efficiency_ratio_kaufman'] = 0.0
            
        try:
            num = pd.Series(0.0, index=c.index)
            den = pd.Series(0.0, index=c.index)
            for i in range(10):
                num += c.shift(i) * (i + 1)
                den += c.shift(i)
            features['stat_center_of_gravity'] = self._safe_divide(num, den).fillna(0.0)
        except: features['stat_center_of_gravity'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_cross_series(self) -> pd.DataFrame:
        """Phase 15: Cross-Series Correlation & Asymmetric Ratios (8 Metrics)"""
        features: Dict[str, pd.Series] = {}
        c, v = self.df['close'], self.df['volume']
        
        try:
            ret = c.pct_change()
            v_chg = v.pct_change()
            features['stat_covariance_price_volume'] = ret.rolling(20, min_periods=2).cov(v_chg).fillna(0.0)
            features['stat_beta_price_volume'] = self._safe_divide(features['stat_covariance_price_volume'], v_chg.rolling(20, min_periods=2).var()).fillna(0.0)
            features['stat_spearman_rank_corr'] = ret.rolling(20, min_periods=2).corr(v_chg).fillna(0.0)
        except:
            features['stat_covariance_price_volume'] = 0.0
            features['stat_beta_price_volume'] = 0.0
            features['stat_spearman_rank_corr'] = 0.0
            
        try:
            dir_c = np.sign(ret)
            dir_v = np.sign(v_chg)
            concordant = (dir_c == dir_v).astype(float)
            features['stat_kendall_tau_corr'] = concordant.rolling(20, min_periods=2).mean().fillna(0.0)
        except: features['stat_kendall_tau_corr'] = 0.0
        
        try:
            ma = c.rolling(50, min_periods=2).mean()
            active_ret = ret - ma.pct_change()
            features['stat_information_ratio_proxy'] = self._safe_divide(active_ret.rolling(20, min_periods=2).mean(), active_ret.rolling(20, min_periods=2).std()).fillna(0.0)
        except: features['stat_information_ratio_proxy'] = 0.0
        
        try:
            max_c = c.rolling(14, min_periods=2).max()
            drawdown_pct = self._safe_divide(max_c - c, max_c) * 100
            features['stat_ulcer_index_proxy'] = np.sqrt((drawdown_pct ** 2).rolling(14, min_periods=2).mean()).fillna(0.0)
            features['stat_pain_index_proxy'] = drawdown_pct.abs().rolling(14, min_periods=2).mean().fillna(0.0)
        except:
            features['stat_ulcer_index_proxy'] = 0.0
            features['stat_pain_index_proxy'] = 0.0
            
        try:
            ret_10 = c.pct_change(10)
            ret_50 = c.pct_change(50)
            features['stat_cross_sectional_momentum'] = (ret_10 - ret_50).fillna(0.0)
        except: features['stat_cross_sectional_momentum'] = 0.0
        
        return pd.DataFrame(features, index=self.df.index)

    def generate_all_features(self) -> pd.DataFrame:
        p0 = self.generate_legacy_metrics()
        p1 = self.generate_distribution_moments(p0)
        p2 = self.generate_autocorrelation()
        p3 = self.generate_stationarity()
        p4 = self.generate_entropy()
        p5 = self.generate_transformations()
        p6 = self.generate_risk_adjusted()
        p7 = self.generate_linear_regression()
        p8 = self.generate_tail_risk()
        
        # Combine early features required by others
        base = pd.concat([p0, p1, p2, p3, p4], axis=1)
        
        p9 = self.generate_kinematics(base)
        p10 = self.generate_spectral()
        p11 = self.generate_chaos(base)
        p12 = self.generate_markov()
        p13 = self.generate_higher_order(base)
        p14 = self.generate_geometry()
        p15 = self.generate_cross_series()
        
        all_features = pd.concat([p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14, p15], axis=1)
        
        # Ensure Neural Network Safety
        all_features = all_features.replace([np.inf, -np.inf], np.nan)
        all_features = all_features.ffill().fillna(0.0)
        
        # Gradient Explosion Protection
        all_features = all_features.clip(-1000.0, 1000.0)
        
        return all_features

    @staticmethod
    def calculate_all(df_raw: pd.DataFrame, requested_features: list = None) -> pd.DataFrame:
        df_safe = df_raw.copy()
        try:
            extractor = StatisticalFeatures(df_safe)
            new_features = extractor.generate_all_features()
            
            cols_to_use = new_features.columns.difference(df_safe.columns)
            
            # If user explicitly selected subset of features, only return those
            if requested_features:
                requested_existing = [f for f in requested_features if f in cols_to_use]
                if requested_existing:
                    cols_to_use = requested_existing
                    
            result = pd.concat([df_safe, new_features[cols_to_use]], axis=1)
            return result
        except Exception as e:
            logger.error(f"Error calculating Statistical Features: {e}")
            return df_raw
