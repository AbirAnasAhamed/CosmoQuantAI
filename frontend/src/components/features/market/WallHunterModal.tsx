import React, { useEffect, useState } from 'react';
import { fetchApiKeys } from '../../../services/settings';
import { botService } from '../../../services/botService';

export const WallHunterModal: React.FC<{ isOpen: boolean; onClose: () => void; symbol: string; bids?: any[]; asks?: any[]; onDeploySuccess?: (botId: number) => void }> = ({ isOpen, onClose, symbol, bids = [], asks = [], onDeploySuccess }) => {
    const [savedKeys, setSavedKeys] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');
    const [activeTab, setActiveTab] = useState('basic'); // NEW: Tab state
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
        spoofTime: 3.0, // NEW: Spoofing Detection Time Default 3 Seconds
        enablePartialTp: true, // NEW: Toggle state
        partialTp: 50.0, // NEW: Default sell 50% at TP1
        vpvrEnabled: false,
        vpvrTolerance: 0.2,
        atrEnabled: false,
        atrPeriod: 14,
        atrMultiplier: 2.0
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

                // Fetch active bot for this symbol
                botService.getAllBots().then((bots: any) => {
                    console.log("🔥 [WallHunterModal] Fetched bots:", bots);
                    const activeWallHunter = bots.find((b: any) => b.market === symbol && b.strategy === 'wall_hunter' && b.status === 'active');
                    console.log("🔥 [WallHunterModal] Active match for", symbol, ":", activeWallHunter);
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
                            atrMultiplier: c.atr_multiplier !== undefined ? c.atr_multiplier : 2.0
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
            // 1. Calculate Optimal Spread
            const bestBid = bids[0].price;
            const bestAsk = asks[0].price;
            const currentSpread = bestAsk - bestBid;
            optimalSpread = currentSpread + (bestAsk * 0.001);
            optimalSpread = parseFloat(Math.max(0.0001, Math.min(0.0100, optimalSpread)).toFixed(4));

            // 2. Calculate Optimal Volume Threshold
            const allSizes = [...bids.map(b => b.size), ...asks.map(a => a.size)];

            if (allSizes.length > 0) {
                const maxSize = Math.max(...allSizes);
                const avgSize = allSizes.reduce((sum, size) => sum + size, 0) / allSizes.length;

                // We define a wall as 3x the average size of the orderbook
                let calculatedVol = avgSize * 3;

                // Ensure the threshold is achievable: it shouldn't be higher than 80% of the CURRENT max wall
                if (calculatedVol > maxSize * 0.9) {
                    calculatedVol = maxSize * 0.8;
                }

                if (calculatedVol > 10000) {
                    optimalVol = Math.round(calculatedVol / 1000) * 1000;
                } else {
                    optimalVol = Math.round(calculatedVol / 100) * 100;
                }
                optimalVol = Math.max(10, optimalVol);

                // 3. Calculate Optimal Trade Amount
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

        setErrorMsg('');
        setIsLoading(true);

        try {
            const payload = {
                name: `L2 Hunter: ${form.symbol}`,
                description: "Orderbook Volume Scalping Hunter",
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
                    min_wall_lifetime: form.spoofTime, // NEW: Sending value to backend
                    partial_tp_pct: form.enablePartialTp ? form.partialTp : 0.0, // NEW: Sending Scale-Out ratio to backend. Send 0.0 to disable.
                    vpvr_enabled: form.vpvrEnabled,
                    vpvr_tolerance: form.vpvrTolerance,
                    atr_sl_enabled: form.atrEnabled,
                    atr_period: form.atrPeriod,
                    atr_multiplier: form.atrMultiplier
                }
            };

            if (existingBot) {
                // Update existing bot
                await botService.updateBot(existingBot.id, payload);
                setTimeout(() => {
                    setIsLoading(false);
                    setErrorMsg("⚡ Live Config Updated Successfully!");
                    setTimeout(() => setErrorMsg(''), 3000);
                }, 1000);
            } else {
                // Create new bot
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

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
            <div className="w-[600px] bg-[#0B1120] border-2 border-yellow-500/30 rounded-[2rem] p-6 shadow-[0_0_50px_rgba(59,130,246,0.2)] max-h-[90vh] flex flex-col">
                <div className="flex justify-between items-center mb-4 flex-shrink-0">
                    <h2 className="text-2xl font-black italic text-white tracking-tighter">SNIPER DEPLOYMENT</h2>
                    <button
                        onClick={handleAutoDetect}
                        className="flex items-center gap-1 bg-brand-primary/20 hover:bg-brand-primary/30 border border-brand-primary/50 text-brand-primary px-3 py-1.5 rounded-full text-xs font-bold transition-colors shadow-[0_0_10px_rgba(59,130,246,0.2)]"
                        title="Auto-detect optimal Volume Wall Threshold and Target Spread from real-time Order Book"
                    >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                        AUTO DETECT
                    </button>
                </div>

                {/* --- TABS NAVIGATION --- */}
                <div className="flex gap-2 border-b border-white/10 mb-4 pb-2 overflow-x-auto flex-shrink-0 hide-scrollbar">
                    <button onClick={() => setActiveTab('basic')} className={`px-4 py-2 text-xs font-black tracking-wider uppercase rounded-xl transition-all ${activeTab === 'basic' ? 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/30 shadow-[0_0_15px_rgba(234,179,8,0.2)]' : 'text-gray-500 hover:bg-white/5'}`}>Basic & Execution</button>
                    <button onClick={() => setActiveTab('risk')} className={`px-4 py-2 text-xs font-black tracking-wider uppercase rounded-xl transition-all ${activeTab === 'risk' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.2)]' : 'text-gray-500 hover:bg-white/5'}`}>Risk Management</button>
                    <button onClick={() => setActiveTab('advanced')} className={`px-4 py-2 text-xs font-black tracking-wider uppercase rounded-xl transition-all ${activeTab === 'advanced' ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30 shadow-[0_0_15px_rgba(168,85,247,0.2)]' : 'text-gray-500 hover:bg-white/5'}`}>Advanced Settings</button>
                </div>

                {/* --- TABS CONTENT (Scrollable Area) --- */}
                <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-4">
                    {activeTab === 'basic' && (
                        <div className="animate-fadeIn space-y-4">
                            {/* Asset & Exchange Selection (Compact) */}
                            <div className="flex gap-4">
                                <div className="space-y-1 w-1/3">
                                    <label className="text-[10px] text-gray-500 font-bold uppercase">Asset</label>
                                    <input className="w-full bg-white/5 p-2 rounded-xl text-yellow-500 font-mono outline-none border border-transparent focus:border-yellow-500/50 text-sm" value={form.symbol} readOnly />
                                </div>
                                <div className="space-y-1 w-1/3">
                                    <label className="text-[10px] text-gray-500 font-bold uppercase">Exchange</label>
                                    <select className="w-full bg-white/5 p-2 rounded-xl text-white outline-none text-sm" value={form.exchange} onChange={(e) => setForm({ ...form, exchange: e.target.value })}>
                                        <option className="bg-[#0B1120] text-white" value="binance">Binance</option>
                                        <option className="bg-[#0B1120] text-white" value="bybit">Bybit</option>
                                        <option className="bg-[#0B1120] text-white" value="okx">OKX</option>
                                        <option className="bg-[#0B1120] text-white" value="kucoin">KuCoin</option>
                                        <option className="bg-[#0B1120] text-white" value="gateio">Gate.io</option>
                                        <option className="bg-[#0B1120] text-white" value="mexc">MEXC</option>
                                    </select>
                                </div>
                                <div className="w-1/3 space-y-1">
                                    <label className="text-[10px] text-gray-500 font-bold uppercase">Sell Order Type (TP)</label>
                                    <select
                                        className="w-full bg-white/5 border border-white/10 rounded-xl p-2 text-white outline-none focus:border-brand-primary text-sm"
                                        value={form.sellOrderType}
                                        onChange={(e) => handleFormChange('sellOrderType', e.target.value as 'market' | 'limit')}
                                    >
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

                            {/* API Key Selection Inline */}
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

                            {/* Volume Slider Input */}
                            <div>
                                <div className="flex justify-between items-end mb-1">
                                    <label className="text-[10px] font-bold text-gray-500 uppercase">Volume Wall Threshold ({form.symbol ? form.symbol.split('/')[0] : 'Asset'})</label>
                                    <span className="text-xs font-mono font-bold text-brand-primary">{form.vol.toLocaleString()}</span>
                                </div>
                                <div className="flex gap-3 items-center">
                                    <input type="range" min="0" max="10000000" step="1000" className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-primary" value={form.vol} onChange={(e) => setForm({ ...form, vol: parseFloat(e.target.value) })} />
                                    <input type="number" className="w-24 bg-white/5 border border-white/10 rounded-xl p-2 text-white text-sm outline-none focus:border-brand-primary font-mono text-center" value={form.vol} onChange={(e) => setForm({ ...form, vol: parseFloat(e.target.value) })} />
                                </div>
                            </div>

                            {/* Target Spread Slider Input */}
                            <div>
                                <div className="flex justify-between items-end mb-1">
                                    <label className="text-[10px] font-bold text-gray-500 uppercase">Target Spread Profit</label>
                                    <span className="text-xs font-mono font-bold text-brand-primary">{form.spread.toFixed(4)}</span>
                                </div>
                                <div className="flex gap-3 items-center">
                                    <input type="range" min="0" max="0.0100" step="0.0001" className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-primary" value={form.spread} onChange={(e) => setForm({ ...form, spread: parseFloat(e.target.value) })} />
                                    <input type="number" step="0.0001" className="w-24 bg-white/5 border border-white/10 rounded-xl p-2 text-white text-sm outline-none focus:border-brand-primary font-mono text-center" value={form.spread} onChange={(e) => setForm({ ...form, spread: parseFloat(e.target.value) })} />
                                </div>
                            </div>

                            <div className="w-full">
                                <InputField label={`Trading Amount (${form.symbol ? form.symbol.split('/')[1] || 'Quote Asset' : 'Quote Asset'})`} value={form.amount} onChange={(v: number) => setForm({ ...form, amount: v })} step={10} />
                            </div>
                        </div>
                    )}

                    {activeTab === 'risk' && (
                        <div className="animate-fadeIn space-y-4">
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
                                    <span className={`text-[10px] font-black px-2 py-1 rounded-md ${form.enablePartialTp ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-white/5 text-gray-500'}`}>{form.enablePartialTp ? 'ACTIVE' : 'INACTIVE'}</span>
                                </div>

                                {form.enablePartialTp && (
                                    <div className="flex gap-4 items-center animate-fadeIn p-3 bg-black/20 rounded-xl border border-white/5">
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-gray-500 uppercase mb-1 block">Sell at Target TP1 (%)</label>
                                            <input type="number" step="10" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white outline-none focus:border-brand-primary transition-colors text-center font-mono text-lg" value={form.partialTp} onChange={(e) => handleFormChange('partialTp', parseFloat(e.target.value))} />
                                        </div>
                                        <div className="flex-1 text-center bg-green-500/10 border border-green-500/30 rounded-xl p-3 flex flex-col justify-center h-[72px]">
                                            <span className="text-[10px] text-green-500 font-bold uppercase tracking-wider mb-1">Auto Defense</span>
                                            <span className="text-sm text-white font-black whitespace-nowrap">MOVE TO ENTRY</span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {activeTab === 'advanced' && (
                        <div className="animate-fadeIn space-y-4">
                            <div>
                                <InputField label="Spoof Detect Time (Seconds)" value={form.spoofTime} onChange={(v: number) => setForm({ ...form, spoofTime: v })} step={0.5} />
                                <p className="text-[10px] text-gray-500 mt-1 ml-1 font-medium">How long a volume wall must exist in the orderbook before buying. (0 = Instant execution)</p>
                            </div>

                            <div className="bg-white/5 border border-white/10 rounded-xl p-4 mt-2 hover:border-yellow-500/30 transition-colors">
                                <div className="flex items-center justify-between mb-4 cursor-pointer" onClick={(e) => { e.stopPropagation(); handleFormChange('vpvrEnabled', !form.vpvrEnabled); }}>
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-6 rounded-full p-1 transition-colors duration-200 ease-in-out flex items-center ${form.vpvrEnabled ? 'bg-yellow-500' : 'bg-gray-700'}`}>
                                            <div className={`w-4 h-4 bg-white rounded-full shadow-md transform transition-transform duration-200 ease-in-out ${form.vpvrEnabled ? 'translate-x-6' : 'translate-x-0'}`}></div>
                                        </div>
                                        <div>
                                            <span className="text-xs font-black text-white uppercase tracking-wider flex items-center gap-1.5">
                                                VPVR Confirmation
                                                <span className="text-[8px] bg-yellow-500 text-black px-1.5 py-0.5 rounded-sm font-black animate-pulse">PRO</span>
                                            </span>
                                            <span className="text-[10px] text-gray-400">Match sniper walls with High Volume Nodes</span>
                                        </div>
                                    </div>
                                    <span className={`text-[10px] font-black px-2 py-1 rounded-md ${form.vpvrEnabled ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' : 'bg-white/5 text-gray-500'}`}>{form.vpvrEnabled ? 'ACTIVE' : 'INACTIVE'}</span>
                                </div>

                                {form.vpvrEnabled && (
                                    <div className="flex gap-4 items-center animate-fadeIn p-3 bg-black/20 rounded-xl border border-white/5">
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-gray-500 uppercase mb-1 block">HVN Tolerance Range (%)</label>
                                            <input type="number" step="0.1" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white outline-none focus:border-yellow-500/50 transition-colors text-center font-mono text-lg" value={form.vpvrTolerance} onChange={(e) => handleFormChange('vpvrTolerance', parseFloat(e.target.value))} />
                                        </div>
                                        <div className="flex-1 text-center bg-blue-500/10 border border-blue-500/30 rounded-xl p-3 flex flex-col justify-center h-[72px]">
                                            <span className="text-[10px] text-blue-400 font-bold uppercase tracking-wider mb-1">Background Worker</span>
                                            <span className="text-xs text-white font-black">TOP 3 NODES / 5M</span>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* --- NEW: Dynamic ATR Stop-Loss --- */}
                            <div className="bg-white/5 border border-white/10 rounded-xl p-4 mt-2 hover:border-green-500/30 transition-colors">
                                <div className="flex items-center justify-between mb-4 cursor-pointer" onClick={(e) => { e.stopPropagation(); handleFormChange('atrEnabled', !form.atrEnabled); }}>
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-6 rounded-full p-1 transition-colors duration-200 ease-in-out flex items-center ${form.atrEnabled ? 'bg-green-500' : 'bg-gray-700'}`}>
                                            <div className={`w-4 h-4 bg-white rounded-full shadow-md transform transition-transform duration-200 ease-in-out ${form.atrEnabled ? 'translate-x-6' : 'translate-x-0'}`}></div>
                                        </div>
                                        <div>
                                            <span className="text-xs font-black text-white uppercase tracking-wider flex items-center gap-1.5">
                                                Dynamic ATR Stop-Loss
                                                <span className="text-[8px] bg-green-500 text-black px-1.5 py-0.5 rounded-sm font-black animate-pulse">PRO</span>
                                            </span>
                                            <span className="text-[10px] text-gray-400">Adaptive SL based on market volatility</span>
                                        </div>
                                    </div>
                                    <span className={`text-[10px] font-black px-2 py-1 rounded-md ${form.atrEnabled ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-white/5 text-gray-500'}`}>{form.atrEnabled ? 'ACTIVE' : 'INACTIVE'}</span>
                                </div>

                                {form.atrEnabled && (
                                    <div className="flex gap-4 items-center animate-fadeIn p-3 bg-black/20 rounded-xl border border-white/5">
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-gray-500 uppercase mb-1 block">ATR Period (1m)</label>
                                            <input type="number" step="1" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white outline-none focus:border-green-500/50 transition-colors text-center font-mono text-lg" value={form.atrPeriod} onChange={(e) => handleFormChange('atrPeriod', parseInt(e.target.value))} />
                                        </div>
                                        <div className="flex-1">
                                            <label className="text-[10px] font-bold text-gray-500 uppercase mb-1 block">ATR Multiplier</label>
                                            <input type="number" step="0.1" className="w-full bg-black/40 border border-white/10 rounded-xl p-2.5 text-white outline-none focus:border-green-500/50 transition-colors text-center font-mono text-lg" value={form.atrMultiplier} onChange={(e) => handleFormChange('atrMultiplier', parseFloat(e.target.value))} />
                                        </div>
                                    </div>
                                )}
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
                            className={`flex-1 h-12 rounded-xl font-black text-white text-sm transition-all shadow-[0_0_15px_rgba(245,158,11,0.2)] ${isLoading ? 'bg-gray-600 cursor-not-allowed opacity-70' : existingBot ? 'bg-gradient-to-r from-blue-500 to-indigo-600 hover:shadow-[0_0_25px_rgba(99,102,241,0.5)] shadow-[0_0_15px_rgba(99,102,241,0.3)] hover:scale-[1.02] active:scale-95' : 'bg-gradient-to-r from-yellow-400 to-orange-600 hover:scale-[1.02] active:scale-95 hover:shadow-[0_0_25px_rgba(245,158,11,0.3)]'}`}
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
