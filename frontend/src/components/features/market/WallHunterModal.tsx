import { useEffect, useState, FC } from 'react';
import { fetchApiKeys } from '../../../services/settings';
import { botService } from '../../../services/botService';
import { marketDataService } from '../../../services/marketData';
import { marketDepthService } from '../../../services/marketDepthService';
import { calculateATR } from '../../../utils/indicators';

export const WallHunterModal: FC<{ isOpen: boolean; onClose: () => void; symbol: string; bids?: any[]; asks?: any[]; onDeploySuccess?: (botId: number) => void }> = ({ isOpen, onClose, symbol, bids = [], asks = [], onDeploySuccess }) => {
    const [savedKeys, setSavedKeys] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');
    const [activeTab, setActiveTab] = useState('basic');
    
    // --- NEW: Trading Mode State ---
    const [tradingMode, setTradingMode] = useState<'spot' | 'futures'>('spot');
    const [availableExchanges, setAvailableExchanges] = useState<string[]>([]);
    const [showAdvancedTSL, setShowAdvancedTSL] = useState(false);

    const [form, setForm] = useState({
        symbol: symbol,
        exchange: 'binance',
        isPaper: true,
        apiKeyId: '',
        vol: 500000,
        spread: 0.0002,
        risk: 0.5,
        enableTsl: true,
        tsl: 0.03,
        amount: 100,
        sellOrderType: 'market',
        spoofTime: 3.0,
        enablePartialTp: true,
        partialTp: 50.0,
        partialTpTriggerPct: 0.0,
        enableBreakevenSl: false,
        breakevenTriggerPct: 0.05,
        breakevenTargetPct: 0.02,
        vpvrEnabled: false,
        vpvrTolerance: 0.2,
        atrEnabled: false,
        atrPeriod: 14,
        atrMultiplier: 2.0,
        
        // --- NEW: Custom Buy Order Type & Buffer ---
        buyOrderType: 'market',
        limitBuffer: 0.5,

        enableWallTrigger: true,        
        maxWallDistancePct: 1.0,        
        enableLiqTrigger: false,        
        liqThreshold: 50000,            
        enableMicroScalp: false,        
        microScalpProfitTicks: 2,       
        microScalpMinWall: 100000,      

        enableLiqCascade: false,        
        liqCascadeWindow: 5,            
        enableDynamicLiq: false,        
        dynamicLiqMultiplier: 1.0,      
        enableObImbalance: false,       
        obImbalanceRatio: 1.5,          

        followBtcLiq: false,
        btcLiqThreshold: 500000,

        // --- NEW: Futures Specific States ---
        marginMode: 'cross',
        leverage: 10,
        positionDirection: 'auto',
        reduceOnly: true,
        liquidationSafetyPct: 5.0,

        // --- NEW: CVD Absorption Confirmation ---
        enableAbsorption: false,
        absorptionThreshold: 50000,
        absorptionWindow: 10,

        // --- NEW: BTC Correlation Filter ---
        enableBtcCorrelation: false,
        btcCorrelationThreshold: 0.5,
        btcTimeWindow: 15,
        btcMinMovePct: 0.025
    });

    const [existingBot, setExistingBot] = useState<any>(null);

    useEffect(() => {
        setForm(prev => ({ ...prev, symbol }));
    }, [symbol]);

    useEffect(() => {
        if (isOpen) {
            try {
                if (typeof fetchApiKeys === 'function') {
                    fetchApiKeys().then((keys: any) => setSavedKeys(keys || [])).catch(() => { });
                }

                botService.getAllBots().then((bots: any) => {
                    const activeWallHunter = bots.find((b: any) => b.market === symbol && b.strategy === 'wall_hunter' && b.status === 'active');
                    if (activeWallHunter) {
                        setExistingBot(activeWallHunter);
                        const c = activeWallHunter.config || {};
                        
                        // Detect mode from existing config
                        if (c.trading_mode === 'futures') {
                            setTradingMode('futures');
                        } else {
                            setTradingMode('spot');
                        }

                        setForm(prev => ({
                            ...prev,
                            exchange: activeWallHunter.exchange,
                            isPaper: activeWallHunter.is_paper_trading,
                            apiKeyId: activeWallHunter.api_key_id || '',
                            vol: c.vol_threshold || 500000,
                            spread: c.target_spread || 0.0002,
                            risk: c.risk_pct || 0.5,
                            enableTsl: c.trailing_stop !== undefined ? c.trailing_stop > 0 : true,
                            tsl: c.trailing_stop !== undefined && c.trailing_stop > 0 ? c.trailing_stop : 0.03,
                            amount: c.amount_per_trade || 100,
                            sellOrderType: c.sell_order_type || 'market',
                            spoofTime: c.min_wall_lifetime !== undefined ? c.min_wall_lifetime : 3.0,
                            enablePartialTp: c.partial_tp_pct !== undefined ? c.partial_tp_pct > 0 : true,
                            partialTp: c.partial_tp_pct !== undefined && c.partial_tp_pct > 0 ? c.partial_tp_pct : 50.0,
                            partialTpTriggerPct: c.partial_tp_trigger_pct || 0.0,
                            enableBreakevenSl: c.sl_breakeven_trigger_pct !== undefined ? c.sl_breakeven_trigger_pct > 0 : false,
                            breakevenTriggerPct: c.sl_breakeven_trigger_pct !== undefined && c.sl_breakeven_trigger_pct > 0 ? c.sl_breakeven_trigger_pct : 0.05,
                            breakevenTargetPct: c.sl_breakeven_target_pct !== undefined ? c.sl_breakeven_target_pct : 0.02,
                            vpvrEnabled: c.vpvr_enabled !== undefined ? c.vpvr_enabled : false,
                            vpvrTolerance: c.vpvr_tolerance !== undefined ? c.vpvr_tolerance : 0.2,
                            atrEnabled: c.atr_sl_enabled !== undefined ? c.atr_sl_enabled : false,
                            atrPeriod: c.atr_period !== undefined ? c.atr_period : 14,
                            atrMultiplier: c.atr_multiplier !== undefined ? c.atr_multiplier : 2.0,

                            enableWallTrigger: c.enable_wall_trigger !== undefined ? c.enable_wall_trigger : true,
                            maxWallDistancePct: c.max_wall_distance_pct !== undefined ? c.max_wall_distance_pct : 1.0,
                            enableLiqTrigger: c.enable_liq_trigger !== undefined ? c.enable_liq_trigger : false,
                            liqThreshold: c.liq_threshold || 50000,
                            enableMicroScalp: c.enable_micro_scalp !== undefined ? c.enable_micro_scalp : false,
                            microScalpProfitTicks: c.micro_scalp_profit_ticks || 2,
                            microScalpMinWall: c.micro_scalp_min_wall || 100000,

                            enableLiqCascade: c.enable_liq_cascade !== undefined ? c.enable_liq_cascade : false,
                            liqCascadeWindow: c.liq_cascade_window || 5,
                            enableDynamicLiq: c.enable_dynamic_liq !== undefined ? c.enable_dynamic_liq : false,
                            dynamicLiqMultiplier: c.dynamic_liq_multiplier || 1.0,
                            enableObImbalance: c.enable_ob_imbalance !== undefined ? c.enable_ob_imbalance : false,
                            obImbalanceRatio: c.ob_imbalance_ratio || 1.5,

                            followBtcLiq: c.follow_btc_liq !== undefined ? c.follow_btc_liq : false,
                            btcLiqThreshold: c.btc_liq_threshold || 500000,

                            // Futures existing configs
                            marginMode: c.margin_mode || 'cross',
                            leverage: c.leverage || 10,
                            positionDirection: c.position_direction || 'auto',
                            reduceOnly: c.reduce_only !== undefined ? c.reduce_only : true,
                            liquidationSafetyPct: c.liquidation_safety_pct || 5.0,

                            enableAbsorption: c.enable_absorption !== undefined ? c.enable_absorption : false,
                            absorptionThreshold: c.absorption_threshold || 50000,
                            absorptionWindow: c.absorption_window || 10,

                            enableBtcCorrelation: c.enable_btc_correlation !== undefined ? c.enable_btc_correlation : false,
                            btcCorrelationThreshold: c.btc_correlation_threshold || 0.7,
                            btcTimeWindow: c.btc_time_window || 15,
                            btcMinMovePct: c.btc_min_move_pct || 0.1,
                            
                            // Load custom buy order settings
                            buyOrderType: c.buy_order_type || 'market',
                            limitBuffer: c.limit_buffer !== undefined ? c.limit_buffer : 0.5
                        }));
                    } else {
                        setExistingBot(null);
                    }
                }).catch(() => { });
            } catch (e) { }
        }
    }, [isOpen, symbol]);

    useEffect(() => {
        if (isOpen) {
            marketDataService.getAllExchanges()
                .then(exs => setAvailableExchanges(exs))
                .catch(err => console.error("Failed to load exchanges:", err));
        }
    }, [isOpen]);

    if (!isOpen) return null;

    const handleAutoDetect = async () => {
        setIsLoading(true);
        setErrorMsg('Detecting optimal parameters...');
        
        try {
            // 1. Fetch Deep Order Book (limit=200)
            const deepBook = await marketDepthService.getRawOrderBook(form.symbol, form.exchange, 200);
            const deepBids = deepBook.bids || [];
            const deepAsks = deepBook.asks || [];

            // 2. Fetch OHLCV for ATR Calculation (1h timeframe, 30 candles)
            const ohlcv = await marketDepthService.getOHLCV(form.symbol.toUpperCase(), form.exchange.toLowerCase(), '1h', 30);
            
            let optimalVol = form.vol;
            let optimalSpread = form.spread;
            let optimalAmount = form.amount;

            if (deepBids.length > 0 && deepAsks.length > 0) {
                const bestBid = deepBids[0].price;
                const bestAsk = deepAsks[0].price;
                const currentMarketSpread = bestAsk - bestBid;
                const currentPrice = bestBid;
                
                // Determine dynamic precision based on price
                let dynamicStep = 0.01;
                let displayDigits = 2;
                if (currentPrice < 0.000001) { dynamicStep = 0.00000001; displayDigits = 8; }
                else if (currentPrice < 0.00001) { dynamicStep = 0.0000001; displayDigits = 7; }
                else if (currentPrice < 0.0001) { dynamicStep = 0.000001; displayDigits = 6; }
                else if (currentPrice < 0.001) { dynamicStep = 0.00001; displayDigits = 5; }
                else if (currentPrice < 1) { dynamicStep = 0.0001; displayDigits = 4; }
                else if (currentPrice < 10) { dynamicStep = 0.001; displayDigits = 3; }
                else if (currentPrice < 100) { dynamicStep = 0.01; displayDigits = 2; }
                else if (currentPrice < 1000) { dynamicStep = 0.1; displayDigits = 1; }
                else { dynamicStep = 1; displayDigits = 0; }

                // --- SMART SPREAD (ATR BASED) ---
                if (ohlcv && ohlcv.length > 15) {
                    const atrData = calculateATR(ohlcv, 14);
                    if (atrData.length > 0) {
                        const currentATR = atrData[atrData.length - 1].value;
                        // Use 25% of ATR as a starting point for scalping spread
                        const atrSpread = currentATR * 0.25;
                        // Ensure spread is at least slightly wider than the current market spread
                        optimalSpread = Math.max(currentMarketSpread * 1.5, atrSpread);
                    } else {
                        optimalSpread = currentMarketSpread + (bestAsk * 0.001);
                    }
                } else {
                    optimalSpread = currentMarketSpread + (bestAsk * 0.001);
                }
                
                // Final formatting for spread
                optimalSpread = parseFloat(Math.max(dynamicStep, Math.min(dynamicStep * 500, optimalSpread)).toFixed(displayDigits));

                // --- SMART VOLUME (DEEP BOOK ANALYSIS) ---
                const allSizes = [...deepBids.map((b: any) => b.size), ...deepAsks.map((a: any) => a.size)];
                if (allSizes.length > 0) {
                    // Sort sizes to find percentiles
                    allSizes.sort((a, b) => a - b);
                    // Use 90th percentile as the "Wall" threshold - this is a high volume level
                    const p90Idx = Math.floor(allSizes.length * 0.9);
                    const p90Size = allSizes[p90Idx];
                    
                    // We want to trigger when a wall is detected, so our threshold should be large enough
                    // but not so large that it never triggers. 
                    const calculatedVol = p90Size * 1.2;

                    if (calculatedVol > 10000) optimalVol = Math.round(calculatedVol / 1000) * 1000;
                    else if (calculatedVol > 100) optimalVol = Math.round(calculatedVol / 10) * 10;
                    else optimalVol = parseFloat(calculatedVol.toFixed(2));
                    
                    optimalVol = Math.max(dynamicStep * 10, optimalVol);

                    // Amount based on 10% of typical depth size for safety
                    const avgSize = allSizes.reduce((s, a) => s + a, 0) / allSizes.length;
                    const avgQuoteValue = avgSize * currentPrice;
                    optimalAmount = parseFloat(Math.max(10, avgQuoteValue * 0.2).toFixed(2));
                }
            }

            setForm(prev => ({
                ...prev,
                vol: optimalVol,
                spread: optimalSpread,
                amount: optimalAmount
            }));
            
            setErrorMsg("✅ Parameters auto-detected!");
            setTimeout(() => setErrorMsg(''), 3000);

        } catch (err: any) {
            console.error("Auto detect failed:", err);
            setErrorMsg("❌ Detection failed: " + (err.response?.data?.detail || err.message));
        } finally {
            setIsLoading(false);
        }
    };

    const handleDeploy = async () => {
        if (!form.isPaper && !form.apiKeyId) {
            setErrorMsg("Please select an API Key for Live Trading.");
            return;
        }

        if (!form.enableWallTrigger && !form.enableLiqTrigger) {
            setErrorMsg("Please enable at least one Entry Trigger (Orderbook Wall or Liquidation).");
            return;
        }

        setErrorMsg('');
        setIsLoading(true);

        try {
            const payload = {
                name: `${tradingMode === 'futures' ? 'Perp Hunter' : 'L2 Hunter'}: ${form.symbol}`,
                description: `Orderbook & Liquidation Scalping Hunter (${tradingMode.toUpperCase()})`,
                exchange: form.exchange,
                market: form.symbol,
                strategy: "wall_hunter",
                timeframe: "1m",
                trade_value: form.amount,
                trade_unit: "QUOTE",
                api_key_id: form.isPaper ? null : form.apiKeyId,
                is_paper_trading: form.isPaper,
                config: {
                    trading_mode: tradingMode, // Spot vs Futures Isolation Flag
                    amount_per_trade: form.amount,
                    target_spread: form.spread,
                    trailing_stop: form.enableTsl ? form.tsl : 0.0,
                    vol_threshold: form.vol,
                    risk_pct: form.risk,
                    sell_order_type: form.sellOrderType,
                    min_wall_lifetime: form.spoofTime,
                    partial_tp_pct: form.enablePartialTp ? form.partialTp : 0.0,
                    partial_tp_trigger_pct: form.enablePartialTp ? form.partialTpTriggerPct : 0.0,
                    sl_breakeven_trigger_pct: form.enableBreakevenSl ? form.breakevenTriggerPct : 0.0,
                    sl_breakeven_target_pct: form.enableBreakevenSl ? form.breakevenTargetPct : 0.0,
                    vpvr_enabled: form.vpvrEnabled,
                    vpvr_tolerance: form.vpvrTolerance,
                    atr_sl_enabled: form.atrEnabled,
                    atr_period: form.atrPeriod,
                    atr_multiplier: form.atrMultiplier,

                    enable_wall_trigger: form.enableWallTrigger,
                    max_wall_distance_pct: form.maxWallDistancePct,
                    enable_liq_trigger: form.enableLiqTrigger,
                    liq_threshold: form.liqThreshold,
                    enable_micro_scalp: form.enableMicroScalp,
                    micro_scalp_profit_ticks: form.microScalpProfitTicks,
                    micro_scalp_min_wall: form.microScalpMinWall,

                    enable_liq_cascade: form.enableLiqCascade,
                    liq_cascade_window: form.liqCascadeWindow,
                    enable_dynamic_liq: form.enableDynamicLiq,
                    dynamic_liq_multiplier: form.dynamicLiqMultiplier,
                    enable_ob_imbalance: form.enableObImbalance,
                    ob_imbalance_ratio: form.obImbalanceRatio,

                    follow_btc_liq: form.followBtcLiq,
                    btc_liq_threshold: form.btcLiqThreshold,

                    // Conditionally append Futures config
                    ...(tradingMode === 'futures' && {
                        margin_mode: form.marginMode,
                        leverage: form.leverage,
                        position_direction: form.positionDirection,
                        reduce_only: form.reduceOnly,
                        liquidation_safety_pct: form.liquidationSafetyPct
                    }),

                    // CVD Absorption Confirmation
                    enable_absorption: form.enableAbsorption,
                    absorption_threshold: form.absorptionThreshold,
                    absorption_window: form.absorptionWindow,

                    // BTC Correlation Filter
                    enable_btc_correlation: form.enableBtcCorrelation,
                    btc_correlation_threshold: form.btcCorrelationThreshold,
                    btc_time_window: form.btcTimeWindow,
                    btc_min_move_pct: form.btcMinMovePct,

                    // New Buy Order Logic
                    buy_order_type: form.buyOrderType,
                    limit_buffer: form.limitBuffer
                }
            };

            if (existingBot) {
                await botService.updateBot(existingBot.id, payload);
                setTimeout(() => {
                    setIsLoading(false);
                    setErrorMsg("⚡ Live Config Updated Successfully!");
                    setTimeout(() => setErrorMsg(''), 3000);
                }, 1000);
            } else {
                const createdBot = await botService.createBot(payload);
                await botService.controlBot(createdBot.id, 'start');

                setTimeout(() => {
                    setIsLoading(false);
                    if (onDeploySuccess) onDeploySuccess(Number(createdBot.id));
                    else onClose();
                }, 1000);
            }
        } catch (err: any) {
            console.error(err);
            setErrorMsg(err.response?.data?.detail || err.message || "Failed to deploy bot.");
            setIsLoading(false);
        }
    };

    const handleFormChange = (field: string, value: any) => {
        setForm(prev => ({ ...prev, [field]: value }));
    };

    const currentPrice = bids.length > 0 ? bids[0].price : (asks.length > 0 ? asks[0].price : 1);
    
    let dynamicStep = 0.01;
    let displayDigits = 2;
    if (currentPrice < 0.000001) { dynamicStep = 0.00000001; displayDigits = 8; }
    else if (currentPrice < 0.00001) { dynamicStep = 0.0000001; displayDigits = 7; }
    else if (currentPrice < 0.0001) { dynamicStep = 0.000001; displayDigits = 6; }
    else if (currentPrice < 0.001) { dynamicStep = 0.00001; displayDigits = 5; }
    else if (currentPrice < 1) { dynamicStep = 0.0001; displayDigits = 4; }
    else if (currentPrice < 10) { dynamicStep = 0.001; displayDigits = 3; }
    else if (currentPrice < 100) { dynamicStep = 0.01; displayDigits = 2; }
    else if (currentPrice < 1000) { dynamicStep = 0.1; displayDigits = 1; }
    else { dynamicStep = 1; displayDigits = 0; }

    const dynamicMax = dynamicStep * 500; 

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
            <div className="w-[600px] bg-[#0B1120] border-2 border-yellow-500/30 rounded-[2rem] p-6 shadow-[0_0_50px_rgba(59,130,246,0.2)] max-h-[90vh] flex flex-col">
                <div className="flex justify-between items-center mb-4 flex-shrink-0">
                    <h2 className="text-2xl font-black italic text-white tracking-tighter">SNIPER DEPLOYMENT</h2>
                    <button
                        onClick={handleAutoDetect}
                        className="flex items-center gap-1 bg-brand-primary/20 hover:bg-brand-primary/30 border border-brand-primary/50 text-brand-primary px-3 py-1.5 rounded-full text-xs font-bold transition-colors shadow-[0_0_10px_rgba(59,130,246,0.2)]"
                    >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                        AUTO DETECT
                    </button>
                </div>

                {/* --- MAIN TRADING MODE TOGGLE --- */}
                <div className="flex bg-black/40 p-1.5 rounded-2xl mb-4 border border-white/5 flex-shrink-0">
                    <button
                        onClick={() => setTradingMode('spot')}
                        className={`flex-1 py-2.5 text-xs font-black uppercase rounded-xl transition-all ${tradingMode === 'spot' ? 'bg-brand-primary text-white shadow-[0_0_15px_rgba(59,130,246,0.4)]' : 'text-gray-500 hover:text-white hover:bg-white/5'}`}
                    >
                        SPOT BOT
                    </button>
                    <button
                        onClick={() => setTradingMode('futures')}
                        className={`flex-1 py-2.5 text-xs font-black uppercase rounded-xl transition-all flex items-center justify-center gap-2 ${tradingMode === 'futures' ? 'bg-orange-500 text-white shadow-[0_0_15px_rgba(249,115,22,0.4)]' : 'text-gray-500 hover:text-white hover:bg-white/5'}`}
                    >
                        FUTURE TRADING BOT ⚡
                    </button>
                </div>

                {/* --- TABS NAVIGATION --- */}
                <div className="flex gap-2 border-b border-white/10 mb-4 pb-2 overflow-x-auto flex-shrink-0 hide-scrollbar">
                    <button onClick={() => setActiveTab('basic')} className={`px-4 py-2 text-xs font-black tracking-wider uppercase rounded-xl transition-all ${activeTab === 'basic' ? 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/30 shadow-[0_0_15px_rgba(234,179,8,0.2)]' : 'text-gray-500 hover:bg-white/5'}`}>Basic & Execution</button>
                    <button onClick={() => setActiveTab('triggers')} className={`px-4 py-2 text-xs font-black tracking-wider uppercase rounded-xl transition-all ${activeTab === 'triggers' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]' : 'text-gray-500 hover:bg-white/5'}`}>Entry Triggers</button>
                    <button onClick={() => setActiveTab('risk')} className={`px-4 py-2 text-xs font-black tracking-wider uppercase rounded-xl transition-all ${activeTab === 'risk' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.2)]' : 'text-gray-500 hover:bg-white/5'}`}>Risk Management</button>
                    <button onClick={() => setActiveTab('advanced')} className={`px-4 py-2 text-xs font-black tracking-wider uppercase rounded-xl transition-all ${activeTab === 'advanced' ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30 shadow-[0_0_15px_rgba(168,85,247,0.2)]' : 'text-gray-500 hover:bg-white/5'}`}>Advanced</button>
                </div>

                {/* --- TABS CONTENT --- */}
                <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-4">
                    {activeTab === 'basic' && (
                        <div className="animate-fadeIn space-y-4">
                            <div className="flex gap-4">
                                <div className="space-y-1 w-1/3">
                                    <label className="text-[10px] text-gray-500 font-bold uppercase">Asset</label>
                                    <input className="w-full bg-white/5 p-2 rounded-xl text-yellow-500 font-mono outline-none border border-transparent text-sm" value={form.symbol} readOnly />
                                </div>
                                <div className="space-y-1 w-1/3">
                                    <label className="text-[10px] text-gray-500 font-bold uppercase">Exchange</label>
                                    <select 
                                        className="w-full bg-white/5 p-2 rounded-xl text-white outline-none text-sm" 
                                        value={form.exchange} 
                                        onChange={(e) => setForm({ ...form, exchange: e.target.value })}
                                    >
                                        {availableExchanges.length > 0 ? (
                                            availableExchanges.map(ex => (
                                                <option key={ex} className="bg-[#0B1120] text-white" value={ex}>
                                                    {ex.charAt(0).toUpperCase() + ex.slice(1)}
                                                </option>
                                            ))
                                        ) : (
                                            <>
                                                <option className="bg-[#0B1120] text-white" value="binance">Binance</option>
                                                <option className="bg-[#0B1120] text-white" value="bybit">Bybit</option>
                                                <option className="bg-[#0B1120] text-white" value="okx">OKX</option>
                                                <option className="bg-[#0B1120] text-white" value="mexc">MEXC</option>
                                            </>
                                        )}
                                    </select>
                                </div>
                                <div className="w-1/3 space-y-1">
                                    <label className="text-[10px] text-gray-500 font-bold uppercase">Sell Order (TP)</label>
                                    <select className="w-full bg-white/5 border border-white/10 rounded-xl p-2 text-white outline-none focus:border-brand-primary text-sm" value={form.sellOrderType} onChange={(e) => handleFormChange('sellOrderType', e.target.value)}>
                                        <option className="bg-[#0B1120] text-white" value="market">Market</option>
                                        <option className="bg-[#0B1120] text-white" value="limit">Limit</option>
                                    </select>
                                </div>
                            </div>
                            
                            {/* --- NEW: BUY ORDER TYPE & BUFFER --- */}
                            <div className="flex gap-4 p-3 bg-white/5 border border-white/10 rounded-2xl">
                                <div className="flex-1 space-y-1">
                                    <label className="text-[10px] text-gray-400 font-black uppercase">Buy Order Type</label>
                                    <select 
                                        className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white outline-none focus:border-brand-primary text-sm font-bold" 
                                        value={form.buyOrderType} 
                                        onChange={(e) => handleFormChange('buyOrderType', e.target.value)}
                                    >
                                        <option className="bg-[#0B1120]" value="market">Market (Normal)</option>
                                        <option className="bg-[#0B1120]" value="limit">Limit (Maker)</option>
                                        <option className="bg-[#0B1120]" value="marketable_limit">Marketable Limit (Recommended for MEXC)</option>
                                    </select>
                                </div>
                                {form.buyOrderType === 'marketable_limit' && (
                                    <div className="w-1/3 space-y-1 animate-fadeIn">
                                        <label className="text-[10px] text-orange-400 font-black uppercase">Limit Buffer (%)</label>
                                        <input 
                                            type="number" 
                                            step="0.01" 
                                            className="w-full bg-orange-500/10 border border-orange-500/30 rounded-xl p-2.5 text-orange-400 outline-none text-center font-mono font-bold" 
                                            value={form.limitBuffer} 
                                            onChange={(e) => handleFormChange('limitBuffer', parseFloat(e.target.value))} 
                                        />
                                    </div>
                                )}
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div className={`p-2 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${form.isPaper ? 'bg-green-500/10 border-green-500' : 'bg-white/5 border-white/10'}`} onClick={() => setForm({ ...form, isPaper: true })}>
                                    <p className="text-xs font-bold text-white">Paper Trading <span className="text-[10px] text-green-500 ml-1">(SIM)</span></p>
                                    {form.isPaper && <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>}
                                </div>
                                <div className={`p-2 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${!form.isPaper ? 'bg-red-500/10 border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.3)]' : 'bg-white/5 border-white/10'}`} onClick={() => setForm({ ...form, isPaper: false })}>
                                    <p className="text-xs font-bold text-white">Live Market <span className="text-[10px] text-red-500 ml-1">(REAL)</span></p>
                                    {!form.isPaper && <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>}
                                </div>
                            </div>

                            {!form.isPaper && (
                                <div className="flex flex-col">
                                    <label className="text-[10px] text-gray-500 font-bold uppercase mb-1">Select API Config</label>
                                    <select className="w-full bg-yellow-500/10 border border-yellow-500/20 p-2.5 rounded-xl text-white outline-none text-sm" value={form.apiKeyId} onChange={(e) => setForm({ ...form, apiKeyId: e.target.value })}>
                                        <option className="bg-[#0B1120] text-white" value="">-- Choose Saved Key --</option>
                                        {savedKeys.filter(k => k.exchange === form.exchange).map(k => (
                                            <option className="bg-[#0B1120] text-white" key={k.id} value={k.id}>{k.name}</option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            {/* --- FUTURES SPECIFIC SETTINGS IN BASIC TAB --- */}
                            {tradingMode === 'futures' && (
                                <div className="animate-fadeIn bg-orange-500/5 border border-orange-500/20 p-4 rounded-xl space-y-4">
                                    <div className="flex justify-between items-center mb-2">
                                        <h3 className="text-xs font-black text-orange-400 uppercase tracking-wider flex items-center gap-2">
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                                            Futures Configuration
                                        </h3>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-1">
                                            <label className="text-[10px] text-gray-400 font-bold uppercase">Margin Mode</label>
                                            <div className="flex bg-black/40 rounded-lg p-1 border border-white/10">
                                                <button onClick={() => handleFormChange('marginMode', 'cross')} className={`flex-1 py-1.5 text-[10px] font-bold uppercase rounded ${form.marginMode === 'cross' ? 'bg-orange-500 text-white' : 'text-gray-500'}`}>Cross</button>
                                                <button onClick={() => handleFormChange('marginMode', 'isolated')} className={`flex-1 py-1.5 text-[10px] font-bold uppercase rounded ${form.marginMode === 'isolated' ? 'bg-orange-500 text-white' : 'text-gray-500'}`}>Isolated</button>
                                            </div>
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-[10px] text-gray-400 font-bold uppercase">Position Direction</label>
                                            <select 
                                                className="w-full bg-black/40 border border-white/10 p-2.5 rounded-lg text-white outline-none text-sm" 
                                                value={form.positionDirection} 
                                                onChange={(e) => {
                                                    const val = e.target.value;
                                                    handleFormChange('positionDirection', val);
                                                    if (val === 'auto') handleFormChange('enableObImbalance', true);
                                                }}
                                            >
                                                <option className="bg-[#0B1120]" value="auto">Auto (Heatmap Based)</option>
                                                <option className="bg-[#0B1120] text-green-400" value="long">Long Only</option>
                                                <option className="bg-[#0B1120] text-red-400" value="short">Short Only</option>
                                            </select>
                                        </div>
                                    </div>

                                    {form.positionDirection === 'auto' && (
                                        <div className="animate-fadeIn bg-black/40 border border-orange-500/30 p-3 rounded-xl">
                                            <div className="flex justify-between items-center mb-1">
                                                <label className="text-[10px] font-bold text-orange-400 uppercase tracking-tighter">Heatmap Imbalance Ratio</label>
                                                <span className="text-xs font-mono font-bold text-white">{form.obImbalanceRatio}x</span>
                                            </div>
                                            <div className="flex gap-3 items-center">
                                                <input 
                                                    type="range" 
                                                    min="1.1" 
                                                    max="10.0" 
                                                    step="0.1" 
                                                    className="flex-1 h-1.5 accent-orange-500 bg-white/10 rounded-lg appearance-none cursor-pointer" 
                                                    value={form.obImbalanceRatio} 
                                                    onChange={(e) => handleFormChange('obImbalanceRatio', parseFloat(e.target.value))} 
                                                />
                                                <input 
                                                    type="number" 
                                                    step="0.1" 
                                                    className="w-16 bg-black/40 border border-white/10 rounded-lg p-1 text-white text-center font-mono text-xs" 
                                                    value={form.obImbalanceRatio} 
                                                    onChange={(e) => handleFormChange('obImbalanceRatio', parseFloat(e.target.value))} 
                                                />
                                            </div>
                                            <p className="text-[9px] text-gray-500 mt-1 italic">Bot will only enter if one side has {form.obImbalanceRatio}x more volume than the other.</p>
                                        </div>
                                    )}

                                    <div>
                                        <div className="flex justify-between items-end mb-1">
                                            <label className="text-[10px] font-bold text-gray-400 uppercase">Leverage (Max 125x)</label>
                                            <span className={`text-xs font-mono font-bold ${form.leverage > 20 ? 'text-red-500' : 'text-orange-400'}`}>{form.leverage}x</span>
                                        </div>
                                        <div className="flex gap-3 items-center">
                                            <input type="range" min="1" max="125" step="1" className={`flex-1 h-2 rounded-lg appearance-none cursor-pointer ${form.leverage > 20 ? 'accent-red-500' : 'accent-orange-500'} bg-white/10`} value={form.leverage} onChange={(e) => handleFormChange('leverage', parseInt(e.target.value))} />
                                            <input type="number" min="1" max="125" className="w-20 bg-black/40 border border-white/10 rounded-xl p-1.5 text-white outline-none focus:border-orange-500 text-center font-mono text-sm" value={form.leverage} onChange={(e) => handleFormChange('leverage', parseInt(e.target.value))} />
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div>
                                <div className="flex justify-between items-end mb-1">
                                    <label className="text-[10px] font-bold text-gray-500 uppercase">Target Spread Profit</label>
                                    <span className="text-xs font-mono font-bold text-brand-primary">{form.spread.toFixed(displayDigits)}</span>
                                </div>
                                <div className="flex gap-3 items-center">
                                    <input type="range" min="0" max={dynamicMax} step={dynamicStep} className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-primary" value={form.spread} onChange={(e) => setForm({ ...form, spread: parseFloat(e.target.value) })} />
                                    <input type="number" min="0" step={dynamicStep} className="w-24 bg-black/40 border border-white/10 rounded-xl p-1.5 text-white outline-none focus:border-brand-primary text-center font-mono text-sm" value={form.spread} onChange={(e) => setForm({ ...form, spread: parseFloat(e.target.value) })} />
                                </div>
                            </div>

                            <InputField label={`Margin Allocation (${form.symbol ? form.symbol.split('/')[1] || 'USDT' : 'USDT'})`} value={form.amount} onChange={(v: number) => setForm({ ...form, amount: v })} step={10} />
                        </div>
                    )}

                    {activeTab === 'triggers' && (
                        <div className="animate-fadeIn space-y-4">
                            {/* Triggers remain untouched */}
                            <p className="text-[10px] text-gray-400 mb-2 uppercase tracking-wider">Select the conditions that will trigger an entry order.</p>

                            <div className={`border rounded-xl p-4 transition-colors cursor-pointer ${form.enableWallTrigger ? 'bg-white/5 border-brand-primary/50' : 'bg-transparent border-white/10 hover:border-white/30'}`} onClick={() => handleFormChange('enableWallTrigger', !form.enableWallTrigger)}>
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-5 rounded-full p-1 transition-colors duration-200 flex items-center ${form.enableWallTrigger ? 'bg-brand-primary' : 'bg-gray-700'}`}>
                                            <div className={`w-3 h-3 bg-white rounded-full shadow-md transform transition-transform duration-200 ${form.enableWallTrigger ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                        </div>
                                        <span className="text-sm font-black text-white uppercase tracking-wider">Orderbook Wall</span>
                                    </div>
                                </div>
                                {form.enableWallTrigger && (
                                    <div className="mt-3 pl-1 space-y-4" onClick={e => e.stopPropagation()}>
                                        <div>
                                            <div className="flex justify-between items-end mb-1">
                                                <label className="text-[10px] font-bold text-gray-400 uppercase">Volume Wall Threshold</label>
                                                <span className="text-xs font-mono font-bold text-brand-primary">{form.vol.toLocaleString()}</span>
                                            </div>
                                            <input type="range" min="0" max="10000000" step="1000" className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-primary" value={form.vol} onChange={(e) => setForm({ ...form, vol: parseFloat(e.target.value) })} />
                                        </div>
                                        <div className="bg-black/20 p-3 rounded-lg border border-white/5">
                                            <div className="flex justify-between items-end mb-1">
                                                <label className="text-[10px] font-bold text-gray-400 uppercase">Max Wall Distance (%)</label>
                                                <span className="text-xs font-mono font-bold text-brand-primary">{form.maxWallDistancePct}%</span>
                                            </div>
                                            <div className="flex gap-3 items-center">
                                                <input type="range" min="0.1" max="10.0" step="0.1" className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-primary" value={form.maxWallDistancePct} onChange={(e) => setForm({ ...form, maxWallDistancePct: parseFloat(e.target.value) })} />
                                                <input type="number" min="0.1" max="100" step="0.1" className="w-20 bg-black/40 border border-white/10 rounded-xl p-1.5 text-white outline-none focus:border-brand-primary text-center font-mono text-sm" value={form.maxWallDistancePct} onChange={(e) => setForm({ ...form, maxWallDistancePct: parseFloat(e.target.value) })} />
                                            </div>
                                        </div>

                                        {/* CVD ABSORPTION CONFIRMATION */}
                                        <div className={`mt-3 p-3 rounded-lg border transition-all ${form.enableAbsorption ? 'bg-cyan-500/10 border-cyan-500/50' : 'bg-black/20 border-white/5'}`}>
                                            <div className="flex items-center justify-between cursor-pointer" onClick={() => handleFormChange('enableAbsorption', !form.enableAbsorption)}>
                                                <div className="flex items-center gap-2">
                                                    <div className={`w-10 h-5 rounded-full p-1 transition-colors flex items-center ${form.enableAbsorption ? 'bg-cyan-500' : 'bg-gray-700'}`}>
                                                        <div className={`w-3 h-3 bg-white rounded-full shadow-md transform transition-transform ${form.enableAbsorption ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                                    </div>
                                                    <span className="text-[11px] font-black text-white uppercase tracking-wider flex items-center gap-1">
                                                        CVD Absorption Meta-Confirmation
                                                        <div className="group relative">
                                                            <svg className="w-3 h-3 text-gray-400 cursor-help" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" /></svg>
                                                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-black border border-white/10 rounded-lg text-[9px] text-gray-300 hidden group-hover:block z-50 shadow-xl backdrop-blur-md">
                                                                Triggers ONLY if high market volume (Delta) hits the wall but fails to break it. High probability reversal signal.
                                                            </div>
                                                        </div>
                                                    </span>
                                                </div>
                                            </div>
                                            {form.enableAbsorption && (
                                                <div className="mt-3 space-y-3 animate-fadeIn">
                                                    <div>
                                                        <div className="flex justify-between items-end mb-1">
                                                            <label className="text-[9px] font-bold text-gray-400 uppercase">Min. Delta to Absorb ($)</label>
                                                            <span className="text-xs font-mono font-bold text-cyan-400">${form.absorptionThreshold.toLocaleString()}</span>
                                                        </div>
                                                        <input type="range" min="1000" max="1000000" step="1000" className="w-full h-1.5 accent-cyan-500 bg-white/10 rounded-lg appearance-none cursor-pointer" value={form.absorptionThreshold} onChange={(e) => handleFormChange('absorptionThreshold', parseFloat(e.target.value))} />
                                                    </div>
                                                    <div>
                                                        <div className="flex justify-between items-end mb-1">
                                                            <label className="text-[9px] font-bold text-gray-400 uppercase">Analysis Window (sec)</label>
                                                            <span className="text-xs font-mono font-bold text-cyan-400">{form.absorptionWindow}s</span>
                                                        </div>
                                                        <input type="range" min="1" max="60" className="w-full h-1.5 accent-cyan-500 bg-white/10 rounded-lg appearance-none cursor-pointer" value={form.absorptionWindow} onChange={(e) => handleFormChange('absorptionWindow', parseInt(e.target.value))} />
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className={`border rounded-xl p-4 transition-colors cursor-pointer ${form.enableLiqTrigger ? 'bg-rose-500/5 border-rose-500/50' : 'bg-transparent border-white/10 hover:border-white/30'}`} onClick={() => handleFormChange('enableLiqTrigger', !form.enableLiqTrigger)}>
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-5 rounded-full p-1 transition-colors duration-200 flex items-center ${form.enableLiqTrigger ? 'bg-rose-500' : 'bg-gray-700'}`}>
                                            <div className={`w-3 h-3 bg-white rounded-full shadow-md transform transition-transform duration-200 ${form.enableLiqTrigger ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                        </div>
                                        <span className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">Liquidation Sniping</span>
                                    </div>
                                </div>
                                {form.enableLiqTrigger && (
                                    <div className="mt-3 pl-1 space-y-4" onClick={e => e.stopPropagation()}>
                                        <div className={form.followBtcLiq ? 'opacity-30 pointer-events-none grayscale transition-all' : 'transition-all'}>
                                            <div className="flex justify-between items-end mb-1">
                                                <label className="text-[10px] font-bold text-gray-400 uppercase">Local Asset Liq. Threshold ($) {form.followBtcLiq && '(Ignored)'}</label>
                                                <span className="text-xs font-mono font-bold text-rose-500">${form.liqThreshold.toLocaleString()}</span>
                                            </div>
                                            <input 
                                                type="range" 
                                                min="1000" 
                                                max="1000000" 
                                                step="1000" 
                                                className="w-full h-2 rounded-lg appearance-none cursor-pointer accent-rose-500 bg-white/10" 
                                                value={form.liqThreshold} 
                                                disabled={form.followBtcLiq}
                                                onChange={(e) => setForm({ ...form, liqThreshold: parseFloat(e.target.value) })} 
                                            />
                                        </div>

                                        {/* BTC Follower */}
                                        <div className="bg-black/20 p-3 rounded-lg border border-white/5 space-y-3">
                                            <div className="flex items-center justify-between cursor-pointer" onClick={() => handleFormChange('followBtcLiq', !form.followBtcLiq)}>
                                                <div className="flex items-center gap-2">
                                                    <div className={`w-10 h-5 rounded-full p-1 transition-colors flex items-center ${form.followBtcLiq ? 'bg-orange-500' : 'bg-gray-700'}`}>
                                                        <div className={`w-3 h-3 bg-white rounded-full shadow-md transform transition-transform ${form.followBtcLiq ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                                    </div>
                                                    <span className="text-[11px] font-black text-white uppercase tracking-wider">Follow BTC Liquidation Flux</span>
                                                </div>
                                            </div>
                                            {form.followBtcLiq && (
                                                <div className="animate-fadeIn pt-1">
                                                    <div className="flex justify-between items-end mb-1">
                                                        <label className="text-[10px] font-bold text-gray-400 uppercase">BTC Threshold ($)</label>
                                                        <span className="text-xs font-mono font-bold text-orange-400">${form.btcLiqThreshold.toLocaleString()}</span>
                                                    </div>
                                                    <div className="flex gap-3 items-center">
                                                        <input type="range" min="10000" max="5000000" step="10000" className="flex-1 h-1.5 rounded-lg appearance-none cursor-pointer accent-orange-500 bg-white/10" value={form.btcLiqThreshold} onChange={(e) => handleFormChange('btcLiqThreshold', parseFloat(e.target.value))} />
                                                        <input type="number" step="10000" className="w-24 bg-black/40 border border-white/10 rounded-lg p-1 text-white text-center font-mono text-xs" value={form.btcLiqThreshold} onChange={(e) => handleFormChange('btcLiqThreshold', parseFloat(e.target.value))} />
                                                    </div>
                                                </div>
                                            )}
                                        </div>

                                        {/* Cascade & Dynamic */}
                                        <div className="grid grid-cols-2 gap-3">
                                            <div className={`bg-black/20 p-3 rounded-lg border cursor-pointer transition-colors ${form.enableLiqCascade ? 'border-rose-500/30 bg-rose-500/5' : 'border-white/5'}`} onClick={() => handleFormChange('enableLiqCascade', !form.enableLiqCascade)}>
                                                <span className="text-[10px] font-bold text-white uppercase block mb-2">Cascade Detection</span>
                                                {form.enableLiqCascade ? (
                                                    <div onClick={e => e.stopPropagation()}>
                                                        <div className="flex justify-between text-[9px] mb-1">
                                                            <span className="text-gray-400">WINDOW</span>
                                                            <span className="text-rose-400 font-mono">{form.liqCascadeWindow}s</span>
                                                        </div>
                                                        <input type="range" min="1" max="60" className="w-full h-1 accent-rose-500" value={form.liqCascadeWindow} onChange={(e) => handleFormChange('liqCascadeWindow', parseInt(e.target.value))} />
                                                    </div>
                                                ) : (
                                                    <span className="text-[9px] text-gray-500">Enable to detect liquidations in series</span>
                                                )}
                                            </div>
                                            
                                            <div className={`bg-black/20 p-3 rounded-lg border cursor-pointer transition-colors ${form.enableDynamicLiq ? 'border-cyan-500/30 bg-cyan-500/5' : 'border-white/5'}`} onClick={() => handleFormChange('enableDynamicLiq', !form.enableDynamicLiq)}>
                                                <span className="text-[10px] font-bold text-white uppercase block mb-2">Dynamic Adapt</span>
                                                {form.enableDynamicLiq ? (
                                                    <div onClick={e => e.stopPropagation()}>
                                                        <div className="flex justify-between text-[9px] mb-1">
                                                            <span className="text-gray-400">MULT</span>
                                                            <span className="text-cyan-400 font-mono">{form.dynamicLiqMultiplier}x</span>
                                                        </div>
                                                        <input type="range" min="0.5" max="5.0" step="0.1" className="w-full h-1 accent-cyan-500" value={form.dynamicLiqMultiplier} onChange={(e) => handleFormChange('dynamicLiqMultiplier', parseFloat(e.target.value))} />
                                                    </div>
                                                ) : (
                                                    <span className="text-[9px] text-gray-500">Auto-adjust threshold based on volatility</span>
                                                )}
                                            </div>
                                        </div>

                                        {/* Imbalance Filter for Liquidation */}
                                        <div className={`bg-black/20 p-3 rounded-lg border cursor-pointer transition-colors ${form.enableObImbalance ? 'border-amber-500/30 bg-amber-500/5' : 'border-white/5'}`} onClick={() => handleFormChange('enableObImbalance', !form.enableObImbalance)}>
                                            <div className="flex justify-between items-center mb-2">
                                                <span className="text-[10px] font-bold text-white uppercase">Bid/Ask Imbalance Filter</span>
                                                {form.enableObImbalance && <span className="text-xs font-mono font-bold text-amber-500">{form.obImbalanceRatio}x</span>}
                                            </div>
                                            {form.enableObImbalance && (
                                                <div onClick={e => e.stopPropagation()} className="animate-fadeIn">
                                                    <input type="range" min="1.1" max="10.0" step="0.1" className="w-full h-1.5 accent-amber-500 bg-white/10 rounded-lg appearance-none cursor-pointer" value={form.obImbalanceRatio} onChange={(e) => handleFormChange('obImbalanceRatio', parseFloat(e.target.value))} />
                                                    <p className="text-[8px] text-gray-500 mt-1 italic">Only trigger if orderbook also shows {form.obImbalanceRatio}x imbalance.</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {activeTab === 'risk' && (
                        <div className="animate-fadeIn space-y-4">

                            {/* --- FUTURES SPECIFIC RISK SETTINGS --- */}
                            {tradingMode === 'futures' && (
                                <div className="bg-orange-500/10 border border-orange-500/20 rounded-xl p-4 space-y-4 mb-2">
                                    <div className="flex items-center justify-between cursor-pointer" onClick={() => handleFormChange('reduceOnly', !form.reduceOnly)}>
                                        <div className="flex items-center gap-3">
                                            <div className={`w-10 h-5 rounded-full p-1 transition-colors duration-200 flex items-center ${form.reduceOnly ? 'bg-orange-500' : 'bg-gray-700'}`}>
                                                <div className={`w-3 h-3 bg-white rounded-full transform transition-transform duration-200 ${form.reduceOnly ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                            </div>
                                            <div>
                                                <span className="text-xs font-black text-orange-400 uppercase block">Reduce-Only Orders</span>
                                                <span className="text-[9px] text-gray-400">Prevents SL/TP from opening reverse positions</span>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <div className="flex justify-between items-end mb-1">
                                            <label className="text-[10px] font-bold text-orange-400/80 uppercase">Liquidation Distance Safety (%)</label>
                                            <span className="text-xs font-mono font-bold text-orange-400">{form.liquidationSafetyPct}%</span>
                                        </div>
                                        <input type="range" min="1.0" max="20.0" step="0.5" className="w-full h-2 rounded-lg appearance-none cursor-pointer accent-orange-500 bg-white/10" value={form.liquidationSafetyPct} onChange={(e) => handleFormChange('liquidationSafetyPct', parseFloat(e.target.value))} />
                                        <p className="text-[9px] text-gray-500 mt-1.5">Bot will not enter if liquidation price is closer than this percentage.</p>
                                    </div>
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-4">
                                <InputField label="Initial Risk % (Stop-Loss)" value={form.risk} onChange={(v: number) => setForm({ ...form, risk: v })} step={0.1} />
                                
                                <div className="bg-white/5 border border-white/10 rounded-xl p-3 flex flex-col justify-center">
                                    <div className="flex items-center justify-between mb-2">
                                        <label className="text-[10px] font-bold text-gray-400 uppercase">Trailing SL</label>
                                        <div className={`w-8 h-4 rounded-full p-0.5 flex items-center cursor-pointer ${form.enableTsl ? 'bg-brand-primary' : 'bg-gray-700'}`}
                                             onClick={(e) => { e.stopPropagation(); handleFormChange('enableTsl', !form.enableTsl); }}>
                                            <div className={`w-3 h-3 bg-white rounded-full transform transition-transform ${form.enableTsl ? 'translate-x-4' : 'translate-x-0'}`}></div>
                                        </div>
                                    </div>
                                    {form.enableTsl ? (
                                        <input type="number" step="0.1" className="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-white outline-none focus:border-brand-primary text-center font-mono text-sm" value={form.tsl} onChange={(e) => handleFormChange('tsl', parseFloat(e.target.value))} />
                                    ) : (
                                        <div className="text-xs text-gray-500 text-center py-2 font-mono">Disabled</div>
                                    )}
                                </div>
                            </div>

                            <div className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-brand-primary/30 transition-colors">
                                <div className="flex items-center justify-between mb-4 cursor-pointer" onClick={(e) => { e.stopPropagation(); handleFormChange('enablePartialTp', !form.enablePartialTp); }}>
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-6 rounded-full p-1 flex items-center ${form.enablePartialTp ? 'bg-brand-primary' : 'bg-gray-700'}`}>
                                            <div className={`w-4 h-4 bg-white rounded-full transform transition-transform ${form.enablePartialTp ? 'translate-x-6' : 'translate-x-0'}`}></div>
                                        </div>
                                        <div>
                                            <span className="text-xs font-black text-white uppercase block">Scale-Out (Partial TP)</span>
                                        </div>
                                    </div>
                                </div>
                                {form.enablePartialTp && (
                                    <div className="flex gap-4 items-center animate-fadeIn p-3 bg-black/20 rounded-xl border border-white/5">
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-gray-500 uppercase mb-1 block">Scale-Out Trigger Price (%)</label>
                                            <input type="number" step="0.1" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white outline-none focus:border-brand-primary text-center font-mono text-lg" value={form.partialTpTriggerPct} onChange={(e) => handleFormChange('partialTpTriggerPct', parseFloat(e.target.value))} />
                                        </div>
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-gray-500 uppercase mb-1 block">Sell Position Amount (%)</label>
                                            <input type="number" step="1" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white outline-none focus:border-brand-primary text-center font-mono text-lg" value={form.partialTp} onChange={(e) => handleFormChange('partialTp', parseFloat(e.target.value))} />
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* --- NEW: BREAKEVEN SL SECTION --- */}
                            <div className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-emerald-500/30 transition-colors mt-4">
                                <div className="flex items-center justify-between mb-4 cursor-pointer" onClick={(e) => { e.stopPropagation(); handleFormChange('enableBreakevenSl', !form.enableBreakevenSl); }}>
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-6 rounded-full p-1 flex items-center ${form.enableBreakevenSl ? 'bg-emerald-500' : 'bg-gray-700'}`}>
                                            <div className={`w-4 h-4 bg-white rounded-full transform transition-transform ${form.enableBreakevenSl ? 'translate-x-6' : 'translate-x-0'}`}></div>
                                        </div>
                                        <div>
                                            <span className="text-xs font-black text-white uppercase block">Risk-Free (SL to Breakeven)</span>
                                            <span className="text-[9px] text-gray-500 uppercase mt-0.5 block">Moves Stop-Loss based on Profit Target</span>
                                        </div>
                                    </div>
                                </div>
                                {form.enableBreakevenSl && (
                                    <div className="flex gap-4 items-center animate-fadeIn p-3 bg-black/20 rounded-xl border border-white/5">
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-gray-500 uppercase mb-1 block">Breakeven Trigger (%)</label>
                                            <input type="number" step="0.1" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white outline-none focus:border-emerald-500 text-center font-mono text-lg" value={form.breakevenTriggerPct} onChange={(e) => handleFormChange('breakevenTriggerPct', parseFloat(e.target.value))} />
                                        </div>
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-gray-500 uppercase mb-1 block">Breakeven Target (%)</label>
                                            <input type="number" step="0.05" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white outline-none focus:border-emerald-500 text-center font-mono text-lg" value={form.breakevenTargetPct} onChange={(e) => handleFormChange('breakevenTargetPct', parseFloat(e.target.value))} />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {activeTab === 'advanced' && (
                        <div className="animate-fadeIn space-y-4">
                            <div className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-cyan-500/30 transition-colors shadow-[0_4px_20px_rgba(0,0,0,0.2)]">
                                <div className="flex items-center justify-between mb-4 cursor-pointer" onClick={(e) => { e.stopPropagation(); handleFormChange('enableMicroScalp', !form.enableMicroScalp); }}>
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-6 rounded-full p-1 flex items-center ${form.enableMicroScalp ? 'bg-cyan-500' : 'bg-gray-700'}`}>
                                            <div className={`w-4 h-4 bg-white rounded-full transform transition-transform ${form.enableMicroScalp ? 'translate-x-6' : 'translate-x-0'}`}></div>
                                        </div>
                                        <div>
                                            <span className="text-xs font-black text-white uppercase tracking-wider flex items-center gap-1.5">Micro-Scalp / Quick Bounce</span>
                                        </div>
                                    </div>
                                </div>
                                {form.enableMicroScalp && (
                                    <div className="flex gap-4 items-center p-3 bg-black/20 rounded-xl border border-white/5">
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-gray-500 uppercase block">Target Profit (Ticks)</label>
                                            <input type="number" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white text-center" value={form.microScalpProfitTicks} onChange={(e) => handleFormChange('microScalpProfitTicks', parseInt(e.target.value))} />
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <InputField label="Spoof Detect Time (Seconds)" value={form.spoofTime} onChange={(v: number) => setForm({ ...form, spoofTime: v })} step={0.5} />
                                <InputField label="Trailing SL Step (%)" value={form.tsl} onChange={(v: number) => setForm({ ...form, tsl: v })} step={0.1} />
                            </div>

                            {/* --- BTC CORRELATION FILTER SECTION --- */}
                            <div className={`border rounded-xl p-4 transition-colors cursor-pointer ${form.enableBtcCorrelation ? 'bg-orange-500/5 border-orange-500/50' : 'bg-transparent border-white/10 hover:border-white/30'}`} onClick={() => handleFormChange('enableBtcCorrelation', !form.enableBtcCorrelation)}>
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-5 rounded-full p-1 transition-colors duration-200 flex items-center ${form.enableBtcCorrelation ? 'bg-orange-500' : 'bg-gray-700'}`}>
                                            <div className={`w-3 h-3 bg-white rounded-full shadow-md transform transition-transform duration-200 ${form.enableBtcCorrelation ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                        </div>
                                        <span className="text-sm font-black text-white uppercase tracking-wider">BTC Correlation Anti-Fakeout</span>
                                    </div>
                                </div>
                                {form.enableBtcCorrelation && (
                                    <div className="mt-3 pl-1 grid grid-cols-2 gap-4 animate-fadeIn" onClick={e => e.stopPropagation()}>
                                        <div className="col-span-2">
                                            <label className="text-[10px] font-bold text-gray-400 uppercase mb-1 block">Correlation Threshold (Pearson)</label>
                                            <div className="flex gap-3 items-center">
                                                <input type="range" min="0.1" max="1.0" step="0.1" className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-orange-500" value={form.btcCorrelationThreshold} onChange={(e) => handleFormChange('btcCorrelationThreshold', parseFloat(e.target.value))} />
                                                <input type="number" step="0.1" className="w-20 bg-black/40 border border-white/10 rounded-xl p-1.5 text-white text-center font-mono text-sm" value={form.btcCorrelationThreshold} onChange={(e) => handleFormChange('btcCorrelationThreshold', parseFloat(e.target.value))} />
                                            </div>
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-bold text-gray-400 uppercase mb-1 block">Time Window (Mins)</label>
                                            <input type="number" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white text-center font-mono" value={form.btcTimeWindow} onChange={(e) => handleFormChange('btcTimeWindow', parseInt(e.target.value))} />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-bold text-gray-400 uppercase mb-1 block">Min BTC Move (%)</label>
                                            <input type="number" step="0.05" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white text-center font-mono" value={form.btcMinMovePct} onChange={(e) => handleFormChange('btcMinMovePct', parseFloat(e.target.value))} />
                                        </div>
                                        <p className="col-span-2 text-[9px] text-gray-500 mt-1 italic">Only enter trades if BTC aligns with the target asset's direction and has moved the minimum %.</p>
                                    </div>
                                )}
                            </div>

                            {/* --- VPVR SECTION --- */}
                            <div className={`border rounded-xl p-4 transition-colors cursor-pointer ${form.vpvrEnabled ? 'bg-yellow-500/5 border-yellow-500/50' : 'bg-transparent border-white/10 hover:border-white/30'}`} onClick={() => handleFormChange('vpvrEnabled', !form.vpvrEnabled)}>
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-5 rounded-full p-1 transition-colors duration-200 flex items-center ${form.vpvrEnabled ? 'bg-yellow-500' : 'bg-gray-700'}`}>
                                            <div className={`w-3 h-3 bg-white rounded-full shadow-md transform transition-transform duration-200 ${form.vpvrEnabled ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                        </div>
                                        <span className="text-sm font-black text-white uppercase tracking-wider">VPVR High Volume Node Confirmation</span>
                                    </div>
                                </div>
                                {form.vpvrEnabled && (
                                    <div className="mt-3 pl-1 animate-fadeIn" onClick={e => e.stopPropagation()}>
                                        <label className="text-[10px] font-bold text-gray-400 uppercase mb-1 block">Value Area Tolerance (%)</label>
                                        <div className="flex gap-3 items-center">
                                            <input type="range" min="0.05" max="2.0" step="0.05" className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-yellow-500" value={form.vpvrTolerance} onChange={(e) => handleFormChange('vpvrTolerance', parseFloat(e.target.value))} />
                                            <input type="number" step="0.05" className="w-20 bg-black/40 border border-white/10 rounded-xl p-1.5 text-white text-center font-mono text-sm" value={form.vpvrTolerance} onChange={(e) => handleFormChange('vpvrTolerance', parseFloat(e.target.value))} />
                                        </div>
                                        <p className="text-[9px] text-gray-500 mt-2 italic">Only enter trades if price is within this % of the Volume Profile High Volume Node.</p>
                                    </div>
                                )}
                            </div>

                            {/* --- ATR SECTION --- */}
                            <div className={`border rounded-xl p-4 transition-colors cursor-pointer ${form.atrEnabled ? 'bg-blue-500/5 border-blue-500/50' : 'bg-transparent border-white/10 hover:border-white/30'}`} onClick={() => handleFormChange('atrEnabled', !form.atrEnabled)}>
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-5 rounded-full p-1 transition-colors duration-200 flex items-center ${form.atrEnabled ? 'bg-blue-500' : 'bg-gray-700'}`}>
                                            <div className={`w-3 h-3 bg-white rounded-full shadow-md transform transition-transform duration-200 ${form.atrEnabled ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                        </div>
                                        <span className="text-sm font-black text-white uppercase tracking-wider">ATR Volatility Based Stops</span>
                                    </div>
                                </div>
                                {form.atrEnabled && (
                                    <div className="mt-3 pl-1 grid grid-cols-2 gap-4 animate-fadeIn" onClick={e => e.stopPropagation()}>
                                        <div>
                                            <label className="text-[10px] font-bold text-gray-400 uppercase mb-1 block">ATR Period</label>
                                            <input type="number" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white text-center font-mono" value={form.atrPeriod} onChange={(e) => handleFormChange('atrPeriod', parseInt(e.target.value))} />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-bold text-gray-400 uppercase mb-1 block">Multiplier</label>
                                            <input type="number" step="0.1" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white text-center font-mono" value={form.atrMultiplier} onChange={(e) => handleFormChange('atrMultiplier', parseFloat(e.target.value))} />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* --- FOOTER ACTIONS --- */}
                <div className="pt-4 border-t border-white/10 mt-2 flex-shrink-0">
                    {errorMsg && (
                        <p className={`text-xs font-bold mb-3 animate-pulse text-center py-2 rounded-lg ${errorMsg.includes('Success') ? 'text-green-400 bg-green-500/10' : 'text-red-500 bg-red-500/10'}`}>
                            {errorMsg}
                        </p>
                    )}

                    <div className="flex gap-3">
                        <button onClick={onClose} disabled={isLoading} className="w-[120px] bg-white/5 hover:bg-white/10 text-gray-400 rounded-xl text-xs font-bold transition-colors">
                            CANCEL
                        </button>
                        <button
                            onClick={handleDeploy}
                            disabled={isLoading}
                            className={`flex-1 h-12 rounded-xl font-black text-white text-sm transition-all shadow-[0_0_15px_rgba(245,158,11,0.2)] ${isLoading ? 'bg-gray-600 cursor-not-allowed opacity-70' : existingBot ? 'bg-gradient-to-r from-blue-500 to-indigo-600' : tradingMode === 'futures' ? 'bg-gradient-to-r from-orange-500 to-red-600 hover:scale-[1.02]' : 'bg-gradient-to-r from-yellow-400 to-orange-600 hover:scale-[1.02]'}`}
                        >
                            {isLoading ? 'PROCESSING...' : existingBot ? '⚙️ UPDATE CONFIGURATION' : tradingMode === 'futures' ? '⚡ DEPLOY FUTURE BOT' : '🚀 DEPLOY SNIPER'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

const InputField = ({ label, value, onChange, step = 1 }: any) => (
    <div>
        <label className="text-[10px] font-bold text-gray-500 uppercase mb-1 block">{label}</label>
        <input type="number" step={step} className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white outline-none focus:border-brand-primary" value={value} onChange={(e) => onChange(parseFloat(e.target.value))} />
    </div>
);
