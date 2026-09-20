import pandas as pd
import numpy as np
import logging

class BasicPriceActionEngine:
    """
    100% Modular, Vectorised, Hedge-Fund Grade Feature Engineering.
    Focus: Category 1 - Basic Price Action (Forex Layer Only).
    
    Contains 88 Metrics:
    - Phase 1: Core Returns & Base Kinematics
    - Phase 2: Intrabar Proportions & Wick Geometry
    - Phase 3: Rolling Statistical Distribution & Quantiles
    - Phase 4: Power Balance & Reversion Dynamics
    - Phase 5: Micro-Structure & Gap Dynamics
    - Phase 6: Spectral, Markov & Polynomial Transforms
    - Phase 7: Historical & Structural Anchors (Original 24 preserved)
    """
    
    def __init__(self, df_raw: pd.DataFrame):
        self.df = df_raw.copy()
        
    def generate_all_features(self) -> pd.DataFrame:
        if self.df.empty:
            return self.df
            
        required_cols = ['open', 'high', 'low', 'close']
        for col in required_cols:
            if col not in self.df.columns:
                logging.warning(f"Missing column '{col}' for Basic Price Action features.")
                return self.df
                
        try:
            self._precompute_bases()
            self._calc_phase_1_kinematics()
            self._calc_phase_2_intrabar()
            self._calc_phase_3_distribution()
            self._calc_phase_4_power_balance()
            self._calc_phase_5_microstructure()
            self._calc_phase_6_transforms()
            self._calc_phase_7_historical()
            
        except Exception as e:
            logging.error(f"Error calculating Basic Price Action features: {e}")
            
        self.df = self.df.replace([np.inf, -np.inf], np.nan)
        self.df = self.df.ffill()
        self.df = self.df.fillna(0)
        
        return self.df

    def _precompute_bases(self):
        self.close = self.df['close']
        self.high = self.df['high']
        self.low = self.df['low']
        self.open_p = self.df['open']
        self.candle_range = (self.high - self.low).clip(lower=1e-9)
        self.body_range = np.abs(self.close - self.open_p)
        self.upper_wick = self.high - np.maximum(self.open_p, self.close)
        self.lower_wick = np.minimum(self.open_p, self.close) - self.low

    def _calc_phase_1_kinematics(self):
        # 1. pa_log_returns
        self.df['pa_log_returns'] = np.log(self.close / self.close.shift(1).clip(lower=1e-9)).fillna(0)
        # 2. pa_price_acceleration
        self.df['pa_price_acceleration'] = self.df['pa_log_returns'].diff().fillna(0)
        # 3. pa_session_gap
        self.df['pa_session_gap'] = (self.open_p - self.close.shift(1)) / self.close.shift(1).clip(lower=1e-9)
        self.df['pa_session_gap'] = self.df['pa_session_gap'].fillna(0)
        # 4. pa_true_range
        self.df['pa_true_range'] = np.maximum(self.candle_range, 
                                              np.maximum(np.abs(self.high - self.close.shift(1)), 
                                                         np.abs(self.low - self.close.shift(1))))
        # 5. pa_price_velocity_1d
        self.df['pa_price_velocity_1d'] = self.close - self.close.shift(1)
        # 6. pa_price_jerk_3d
        self.df['pa_price_jerk_3d'] = self.df['pa_price_acceleration'].diff().fillna(0)
        # 7. pa_directional_velocity_decay
        self.df['pa_directional_velocity_decay'] = self.df['pa_price_velocity_1d'].abs().diff(3)
        # 8. pa_intrabar_travel_efficiency
        self.df['pa_intrabar_travel_efficiency'] = (self.close - self.open_p) / self.candle_range
        # 9. pa_rolling_drift_coefficient
        sum_bodies = self.body_range.rolling(14, min_periods=1).sum()
        sum_ranges = self.candle_range.rolling(14, min_periods=1).sum()
        self.df['pa_rolling_drift_coefficient'] = sum_bodies / sum_ranges.clip(lower=1e-9)
        # 10. pa_price_return_skewness
        self.df['pa_price_return_skewness'] = self.df['pa_log_returns'].rolling(14, min_periods=1).skew().fillna(0)
        # 11. pa_tail_rejection_velocity
        prev_candle_range = self.candle_range.shift(1).clip(lower=1e-9)
        max_wick = np.maximum(self.upper_wick, self.lower_wick)
        self.df['pa_tail_rejection_velocity'] = max_wick / prev_candle_range
        # 12. pa_price_action_thrust
        self.df['pa_price_action_thrust'] = (self.close - self.close.shift(1)) / self.candle_range

    def _calc_phase_2_intrabar(self):
        # 13. pa_upper_wick_ratio
        self.df['pa_upper_wick_ratio'] = self.upper_wick / self.candle_range
        # 14. pa_lower_wick_ratio
        self.df['pa_lower_wick_ratio'] = self.lower_wick / self.candle_range
        # 15. pa_body_ratio
        self.df['pa_body_ratio'] = self.body_range / self.candle_range
        # 16. pa_cpr (Close Position in Range)
        self.df['pa_cpr'] = (self.close - self.low) / self.candle_range
        # 17. pa_body_center_to_range_mid_deviation
        body_center = (self.open_p + self.close) / 2
        range_mid = (self.high + self.low) / 2
        self.df['pa_body_center_to_range_mid_deviation'] = (body_center - range_mid) / self.candle_range
        # 18. pa_bar_expansion_symmetry
        self.df['pa_bar_expansion_symmetry'] = self.upper_wick / self.lower_wick.clip(lower=1e-9)
        # 19. pa_high_low_midpoint_drift
        self.df['pa_high_low_midpoint_drift'] = range_mid - range_mid.shift(1)
        # 20. pa_hlc3_close_divergence
        hlc3 = (self.high + self.low + self.close) / 3
        self.df['pa_hlc3_close_divergence'] = (self.close - hlc3) / self.candle_range
        # 21. pa_bar_absorption_rate
        prev_body = self.body_range.shift(1).clip(lower=1e-9)
        self.df['pa_bar_absorption_rate'] = np.maximum(self.upper_wick, self.lower_wick) / prev_body
        # 22. pa_structural_overlap_percentage
        prev_high = self.high.shift(1)
        prev_low = self.low.shift(1)
        overlap_high = np.minimum(self.high, prev_high)
        overlap_low = np.maximum(self.low, prev_low)
        overlap_range = np.maximum(0, overlap_high - overlap_low)
        self.df['pa_structural_overlap_percentage'] = overlap_range / self.candle_range.shift(1).clip(lower=1e-9)
        # 23. pa_intrabar_swing_ratio
        self.df['pa_intrabar_swing_ratio'] = (self.upper_wick / self.lower_wick.clip(lower=1e-9)) * self.body_range
        # 24. pa_bar_weight_distribution
        # Ratio of body in top half vs bottom half of the range
        mid = (self.high + self.low) / 2
        body_top_half = np.maximum(0, np.minimum(self.high, np.maximum(self.open_p, self.close)) - mid)
        body_bottom_half = np.maximum(0, mid - np.maximum(self.low, np.minimum(self.open_p, self.close)))
        self.df['pa_bar_weight_distribution'] = body_top_half / body_bottom_half.clip(lower=1e-9)

    def _calc_phase_3_distribution(self):
        # 25. pa_rolling_z_score
        rolling_mean = self.close.rolling(20, min_periods=1).mean()
        rolling_std = self.close.rolling(20, min_periods=1).std().clip(lower=1e-9)
        self.df['pa_rolling_z_score'] = (self.close - rolling_mean) / rolling_std
        # 26. pa_price_vs_median
        median_20 = self.close.rolling(20, min_periods=1).median()
        self.df['pa_price_vs_median'] = (self.close - median_20) / median_20.clip(lower=1e-9)
        # 27. pa_rolling_close_percentile_rank
        # Vectorized percentile rank approximation using expanding/rolling
        def rolling_rank(s):
            return s.rolling(100, min_periods=1).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
        self.df['pa_rolling_close_percentile_rank'] = rolling_rank(self.close)
        # 28. pa_rolling_high_percentile_rank
        self.df['pa_rolling_high_percentile_rank'] = rolling_rank(self.high)
        # 29. pa_rolling_low_percentile_rank
        self.df['pa_rolling_low_percentile_rank'] = rolling_rank(self.low)
        # 30. pa_price_density_cluster_score
        # Count of previous 20 closes within 0.1% of current close
        band = self.close * 0.001
        up_b = self.close + band
        dn_b = self.close - band
        # Vectorized check
        # We can approximate by checking if past closes are between up_b and dn_b
        # This is a bit tricky to vectorize cleanly without a loop or apply, so we use a simple apply
        self.df['pa_price_density_cluster_score'] = self.close.rolling(20, min_periods=1).apply(
            lambda x: ((x >= x.iloc[-1] * 0.999) & (x <= x.iloc[-1] * 1.001)).sum(), raw=False
        )
        # 31. pa_price_entropy_14d
        # Simplified Shannon entropy of binned returns
        def entropy(x):
            hist, _ = np.histogram(x, bins=10, density=True)
            p = hist[hist > 0]
            return -np.sum(p * np.log2(p))
        self.df['pa_price_entropy_14d'] = self.df['pa_log_returns'].rolling(14, min_periods=1).apply(entropy, raw=True).fillna(0)
        # 32. pa_price_dispersion_index
        self.df['pa_price_dispersion_index'] = self.candle_range.rolling(14, min_periods=1).std() / self.candle_range.rolling(14, min_periods=1).mean().clip(lower=1e-9)
        # 33. pa_kinematic_energy_proxy
        self.df['pa_kinematic_energy_proxy'] = self.df['pa_price_velocity_1d'] ** 2
        # 34. pa_potential_energy_proxy
        min_14 = self.low.rolling(14, min_periods=1).min()
        max_14 = self.high.rolling(14, min_periods=1).max()
        range_14 = (max_14 - min_14).clip(lower=1e-9)
        self.df['pa_potential_energy_proxy'] = (self.close - min_14) / range_14
        # 35. pa_energy_dissipation_rate
        self.df['pa_energy_dissipation_rate'] = self.df['pa_kinematic_energy_proxy'].diff(3).fillna(0)
        # 36. pa_tail_risk_kurtosis_rolling
        self.df['pa_tail_risk_kurtosis_rolling'] = self.df['pa_log_returns'].rolling(20, min_periods=1).kurt().fillna(0)

    def _calc_phase_4_power_balance(self):
        # 37. pa_consecutive_runs
        trade_dir = np.where(self.close > self.close.shift(1), 1, np.where(self.close < self.close.shift(1), -1, 0))
        trade_dir_series = pd.Series(trade_dir, index=self.df.index)
        run_blocks = (trade_dir_series != trade_dir_series.shift()).cumsum()
        self.df['pa_consecutive_runs'] = (trade_dir_series.groupby(run_blocks).cumcount() + 1) * trade_dir_series
        # 38. pa_bull_bear_power_balance
        bull_power = (self.high - self.open_p).rolling(14, min_periods=1).sum()
        bear_power = (self.open_p - self.low).rolling(14, min_periods=1).sum()
        self.df['pa_bull_bear_power_balance'] = bull_power / bear_power.clip(lower=1e-9)
        # 39. pa_mean_reversion_stretch
        # Distance from 20 MA divided by ATR
        atr = self.df['pa_true_range'].rolling(14, min_periods=1).mean().clip(lower=1e-9)
        self.df['pa_mean_reversion_stretch'] = (self.close - self.close.rolling(20, min_periods=1).mean()) / atr
        # 40. pa_sequential_up_down_ratio
        up_count = (self.close > self.close.shift(1)).rolling(14, min_periods=1).sum()
        dn_count = (self.close < self.close.shift(1)).rolling(14, min_periods=1).sum()
        self.df['pa_sequential_up_down_ratio'] = up_count / dn_count.clip(lower=1e-9)
        # 41. pa_current_bar_exhaustion_index
        # Close proximity to high after 3 up bars
        is_up_3 = (trade_dir_series.rolling(3, min_periods=1).sum() == 3)
        self.df['pa_current_bar_exhaustion_index'] = np.where(is_up_3, (self.high - self.close) / self.candle_range, 0)
        # 42. pa_close_open_correlation
        self.df['pa_close_open_correlation'] = self.close.rolling(14, min_periods=1).corr(self.open_p).fillna(0)
        # 43. pa_high_low_correlation
        self.df['pa_high_low_correlation'] = self.high.rolling(14, min_periods=1).corr(self.low).fillna(0)
        # 44. pa_hurst_exponent_proxy
        # Simplified proxy for Hurst
        lags = range(2, 10)
        def hurst_proxy(price):
            if len(price) < 10: return 0.5
            tau = [np.std(price[lag:] - price[:-lag]) for lag in lags]
            if np.any(np.isnan(tau)) or np.any(np.array(tau) == 0): return 0.5
            reg = np.polyfit(np.log(lags), np.log(tau), 1)
            return reg[0]
        self.df['pa_hurst_exponent_proxy'] = self.close.rolling(20, min_periods=1).apply(hurst_proxy, raw=True).fillna(0.5)
        # 45. pa_price_elasticity_coefficient
        # Return / Volatility
        vol = self.df['pa_log_returns'].rolling(14, min_periods=1).std().clip(lower=1e-9)
        self.df['pa_price_elasticity_coefficient'] = self.df['pa_log_returns'] / vol
        # 46. pa_three_bar_net_momentum
        sum_tr_3 = self.df['pa_true_range'].rolling(3, min_periods=1).sum().clip(lower=1e-9)
        self.df['pa_three_bar_net_momentum'] = (self.close - self.close.shift(3)) / sum_tr_3
        # 47. pa_n_period_consolidation_break
        min_10 = self.low.rolling(10, min_periods=1).min()
        max_10 = self.high.rolling(10, min_periods=1).max()
        range_10 = (max_10 - min_10).clip(lower=1e-9)
        self.df['pa_n_period_consolidation_break'] = (self.close - min_10) / range_10
        # 48. pa_hausdorff_dimension_proxy
        # Box counting proxy
        self.df['pa_hausdorff_dimension_proxy'] = np.log(self.candle_range.rolling(10, min_periods=1).sum() / range_10.clip(lower=1e-9)) / np.log(10)
        self.df['pa_hausdorff_dimension_proxy'] = self.df['pa_hausdorff_dimension_proxy'].replace([np.inf, -np.inf], 0).fillna(0)

    def _calc_phase_5_microstructure(self):
        # 49. pa_micro_gap_magnitude
        self.df['pa_micro_gap_magnitude'] = (self.open_p - self.close.shift(1)) / self.candle_range.shift(1).clip(lower=1e-9)
        # 50. pa_micro_gap_fill_state
        gap = self.open_p - self.close.shift(1)
        filled_up = (gap < 0) & (self.high >= self.close.shift(1))
        filled_dn = (gap > 0) & (self.low <= self.close.shift(1))
        self.df['pa_micro_gap_fill_state'] = (filled_up | filled_dn).astype(float)
        # 51. pa_lap_state_bullish
        inside_open = (self.open_p <= np.maximum(self.open_p.shift(1), self.close.shift(1))) & \
                      (self.open_p >= np.minimum(self.open_p.shift(1), self.close.shift(1)))
        lap_bull = inside_open & (self.close > self.high.shift(1))
        self.df['pa_lap_state_bullish'] = lap_bull.astype(float)
        # 52. pa_lap_state_bearish
        lap_bear = inside_open & (self.close < self.low.shift(1))
        self.df['pa_lap_state_bearish'] = lap_bear.astype(float)
        # 53. pa_outside_bar_magnitude
        is_outside = (self.high > self.high.shift(1)) & (self.low < self.low.shift(1))
        self.df['pa_outside_bar_magnitude'] = np.where(is_outside, self.candle_range / self.candle_range.shift(1).clip(lower=1e-9), 0)
        # 54. pa_anomaly_bar_flag
        avg_r_20 = self.candle_range.rolling(20, min_periods=1).mean()
        std_r_20 = self.candle_range.rolling(20, min_periods=1).std()
        self.df['pa_anomaly_bar_flag'] = (self.candle_range > (avg_r_20 + 3 * std_r_20)).astype(float)
        # 55. pa_consecutive_tight_ranges
        is_tight = self.candle_range < avg_r_20 * 0.5
        tight_blocks = (is_tight != is_tight.shift(1)).cumsum()
        self.df['pa_consecutive_tight_ranges'] = is_tight.groupby(tight_blocks).cumcount() + 1
        self.df['pa_consecutive_tight_ranges'] *= is_tight
        # 56. pa_shadow_imbalance_ratio
        sum_up_wick = self.upper_wick.rolling(14, min_periods=1).sum()
        sum_dn_wick = self.lower_wick.rolling(14, min_periods=1).sum()
        self.df['pa_shadow_imbalance_ratio'] = sum_up_wick / sum_dn_wick.clip(lower=1e-9)
        # 57. pa_price_vacuum_zone_distance
        # Proxy: Distance to last anomaly bar
        anomaly_bars = self.df['pa_anomaly_bar_flag'] == 1
        last_anomaly_close = self.close.where(anomaly_bars).ffill()
        self.df['pa_price_vacuum_zone_distance'] = (self.close - last_anomaly_close) / self.candle_range
        # 58. pa_gap_exhaustion_proxy
        # 3 consecutive gaps in same direction
        gaps = np.sign(self.open_p - self.close.shift(1))
        consec_gaps = (gaps == gaps.shift(1)) & (gaps == gaps.shift(2))
        self.df['pa_gap_exhaustion_proxy'] = consec_gaps.astype(float) * gaps
        # 59. pa_price_cycle_periodicity_proxy
        # Distance between last 2 swing highs
        swing_h = (self.high > self.high.shift(1)) & (self.high > self.high.shift(-1))
        row_nums = np.arange(len(self.df))
        swing_idx = pd.Series(np.where(swing_h, row_nums, np.nan)).ffill()
        # Distance in bars
        self.df['pa_price_cycle_periodicity_proxy'] = swing_idx.diff().fillna(0)
        # 60. pa_price_cycle_amplitude_proxy
        last_h = self.high.where(swing_h).ffill()
        swing_l = (self.low < self.low.shift(1)) & (self.low < self.low.shift(-1))
        last_l = self.low.where(swing_l).ffill()
        self.df['pa_price_cycle_amplitude_proxy'] = (last_h - last_l) / self.close

    def _calc_phase_6_transforms(self):
        # 61. pa_poly_fit_slope_3d
        # Slope of last 3 points
        x = np.array([1, 2, 3])
        x_mean = 2.0
        x_var = 2.0 # sum((x - 2)^2) = 1 + 0 + 1 = 2
        # beta = sum((x - x_mean)*(y - y_mean)) / x_var
        # vectorized:
        y1, y2, y3 = self.close.shift(2), self.close.shift(1), self.close
        y_mean = (y1 + y2 + y3) / 3
        # cov = (-1)*(y1 - y_mean) + (0)*(y2 - y_mean) + (1)*(y3 - y_mean) = y3 - y1
        self.df['pa_poly_fit_slope_3d'] = (y3 - y1) / 2.0
        
        # 62. pa_poly_fit_curve_5d
        # 2nd derivative approximation over 5 bars: f''(x) ~ y[i] - 2y[i-2] + y[i-4]
        self.df['pa_poly_fit_curve_5d'] = self.close - 2*self.close.shift(2) + self.close.shift(4)
        
        # 63-64. DCT Coefficients
        # Very simplified DCT-II for N=4
        y0, y1, y2, y3 = self.close.shift(3), self.close.shift(2), self.close.shift(1), self.close
        # DCT0 = y0+y1+y2+y3 (DC)
        # DCT1 approx = 0.65*y0 + 0.27*y1 - 0.27*y2 - 0.65*y3 (Macro trend)
        self.df['pa_dct_coefficient_1'] = 0.65*y0 + 0.27*y1 - 0.27*y2 - 0.65*y3
        # DCT2 approx = 0.5*y0 - 0.5*y1 - 0.5*y2 + 0.5*y3 (Wave/Oscillation)
        self.df['pa_dct_coefficient_2'] = 0.5*y0 - 0.5*y1 - 0.5*y2 + 0.5*y3
        
        # 65. pa_renko_brick_proxy
        atr = self.df['pa_true_range'].rolling(14, min_periods=1).mean().clip(lower=1e-9)
        self.df['pa_renko_brick_proxy'] = np.floor((self.close - self.open_p) / atr)
        
        # 66. pa_pnf_reversal_state
        # 3-box reversal proxy
        self.df['pa_pnf_reversal_state'] = (np.abs(self.close - self.close.shift(3)) > 3 * atr).astype(float)
        
        # 67-68. Markov Probabilities
        up = (self.close > self.close.shift(1)).astype(int)
        dn = (self.close < self.close.shift(1)).astype(int)
        up_up = (up & up.shift(1).fillna(0).astype(int))
        dn_dn = (dn & dn.shift(1).fillna(0).astype(int))
        self.df['pa_markov_up_up_prob'] = up_up.rolling(20, min_periods=1).sum() / up.shift(1).rolling(20, min_periods=1).sum().clip(lower=1)
        self.df['pa_markov_down_down_prob'] = dn_dn.rolling(20, min_periods=1).sum() / dn.shift(1).rolling(20, min_periods=1).sum().clip(lower=1)
        
        # 69. pa_kl_divergence_normal
        # Proxy KL Divergence vs Normal(0,1) for z-scored returns
        z_ret = (self.df['pa_log_returns'] - self.df['pa_log_returns'].rolling(20).mean()) / self.df['pa_log_returns'].rolling(20).std().clip(lower=1e-9)
        # KL approx ~ 0.5 * (std^2 + mean^2 - 1 - log(std^2))
        # Since it's z-scored, empirical mean is 0 and std is 1 over 20, but locally over 5 it differs
        local_std = z_ret.rolling(5, min_periods=1).std().clip(lower=1e-9)
        local_mean = z_ret.rolling(5, min_periods=1).mean()
        self.df['pa_kl_divergence_normal'] = 0.5 * (local_std**2 + local_mean**2 - 1 - np.log(local_std**2))
        
        # 70. pa_cooks_distance_proxy
        # Leverage of current point on 20-period mean
        mean_20 = self.close.rolling(20, min_periods=1).mean()
        mean_19 = self.close.shift(1).rolling(19, min_periods=1).mean()
        self.df['pa_cooks_distance_proxy'] = np.abs(mean_20 - mean_19) / self.candle_range
        
        # 71. pa_dtw_linear_distance
        # DTW to straight line between open[t-4] and close[t]
        y0_p = self.close.shift(4)
        y4_p = self.close
        step = (y4_p - y0_p) / 4
        # Straight line pts: y0_p, y0_p+step, y0_p+2step, y0_p+3step, y4_p
        dist = np.abs(self.close.shift(3) - (y0_p+step)) + \
               np.abs(self.close.shift(2) - (y0_p+2*step)) + \
               np.abs(self.close.shift(1) - (y0_p+3*step))
        self.df['pa_dtw_linear_distance'] = dist / self.candle_range.rolling(5, min_periods=1).mean().clip(lower=1e-9)
        
        # 72. pa_price_curve_length
        path_len = self.df['pa_price_velocity_1d'].abs().rolling(10, min_periods=1).sum()
        net_len = np.abs(self.close - self.close.shift(10))
        self.df['pa_price_curve_length'] = path_len / net_len.clip(lower=1e-9)

    def _calc_phase_7_historical(self):
        # The remaining 16 original metrics ensuring backward compatibility
        rolling_high_20 = self.high.rolling(20, min_periods=1).max()
        rolling_low_20 = self.low.rolling(20, min_periods=1).min()
        
        # 73. pa_dist_to_support
        self.df['pa_dist_to_support'] = (self.close - rolling_low_20) / self.close.clip(lower=1e-9)
        
        # 74. pa_dist_to_resistance
        self.df['pa_dist_to_resistance'] = (rolling_high_20 - self.close) / self.close.clip(lower=1e-9)
        
        # Swings (Logic from original file)
        swing_h_cond = (self.high.shift(2) > self.high.shift(3)) & (self.high.shift(2) > self.high.shift(4)) & \
                       (self.high.shift(2) > self.high.shift(1)) & (self.high.shift(2) > self.high)
        swing_l_cond = (self.low.shift(2) < self.low.shift(3)) & (self.low.shift(2) < self.low.shift(4)) & \
                       (self.low.shift(2) < self.low.shift(1)) & (self.low.shift(2) < self.low)
        
        last_swing_h_price = pd.Series(np.where(swing_h_cond, self.high.shift(2), np.nan)).ffill()
        last_swing_l_price = pd.Series(np.where(swing_l_cond, self.low.shift(2), np.nan)).ffill()
        
        # 75. pa_swing_high_dist
        self.df['pa_swing_high_dist'] = (last_swing_h_price - self.close) / self.close.clip(lower=1e-9)
        self.df['pa_swing_high_dist'] = self.df['pa_swing_high_dist'].fillna(0)
        
        # 76. pa_swing_low_dist
        self.df['pa_swing_low_dist'] = (self.close - last_swing_l_price) / self.close.clip(lower=1e-9)
        self.df['pa_swing_low_dist'] = self.df['pa_swing_low_dist'].fillna(0)
        
        # 77. pa_price_rejection_score
        self.df['pa_price_rejection_score'] = (self.df['pa_upper_wick_ratio'] - self.df['pa_lower_wick_ratio']) * self.df['pa_true_range']
        
        # 78. pa_bars_since_swing_h
        blocks_h = swing_h_cond.astype(int).cumsum()
        self.df['pa_bars_since_swing_h'] = self.df.groupby(blocks_h).cumcount() + 2
        
        # 79. pa_bars_since_swing_l
        blocks_l = swing_l_cond.astype(int).cumsum()
        self.df['pa_bars_since_swing_l'] = self.df.groupby(blocks_l).cumcount() + 2
        
        # 80. pa_dist_to_anchor (Restored Daily Anchor / Midnight Open Distance robust logic)
        # Find the time column for daily grouping
        time_col = None
        if pd.api.types.is_datetime64_any_dtype(self.df.index):
            time_col = pd.Series(self.df.index.date, index=self.df.index)
        elif 'timestamp' in self.df.columns:
            time_col = pd.to_datetime(self.df['timestamp']).dt.date
        elif 'time' in self.df.columns:
            time_col = pd.to_datetime(self.df['time']).dt.date
        elif 'datetime' in self.df.columns:
            time_col = pd.to_datetime(self.df['datetime']).dt.date
            
        if time_col is not None:
            proxy_open = self.df.groupby(time_col)['open'].transform('first')
        else:
            # 288 bars = 24 hours of 5-min candles. Fallback for non-datetime index.
            proxy_open = self.open_p.shift(288).ffill().fillna(self.open_p)
            
        self.df['pa_dist_to_anchor'] = (self.close - proxy_open) / proxy_open.clip(lower=1e-9)
        
        # 81. pa_fractal_dimension (Restored Choppiness Index formulation)
        # The previous raw log(path) / log(net) is scale-dependent. This scales beautifully.
        sum_tr = self.df['pa_true_range'].rolling(20, min_periods=1).sum()
        net_range = (rolling_high_20 - rolling_low_20).clip(lower=1e-9)
        self.df['pa_fractal_dimension'] = np.log10(sum_tr / net_range) / np.log10(20)
        self.df['pa_fractal_dimension'] = self.df['pa_fractal_dimension'].replace([np.inf, -np.inf], 0).fillna(0)
        
        # 82. pa_donchian_pos
        self.df['pa_donchian_pos'] = (self.close - rolling_low_20) / np.maximum(rolling_high_20 - rolling_low_20, 1e-9)
        
        # 83. pa_hist_volatility
        self.df['pa_hist_volatility'] = self.df['pa_log_returns'].rolling(20, min_periods=1).std().fillna(0)
        
        # 84. pa_frac_diff_proxy
        # Fractional Differencing (Simplified proxy for fast vectorised HFT)
        # True frac diff requires expanding window math. Here we use an institutional proxy:
        # weighted blend of Return and Price Z-score
        self.df['pa_frac_diff_proxy'] = (0.5 * self.df['pa_log_returns']) + (0.5 * self.df.get('pa_rolling_z_score', pd.Series(0)).diff().fillna(0))
        
        # 85. pa_inside_outside
        is_inside = (self.high <= self.high.shift(1)) & (self.low >= self.low.shift(1))
        is_outside = (self.high > self.high.shift(1)) & (self.low < self.low.shift(1))
        self.df['pa_inside_outside'] = np.where(is_outside, 1, np.where(is_inside, -1, 0))
        
        # 86. pa_structural_anchor_variance
        self.df['pa_structural_anchor_variance'] = self.df['pa_dist_to_anchor'].rolling(10, min_periods=1).var().fillna(0)
        
        # 87. pa_swing_efficiency_ratio
        self.df['pa_swing_efficiency_ratio'] = self.df['pa_swing_high_dist'] / self.df['pa_swing_low_dist'].replace(0, 1e-9)
        
        # 88. pa_support_resistance_density
        self.df['pa_support_resistance_density'] = (self.df['pa_dist_to_support'] + self.df['pa_dist_to_resistance']) / self.candle_range
