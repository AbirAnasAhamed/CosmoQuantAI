import React, { useState } from 'react';
import { Activity, Clock, Globe, Terminal, ChevronDown, CheckSquare, Square, Database, Trash2, TrendingUp, BarChart2, Zap, Target, Layers, AlignLeft } from 'lucide-react';
import { ForexScraperPanel } from '../../ml/forex/ForexScraperPanel';

export const FOREX_MODULES = [
    {
        id: 'basic_price_action',
        title: 'Basic Price Action',
        icon: AlignLeft,
        description: 'Core candlestick morphology and spreads.',
        source: 'ohlcv',
        features: [
            { id: 'log_return', name: 'Log Return (Close to Close)' },
            { id: 'candle_body_size', name: 'Candle Body Size' },
            { id: 'upper_shadow', name: 'Upper Shadow Size' },
            { id: 'lower_shadow', name: 'Lower Shadow Size' },
            { id: 'high_low_range', name: 'High-Low Range' },
            { id: 'typical_price', name: 'Typical Price' },
            { id: 'weighted_close', name: 'Weighted Close' },
            { id: 'median_price', name: 'Median Price' },
            { id: 'body_to_range_ratio', name: 'Body to Range Ratio' }
        ]
    },
    {
        id: 'trend_ma',
        title: 'Trend & Moving Averages',
        icon: TrendingUp,
        description: 'Trend identification and moving averages.',
        source: 'ohlcv',
        features: [
            { id: 'sma', name: 'Simple Moving Average (SMA)' },
            { id: 'ema', name: 'Exponential Moving Average (EMA)' },
            { id: 'wma', name: 'Weighted Moving Average (WMA)' },
            { id: 'hma', name: 'Hull Moving Average (HMA)' },
            { id: 'price_to_sma_ratio', name: 'Price to SMA Ratio' },
            { id: 'ma_crossover', name: 'Moving Average Crossover' },
            { id: 'macd_line', name: 'MACD Line' },
            { id: 'macd_signal', name: 'MACD Signal' },
            { id: 'macd_hist', name: 'MACD Histogram' },
            { id: 'parabolic_sar', name: 'Parabolic SAR' },
            { id: 'adx', name: 'ADX (Average Directional Index)' },
            { id: 'supertrend', name: 'Supertrend' }
        ]
    },
    {
        id: 'momentum_osc',
        title: 'Momentum Oscillators',
        icon: Zap,
        description: 'Overbought/Oversold and rate of change.',
        source: 'ohlcv',
        features: [
            { id: 'rsi', name: 'RSI (Relative Strength Index)' },
            { id: 'stoch_k', name: 'Stochastic %K' },
            { id: 'stoch_d', name: 'Stochastic %D' },
            { id: 'williams_r', name: 'Williams %R' },
            { id: 'roc', name: 'Rate of Change (ROC)' },
            { id: 'cci', name: 'Commodity Channel Index (CCI)' },
            { id: 'momentum', name: 'Momentum (MOM)' },
            { id: 'awesome_oscillator', name: 'Awesome Oscillator (AO)' },
            { id: 'tsi', name: 'True Strength Index (TSI)' }
        ]
    },
    {
        id: 'volatility_ind',
        title: 'Volatility Indicators',
        icon: Target,
        description: 'Market volatility and standard deviation bands.',
        source: 'ohlcv',
        features: [
            { id: 'true_range', name: 'True Range (TR)' },
            { id: 'atr', name: 'Average True Range (ATR)' },
            { id: 'bb_upper', name: 'Bollinger Bands Upper' },
            { id: 'bb_lower', name: 'Bollinger Bands Lower' },
            { id: 'bb_width', name: 'Bollinger Bands Width' },
            { id: 'bb_pct_b', name: 'Bollinger %B' },
            { id: 'keltner_upper', name: 'Keltner Channel Upper' },
            { id: 'keltner_lower', name: 'Keltner Channel Lower' },
            { id: 'donchian_upper', name: 'Donchian Channel Upper' },
            { id: 'donchian_lower', name: 'Donchian Channel Lower' },
            { id: 'historical_volatility', name: 'Historical Volatility' },
            { id: 'choppiness_index', name: 'Choppiness Index' }
        ]
    },
    {
        id: 'tick_volume_metrics',
        title: 'Tick Volume Metrics',
        icon: BarChart2,
        description: 'Forex tick volume based indicators.',
        source: 'ohlcv',
        features: [
            { id: 'obv', name: 'On-Balance Volume (OBV)' },
            { id: 'volume_sma', name: 'Volume SMA' },
            { id: 'vroc', name: 'Volume Rate of Change (VROC)' },
            { id: 'mfi', name: 'Money Flow Index (MFI)' },
            { id: 'force_index', name: 'Force Index' },
            { id: 'cmf', name: 'Chaikin Money Flow (CMF)' }
        ]
    },
    {
        id: 'statistical_features',
        title: 'Statistical & Time-Series',
        icon: Layers,
        description: 'Distribution tails, skewness, and variance.',
        source: 'ohlcv',
        features: [
            { id: 'rolling_std', name: 'Rolling Standard Deviation' },
            { id: 'rolling_skewness', name: 'Rolling Skewness' },
            { id: 'rolling_kurtosis', name: 'Rolling Kurtosis' }
        ]
    },
    {
        id: 'smc_order_flow',
        title: 'SMC & Market Structure',
        icon: Activity,
        description: 'Smart Money Concepts and Institutional footprints.',
        source: 'ohlcv',
        features: [
            { id: 'swing_high_low', name: 'Swing Highs / Lows (Fractal)' },
            { id: 'bos_choch', name: 'Break of Structure (BOS & CHoCH)' },
            { id: 'fvg', name: 'Fair Value Gaps (FVG)' },
            { id: 'order_blocks', name: 'Order Blocks (OB)' },
            { id: 'fvg_liquidity', name: 'FVG Liquidity Draw Probability' },
            { id: 'order_block_mitigation', name: 'Order Block Mitigation Speed' },
            { id: 'retail_sentiment', name: 'Retail Sentiment & OBI Proxy' },
            { id: 'currency_correlation', name: 'Currency Correlation Matrix' }
        ]
    },
    {
        id: 'candlestick_patterns',
        title: 'Candlestick Patterns',
        icon: Layers,
        description: 'Classic single and multi-candle patterns.',
        source: 'ohlcv',
        features: [
            { id: 'cdl_doji', name: 'Doji (Reversal/Indecision)' },
            { id: 'cdl_engulfing', name: 'Engulfing (Bullish/Bearish)' },
            { id: 'cdl_hammer', name: 'Hammer' },
            { id: 'cdl_shooting_star', name: 'Shooting Star' },
            { id: 'cdl_morning_star', name: 'Morning Star' },
            { id: 'cdl_evening_star', name: 'Evening Star' }
        ]
    },
    {
        id: 'market_psychology',
        title: 'Market Psychology',
        icon: Target,
        description: 'Consecutive moves, gaps, and buying/selling pressure.',
        source: 'ohlcv',
        features: [
            { id: 'consecutive_candles', name: 'Consecutive Bull/Bear Candles' },
            { id: 'buying_selling_pressure', name: 'Buying & Selling Pressure' },
            { id: 'gap_analysis', name: 'Session & Weekend Gap Analysis' }
        ]
    },
    {
        id: 'ict_macro',
        title: 'ICT Time & Macro Dynamics',
        icon: Clock,
        description: 'Time-based killzones and session volatilities.',
        source: 'ohlcv',
        features: [
            { id: 'london_ny_killzone', name: 'London & NY Killzone Momentum' },
            { id: 'judas_swing', name: 'Judas Swing & Turtle Soup Fakeouts' },
            { id: 'pdh_pdl_sweep', name: 'PDH/PDL Sweep Proxy' },
            { id: 'session_features', name: 'Market Session Pipeline' },
            { id: 'weekend_gap', name: 'Weekend Gap Handler' },
        ]
    },
    {
        id: 'alt_data',
        title: 'Alternative Data & Sentiment',
        icon: Globe,
        description: 'Macro events, Central Bank NLP and Yields.',
        source: 'alt_data',
        features: [
            { id: 'central_bank_nlp', name: 'Central Bank NLP Sentiment' },
            { id: 'stop_hunt_sweeps', name: 'Stop-Hunt & Liquidity Sweeps' },
            { id: 'macro_calendar', name: 'Macroeconomic Calendar' },
            { id: 'cot_sentiment', name: 'COT Sentiment (Smart Money)' },
            { id: 'yield_differentials', name: 'Yield Differentials' },
        ]
    },
    {
        id: 'l2_price_spread',
        title: 'Price & Spread (L2)',
        icon: AlignLeft,
        description: 'Best prices, spreads, and micro-price.',
        source: 'l2_orderbook',
        features: [
            { id: 'l1_best_bid', name: 'Best Bid Price' },
            { id: 'l1_best_ask', name: 'Best Ask Price' },
            { id: 'l2_mid_price', name: 'Mid Price' },
            { id: 'spread_absolute', name: 'Bid-Ask Spread (Absolute)' },
            { id: 'spread_bps', name: 'Bid-Ask Spread (BPS)' },
            { id: 'weighted_mid_price', name: 'Weighted Mid Price' },
            { id: 'micro_price', name: 'Micro-Price' },
            { id: 'spread_sma', name: 'Spread Moving Average' },
            { id: 'spread_volatility', name: 'Spread Volatility' },
            { id: 'spread_roc', name: 'Spread Rate of Change' }
        ]
    },
    {
        id: 'l2_imbalance',
        title: 'Order Book Imbalance (L2)',
        icon: BarChart2,
        description: 'Bid/Ask pressure and volume ratios.',
        source: 'l2_orderbook',
        features: [
            { id: 'l1_imbalance', name: 'Level 1 Imbalance' },
            { id: 'top5_imbalance', name: 'Top 5 Levels Imbalance' },
            { id: 'top10_imbalance', name: 'Top 10 Levels Imbalance' },
            { id: 'cumulative_imbalance', name: 'Cumulative Imbalance (N pips)' },
            { id: 'price_weighted_imbalance', name: 'Price-Weighted Imbalance' },
            { id: 'volume_weighted_imbalance', name: 'Volume-Weighted Imbalance' },
            { id: 'imbalance_sma', name: 'Imbalance Moving Average' },
            { id: 'imbalance_roc', name: 'Imbalance Rate of Change' },
            { id: 'order_book_skewness', name: 'Order Book Skewness' },
            { id: 'order_book_kurtosis', name: 'Order Book Kurtosis' }
        ]
    },
    {
        id: 'l2_liquidity',
        title: 'Liquidity & Depth (L2)',
        icon: Database,
        description: 'Volume depth and depletion rates.',
        source: 'l2_orderbook',
        features: [
            { id: 'total_bid_depth', name: 'Total Bid Volume (Depth)' },
            { id: 'total_ask_depth', name: 'Total Ask Volume (Depth)' },
            { id: 'market_depth_ratio', name: 'Market Depth Ratio' },
            { id: 'near_touch_liquidity', name: 'Near-Touch Liquidity' },
            { id: 'far_touch_liquidity', name: 'Far-from-Touch Liquidity' },
            { id: 'bid_depletion_rate', name: 'Bid Side Depletion Rate' },
            { id: 'ask_depletion_rate', name: 'Ask Side Depletion Rate' },
            { id: 'orderbook_vwap_bid', name: 'Orderbook VWAP (Bid)' },
            { id: 'orderbook_vwap_ask', name: 'Orderbook VWAP (Ask)' },
            { id: 'cost_of_execution', name: 'Cost of Execution (Market Impact)' }
        ]
    },
    {
        id: 'l2_order_flow',
        title: 'Order Flow & Microstructure (L2)',
        icon: Layers,
        description: 'OFI, VPIN, and replenishment rates.',
        source: 'l2_orderbook',
        features: [
            { id: 'ofi', name: 'Order Flow Imbalance (OFI)' },
            { id: 'multi_level_ofi', name: 'Multi-level OFI' },
            { id: 'bid_replenishment', name: 'Bid Replenishment Rate' },
            { id: 'ask_replenishment', name: 'Ask Replenishment Rate' },
            { id: 'bid_cancellation', name: 'Bid Cancellation Rate' },
            { id: 'ask_cancellation', name: 'Ask Cancellation Rate' },
            { id: 'quote_stuffing_ratio', name: 'Quote Stuffing Ratio' },
            { id: 'vpin_proxy', name: 'VPIN Proxy (Informed Trading)' },
            { id: 'trade_sign_proxy', name: 'Trade Sign Proxy (Lee-Ready)' },
            { id: 'market_vs_limit', name: 'Market vs Limit Arrival Rate' }
        ]
    },
    {
        id: 'l2_volatility',
        title: 'Volatility & Price Pressure (L2)',
        icon: Target,
        description: 'High-frequency volatility and bounces.',
        source: 'l2_orderbook',
        features: [
            { id: 'hf_realized_volatility', name: 'High-Freq Realized Volatility' },
            { id: 'bid_ask_bounce', name: 'Bid/Ask Bounce Ratio' },
            { id: 'buying_pressure_tick', name: 'Buying Pressure (Tick)' },
            { id: 'selling_pressure_tick', name: 'Selling Pressure (Tick)' },
            { id: 'micro_rsi', name: 'Micro-RSI (Mid Price)' },
            { id: 'lob_slope_bid', name: 'LOB Slope (Bid)' },
            { id: 'lob_slope_ask', name: 'LOB Slope (Ask)' },
            { id: 'amihud_illiquidity', name: 'Amihud Illiquidity Proxy' },
            { id: 'depth_to_spread', name: 'Depth-to-Spread Ratio' },
            { id: 'toxic_order_flow', name: 'Toxic Order Flow Indicator' }
        ]
    },
    {
        id: 'l2_advanced_math',
        title: 'Advanced Derived ML (L2)',
        icon: Terminal,
        description: 'Derivatives, Entropy, and Center of Mass.',
        source: 'l2_orderbook',
        features: [
            { id: 'l1_imbalance_deriv1', name: '1st Derivative of L1 Imbalance' },
            { id: 'l1_imbalance_deriv2', name: '2nd Derivative of L1 Imbalance' },
            { id: 'spread_imbalance_corr', name: 'Spread-Imbalance Cross-Correlation' },
            { id: 'top5_imbalance_zscore', name: 'Z-Score of Top 5 Imbalance' },
            { id: 'entropy_order_book', name: 'Entropy of Order Book' },
            { id: 'center_of_mass', name: 'Order Book Center of Mass' },
            { id: 'time_decay_imbalance', name: 'Time-Decay Weighted Imbalance' },
            { id: 'bid_ask_volume_div', name: 'Bid-Ask Volume Divergence' }
        ]
    },
    {
        id: 'plp_liquidity_cluster',
        title: 'Liquidity Cluster & Density Module (PLP)',
        icon: Target,
        description: 'Maps retail trapped funds and liquidation zones synthetically.',
        source: 'l2_orderbook',
        features: [
            { id: 'abs_long_liq_pool_proxy', name: 'Absolute Long Liquidation Pool Proxy 🚀' },
            { id: 'abs_short_liq_pool_proxy', name: 'Absolute Short Liquidation Pool Proxy 🚀' },
            { id: 'liquidation_density_z_score_proxy', name: 'Liquidation Density Z-Score Proxy 🚀' },
            { id: 'leverage_washout_z_score_proxy', name: 'Leverage Washout Z-Score Proxy 🚀' },
            { id: 'high_leverage_cluster_proximity_proxy', name: 'High-Leverage Cluster Proximity 🚀' },
            { id: 'margin_call_proximity_index_proxy', name: 'Margin Call Proximity Index 🚀' },
            { id: 'magnetic_liquidity_pull_vector_proxy', name: 'Magnetic Liquidity Pull Vector 🚀' },
            { id: 'liq_cluster_density_heatmap_proxy', name: 'Liquidation Cluster Density Heatmap 🚀' },
            { id: 'synthetic_leverage_ratio_proxy', name: 'Synthetic Leverage Ratio 🚀' },
            { id: 'hidden_liquidity_absorption_proxy', name: 'Hidden Liquidity Absorption 🚀' },
            { id: 'stale_liquidity_decay_proxy', name: 'Stale Liquidity Decay 🚀' },
            { id: 'cross_margin_cascade_risk_proxy', name: 'Cross-Margin Cascade Risk 🚀' },
            { id: 'stealth_liquidation_proxies_proxy', name: 'Stealth Liquidation Proxies 🚀' },
            { id: 'gamma_exposure_imbalance_proxy', name: 'GEX Imbalance Proxy 🚀' },
            { id: 'zero_dte_options_proxy_pull', name: '0-DTE Options Pull Proxy 🚀' },
            { id: 'retail_pain_threshold_proxy', name: 'Retail Pain Threshold 🚀' },
            { id: 'liquidation_void_zones_proxy', name: 'Liquidation Void Zones 🚀' },
            { id: 'smart_money_trap_indicator_proxy', name: 'Smart Money Trap 🚀' },
            { id: 'leveraged_retail_skew_proxy', name: 'Leveraged Retail Skew 🚀' }
        ]
    },
    {
        id: 'plp_cascade_dynamics',
        title: 'Cascade & Trigger Dynamics Module (PLP)',
        icon: Zap,
        description: 'Measures domino effects and chain reactions synthetically.',
        source: 'l2_orderbook',
        features: [
            { id: 'liquidation_cascade_multiplier_proxy', name: 'Liquidation Cascade Multiplier 🚀' },
            { id: 'long_squeeze_probability_proxy', name: 'Long Squeeze Probability 🚀' },
            { id: 'short_squeeze_probability_proxy', name: 'Short Squeeze Probability 🚀' },
            { id: 'cascade_velocity_index_proxy', name: 'Cascade Velocity Index 🚀' },
            { id: 'domino_effect_threshold_proxy', name: 'Domino Effect Threshold 🚀' },
            { id: 'cascade_decay_rate_proxy', name: 'Cascade Decay Rate 🚀' },
            { id: 'forced_liquidation_trigger_pts_proxy', name: 'Forced Liquidation Trigger Points 🚀' },
            { id: 'volatility_expansion_on_liq_proxy', name: 'Volatility Expansion on Liquidation 🚀' },
            { id: 'squeeze_exhaustion_metric_proxy', name: 'Squeeze Exhaustion Metric 🚀' },
            { id: 'liquidator_bot_activity_proxy', name: 'Liquidator Bot Activity Proxy 🚀' },
            { id: 'domino_trigger_threshold_alpha_proxy', name: 'Domino Trigger Alpha 🚀' },
            { id: 'contagion_effect_probability_proxy', name: 'Contagion Effect Prob 🚀' },
            { id: 'price_volume_dislocation_liq_proxy', name: 'Price-Volume Dislocation 🚀' },
            { id: 'cascade_halflife_decay_proxy', name: 'Cascade Half-life Decay 🚀' },
            { id: 'liquidation_wall_impact_proxy', name: 'Liquidation Wall Impact 🚀' },
            { id: 'short_squeeze_velocity_factor_proxy', name: 'Short Squeeze Velocity Factor 🚀' },
            { id: 'synthetic_domino_proxy', name: 'Synthetic Domino Proxy 🚀' }
        ]
    },
    {
        id: 'plp_stop_hunt',
        title: 'Stop-Hunt & Sweep Mechanism Module (PLP)',
        icon: Crosshair,
        description: 'Identifies retail stop-loss hunts and fakeouts synthetically.',
        source: 'l2_orderbook',
        features: [
            { id: 'stop_hunt_probability_proxy', name: 'Stop-Hunt Probability 🚀' },
            { id: 'liquidity_sweep_velocity_proxy', name: 'Liquidity Sweep Velocity 🚀' },
            { id: 'fakeout_prob_model_proxy', name: 'Fakeout Probability Model (FPM) 🚀' },
            { id: 'sweep_and_reversal_ratio_proxy', name: 'Sweep and Reversal Ratio 🚀' },
            { id: 'stop_loss_trigger_density_proxy', name: 'Stop-Loss Trigger Density 🚀' },
            { id: 'predatory_algo_footprint_proxy', name: 'Predatory Algo Footprint 🚀' },
            { id: 'institutional_sweep_divergence_proxy', name: 'Institutional Sweep Divergence 🚀' },
            { id: 'retail_trap_indicator_proxy', name: 'Retail Trap Indicator 🚀' },
            { id: 'high_frequency_hunt_ratio_proxy', name: 'High Frequency Hunt Ratio 🚀' },
            { id: 'sweep_efficiency_score_proxy', name: 'Sweep Efficiency Score 🚀' },
            { id: 'low_latency_sweep_detection_proxy', name: 'Low-Latency Sweep Detect 🚀' },
            { id: 'wash_trade_sweep_detection_proxy', name: 'Wash Trade Sweep Detect 🚀' },
            { id: 'institutional_footprint_masking_proxy', name: 'Institutional Masking 🚀' },
            { id: 'fakeout_velocity_acceleration_proxy', name: 'Fakeout Velocity Accel 🚀' },
            { id: 'stop_hunt_asymmetry_proxy', name: 'Stop-Hunt Asymmetry 🚀' },
            { id: 'retail_panic_sweep_proxy', name: 'Retail Panic Sweep Proxy 🚀' },
            { id: 'algo_hunt_intensity_proxy', name: 'Algo Hunt Intensity 🚀' }
        ]
    }
];

interface ForexAdvancedPipelineProps {
    selectedFeatures: string[];
    onToggleFeature: (featureId: string) => void;
    onSetMultipleFeatures: (featureIds: string[]) => void;
    disabled?: boolean;
    // Scraper Props
    symbol: string;
    isTraining: boolean;
    timeframe: string;
    forexSnapshotFiles: string[];
    selectedForexFile: string;
    setSelectedForexFile: (v: string) => void;
    handleDeleteSnapshot: (e: React.MouseEvent) => void;
    forexScrapeJob: any;
    setForexScrapeJob: (job: any) => void;
    onStartCollector: (config: any) => void;
    onCancelCollector: () => void;
    // L2 Upload Props
    l2OrderbookFiles: string[];
    selectedL2File: string;
    setSelectedL2File: (v: string) => void;
    handleUploadL2Csv: (e: React.ChangeEvent<HTMLInputElement>) => void;
    handleDeleteL2Snapshot: (e: React.MouseEvent) => void;
    isUploadingL2: boolean;
}

export const ForexAdvancedPipeline: React.FC<ForexAdvancedPipelineProps> = (props) => {
    const [dataSource, setDataSource] = useState<string>('ohlcv');
    const [expandedModule, setExpandedModule] = useState<string | null>('smc_order_flow');

    const handleSelectAll = (moduleId: string, features: {id: string}[], isAllSelected: boolean) => {
        if (props.disabled) return;
        
        let newSelection = [...props.selectedFeatures];
        if (isAllSelected) {
            // Remove all features from this module
            const moduleFeatureIds = features.map(f => f.id);
            newSelection = newSelection.filter(id => !moduleFeatureIds.includes(id));
        } else {
            // Add all
            features.forEach(f => {
                if (!newSelection.includes(f.id)) newSelection.push(f.id);
            });
        }
        props.onSetMultipleFeatures(newSelection);
    };

    return (
        <div className="flex flex-col h-full bg-[#0A0A0A]/90 border border-teal-500/30 rounded-[22px] shadow-[0_0_20px_rgba(20,184,166,0.1)] overflow-hidden relative">
            {/* Ambient Background Effects */}
            <div className="absolute top-0 right-0 w-48 h-48 bg-teal-600/10 blur-[80px] rounded-full pointer-events-none"></div>
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-blue-600/10 blur-[80px] rounded-full pointer-events-none"></div>
            
            <div className="p-5 bg-black/40 border-b border-white/10 flex-shrink-0 relative z-20">
                <div className="flex items-center justify-between mb-4">
                    <label className="flex items-center gap-2 text-sm font-medium text-white">
                        <Database className="w-5 h-5 text-cyan-400" /> Data Source Engine
                    </label>
                </div>
                
                <div className="grid grid-cols-3 gap-2">
                    <button
                        onClick={() => { setDataSource('ohlcv'); setExpandedModule('smc_order_flow'); }}
                        disabled={props.isTraining}
                        className={`py-2 rounded-xl text-[11px] font-bold transition-all duration-300 ${dataSource === 'ohlcv' ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-[0_0_15px_rgba(56,189,248,0.4)]' : 'bg-white/5 text-slate-400 hover:bg-white/10 border border-white/5 hover:text-white'}`}
                    >
                        Standard OHLCV
                    </button>
                    <button
                        onClick={() => { setDataSource('l2_orderbook'); setExpandedModule('l2_price_spread'); }}
                        disabled={props.isTraining}
                        className={`py-2 rounded-xl text-[11px] font-bold transition-all duration-300 ${dataSource === 'l2_orderbook' ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-[0_0_15px_rgba(168,85,247,0.4)]' : 'bg-white/5 text-slate-400 hover:bg-white/10 border border-white/5 hover:text-white'}`}
                    >
                        Level 2 Orderbook
                    </button>
                    <button
                        onClick={() => { setDataSource('alt_data'); setExpandedModule('alt_data'); }}
                        disabled={props.isTraining}
                        className={`py-2 rounded-xl text-[11px] font-bold transition-all duration-300 ${dataSource === 'alt_data' ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-[0_0_15px_rgba(16,185,129,0.4)]' : 'bg-white/5 text-slate-400 hover:bg-white/10 border border-white/5 hover:text-white'}`}
                    >
                        Alternative Data
                    </button>
                </div>
            </div>
            
            <div className="p-4 overflow-y-auto custom-scrollbar h-full relative z-10 space-y-3">
                {/* OHLCV SCRAPER INJECTION */}
                {dataSource === 'ohlcv' && (
                    <div className="mb-4 p-4 border border-white/10 rounded-xl bg-white/[0.02]">
                        <div className="mb-4">
                            <label className="block text-sm font-bold text-slate-300 mb-2">Select Dataset Snapshot (Parquet)</label>
                            <div className="flex items-center gap-2">
                                <select 
                                    value={props.selectedForexFile} 
                                    onChange={e => props.setSelectedForexFile(e.target.value)}
                                    disabled={props.isTraining}
                                    className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-teal-500/50 outline-none"
                                >
                                    {props.forexSnapshotFiles.length === 0 && <option value="" className="text-slate-500">No snapshots available. Please collect data first.</option>}
                                    {props.forexSnapshotFiles.map(f => (
                                        <option key={f} value={f} className="bg-gray-900 text-white">{f}</option>
                                    ))}
                                </select>
                                {props.selectedForexFile && (
                                    <button
                                        onClick={props.handleDeleteSnapshot}
                                        disabled={props.isTraining}
                                        className="p-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-xl border border-red-500/20 transition-all flex items-center justify-center"
                                        title="Delete selected snapshot"
                                    >
                                        <Trash2 className="w-5 h-5" />
                                    </button>
                                )}
                            </div>
                        </div>

                        <ForexScraperPanel 
                            symbol={props.symbol}
                            isTraining={props.isTraining}
                            forexScrapeJob={props.forexScrapeJob}
                            setForexScrapeJob={props.setForexScrapeJob}
                            onStartCollector={props.onStartCollector}
                            onCancelCollector={props.onCancelCollector}
                            timeframe={props.timeframe}
                        />
                    </div>
                )}

                {/* LEVEL 2 CSV UPLOAD INJECTION */}
                {dataSource === 'l2_orderbook' && (
                    <div className="mb-4 p-5 border border-purple-500/30 rounded-xl bg-purple-500/5 shadow-[inset_0_0_20px_rgba(168,85,247,0.05)]">
                        <div className="mb-5 text-center">
                            <h4 className="text-sm font-bold text-purple-400 mb-1">Custom L2 Orderbook Data</h4>
                            <p className="text-[10px] text-slate-400">Upload CSV files containing historical DOM/L2 data.</p>
                        </div>
                        
                        <div className="mb-5">
                            <label className="block text-[11px] font-bold text-slate-300 mb-2 uppercase tracking-wider">Select L2 Dataset (CSV)</label>
                            <div className="flex items-center gap-2">
                                <select 
                                    value={props.selectedL2File} 
                                    onChange={e => props.setSelectedL2File(e.target.value)}
                                    disabled={props.isTraining || props.isUploadingL2}
                                    className="w-full bg-black/40 border border-purple-500/20 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-purple-500/50 outline-none"
                                >
                                    {props.l2OrderbookFiles.length === 0 && <option value="" className="text-slate-500">No L2 datasets available. Please upload one.</option>}
                                    {props.l2OrderbookFiles.map(f => (
                                        <option key={f} value={f} className="bg-gray-900 text-white">{f}</option>
                                    ))}
                                </select>
                                {props.selectedL2File && (
                                    <button
                                        onClick={props.handleDeleteL2Snapshot}
                                        disabled={props.isTraining || props.isUploadingL2}
                                        className="p-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-xl border border-red-500/20 transition-all flex items-center justify-center"
                                        title="Delete selected L2 dataset"
                                    >
                                        <Trash2 className="w-5 h-5" />
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="relative border-2 border-dashed border-purple-500/30 hover:border-purple-400/60 rounded-xl p-6 text-center transition-all bg-black/20 group">
                            <input 
                                type="file" 
                                accept=".csv"
                                onChange={props.handleUploadL2Csv}
                                disabled={props.isTraining || props.isUploadingL2}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                            />
                            <div className="flex flex-col items-center justify-center pointer-events-none">
                                <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                                    <Database className="w-5 h-5 text-purple-400" />
                                </div>
                                <span className="text-sm font-bold text-slate-300 group-hover:text-purple-300 transition-colors">
                                    {props.isUploadingL2 ? 'Uploading...' : 'Click or Drag to Upload CSV'}
                                </span>
                                <span className="text-[10px] text-slate-500 mt-1">Only .csv format is supported</span>
                            </div>
                        </div>
                    </div>
                )}

                {/* ACCORDION MODULES */}
                {FOREX_MODULES.filter(m => m.source === dataSource).map((module) => {
                    const ModuleIcon = module.icon;
                    const isExpanded = expandedModule === module.id;
                    
                    const moduleFeatureIds = module.features.map(f => f.id);
                    const selectedInModule = props.selectedFeatures.filter(id => moduleFeatureIds.includes(id));
                    const isAllSelected = selectedInModule.length === module.features.length;
                    const isPartiallySelected = selectedInModule.length > 0 && !isAllSelected;

                    return (
                        <div 
                            key={module.id} 
                            className={`rounded-xl border transition-all duration-300 overflow-hidden ${isExpanded ? 'border-teal-500/40 bg-teal-500/5' : 'border-white/5 bg-white/[0.02] hover:bg-white/[0.04]'}`}
                        >
                            {/* Accordion Header */}
                            <div 
                                className="flex items-center justify-between p-3 cursor-pointer"
                                onClick={() => setExpandedModule(isExpanded ? null : module.id)}
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`p-2 rounded-lg transition-colors ${isExpanded ? 'bg-teal-500/20 text-teal-300' : 'bg-white/5 text-slate-400'}`}>
                                        <ModuleIcon className="w-4 h-4" />
                                    </div>
                                    <div>
                                        <h4 className={`text-sm font-bold tracking-wide transition-colors ${isExpanded ? 'text-teal-300' : 'text-slate-300'}`}>
                                            {module.title}
                                        </h4>
                                        {!isExpanded && (
                                            <p className="text-[10px] text-slate-500 mt-0.5">{module.description}</p>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="text-[10px] font-mono text-teal-400 bg-teal-400/10 px-2 py-0.5 rounded-md">
                                        {selectedInModule.length} / {module.features.length}
                                    </div>
                                    <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`} />
                                </div>
                            </div>

                            {/* Accordion Body */}
                            {isExpanded && (
                                <div className="p-3 pt-0 border-t border-white/5 mt-2 space-y-1">
                                    <div className="flex items-center justify-between mb-3 px-2 py-1 bg-white/5 rounded-md">
                                        <span className="text-xs text-slate-400 font-medium">{module.description}</span>
                                        <button 
                                            disabled={props.disabled}
                                            onClick={(e) => { e.stopPropagation(); handleSelectAll(module.id, module.features, isAllSelected); }}
                                            className="text-[10px] uppercase font-bold tracking-wider text-teal-400 hover:text-teal-300 px-2 py-1 rounded hover:bg-teal-400/10 transition-colors"
                                        >
                                            {isAllSelected ? 'Deselect All' : 'Select All'}
                                        </button>
                                    </div>

                                    <div className="grid grid-cols-1 gap-1">
                                        {module.features.map(feature => {
                                            const isSelected = props.selectedFeatures.includes(feature.id);
                                            return (
                                                <div 
                                                    key={feature.id}
                                                    onClick={() => !props.disabled && props.onToggleFeature(feature.id)}
                                                    className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors ${isSelected ? 'bg-teal-500/10 hover:bg-teal-500/20' : 'hover:bg-white/5'} ${props.disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                                                >
                                                    <div className={`transition-colors ${isSelected ? 'text-teal-400' : 'text-slate-600'}`}>
                                                        {isSelected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                                                    </div>
                                                    <span className={`text-xs font-medium ${isSelected ? 'text-teal-200' : 'text-slate-400'}`}>
                                                        {feature.name}
                                                    </span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
