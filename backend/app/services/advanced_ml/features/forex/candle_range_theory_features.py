import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class CandleRangeTheoryEngine:
    """
    100% Modular, Vectorised, Hedge-Fund Grade Feature Engineering for Candle Range Theory (CRT).
    Focus: Advanced metrics on intra-candle and multi-candle range dynamics without lookahead bias.
    Contains 62 unique metrics prefixed with 'crt_'.
    """
    
    def __init__(self, df_raw: pd.DataFrame):
        self.df = df_raw.copy()
        
    def generate_all_features(self) -> pd.DataFrame:
        if self.df.empty:
            return self.df
            
        required_cols = ['open', 'high', 'low', 'close']
        for col in required_cols:
            if col not in self.df.columns:
                logger.warning(f"Missing column '{col}' for Candle Range Theory features.")
                return self.df
                
        try:
            self._precompute_bases()
            
            # Phase 1-5: The Originals (Modified & Optimized)
            self._calc_phase_original()
            
            # Phase 6-15: Hedge-Fund Grade Advanced Metrics
            self._calc_phase_6_overlap_gap()
            self._calc_phase_7_advanced_wick()
            self._calc_phase_8_master_candle_trap()
            self._calc_phase_9_intra_candle_asymmetry()
            self._calc_phase_10_adr_fractional()
            self._calc_phase_11_fractal_kinematics()
            self._calc_phase_12_body_dominance()
            self._calc_phase_13_squeeze_cycles()
            self._calc_phase_14_structural_density()
            self._calc_phase_15_exhaustion_geometry()
            
        except Exception as e:
            logger.error(f"Error calculating Candle Range Theory features: {e}")
            
        # Final NaN/Inf safeguard
        self.df = self.df.replace([np.inf, -np.inf], np.nan)
        self.df = self.df.ffill().fillna(0)
        
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
        
        self.avg_range_20 = self.candle_range.rolling(20, min_periods=1).mean()
        self.std_range_20 = self.candle_range.rolling(20, min_periods=1).std()
        
        self.rolling_high_5 = self.high.rolling(5, min_periods=1).max().shift(1)
        self.rolling_low_5 = self.low.rolling(5, min_periods=1).min().shift(1)
        self.rolling_range_5 = (self.rolling_high_5 - self.rolling_low_5).clip(lower=1e-9)

    def _calc_phase_original(self):
        # ==========================================
        # PHASE 1: Master Candle & Range Compression
        # ==========================================
        # A master candle is defined here as a candle whose range encapsulates the next N candles.
        # However, dynamically checking forward creates data leakage (lookahead bias).
        # Instead, we look backward: Is the current candle compressed inside a recent large candle?
        
        # 1. crt_master_candle_active_state
        # 1 if current candle is completely inside the 5-period lookback range, -1 if breaking out
        is_inside_master = (self.high <= self.rolling_high_5) & (self.low >= self.rolling_low_5)
        self.df['crt_master_candle_active_state'] = np.where(is_inside_master, 1, -1)
        
        # 2. crt_master_candle_compression_ratio
        # How compressed is the current candle relative to the 5-period macro range
        self.df['crt_master_candle_compression_ratio'] = self.candle_range / self.rolling_range_5
        
        # 3. crt_master_candle_breakout_prob (Proxy based on compression and proximity to edges)
        # Higher when highly compressed and near the high/low of the master range
        dist_to_high = (self.rolling_high_5 - self.close) / self.rolling_range_5
        dist_to_low = (self.close - self.rolling_low_5) / self.rolling_range_5
        edge_proximity = 1.0 - np.minimum(dist_to_high, dist_to_low)
        self.df['crt_master_candle_breakout_prob'] = edge_proximity * (1.0 - self.df['crt_master_candle_compression_ratio'])
        
        # ==========================================
        # PHASE 2: Range Expansion & Contraction
        # ==========================================
        
        # 4. crt_nr4_nr7_state
        # Narrow Range 4/7: Current range is the narrowest of the last 4 or 7 bars.
        range_min_3 = self.candle_range.shift(1).rolling(3, min_periods=1).min()
        range_min_6 = self.candle_range.shift(1).rolling(6, min_periods=1).min()
        is_nr4 = self.candle_range < range_min_3
        is_nr7 = self.candle_range < range_min_6
        self.df['crt_nr4_nr7_state'] = np.where(is_nr7, 2, np.where(is_nr4, 1, 0))
        
        # 5. crt_range_expansion_velocity
        # Momentum of the candle range expansion
        self.df['crt_range_expansion_velocity'] = (self.candle_range - self.avg_range_20) / self.avg_range_20.clip(lower=1e-9)
        
        # 6. crt_vcp_contraction_count
        # Count consecutive periods where volatility (range) is contracting
        range_contracting = (self.candle_range < self.candle_range.shift(1)).astype(int)
        range_contract_blocks = (range_contracting != range_contracting.shift(1)).cumsum()
        self.df['crt_vcp_contraction_count'] = range_contracting.groupby(range_contract_blocks).cumcount() + 1
        self.df['crt_vcp_contraction_count'] *= range_contracting  # Reset to 0 when not contracting
        
        # ==========================================
        # PHASE 3: Candle Quartile & Price Delivery
        # ==========================================
        
        # 7-8. crt_close_in_upper_quartile, lower_quartile
        upper_quartile_bound = self.low + (self.candle_range * 0.75)
        lower_quartile_bound = self.low + (self.candle_range * 0.25)
        self.df['crt_close_in_upper_quartile'] = (self.close >= upper_quartile_bound).astype(float)
        self.df['crt_close_in_lower_quartile'] = (self.close <= lower_quartile_bound).astype(float)
        
        # 9. crt_body_center_of_gravity_shift
        # Shift of the candle body midpoint from the total High-Low midpoint
        hl_mid = (self.high + self.low) / 2
        body_mid = (self.open_p + self.close) / 2
        self.df['crt_body_center_of_gravity_shift'] = (body_mid - hl_mid) / self.candle_range
        
        # ==========================================
        # PHASE 4: Wick Theory & Fills
        # ==========================================
        
        # 10. crt_wick_to_range_dominance
        self.df['crt_wick_to_range_dominance'] = (self.upper_wick + self.lower_wick) / self.candle_range
        
        # 11. crt_unfilled_wick_proximity
        # Proximity to the highest high or lowest low of the last 10 bars (representing major wicks)
        extreme_high = self.high.rolling(10, min_periods=1).max()
        extreme_low = self.low.rolling(10, min_periods=1).min()
        dist_to_extreme_h = (extreme_high - self.close) / self.candle_range
        dist_to_extreme_l = (self.close - extreme_low) / self.candle_range
        self.df['crt_unfilled_wick_proximity'] = np.minimum(dist_to_extreme_h, dist_to_extreme_l)
        
        # 12. crt_wick_fill_probability
        # If previous candle had a long wick, probability of current candle trading into it
        prev_upper_wick_ratio = self.upper_wick.shift(1) / self.candle_range.shift(1).clip(lower=1e-9)
        prev_lower_wick_ratio = self.lower_wick.shift(1) / self.candle_range.shift(1).clip(lower=1e-9)
        self.df['crt_wick_fill_probability'] = np.maximum(prev_upper_wick_ratio, prev_lower_wick_ratio)
        
        # ==========================================
        # PHASE 5: Exhaustion & Institutional Ranges
        # ==========================================
        
        # 13. crt_adr_exhaustion_score
        self.df['crt_adr_exhaustion_score'] = self.candle_range / self.avg_range_20.clip(lower=1e-9)
        
        # 14. crt_range_deviation_bands_dist
        upper_range_band = self.avg_range_20 + (2 * self.std_range_20.fillna(0))
        self.df['crt_range_deviation_bands_dist'] = (upper_range_band - self.candle_range) / self.avg_range_20.clip(lower=1e-9)
        
        # 15. crt_orb_extension_magnitude
        prev_range = self.candle_range.shift(1)
        extension_up = np.maximum(0, self.close - self.high.shift(1))
        extension_down = np.maximum(0, self.low.shift(1) - self.close)
        self.df['crt_orb_extension_magnitude'] = (extension_up + extension_down) / prev_range.clip(lower=1e-9)
        
        # 16. crt_dealer_range_proxy
        body_overlap = (np.minimum(np.maximum(self.open_p, self.close), np.maximum(self.open_p.shift(1), self.close.shift(1))) - 
                        np.maximum(np.minimum(self.open_p, self.close), np.minimum(self.open_p.shift(1), self.close.shift(1))))
        body_overlap = np.maximum(0, body_overlap)
        self.df['crt_dealer_range_proxy'] = (body_overlap / self.body_range.clip(lower=1e-9)).rolling(3, min_periods=1).mean()

    def _calc_phase_6_overlap_gap(self):
        prev_h, prev_l = self.high.shift(1), self.low.shift(1)
        
        # 17. crt_range_overlap_pct
        overlap_h = np.minimum(self.high, prev_h)
        overlap_l = np.maximum(self.low, prev_l)
        overlap_range = np.maximum(0, overlap_h - overlap_l)
        self.df['crt_range_overlap_pct'] = overlap_range / self.candle_range
        
        # 18. crt_implied_range_gap
        gap_up = np.maximum(0, self.low - prev_h)
        gap_down = np.maximum(0, prev_l - self.high)
        self.df['crt_implied_range_gap'] = gap_up + gap_down
        
        # 19. crt_multi_bar_engulfment_count
        engulfs_1 = (self.high > prev_h) & (self.low < prev_l)
        engulfs_2 = engulfs_1 & (self.high > self.high.shift(2)) & (self.low < self.low.shift(2))
        engulfs_3 = engulfs_2 & (self.high > self.high.shift(3)) & (self.low < self.low.shift(3))
        self.df['crt_multi_bar_engulfment_count'] = engulfs_1.astype(int) + engulfs_2.astype(int) + engulfs_3.astype(int)
        
        # 20. crt_two_bar_reversal_yield
        is_reversal = (self.close > self.open_p) != (self.close.shift(1) > self.open_p.shift(1))
        yield_val = self.candle_range / self.candle_range.shift(1).clip(lower=1e-9)
        self.df['crt_two_bar_reversal_yield'] = np.where(is_reversal, yield_val, 0)

    def _calc_phase_7_advanced_wick(self):
        prev_up_wick = self.upper_wick.shift(1)
        prev_dn_wick = self.lower_wick.shift(1)
        prev_h, prev_l = self.high.shift(1), self.low.shift(1)
        
        # 21. crt_wick_damage_pct
        dmg_up = np.maximum(0, self.close - (prev_h - prev_up_wick)) / prev_up_wick.clip(lower=1e-9)
        dmg_dn = np.maximum(0, (prev_l + prev_dn_wick) - self.close) / prev_dn_wick.clip(lower=1e-9)
        self.df['crt_wick_damage_pct'] = np.where(prev_up_wick > prev_dn_wick, dmg_up, dmg_dn)
        
        # 22. crt_consecutive_wick_rejections
        is_up_rej = (self.upper_wick / self.candle_range) > 0.25
        is_dn_rej = (self.lower_wick / self.candle_range) > 0.25
        up_strk = is_up_rej.astype(int) + (is_up_rej & is_up_rej.shift(1)).astype(int)
        dn_strk = is_dn_rej.astype(int) + (is_dn_rej & is_dn_rej.shift(1)).astype(int)
        self.df['crt_consecutive_wick_rejections'] = np.maximum(up_strk, dn_strk)
        
        # 23. crt_wick_to_body_expansion_rate
        avg_w = (self.upper_wick + self.lower_wick).rolling(3, min_periods=1).mean()
        avg_b = self.body_range.rolling(3, min_periods=1).mean()
        self.df['crt_wick_to_body_expansion_rate'] = avg_w / avg_b.clip(lower=1e-9)
        
        # 24. crt_wick_zone_consolidation_count
        ext_h_5 = self.high.rolling(5).max()
        ext_l_5 = self.low.rolling(5).min()
        inside = (self.high < ext_h_5) & (self.low > ext_l_5) & (self.candle_range < self.avg_range_20)
        self.df['crt_wick_zone_consolidation_count'] = inside.rolling(3).sum()
        
        # 25. crt_structural_wick_penetration
        ext_h_20 = self.high.rolling(20, min_periods=1).max().shift(1)
        ext_l_20 = self.low.rolling(20, min_periods=1).min().shift(1)
        self.df['crt_structural_wick_penetration'] = ((self.close > ext_h_20) | (self.close < ext_l_20)).astype(float)

    def _calc_phase_8_master_candle_trap(self):
        # 26. crt_inside_bar_fakeout_trap
        broke_high = self.high > self.rolling_high_5
        broke_low = self.low < self.rolling_low_5
        closed_inside = (self.close < self.rolling_high_5) & (self.close > self.rolling_low_5)
        self.df['crt_inside_bar_fakeout_trap'] = ((broke_high | broke_low) & closed_inside).astype(float)
        
        # 27. crt_master_candle_time_decay
        is_inside = (self.high <= self.rolling_high_5) & (self.low >= self.rolling_low_5)
        is_inside_blocks = (is_inside != is_inside.shift(1)).cumsum()
        time_inside = is_inside.groupby(is_inside_blocks).cumcount() + 1
        self.df['crt_master_candle_time_decay'] = time_inside * is_inside
        
        # 28. crt_volatility_cone_state
        lh = self.high < self.high.shift(1)
        hl = self.low > self.low.shift(1)
        self.df['crt_volatility_cone_state'] = (lh & hl & lh.shift(1) & hl.shift(1)).astype(float)

    def _calc_phase_9_intra_candle_asymmetry(self):
        # 29. crt_open_drive_asymmetry
        dist_open_h = self.high - self.open_p
        dist_open_l = self.open_p - self.low
        self.df['crt_open_drive_asymmetry'] = (dist_open_h - dist_open_l) / self.candle_range
        
        # 30. crt_close_drive_asymmetry
        dist_close_h = self.high - self.close
        dist_close_l = self.close - self.low
        self.df['crt_close_drive_asymmetry'] = (dist_close_h - dist_close_l) / self.candle_range
        
        # 31. crt_range_quartile_transition
        open_q = np.floor(4 * (self.open_p - self.low) / self.candle_range.clip(lower=1e-9)).clip(0, 3) + 1
        close_q = np.floor(4 * (self.close - self.low) / self.candle_range.clip(lower=1e-9)).clip(0, 3) + 1
        self.df['crt_range_quartile_transition'] = close_q - open_q
        
        # 32. crt_body_wick_skewness
        ratio = self.body_range / (self.upper_wick + self.lower_wick).clip(lower=1e-9)
        self.df['crt_body_wick_skewness'] = ratio.rolling(10, min_periods=1).skew().fillna(0)

    def _calc_phase_10_adr_fractional(self):
        # 33. crt_session_range_completion_pct
        cum_range = self.candle_range.rolling(5, min_periods=1).sum()
        self.df['crt_session_range_completion_pct'] = cum_range / (self.avg_range_20 * 5)
        
        # 34. crt_adr_extension_magnitude
        self.df['crt_adr_extension_magnitude'] = np.maximum(0, self.candle_range - self.avg_range_20) / self.avg_range_20.clip(lower=1e-9)
        
        # 35. crt_bullish_range_dominance_rolling
        is_bull = self.close > self.open_p
        bull_r = np.where(is_bull, self.candle_range, 0)
        bear_r = np.where(~is_bull, self.candle_range, 0)
        sum_bull = pd.Series(bull_r).rolling(10, min_periods=1).sum()
        sum_bear = pd.Series(bear_r).rolling(10, min_periods=1).sum()
        self.df['crt_bullish_range_dominance_rolling'] = sum_bull / (sum_bull + sum_bear).clip(lower=1e-9)
        
        # 36. crt_range_expansion_sustainability
        is_expanded = self.candle_range > self.avg_range_20
        dist_to_extreme = np.minimum(self.high - self.close, self.close - self.low)
        self.df['crt_range_expansion_sustainability'] = np.where(is_expanded, 1.0 - (dist_to_extreme / self.candle_range), 0)
        
        # 37. crt_range_fractal_efficiency
        net_dist = np.abs(self.close - self.close.shift(10))
        tot_dist = self.candle_range.rolling(10, min_periods=1).sum()
        self.df['crt_range_fractal_efficiency'] = net_dist / tot_dist.clip(lower=1e-9)

    def _calc_phase_11_fractal_kinematics(self):
        # 38. crt_range_velocity_proxy
        self.df['crt_range_velocity_proxy'] = self.candle_range - self.candle_range.shift(1)
        
        # 39. crt_range_acceleration_proxy
        self.df['crt_range_acceleration_proxy'] = self.df['crt_range_velocity_proxy'] - self.df['crt_range_velocity_proxy'].shift(1)
        
        # 40. crt_jerk_range_proxy
        self.df['crt_jerk_range_proxy'] = self.df['crt_range_acceleration_proxy'] - self.df['crt_range_acceleration_proxy'].shift(1)

    def _calc_phase_12_body_dominance(self):
        # 41. crt_elasticity_of_wicks
        var_wick = (self.upper_wick + self.lower_wick).rolling(10, min_periods=1).var()
        var_body = self.body_range.rolling(10, min_periods=1).var()
        self.df['crt_elasticity_of_wicks'] = var_wick / var_body.clip(lower=1e-9)
        
        # 42. crt_true_body_momentum
        dir_body = np.where(self.close > self.open_p, self.body_range, -self.body_range)
        self.df['crt_true_body_momentum'] = pd.Series(dir_body).rolling(10, min_periods=1).sum() / self.candle_range.rolling(10, min_periods=1).sum().clip(lower=1e-9)
        
        # 43. crt_mean_reversion_wick_proxy
        max_wick = np.maximum(self.upper_wick, self.lower_wick)
        is_max = max_wick == max_wick.rolling(5, min_periods=1).max()
        ext_mid = np.where(self.upper_wick > self.lower_wick, self.high - self.upper_wick/2, self.low + self.lower_wick/2)
        ext_mid_series = pd.Series(ext_mid).where(is_max).ffill()
        self.df['crt_mean_reversion_wick_proxy'] = (self.close - ext_mid_series) / self.candle_range

    def _calc_phase_13_squeeze_cycles(self):
        # 44. crt_time_since_max_range
        max_idx = self.candle_range.rolling(20).apply(np.argmax, raw=True)
        self.df['crt_time_since_max_range'] = 19 - max_idx.fillna(0)
        
        # 45. crt_time_since_min_range
        min_idx = self.candle_range.rolling(20).apply(np.argmin, raw=True)
        self.df['crt_time_since_min_range'] = 19 - min_idx.fillna(0)
        
        # 46. crt_range_percentile_rank
        # Using a simpler proxy for rank to keep it vectorized if possible, but rolling apply is fine
        self.df['crt_range_percentile_rank'] = self.candle_range.rolling(100, min_periods=1).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False).fillna(0.5)
        
        # 47. crt_squeeze_to_expansion_ratio
        min_r5 = self.candle_range.rolling(5, min_periods=1).min()
        max_r5 = self.candle_range.rolling(5, min_periods=1).max()
        self.df['crt_squeeze_to_expansion_ratio'] = min_r5 / max_r5.clip(lower=1e-9)

    def _calc_phase_14_structural_density(self):
        # 48. crt_cluster_range_density
        up_b = self.close + self.avg_range_20/2
        dn_b = self.close - self.avg_range_20/2
        inside = (self.close <= up_b) & (self.close >= dn_b)
        self.df['crt_cluster_range_density'] = inside.rolling(10, min_periods=1).sum()
        
        # 49. crt_three_bar_net_displacement
        net_3 = self.high.rolling(3, min_periods=1).max() - self.low.rolling(3, min_periods=1).min()
        sum_3 = self.candle_range.rolling(3, min_periods=1).sum()
        self.df['crt_three_bar_net_displacement'] = net_3 / sum_3.clip(lower=1e-9)
        
        # 50. crt_five_bar_net_displacement
        net_5 = self.high.rolling(5, min_periods=1).max() - self.low.rolling(5, min_periods=1).min()
        sum_5 = self.candle_range.rolling(5, min_periods=1).sum()
        self.df['crt_five_bar_net_displacement'] = net_5 / sum_5.clip(lower=1e-9)
        
        # 51. crt_range_centroid_shift
        mid = (self.high + self.low) / 2
        self.df['crt_range_centroid_shift'] = (mid - mid.shift(1)) / self.avg_range_20.clip(lower=1e-9)

    def _calc_phase_15_exhaustion_geometry(self):
        # 52. crt_upper_tail_exhaustion_rate
        avg_up = self.upper_wick.rolling(10, min_periods=1).mean()
        self.df['crt_upper_tail_exhaustion_rate'] = avg_up / self.avg_range_20.clip(lower=1e-9)
        
        # 53. crt_lower_tail_exhaustion_rate
        avg_dn = self.lower_wick.rolling(10, min_periods=1).mean()
        self.df['crt_lower_tail_exhaustion_rate'] = avg_dn / self.avg_range_20.clip(lower=1e-9)
        
        # 54. crt_tail_asymmetry_index
        self.df['crt_tail_asymmetry_index'] = self.df['crt_upper_tail_exhaustion_rate'] / self.df['crt_lower_tail_exhaustion_rate'].clip(lower=1e-9)
        
        # 55. crt_proximity_to_rolling_high_range
        max_h = self.high.rolling(20, min_periods=1).max()
        self.df['crt_proximity_to_rolling_high_range'] = (max_h - self.close) / self.avg_range_20.clip(lower=1e-9)
        
        # 56. crt_proximity_to_rolling_low_range
        min_l = self.low.rolling(20, min_periods=1).min()
        self.df['crt_proximity_to_rolling_low_range'] = (self.close - min_l) / self.avg_range_20.clip(lower=1e-9)
        
        # 57. crt_volatility_adjusted_body_shift
        self.df['crt_volatility_adjusted_body_shift'] = self.df['crt_body_center_of_gravity_shift'] * self.df.get('crt_range_percentile_rank', 0.5)
        
        # 58. crt_quartile_density_oscillator
        q_val = self.df.get('crt_range_quartile_transition', pd.Series(0, index=self.df.index))
        self.df['crt_quartile_density_oscillator'] = q_val.rolling(10, min_periods=1).mean() / 3.0
        
        # 59. crt_reversal_range_velocity
        is_rev = (self.close > self.open_p) != (self.close.shift(1) > self.open_p.shift(1))
        self.df['crt_reversal_range_velocity'] = np.where(is_rev, self.candle_range / self.candle_range.shift(1).clip(lower=1e-9), 0)
        
        # 60. crt_wick_engulfment_magnitude
        engulfs_up_wick = (self.close > self.high.shift(1)) & (self.open_p < self.high.shift(1) - self.upper_wick.shift(1))
        engulfs_dn_wick = (self.close < self.low.shift(1)) & (self.open_p > self.low.shift(1) + self.lower_wick.shift(1))
        mag = self.body_range / (self.upper_wick.shift(1) + self.lower_wick.shift(1)).clip(lower=1e-9)
        self.df['crt_wick_engulfment_magnitude'] = np.where(engulfs_up_wick | engulfs_dn_wick, mag, 0)
        
        # 61. crt_range_gap_fill_velocity
        gap = self.df.get('crt_implied_range_gap', pd.Series(0, index=self.df.index))
        filled = (gap > 0) & ((self.high >= self.low.shift(2)) | (self.low <= self.high.shift(2)))
        self.df['crt_range_gap_fill_velocity'] = filled.rolling(3).sum() 
        
        # 62. crt_range_golden_ratio_proximity
        ratio = self.candle_range / self.candle_range.shift(1).clip(lower=1e-9)
        dist_1618 = np.abs(ratio - 1.618)
        dist_0618 = np.abs(ratio - 0.618)
        self.df['crt_range_golden_ratio_proximity'] = np.minimum(dist_1618, dist_0618)
