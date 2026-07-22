import pandas as pd
import numpy as np
from typing import List

def generate_plp_liquidity_cluster_features(df: pd.DataFrame, selected_features: List[str]) -> pd.DataFrame:
    """Module 1: Synthetic Liquidity Cluster & Density Module (19 Features)"""
    
    bid_vols = [c for c in df.columns if c.startswith('bid_vol') and c != 'bid_volume']
    ask_vols = [c for c in df.columns if c.startswith('ask_vol') and c != 'ask_volume']
    
    deep_bids = [c for c in bid_vols if c not in ['bid_vol1', 'bid_vol2', 'bid_vol3']]
    deep_asks = [c for c in ask_vols if c not in ['ask_vol1', 'ask_vol2', 'ask_vol3']]
    
    total_deep_bid = df[deep_bids].sum(axis=1) if deep_bids else pd.Series(0, index=df.index)
    total_deep_ask = df[deep_asks].sum(axis=1) if deep_asks else pd.Series(0, index=df.index)
    total_vol = df[bid_vols].sum(axis=1) + df[ask_vols].sum(axis=1) if bid_vols else pd.Series(1, index=df.index)

    if 'abs_long_liq_pool_proxy' in selected_features: df['abs_long_liq_pool_proxy'] = total_deep_bid
    if 'abs_short_liq_pool_proxy' in selected_features: df['abs_short_liq_pool_proxy'] = total_deep_ask
        
    if 'liquidation_density_z_score_proxy' in selected_features:
        z = (total_vol - total_vol.rolling(20).mean()) / total_vol.rolling(20).std().replace(0, np.nan)
        df['liquidation_density_z_score_proxy'] = z.fillna(0)
        
    if 'leverage_washout_z_score_proxy' in selected_features and 'bid_vol1' in df.columns:
        washout = abs(df['bid_vol1'].diff().clip(upper=0)) + abs(df['ask_vol1'].diff().clip(upper=0))
        z_wash = (washout - washout.rolling(20).mean()) / washout.rolling(20).std().replace(0, np.nan)
        df['leverage_washout_z_score_proxy'] = z_wash.fillna(0)

    if 'high_leverage_cluster_proximity_proxy' in selected_features and 'bid1' in df.columns and 'bid5' in df.columns:
        df['high_leverage_cluster_proximity_proxy'] = (df['bid1'] - df['bid5']) / df['bid1']
        
    if 'margin_call_proximity_index_proxy' in selected_features and 'ask5' in df.columns and 'ask1' in df.columns:
        df['margin_call_proximity_index_proxy'] = (df['ask5'] - df['ask1']) / df['ask1']

    if 'magnetic_liquidity_pull_vector_proxy' in selected_features:
        df['magnetic_liquidity_pull_vector_proxy'] = np.where(total_deep_bid > total_deep_ask, -1, np.where(total_deep_ask > total_deep_bid, 1, 0))

    if 'liq_cluster_density_heatmap_proxy' in selected_features:
        df['liq_cluster_density_heatmap_proxy'] = (total_deep_bid + total_deep_ask) / total_vol.replace(0, np.nan).fillna(1)

    if 'synthetic_leverage_ratio_proxy' in selected_features and 'bid_vol1' in df.columns:
        top_vol = df['bid_vol1'] + df['ask_vol1']
        df['synthetic_leverage_ratio_proxy'] = top_vol / total_vol.replace(0, np.nan).fillna(1)

    if 'hidden_liquidity_absorption_proxy' in selected_features and 'bid1' in df.columns:
        price_var = ((df['bid1'] + df['ask1']) / 2).rolling(10).var().replace(0, 1e-9)
        df['hidden_liquidity_absorption_proxy'] = (total_vol.rolling(10).mean() / price_var).fillna(0)

    if 'stale_liquidity_decay_proxy' in selected_features and deep_bids:
        decay = (df[deep_bids[0]].diff().clip(upper=0) + df[deep_asks[0]].diff().clip(upper=0)).abs()
        df['stale_liquidity_decay_proxy'] = decay.rolling(5).mean().fillna(0)

    if 'cross_margin_cascade_risk_proxy' in selected_features and 'bid1' in df.columns:
        spread = df['ask1'] - df['bid1']
        df['cross_margin_cascade_risk_proxy'] = spread.rolling(5).std().fillna(0) * total_vol

    if 'stealth_liquidation_proxies_proxy' in selected_features and 'bid_vol1' in df.columns:
        df['stealth_liquidation_proxies_proxy'] = df['bid_vol1'].diff().abs().rolling(3).sum() * (df['bid1'].diff() == 0).astype(int)

    if 'gamma_exposure_imbalance_proxy' in selected_features and 'bid_vol1' in df.columns:
        df['gamma_exposure_imbalance_proxy'] = (df['bid_vol1'].diff().diff() - df['ask_vol1'].diff().diff()).fillna(0)

    if 'zero_dte_options_proxy_pull' in selected_features and 'bid1' in df.columns:
        mid = (df['bid1'] + df['ask1']) / 2
        mom = mid.diff(3).fillna(0)
        df['zero_dte_options_proxy_pull'] = mom * total_vol

    if 'retail_pain_threshold_proxy' in selected_features and 'bid1' in df.columns:
        spread = df['ask1'] - df['bid1']
        pain = (spread > spread.rolling(50).mean()).astype(int)
        df['retail_pain_threshold_proxy'] = pain.rolling(10).sum()

    if 'liquidation_void_zones_proxy' in selected_features:
        df['liquidation_void_zones_proxy'] = np.where((total_deep_bid + total_deep_ask) < total_vol * 0.1, 1, 0)

    if 'smart_money_trap_indicator_proxy' in selected_features and 'bid1' in df.columns:
        mid = (df['bid1'] + df['ask1']) / 2
        price_trend = np.sign(mid.diff(3)).values
        vol_trend = np.sign(df['bid_vol1'].diff(3) - df['ask_vol1'].diff(3)).values
        df['smart_money_trap_indicator_proxy'] = np.where((price_trend > 0) & (vol_trend < 0), -1, np.where((price_trend < 0) & (vol_trend > 0), 1, 0))

    if 'leveraged_retail_skew_proxy' in selected_features and 'bid_vol1' in df.columns:
        df['leveraged_retail_skew_proxy'] = (df['bid_vol1'] - df['ask_vol1']) / (df['bid_vol1'] + df['ask_vol1'] + 1e-9)

    return df

def generate_plp_cascade_features(df: pd.DataFrame, selected_features: List[str]) -> pd.DataFrame:
    """Module 2: Cascade & Trigger Dynamics Module (17 Features)"""
    
    mid = None
    if 'bid1' in df.columns and 'ask1' in df.columns:
        mid = (df['bid1'] + df['ask1']) / 2
        spread = df['ask1'] - df['bid1']
        
    bid_vols = [c for c in df.columns if c.startswith('bid_vol') and c != 'bid_volume']
    ask_vols = [c for c in df.columns if c.startswith('ask_vol') and c != 'ask_volume']
    total_vol = df[bid_vols].sum(axis=1) + df[ask_vols].sum(axis=1) if bid_vols else pd.Series(1, index=df.index)

    if 'liquidation_cascade_multiplier_proxy' in selected_features and mid is not None:
        spread_widening = (spread.diff() > 0).astype(int)
        depth_dropping = (total_vol.diff() < 0).astype(int)
        cascade = spread_widening & depth_dropping
        df['liquidation_cascade_multiplier_proxy'] = cascade.rolling(3).sum()

    if 'long_squeeze_probability_proxy' in selected_features and mid is not None:
        df['long_squeeze_probability_proxy'] = np.where((mid.diff() < 0) & (df['bid_vol1'].diff() < 0), 1, 0)

    if 'short_squeeze_probability_proxy' in selected_features and mid is not None:
        df['short_squeeze_probability_proxy'] = np.where((mid.diff() > 0) & (df['ask_vol1'].diff() < 0), 1, 0)

    if 'cascade_velocity_index_proxy' in selected_features:
        df['cascade_velocity_index_proxy'] = total_vol.pct_change().rolling(3).mean().fillna(0)

    if 'domino_effect_threshold_proxy' in selected_features:
        drop = total_vol.diff()
        df['domino_effect_threshold_proxy'] = (drop < -3 * drop.rolling(20).std()).astype(int)

    if 'cascade_decay_rate_proxy' in selected_features and mid is not None:
        df['cascade_decay_rate_proxy'] = spread.ewm(span=5).mean().pct_change().fillna(0)

    if 'forced_liquidation_trigger_pts_proxy' in selected_features and mid is not None:
        df['forced_liquidation_trigger_pts_proxy'] = np.where(total_vol.diff() < -total_vol.rolling(10).std(), mid, 0)

    if 'volatility_expansion_on_liq_proxy' in selected_features and mid is not None:
        vol = mid.pct_change().rolling(5).std()
        liq = (total_vol.diff() < -total_vol.rolling(10).std()).astype(int)
        df['volatility_expansion_on_liq_proxy'] = (vol * liq).fillna(0)

    if 'squeeze_exhaustion_metric_proxy' in selected_features and 'bid_vol1' in df.columns:
        df['squeeze_exhaustion_metric_proxy'] = (df['bid_vol1'] / total_vol).rolling(10).std().fillna(0)

    if 'liquidator_bot_activity_proxy' in selected_features and 'bid_vol1' in df.columns:
        can = abs(df['bid_vol1'].diff().clip(upper=0))
        rep = df['bid_vol1'].diff().clip(lower=0)
        df['liquidator_bot_activity_proxy'] = (can * rep).rolling(3).mean().fillna(0)

    if 'domino_trigger_threshold_alpha_proxy' in selected_features and mid is not None:
        df['domino_trigger_threshold_alpha_proxy'] = mid.pct_change().abs().rolling(20).sum().fillna(0)

    if 'contagion_effect_probability_proxy' in selected_features and 'bid_vol5' in df.columns:
        corr = df['bid_vol1'].rolling(10).corr(df['bid_vol5']).fillna(0)
        df['contagion_effect_probability_proxy'] = np.where(corr > 0.8, 1, 0)

    if 'price_volume_dislocation_liq_proxy' in selected_features and mid is not None:
        price_dir = np.sign(mid.diff()).values
        vol_dir = np.sign(df['bid_vol1'].diff() - df['ask_vol1'].diff()).values
        df['price_volume_dislocation_liq_proxy'] = np.where(price_dir != vol_dir, 1, 0)

    if 'cascade_halflife_decay_proxy' in selected_features and mid is not None:
        df['cascade_halflife_decay_proxy'] = spread.rolling(10).apply(lambda x: np.sum(x > x.mean())).fillna(0)

    if 'liquidation_wall_impact_proxy' in selected_features and 'bid_vol1' in df.columns:
        df['liquidation_wall_impact_proxy'] = df['bid_vol1'] / df['bid_vol2'].replace(0, 1e-9)

    if 'short_squeeze_velocity_factor_proxy' in selected_features and mid is not None:
        df['short_squeeze_velocity_factor_proxy'] = np.where(mid.diff() > 0, df['ask_vol1'].diff().abs(), 0)

    if 'synthetic_domino_proxy' in selected_features and mid is not None:
        df['synthetic_domino_proxy'] = (spread.pct_change().rolling(3).apply(lambda x: np.prod(1+x)) - 1).fillna(0)

    return df

def generate_plp_stop_hunt_features(df: pd.DataFrame, selected_features: List[str]) -> pd.DataFrame:
    """Module 3: Stop-Hunt & Sweep Mechanism Module (15 Features)"""
    
    mid = None
    if 'bid1' in df.columns and 'ask1' in df.columns:
        mid = (df['bid1'] + df['ask1']) / 2
        spread = df['ask1'] - df['bid1']
        
    bid_vols = [c for c in df.columns if c.startswith('bid_vol') and c != 'bid_volume']
    ask_vols = [c for c in df.columns if c.startswith('ask_vol') and c != 'ask_volume']
    total_vol = df[bid_vols].sum(axis=1) + df[ask_vols].sum(axis=1) if bid_vols else pd.Series(1, index=df.index)

    if 'stop_hunt_probability_proxy' in selected_features and mid is not None:
        vol_spike = total_vol > total_vol.rolling(10).mean() + 2 * total_vol.rolling(10).std()
        price_spike = abs(mid.diff()) > abs(mid.diff()).rolling(10).mean() * 3
        df['stop_hunt_probability_proxy'] = (vol_spike & price_spike).astype(int)

    if 'liquidity_sweep_velocity_proxy' in selected_features:
        df['liquidity_sweep_velocity_proxy'] = total_vol.diff().abs() / spread.replace(0, 1e-9)

    if 'fakeout_prob_model_proxy' in selected_features and mid is not None:
        mom = mid.diff(3)
        rev = mid.diff().shift(-1) # Fakeout predicts next tick, but wait! NO SHIFT(-1)!
        # Fix: historical fakeout
        rev_hist = np.sign(mid.diff()) != np.sign(mid.diff().shift(1))
        df['fakeout_prob_model_proxy'] = np.where(rev_hist & (abs(mom.shift(1)) > 0.0001), 1, 0)

    if 'sweep_and_reversal_ratio_proxy' in selected_features and mid is not None:
        df['sweep_and_reversal_ratio_proxy'] = abs(mid.diff()) / abs(mid.diff(3)).replace(0, 1e-9)

    if 'stop_loss_trigger_density_proxy' in selected_features and 'bid1' in df.columns:
        # Proxy: round numbers
        dist_to_round = abs(df['bid1'] % 0.0010 - 0.0005)
        df['stop_loss_trigger_density_proxy'] = np.where(dist_to_round < 0.0001, total_vol, 0)

    if 'predatory_algo_footprint_proxy' in selected_features and 'bid_vol1' in df.columns:
        df['predatory_algo_footprint_proxy'] = (df['bid_vol1'].diff().abs() > df['bid_vol1'].rolling(20).std() * 3).astype(int)

    if 'institutional_sweep_divergence_proxy' in selected_features and 'bid_vol1' in df.columns:
        ofi = df['bid_vol1'].diff() - df['ask_vol1'].diff()
        df['institutional_sweep_divergence_proxy'] = np.where((np.sign(ofi) != np.sign(mid.diff())), 1, 0)

    if 'retail_trap_indicator_proxy' in selected_features and 'bid_vol1' in df.columns:
        df['retail_trap_indicator_proxy'] = (spread > spread.rolling(20).mean()).astype(int) * (df['bid_vol1'] < df['bid_vol2']).astype(int)

    if 'high_frequency_hunt_ratio_proxy' in selected_features and mid is not None:
        df['high_frequency_hunt_ratio_proxy'] = mid.rolling(10).apply(lambda x: sum(np.diff(np.sign(np.diff(x))) != 0)).fillna(0)

    if 'sweep_efficiency_score_proxy' in selected_features and mid is not None:
        df['sweep_efficiency_score_proxy'] = (abs(mid.diff()) / total_vol.diff().abs().replace(0, 1e-9)).fillna(0)

    if 'low_latency_sweep_detection_proxy' in selected_features and 'bid_vol3' in df.columns:
        df['low_latency_sweep_detection_proxy'] = ((df['bid_vol1'] == 0) & (df['bid_vol2'] == 0)).astype(int)

    if 'wash_trade_sweep_detection_proxy' in selected_features and 'bid_vol1' in df.columns:
        df['wash_trade_sweep_detection_proxy'] = ((df['bid_vol1'].diff() > 0) & (mid.diff() == 0)).astype(int)

    if 'institutional_footprint_masking_proxy' in selected_features and 'bid_vol1' in df.columns:
        df['institutional_footprint_masking_proxy'] = df['bid_vol1'].rolling(10).var().fillna(0) / (total_vol.rolling(10).var() + 1e-9)

    if 'fakeout_velocity_acceleration_proxy' in selected_features and mid is not None:
        df['fakeout_velocity_acceleration_proxy'] = mid.diff().diff().abs().fillna(0)

    if 'stop_hunt_asymmetry_proxy' in selected_features and 'bid_vol1' in df.columns:
        df['stop_hunt_asymmetry_proxy'] = (df['bid_vol1'].diff().abs() - df['ask_vol1'].diff().abs()).fillna(0)

    if 'retail_panic_sweep_proxy' in selected_features and 'bid1' in df.columns:
        df['retail_panic_sweep_proxy'] = ((spread > spread.rolling(20).mean() * 2) & (total_vol < total_vol.rolling(20).mean() * 0.5)).astype(int)

    if 'algo_hunt_intensity_proxy' in selected_features and 'bid_vol1' in df.columns:
        df['algo_hunt_intensity_proxy'] = (df['bid_vol1'].diff().abs() + df['ask_vol1'].diff().abs()).rolling(5).mean().fillna(0)

    return df

def inject_plp_features(df: pd.DataFrame, selected_features: List[str]) -> pd.DataFrame:
    """Main entry point for all 51 PLP features."""
    df = df.copy()
    df = generate_plp_liquidity_cluster_features(df, selected_features)
    df = generate_plp_cascade_features(df, selected_features)
    df = generate_plp_stop_hunt_features(df, selected_features)
    return df
