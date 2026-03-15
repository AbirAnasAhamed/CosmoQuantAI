import React, { useEffect, useState } from 'react';
import { fetchApiKeys } from '../../../services/settings';
import { botService } from '../../../services/botService';
import { marketDataService } from '../../../services/marketData';

export const WallHunterModal: React.FC<{ isOpen: boolean; onClose: () => void; symbol: string; bids?: any[]; asks?: any[]; onDeploySuccess?: (botId: number) => void }> = ({ isOpen, onClose, symbol, bids = [], asks = [], onDeploySuccess }) => {
    const [savedKeys, setSavedKeys] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');
    const [activeTab, setActiveTab] = useState('basic');
    
    // --- NEW: Trading Mode State ---
    const [tradingMode, setTradingMode] = useState<'spot' | 'futures'>('spot');
    const [availableExchanges, setAvailableExchanges] = useState<string[]>([]);

    const [form, setForm] = useState({
        symbol: symbol,
        exchange: 'binance',
        isPaper: true,
        apiKeyId: '',
        vol: 500000,
        spread: 0.0002,
        risk: 0.5,
        tsl: 0.2,
        amount: 100,
        sellOrderType: 'market',
        spoofTime: 3.0,
        enablePartialTp: true,
        partialTp: 50.0,
        vpvrEnabled: false,
        vpvrTolerance: 0.2,
        atrEnabled: false,
        atrPeriod: 14,
        atrMultiplier: 2.0,

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
        liquidationSafetyPct: 5.0
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
                            tsl: c.trailing_stop || 0.2,
                            amount: c.amount_per_trade || 100,
                            sellOrderType: c.sell_order_type || 'market',
                            spoofTime: c.min_wall_lifetime !== undefined ? c.min_wall_lifetime : 3.0,
                            enablePartialTp: c.partial_tp_pct !== undefined ? c.partial_tp_pct > 0 : true,
                            partialTp: c.partial_tp_pct !== undefined && c.partial_tp_pct > 0 ? c.partial_tp_pct : 50.0,
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
                            liquidationSafetyPct: c.liquidation_safety_pct || 5.0
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

    const handleAutoDetect = () => {
        let optimalVol = form.vol;
        let optimalSpread = form.spread;
        let optimalAmount = form.amount;

        if (bids.length > 0 && asks.length > 0) {
            const bestBid = bids[0].price;
            const bestAsk = asks[0].price;
            const currentSpread = bestAsk - bestBid;
            const currentPrice = bestBid;
            
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

            optimalSpread = currentSpread + (bestAsk * 0.001);
            optimalSpread = parseFloat(Math.max(dynamicStep, Math.min(dynamicStep * 100, optimalSpread)).toFixed(displayDigits));

            const allSizes = [...bids.map(b => b.size), ...asks.map(a => a.size)];

            if (allSizes.length > 0) {
                const maxSize = Math.max(...allSizes);
                const avgSize = allSizes.reduce((sum, size) => sum + size, 0) / allSizes.length;
                let calculatedVol = avgSize * 3;

                if (calculatedVol > maxSize * 0.9) calculatedVol = maxSize * 0.8;
                if (calculatedVol > 10000) optimalVol = Math.round(calculatedVol / 1000) * 1000;
                else optimalVol = Math.round(calculatedVol / 100) * 100;
                optimalVol = Math.max(10, optimalVol);

                const avgQuoteSize = avgSize * bestBid;
                optimalAmount = parseFloat(Math.max(10, avgQuoteSize * 0.1).toFixed(2));
            }
        }

        setForm(prev => ({
            ...prev,
            vol: optimalVol,
            spread: optimalSpread,
            amount: optimalAmount
        }));
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
                    trailing_stop: form.tsl,
                    vol_threshold: form.vol,
                    risk_pct: form.risk,
                    sell_order_type: form.sellOrderType,
                    min_wall_lifetime: form.spoofTime,
                    partial_tp_pct: form.enablePartialTp ? form.partialTp : 0.0,
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
                    })
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
                                            <select className="w-full bg-black/40 border border-white/10 p-2.5 rounded-lg text-white outline-none text-sm" value={form.positionDirection} onChange={(e) => handleFormChange('positionDirection', e.target.value)}>
                                                <option className="bg-[#0B1120]" value="auto">Auto (Hitmap Based)</option>
                                                <option className="bg-[#0B1120] text-green-400" value="long">Long Only</option>
                                                <option className="bg-[#0B1120] text-red-400" value="short">Short Only</option>
                                            </select>
                                        </div>
                                    </div>

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
                                        <div className="flex justify-between items-end mb-1">
                                            <label className="text-[10px] font-bold text-gray-400 uppercase">Local Asset Liq. Threshold ($)</label>
                                            <span className="text-xs font-mono font-bold text-rose-500">${form.liqThreshold.toLocaleString()}</span>
                                        </div>
                                        <input type="range" min="1000" max="500000" step="1000" className="w-full h-2 rounded-lg appearance-none cursor-pointer accent-rose-500 bg-white/10" value={form.liqThreshold} onChange={(e) => setForm({ ...form, liqThreshold: parseFloat(e.target.value) })} />
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
                                <InputField label="Trailing SL Step %" value={form.tsl} onChange={(v: number) => setForm({ ...form, tsl: v })} step={0.1} />
                            </div>

                            <div className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-brand-primary/30 transition-colors">
                                <div className="flex items-center justify-between mb-4 cursor-pointer" onClick={(e) => { e.stopPropagation(); handleFormChange('enablePartialTp', !form.enablePartialTp); }}>
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-6 rounded-full p-1 flex items-center ${form.enablePartialTp ? 'bg-brand-primary' : 'bg-gray-700'}`}>
                                            <div className={`w-4 h-4 bg-white rounded-full transform transition-transform ${form.enablePartialTp ? 'translate-x-6' : 'translate-x-0'}`}></div>
                                        </div>
                                        <div>
                                            <span className="text-xs font-black text-white uppercase block">Scale-Out & Break-Even</span>
                                        </div>
                                    </div>
                                </div>
                                {form.enablePartialTp && (
                                    <div className="flex gap-4 items-center animate-fadeIn p-3 bg-black/20 rounded-xl border border-white/5">
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-gray-500 uppercase mb-1 block">Sell at Target TP1 (%)</label>
                                            <input type="number" step="10" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white outline-none focus:border-brand-primary text-center font-mono text-lg" value={form.partialTp} onChange={(e) => handleFormChange('partialTp', parseFloat(e.target.value))} />
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

                            <div>
                                <InputField label="Spoof Detect Time (Seconds)" value={form.spoofTime} onChange={(v: number) => setForm({ ...form, spoofTime: v })} step={0.5} />
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
