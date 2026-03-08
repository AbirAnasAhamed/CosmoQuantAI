import React, { useEffect, useState } from 'react';
import { fetchApiKeys } from '../../../services/settings';
import { botService } from '../../../services/botService';

export const WallHunterModal: React.FC<{ isOpen: boolean; onClose: () => void; symbol: string; bids?: any[]; asks?: any[]; onDeploySuccess?: (botId: number) => void }> = ({ isOpen, onClose, symbol, bids = [], asks = [], onDeploySuccess }) => {
    const [savedKeys, setSavedKeys] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');
    const [form, setForm] = useState({
        symbol: symbol,
        exchange: 'binance',
        isPaper: true,
        apiKeyId: '',
        vol: 500000,
        spread: 0.0002,
        risk: 0.5,
        tsl: 0.2,
        amount: 100
    });

    useEffect(() => {
        setForm(prev => ({ ...prev, symbol }));
    }, [symbol]);

    useEffect(() => {
        if (isOpen) {
            try {
                if (typeof fetchApiKeys === 'function') {
                    fetchApiKeys().then((keys: any) => setSavedKeys(keys || [])).catch(() => { });
                }
            } catch (e) { }
        }
    }, [isOpen]);

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
            // Target slightly larger than current spread for profit (e.g., current spread + 0.1%)
            optimalSpread = currentSpread + (bestAsk * 0.001);
            // Clamp spread to reasonable values based on input step
            optimalSpread = parseFloat(Math.max(0.0001, Math.min(0.0100, optimalSpread)).toFixed(4));

            // 2. Calculate Optimal Volume Threshold
            // Look at top 10 levels on both sides to find average "normal" volume
            const topBids = bids.slice(0, 10);
            const topAsks = asks.slice(0, 10);
            const allSizes = [...topBids.map(b => b.size), ...topAsks.map(a => a.size)];

            if (allSizes.length > 0) {
                const avgSize = allSizes.reduce((sum, size) => sum + size, 0) / allSizes.length;
                // A "Wall" is typically 5x to 10x the average size
                optimalVol = Math.round((avgSize * 5) / 1000) * 1000; // Round to nearest 1000
                // Clamp volume
                optimalVol = Math.max(10, Math.min(1000000, optimalVol));

                // 3. Calculate Optimal Trade Amount (10% of average order value in quote currency)
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
                    risk_pct: form.risk
                }
            };

            const createdBot = await botService.createBot(payload);
            await botService.controlBot(createdBot.id, 'start');

            // Wait a moment for success feel, then close
            setTimeout(() => {
                setIsLoading(false);
                if (onDeploySuccess) onDeploySuccess(Number(createdBot.id));
                else onClose();
            }, 1000);
        } catch (err: any) {
            console.error(err);
            setErrorMsg(err.response?.data?.detail || err.message || "Failed to deploy bot.");
            setIsLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
            <div className="w-[450px] bg-[#0B1120] border-2 border-yellow-500/30 rounded-[2rem] p-8 shadow-[0_0_50px_rgba(59,130,246,0.2)]">
                <div className="flex justify-between items-center mb-6">
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

                {/* Asset & Exchange Selection */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="space-y-1">
                        <label className="text-[10px] text-gray-500 font-bold uppercase">Asset</label>
                        <input className="w-full bg-white/5 p-3 rounded-xl text-yellow-500 font-mono outline-none border border-transparent focus:border-yellow-500/50" value={form.symbol} readOnly />
                    </div>
                    <div className="space-y-1">
                        <label className="text-[10px] text-gray-500 font-bold uppercase">Exchange</label>
                        <select className="w-full bg-white/5 p-3 rounded-xl text-white outline-none" value={form.exchange} onChange={(e) => setForm({ ...form, exchange: e.target.value })}>
                            <option className="bg-[#0B1120] text-white" value="binance">Binance</option>
                            <option className="bg-[#0B1120] text-white" value="bybit">Bybit</option>
                            <option className="bg-[#0B1120] text-white" value="okx">OKX</option>
                            <option className="bg-[#0B1120] text-white" value="kucoin">KuCoin</option>
                            <option className="bg-[#0B1120] text-white" value="gateio">Gate.io</option>
                            <option className="bg-[#0B1120] text-white" value="mexc">MEXC</option>
                        </select>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className={`p-3 rounded-xl border cursor-pointer transition-all ${form.isPaper ? 'bg-green-500/10 border-green-500' : 'bg-white/5 border-white/10'}`} onClick={() => setForm({ ...form, isPaper: true })}>
                        <p className="text-[10px] font-bold text-green-500 uppercase">Simulated</p>
                        <p className="text-sm font-bold text-white">Paper Trading</p>
                    </div>
                    <div className={`p-3 rounded-xl border cursor-pointer transition-all ${!form.isPaper ? 'bg-red-500/10 border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.3)]' : 'bg-white/5 border-white/10'}`} onClick={() => setForm({ ...form, isPaper: false })}>
                        <p className="text-[10px] font-bold text-red-500 uppercase">Live Market</p>
                        <p className="text-sm font-bold text-white">Real Capital</p>
                    </div>
                </div>

                {/* API Key Selection */}
                {!form.isPaper && (
                    <div className="mb-4">
                        <label className="text-[10px] text-gray-500 font-bold uppercase">Select API Config</label>
                        <select className="w-full bg-yellow-500/10 border border-yellow-500/20 p-3 rounded-xl text-white outline-none" value={form.apiKeyId} onChange={(e) => setForm({ ...form, apiKeyId: e.target.value })}>
                            <option className="bg-[#0B1120] text-white" value="">-- Choose Saved Key --</option>
                            {savedKeys.filter(k => k.exchange === form.exchange).map(k => (
                                <option className="bg-[#0B1120] text-white" key={k.id} value={k.id}>{k.name}</option>
                            ))}
                        </select>
                    </div>
                )}

                <div className="space-y-4">
                    {/* Volume Slider Input */}
                    <div>
                        <div className="flex justify-between items-end mb-1">
                            <label className="text-[10px] font-bold text-gray-500 uppercase">Volume Wall Threshold ({form.symbol ? form.symbol.split('/')[0] : 'Asset'})</label>
                            <span className="text-xs font-mono font-bold text-brand-primary">{form.vol.toLocaleString()}</span>
                        </div>
                        <div className="flex gap-3 items-center">
                            <input
                                type="range"
                                min="0"
                                max="1000000"
                                step="1000"
                                className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-primary"
                                value={form.vol}
                                onChange={(e) => setForm({ ...form, vol: parseFloat(e.target.value) })}
                            />
                            <input
                                type="number"
                                className="w-24 bg-white/5 border border-white/10 rounded-xl p-2 text-white text-sm outline-none focus:border-brand-primary font-mono text-center"
                                value={form.vol}
                                onChange={(e) => setForm({ ...form, vol: parseFloat(e.target.value) })}
                            />
                        </div>
                    </div>

                    {/* Target Spread Slider Input */}
                    <div>
                        <div className="flex justify-between items-end mb-1">
                            <label className="text-[10px] font-bold text-gray-500 uppercase">Target Spread Profit</label>
                            <span className="text-xs font-mono font-bold text-brand-primary">{form.spread.toFixed(4)}</span>
                        </div>
                        <div className="flex gap-3 items-center">
                            <input
                                type="range"
                                min="0"
                                max="0.0100"
                                step="0.0001"
                                className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-primary"
                                value={form.spread}
                                onChange={(e) => setForm({ ...form, spread: parseFloat(e.target.value) })}
                            />
                            <input
                                type="number"
                                step="0.0001"
                                className="w-24 bg-white/5 border border-white/10 rounded-xl p-2 text-white text-sm outline-none focus:border-brand-primary font-mono text-center"
                                value={form.spread}
                                onChange={(e) => setForm({ ...form, spread: parseFloat(e.target.value) })}
                            />
                        </div>
                    </div>
                    <div className="mb-4">
                        <InputField label={`Trading Amount (${form.symbol ? form.symbol.split('/')[1] || 'Quote Asset' : 'Quote Asset'})`} value={form.amount} onChange={(v: number) => setForm({ ...form, amount: v })} step={10} />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <InputField label="Initial Risk %" value={form.risk} onChange={(v: number) => setForm({ ...form, risk: v })} />
                        <InputField label="Trailing SL %" value={form.tsl} onChange={(v: number) => setForm({ ...form, tsl: v })} />
                    </div>
                </div>

                {errorMsg && <p className="text-red-500 text-xs font-bold mt-4 animate-pulse text-center bg-red-500/10 py-2 rounded-lg">{errorMsg}</p>}

                <button
                    onClick={handleDeploy}
                    disabled={isLoading}
                    className={`w-full h-14 rounded-2xl mt-8 font-black text-white text-lg transition-all shadow-[0_0_20px_rgba(245,158,11,0.2)] ${isLoading ? 'bg-gray-600 cursor-not-allowed opacity-70' : 'bg-gradient-to-r from-yellow-400 to-orange-600 hover:scale-[1.02] active:scale-95'}`}
                >
                    {isLoading ? 'DEPLOYING...' : 'ACTIVATE HUNTER'}
                </button>
                <button onClick={onClose} disabled={isLoading} className="w-full text-gray-500 mt-4 text-sm font-bold hover:text-white transition-colors">ABORT MISSION</button>
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
