import React, { useEffect, useState } from 'react';
import { fetchApiKeys } from '../../../services/settings';

export const WallHunterModal: React.FC<{ isOpen: boolean; onClose: () => void; symbol: string }> = ({ isOpen, onClose, symbol }) => {
    const [savedKeys, setSavedKeys] = useState<any[]>([]);
    const [form, setForm] = useState({
        symbol: symbol,
        exchange: 'binance',
        isPaper: true,
        apiKeyId: '',
        vol: 500000,
        spread: 0.0002,
        risk: 0.5,
        tsl: 0.2
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

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
            <div className="w-[450px] bg-[#0B1120] border-2 border-yellow-500/30 rounded-[2rem] p-8 shadow-[0_0_50px_rgba(59,130,246,0.2)]">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-black italic text-white tracking-tighter">SNIPER DEPLOYMENT</h2>
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
                            <option value="binance">Binance</option>
                            <option value="bybit">Bybit</option>
                            <option value="okx">OKX</option>
                            <option value="kucoin">KuCoin</option>
                            <option value="gateio">Gate.io</option>
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
                            <option value="">-- Choose Saved Key --</option>
                            {savedKeys.filter(k => k.exchange === form.exchange).map(k => (
                                <option key={k.id} value={k.id}>{k.name}</option>
                            ))}
                        </select>
                    </div>
                )}

                <div className="space-y-4">
                    <InputField label="Volume Wall Threshold" value={form.vol} onChange={(v: number) => setForm({ ...form, vol: v })} />
                    <InputField label="Target Spread" value={form.spread} step={0.0001} onChange={(v: number) => setForm({ ...form, spread: v })} />
                    <div className="grid grid-cols-2 gap-4">
                        <InputField label="Initial Risk %" value={form.risk} onChange={(v: number) => setForm({ ...form, risk: v })} />
                        <InputField label="Trailing SL %" value={form.tsl} onChange={(v: number) => setForm({ ...form, tsl: v })} />
                    </div>
                </div>

                <button className="w-full bg-gradient-to-r from-yellow-400 to-orange-600 h-14 rounded-2xl mt-8 font-black text-white text-lg hover:scale-[1.02] active:scale-95 transition-all shadow-[0_0_20px_rgba(245,158,11,0.2)]">
                    ACTIVATE HUNTER
                </button>
                <button onClick={onClose} className="w-full text-gray-500 mt-4 text-sm font-bold hover:text-white transition-colors">ABORT MISSION</button>
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
