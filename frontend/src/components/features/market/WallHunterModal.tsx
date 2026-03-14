import React, { useEffect, useState } from 'react';
import { fetchApiKeys } from '../../../services/settings';
import { botService } from '../../../services/botService';

export const WallHunterModal: React.FC<{ isOpen: boolean; onClose: () => void; symbol: string; bids?: any[]; asks?: any[]; onDeploySuccess?: (botId: number) => void }> = ({ isOpen, onClose, symbol, bids = [], asks = [], onDeploySuccess }) => {
    const [savedKeys, setSavedKeys] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');
    const [activeTab, setActiveTab] = useState('basic');
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

        // --- NEW: Liquidation & Scalp States ---
        enableWallTrigger: true,        // Default wall detection
        maxWallDistancePct: 1.0,        // Max distance from mid price
        enableLiqTrigger: false,        // Liquidation sniper toggle
        liqThreshold: 50000,            // Min liquidation amount
        enableMicroScalp: false,        // Auto tick-scalping
        microScalpProfitTicks: 2,       // Ticks to profit
        microScalpMinWall: 100000,      // Confluence wall support

        // --- NEW: Smart Liquidation HFT ---
        enableLiqCascade: false,        // Aggregated Liquidations
        liqCascadeWindow: 5,            // Seconds
        enableDynamicLiq: false,        // ATR Based Threshold
        dynamicLiqMultiplier: 1.0,      // Threshold Multiplier
        enableObImbalance: false,       // Tape Reading
        obImbalanceRatio: 1.5,          // Bid/Ask volume ratio

        // --- BRAND NEW: BTC Liquidation Follower ---
        followBtcLiq: false,
        btcLiqThreshold: 500000
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

                            // Load existing new states if present
                            enableWallTrigger: c.enable_wall_trigger !== undefined ? c.enable_wall_trigger : true,
                            maxWallDistancePct: c.max_wall_distance_pct !== undefined ? c.max_wall_distance_pct : 1.0,
                            enableLiqTrigger: c.enable_liq_trigger !== undefined ? c.enable_liq_trigger : false,
                            liqThreshold: c.liq_threshold || 50000,
                            enableMicroScalp: c.enable_micro_scalp !== undefined ? c.enable_micro_scalp : false,
                            microScalpProfitTicks: c.micro_scalp_profit_ticks || 2,
                            microScalpMinWall: c.micro_scalp_min_wall || 100000,

                            // Load existing smart liquidations
                            enableLiqCascade: c.enable_liq_cascade !== undefined ? c.enable_liq_cascade : false,
                            liqCascadeWindow: c.liq_cascade_window || 5,
                            enableDynamicLiq: c.enable_dynamic_liq !== undefined ? c.enable_dynamic_liq : false,
                            dynamicLiqMultiplier: c.dynamic_liq_multiplier || 1.0,
                            enableObImbalance: c.enable_ob_imbalance !== undefined ? c.enable_ob_imbalance : false,
                            obImbalanceRatio: c.ob_imbalance_ratio || 1.5,

                            // Load BTC feature
                            followBtcLiq: c.follow_btc_liq !== undefined ? c.follow_btc_liq : false,
                            btcLiqThreshold: c.btc_liq_threshold || 500000
                        }));
                    } else {
                        setExistingBot(null);
                    }
                }).catch(() => { });
            } catch (e) { }
        }
    }, [isOpen, symbol]);

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
            
            // Fixed Math Error for low-cap coins
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

        // Trigger Validation
        if (!form.enableWallTrigger && !form.enableLiqTrigger) {
            setErrorMsg("Please enable at least one Entry Trigger (Orderbook Wall or Liquidation).");
            return;
        }

        setErrorMsg('');
        setIsLoading(true);

        try {
            const payload = {
                name: `L2 Hunter: ${form.symbol}`,
                description: "Orderbook & Liquidation Scalping Hunter",
                exchange: form.exchange,
                market: form.symbol,
                strategy: "wall_hunter",
                timeframe: "1m",
                trade_value: form.amount,
                trade_unit: "QUOTE",
                api_key_id: form.isPaper ? null : form.apiKeyId,
                is_paper_trading: form.isPaper,
                config: {
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

                    // --- NEW: Passing to backend ---
                    enable_wall_trigger: form.enableWallTrigger,
                    max_wall_distance_pct: form.maxWallDistancePct,
                    enable_liq_trigger: form.enableLiqTrigger,
                    liq_threshold: form.liqThreshold,
                    enable_micro_scalp: form.enableMicroScalp,
                    micro_scalp_profit_ticks: form.microScalpProfitTicks,
                    micro_scalp_min_wall: form.microScalpMinWall,

                    // --- NEW: Smart Liquidation ---
                    enable_liq_cascade: form.enableLiqCascade,
                    liq_cascade_window: form.liqCascadeWindow,
                    enable_dynamic_liq: form.enableDynamicLiq,
                    dynamic_liq_multiplier: form.dynamicLiqMultiplier,
                    enable_ob_imbalance: form.enableObImbalance,
                    ob_imbalance_ratio: form.obImbalanceRatio,

                    // Pass BTC specific settings
                    follow_btc_liq: form.followBtcLiq,
                    btc_liq_threshold: form.btcLiqThreshold
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

    // --- Dynamic Target Spread Calculation based on asset price magnitude ---
    const currentPrice = bids.length > 0 ? bids[0].price : (asks.length > 0 ? asks[0].price : 1);
    
    // Fixed Math Error for low-cap coins
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

    const dynamicMax = dynamicStep * 500; // Allows up to 500 ticks spread

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
                            {/* Asset, Exchange, Paper Trading UI logic remains same as original */}
                            <div className="flex gap-4">
                                <div className="space-y-1 w-1/3">
                                    <label className="text-[10px] text-gray-500 font-bold uppercase">Asset</label>
                                    <input className="w-full bg-white/5 p-2 rounded-xl text-yellow-500 font-mono outline-none border border-transparent text-sm" value={form.symbol} readOnly />
                                </div>
                                <div className="space-y-1 w-1/3">
                                    <label className="text-[10px] text-gray-500 font-bold uppercase">Exchange</label>
                                    <select className="w-full bg-white/5 p-2 rounded-xl text-white outline-none text-sm" value={form.exchange} onChange={(e) => setForm({ ...form, exchange: e.target.value })}>
                                        <option className="bg-[#0B1120] text-white" value="binance">Binance</option>
                                        <option className="bg-[#0B1120] text-white" value="bybit">Bybit</option>
                                        <option className="bg-[#0B1120] text-white" value="okx">OKX</option>
                                        <option className="bg-[#0B1120] text-white" value="bitget">Bitget</option>
                                        <option className="bg-[#0B1120] text-white" value="bingx">BingX</option>
                                        <option className="bg-[#0B1120] text-white" value="gateio">Gate.io</option>
                                        <option className="bg-[#0B1120] text-white" value="mexc">MEXC</option>
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

                            <InputField label={`Trading Amount (${form.symbol ? form.symbol.split('/')[1] || 'Quote Asset' : 'Quote Asset'})`} value={form.amount} onChange={(v: number) => setForm({ ...form, amount: v })} step={10} />
                        </div>
                    )}

                    {/* --- NEW TAB: TRIGGERS --- */}
                    {activeTab === 'triggers' && (
                        <div className="animate-fadeIn space-y-4">
                            <p className="text-[10px] text-gray-400 mb-2 uppercase tracking-wider">Select the conditions that will trigger a buy order. Enable both for Confluence Mode (Highest Probability).</p>

                            {/* Orderbook Wall Trigger */}
                            <div className={`border rounded-xl p-4 transition-colors cursor-pointer ${form.enableWallTrigger ? 'bg-white/5 border-brand-primary/50' : 'bg-transparent border-white/10 hover:border-white/30'}`} onClick={() => handleFormChange('enableWallTrigger', !form.enableWallTrigger)}>
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-5 rounded-full p-1 transition-colors duration-200 flex items-center ${form.enableWallTrigger ? 'bg-brand-primary' : 'bg-gray-700'}`}>
                                            <div className={`w-3 h-3 bg-white rounded-full shadow-md transform transition-transform duration-200 ${form.enableWallTrigger ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                        </div>
                                        <span className="text-sm font-black text-white uppercase tracking-wider">Orderbook Wall</span>
                                    </div>
                                    <span className={`text-[10px] font-black px-2 py-1 rounded-md ${form.enableWallTrigger ? 'bg-brand-primary/20 text-brand-primary' : 'bg-white/5 text-gray-500'}`}>{form.enableWallTrigger ? 'ON' : 'OFF'}</span>
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
                                            <p className="text-[9px] text-gray-500 mt-1.5">Only trigger if wall is within this % distance from current price to prevent premature entries.</p>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Liquidation Sniper Trigger */}
                            <div className={`border rounded-xl p-4 transition-colors cursor-pointer ${form.enableLiqTrigger ? 'bg-rose-500/5 border-rose-500/50' : 'bg-transparent border-white/10 hover:border-white/30'}`} onClick={() => handleFormChange('enableLiqTrigger', !form.enableLiqTrigger)}>
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-5 rounded-full p-1 transition-colors duration-200 flex items-center ${form.enableLiqTrigger ? 'bg-rose-500' : 'bg-gray-700'}`}>
                                            <div className={`w-3 h-3 bg-white rounded-full shadow-md transform transition-transform duration-200 ${form.enableLiqTrigger ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                        </div>
                                        <div>
                                            <span className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">Short Liquidation <span className="text-[8px] bg-rose-500 text-white px-1.5 py-0.5 rounded-sm animate-pulse">NEW</span></span>
                                        </div>
                                    </div>
                                    <span className={`text-[10px] font-black px-2 py-1 rounded-md ${form.enableLiqTrigger ? 'bg-rose-500/20 text-rose-400' : 'bg-white/5 text-gray-500'}`}>{form.enableLiqTrigger ? 'ON' : 'OFF'}</span>
                                </div>
                                {form.enableLiqTrigger && (
                                    <div className="mt-3 pl-1" onClick={e => e.stopPropagation()}>
                                        
                                        {/* --- NEW: Follow BTC Liquidation Toggle --- */}
                                        <div className="mb-4 bg-orange-500/10 rounded-xl p-3 border border-orange-500/20 flex items-center justify-between cursor-pointer" onClick={() => handleFormChange('followBtcLiq', !form.followBtcLiq)}>
                                            <div>
                                                <p className="text-xs font-bold text-white flex items-center gap-1.5">Follow BTC Liquidation <span className="text-[8px] bg-orange-500 text-white px-1 rounded-sm shadow-[0_0_10px_rgba(249,115,22,0.5)]">ALPHA</span></p>
                                                <p className="text-[9px] text-gray-400 mt-0.5">Trigger buy when BTC gets liquidated heavily</p>
                                            </div>
                                            <div className={`w-8 h-4 rounded-full p-0.5 flex transition-colors ${form.followBtcLiq ? 'bg-orange-500 justify-end' : 'bg-gray-700 justify-start'}`}><div className="w-3 h-3 bg-white rounded-full"></div></div>
                                        </div>

                                        {form.followBtcLiq ? (
                                            <div className="mb-4 bg-black/40 p-3 rounded-lg border border-white/5">
                                                <div className="flex justify-between items-end mb-1">
                                                    <label className="text-[10px] font-bold text-gray-400 uppercase">BTC Liq. Threshold ($)</label>
                                                    <span className="text-xs font-mono font-bold text-orange-500">${form.btcLiqThreshold.toLocaleString()}</span>
                                                </div>
                                                <div className="flex gap-3 items-center">
                                                    <input disabled={form.enableDynamicLiq} type="range" min="100" max="100000000" step="100" className={`flex-1 h-2 rounded-lg appearance-none cursor-pointer accent-orange-500 ${form.enableDynamicLiq ? 'bg-white/5 opacity-50' : 'bg-white/10'}`} value={form.btcLiqThreshold} onChange={(e) => handleFormChange('btcLiqThreshold', parseFloat(e.target.value))} />
                                                    <input disabled={form.enableDynamicLiq} type="number" min="100" max="100000000" step="100" className={`w-24 bg-black/40 border border-white/10 rounded-xl p-1.5 text-white outline-none focus:border-orange-500 text-center font-mono text-sm ${form.enableDynamicLiq ? 'opacity-50' : ''}`} value={form.btcLiqThreshold} onChange={(e) => handleFormChange('btcLiqThreshold', parseFloat(e.target.value))} />
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="mb-4">
                                                <div className="flex justify-between items-end mb-1">
                                                    <label className="text-[10px] font-bold text-gray-400 uppercase">Local Asset Liq. Threshold ($)</label>
                                                    <span className="text-xs font-mono font-bold text-rose-500">${form.liqThreshold.toLocaleString()}</span>
                                                </div>
                                                <input disabled={form.enableDynamicLiq} type="range" min="1000" max="500000" step="1000" className={`w-full h-2 rounded-lg appearance-none cursor-pointer accent-rose-500 ${form.enableDynamicLiq ? 'bg-white/5 opacity-50' : 'bg-white/10'}`} value={form.liqThreshold} onChange={(e) => setForm({ ...form, liqThreshold: parseFloat(e.target.value) })} />
                                            </div>
                                        )}

                                        {/* --- CASCADE FEATURE --- */}
                                        <div className="mt-4 bg-black/20 rounded-xl p-3 border border-white/5 flex items-center justify-between cursor-pointer" onClick={() => handleFormChange('enableLiqCascade', !form.enableLiqCascade)}>
                                            <div>
                                                <p className="text-xs font-bold text-white flex items-center gap-1.5">Cascade Detection <span className="text-[8px] bg-rose-500 text-black px-1 rounded-sm">HFT</span></p>
                                                <p className="text-[9px] text-gray-500 mt-0.5">Sum liquidations over a time window</p>
                                            </div>
                                            <div className={`w-8 h-4 rounded-full p-0.5 flex ${form.enableLiqCascade ? 'bg-rose-500 justify-end' : 'bg-gray-700 justify-start'}`}><div className="w-3 h-3 bg-white rounded-full"></div></div>
                                        </div>
                                        {form.enableLiqCascade && (
                                            <div className="mt-2 flex items-center justify-between bg-black/40 p-2 rounded-lg">
                                                <label className="text-[10px] text-gray-400">Aggregation Window (sec)</label>
                                                <input type="number" min="1" max="60" className="w-16 bg-white/10 text-white text-xs text-center p-1 rounded outline-none" value={form.liqCascadeWindow} onChange={e => handleFormChange('liqCascadeWindow', parseInt(e.target.value))} />
                                            </div>
                                        )}

                                        {/* --- DYNAMIC THRESHOLD --- */}
                                        <div className="mt-2 bg-black/20 rounded-xl p-3 border border-white/5 flex items-center justify-between cursor-pointer" onClick={() => handleFormChange('enableDynamicLiq', !form.enableDynamicLiq)}>
                                            <div>
                                                <p className="text-xs font-bold text-white flex items-center gap-1.5">Dynamic Threshold <span className="text-[8px] bg-green-500 text-black px-1 rounded-sm">SMART</span></p>
                                                <p className="text-[9px] text-gray-500 mt-0.5">Scale threshold using market ATR</p>
                                            </div>
                                            <div className={`w-8 h-4 rounded-full p-0.5 flex ${form.enableDynamicLiq ? 'bg-green-500 justify-end' : 'bg-gray-700 justify-start'}`}><div className="w-3 h-3 bg-white rounded-full"></div></div>
                                        </div>
                                        {form.enableDynamicLiq && (
                                            <div className="mt-2 flex items-center justify-between bg-black/40 p-2 rounded-lg">
                                                <label className="text-[10px] text-gray-400">ATR Multiplier</label>
                                                <input type="number" step="0.1" min="0.1" max="10" className="w-16 bg-white/10 text-white text-xs text-center p-1 rounded outline-none" value={form.dynamicLiqMultiplier} onChange={e => handleFormChange('dynamicLiqMultiplier', parseFloat(e.target.value))} />
                                            </div>
                                        )}

                                        {/* --- OB IMBALANCE --- */}
                                        <div className="mt-2 bg-black/20 rounded-xl p-3 border border-white/5 flex items-center justify-between cursor-pointer" onClick={() => handleFormChange('enableObImbalance', !form.enableObImbalance)}>
                                            <div>
                                                <p className="text-xs font-bold text-white flex items-center gap-1.5">Tape Reading (Bids vs Asks) <span className="text-[8px] bg-blue-500 text-black px-1 rounded-sm">L2</span></p>
                                                <p className="text-[9px] text-gray-500 mt-0.5">Verify buyer pressure post-liquidation</p>
                                            </div>
                                            <div className={`w-8 h-4 rounded-full p-0.5 flex ${form.enableObImbalance ? 'bg-blue-500 justify-end' : 'bg-gray-700 justify-start'}`}><div className="w-3 h-3 bg-white rounded-full"></div></div>
                                        </div>
                                        {form.enableObImbalance && (
                                            <div className="mt-2 flex items-center justify-between bg-black/40 p-2 rounded-lg">
                                                <label className="text-[10px] text-gray-400">Min Bid/Ask Ratio</label>
                                                <input type="number" step="0.1" min="0.5" max="10" className="w-16 bg-white/10 text-white text-xs text-center p-1 rounded outline-none" value={form.obImbalanceRatio} onChange={e => handleFormChange('obImbalanceRatio', parseFloat(e.target.value))} />
                                            </div>
                                        )}

                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {activeTab === 'risk' && (
                        <div className="animate-fadeIn space-y-4">
                            {/* Existing Risk UI */}
                            <div className="grid grid-cols-2 gap-4">
                                <InputField label="Initial Risk % (Stop-Loss)" value={form.risk} onChange={(v: number) => setForm({ ...form, risk: v })} step={0.1} />
                                <InputField label="Trailing SL Step %" value={form.tsl} onChange={(v: number) => setForm({ ...form, tsl: v })} step={0.1} />
                            </div>

                            <div className="bg-white/5 border border-white/10 rounded-xl p-4 mt-2 hover:border-brand-primary/30 transition-colors">
                                <div className="flex items-center justify-between mb-4 cursor-pointer" onClick={(e) => { e.stopPropagation(); handleFormChange('enablePartialTp', !form.enablePartialTp); }}>
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-6 rounded-full p-1 transition-colors duration-200 ease-in-out flex items-center ${form.enablePartialTp ? 'bg-brand-primary' : 'bg-gray-700'}`}>
                                            <div className={`w-4 h-4 bg-white rounded-full shadow-md transform transition-transform duration-200 ease-in-out ${form.enablePartialTp ? 'translate-x-6' : 'translate-x-0'}`}></div>
                                        </div>
                                        <div>
                                            <span className="text-xs font-black text-white uppercase tracking-wider block">Scale-Out & Break-Even</span>
                                            <span className="text-[10px] text-gray-400">Lock profit early and remove risk</span>
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

                            {/* --- NEW: Micro-Scalp Auto-Sell Logic --- */}
                            <div className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-cyan-500/30 transition-colors shadow-[0_4px_20px_rgba(0,0,0,0.2)]">
                                <div className="flex items-center justify-between mb-4 cursor-pointer" onClick={(e) => { e.stopPropagation(); handleFormChange('enableMicroScalp', !form.enableMicroScalp); }}>
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-6 rounded-full p-1 transition-colors duration-200 ease-in-out flex items-center ${form.enableMicroScalp ? 'bg-cyan-500' : 'bg-gray-700'}`}>
                                            <div className={`w-4 h-4 bg-white rounded-full shadow-md transform transition-transform duration-200 ${form.enableMicroScalp ? 'translate-x-6' : 'translate-x-0'}`}></div>
                                        </div>
                                        <div>
                                            <span className="text-xs font-black text-white uppercase tracking-wider flex items-center gap-1.5">
                                                Micro-Scalp / Quick Bounce
                                                <span className="text-[8px] bg-cyan-500 text-black px-1.5 py-0.5 rounded-sm font-black animate-pulse">HFT</span>
                                            </span>
                                            <span className="text-[10px] text-gray-400">Instantly limit sell after entry for fast profit</span>
                                        </div>
                                    </div>
                                    <span className={`text-[10px] font-black px-2 py-1 rounded-md ${form.enableMicroScalp ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 'bg-white/5 text-gray-500'}`}>{form.enableMicroScalp ? 'ACTIVE' : 'INACTIVE'}</span>
                                </div>

                                {form.enableMicroScalp && (
                                    <div className="flex gap-4 items-center animate-fadeIn p-3 bg-black/20 rounded-xl border border-white/5">
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-gray-500 uppercase mb-1 block">Target Profit (Ticks)</label>
                                            <input type="number" step="1" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white outline-none focus:border-cyan-500/50 text-center font-mono text-lg" value={form.microScalpProfitTicks} onChange={(e) => handleFormChange('microScalpProfitTicks', parseInt(e.target.value))} />
                                        </div>
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-gray-500 uppercase mb-1 block">Min. Confluence Wall ($)</label>
                                            <input type="number" step="1000" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white outline-none focus:border-cyan-500/50 text-center font-mono text-lg" value={form.microScalpMinWall} onChange={(e) => handleFormChange('microScalpMinWall', parseInt(e.target.value))} />
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Existing Advanced Settings (VPVR, ATR, Spoof Time) */}
                            <div>
                                <InputField label="Spoof Detect Time (Seconds)" value={form.spoofTime} onChange={(v: number) => setForm({ ...form, spoofTime: v })} step={0.5} />
                            </div>

                            <div className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-yellow-500/30 transition-colors">
                                <div className="flex items-center justify-between cursor-pointer" onClick={() => handleFormChange('vpvrEnabled', !form.vpvrEnabled)}>
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-6 rounded-full p-1 transition-colors duration-200 flex items-center ${form.vpvrEnabled ? 'bg-yellow-500' : 'bg-gray-700'}`}>
                                            <div className={`w-4 h-4 bg-white rounded-full transform transition-transform duration-200 ${form.vpvrEnabled ? 'translate-x-6' : 'translate-x-0'}`}></div>
                                        </div>
                                        <span className="text-xs font-black text-white uppercase">VPVR Confirmation</span>
                                    </div>
                                </div>
                                {form.vpvrEnabled && (
                                    <div className="mt-4"><InputField label="HVN Tolerance (%)" value={form.vpvrTolerance} onChange={(v: number) => setForm({ ...form, vpvrTolerance: v })} step={0.1} /></div>
                                )}
                            </div>

                            <div className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-green-500/30 transition-colors">
                                <div className="flex items-center justify-between cursor-pointer" onClick={() => handleFormChange('atrEnabled', !form.atrEnabled)}>
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-6 rounded-full p-1 transition-colors duration-200 flex items-center ${form.atrEnabled ? 'bg-green-500' : 'bg-gray-700'}`}>
                                            <div className={`w-4 h-4 bg-white rounded-full transform transition-transform duration-200 ${form.atrEnabled ? 'translate-x-6' : 'translate-x-0'}`}></div>
                                        </div>
                                        <span className="text-xs font-black text-white uppercase">Dynamic ATR Stop-Loss</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* --- STICKY FOOTER ACTION BUTTONS --- */}
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
                            className={`flex-1 h-12 rounded-xl font-black text-white text-sm transition-all shadow-[0_0_15px_rgba(245,158,11,0.2)] ${isLoading ? 'bg-gray-600 cursor-not-allowed opacity-70' : existingBot ? 'bg-gradient-to-r from-blue-500 to-indigo-600 hover:shadow-[0_0_25px_rgba(99,102,241,0.5)]' : 'bg-gradient-to-r from-yellow-400 to-orange-600 hover:scale-[1.02] hover:shadow-[0_0_25px_rgba(245,158,11,0.3)]'}`}
                        >
                            {isLoading ? 'PROCESSING...' : existingBot ? '⚙️ UPDATE CONFIGURATION' : '🚀 DEPLOY SNIPER'}
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
// trigger IDE react-jsx refresh
