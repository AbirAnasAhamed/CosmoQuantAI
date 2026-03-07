import React, { useState } from 'react';

export const WallHunterModal: React.FC<{ isOpen: boolean; onClose: () => void; symbol: string }> = ({ isOpen, onClose, symbol }) => {
    const [config, setConfig] = useState({
        vol: 500000, spread: 0.0002, risk: 0.5, tsl: 0.2, exchange: 'binance', isPaper: true
    });

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="w-full max-w-md bg-[#0B1120] border border-brand-primary/40 rounded-3xl p-8 shadow-[0_0_50px_rgba(59,130,246,0.2)]">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-black italic text-white tracking-tighter">WALLHUNTER L2</h2>
                    <span className="bg-brand-primary/20 text-brand-primary px-3 py-1 rounded-full text-[10px] font-bold">{symbol}</span>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className={`p-3 rounded-xl border cursor-pointer transition-all ${config.isPaper ? 'bg-green-500/10 border-green-500' : 'bg-white/5 border-white/10'}`} onClick={() => setConfig({ ...config, isPaper: true })}>
                        <p className="text-[10px] font-bold text-green-500 uppercase">Simulated</p>
                        <p className="text-sm font-bold text-white">Paper Trading</p>
                    </div>
                    <div className={`p-3 rounded-xl border cursor-pointer transition-all ${!config.isPaper ? 'bg-red-500/10 border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.3)]' : 'bg-white/5 border-white/10'}`} onClick={() => setConfig({ ...config, isPaper: false })}>
                        <p className="text-[10px] font-bold text-red-500 uppercase">Live Market</p>
                        <p className="text-sm font-bold text-white">Real Capital</p>
                    </div>
                </div>

                <div className="space-y-4">
                    <InputField label="Volume Wall Threshold" value={config.vol} onChange={(v: number) => setConfig({ ...config, vol: v })} />
                    <InputField label="Target Spread" value={config.spread} step={0.0001} onChange={(v: number) => setConfig({ ...config, spread: v })} />
                    <div className="grid grid-cols-2 gap-4">
                        <InputField label="Initial Risk %" value={config.risk} onChange={(v: number) => setConfig({ ...config, risk: v })} />
                        <InputField label="Trailing SL %" value={config.tsl} onChange={(v: number) => setConfig({ ...config, tsl: v })} />
                    </div>
                </div>

                <button className="w-full bg-gradient-to-r from-brand-primary to-purple-600 h-14 rounded-2xl mt-8 font-black text-white text-lg hover:scale-[1.02] active:scale-95 transition-all">
                    DEPLOY SNIPER BOT
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
