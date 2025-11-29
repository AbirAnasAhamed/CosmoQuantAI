import React, { useState } from 'react';
import { Settings, RefreshCw, Play, TrendingUp, Activity, TrendingDown, AlertTriangle, Download } from 'lucide-react';
import { ResponsiveContainer, AreaChart, CartesianGrid, XAxis, YAxis, Tooltip, Area } from 'recharts';

interface BacktestTrade {
    id: number;
    time: string;
    type: 'BUY' | 'SELL';
    price: number;
    size: number;
    pnl: number;
    balance: number;
}

export const Backtest = () => {
    const [isRunning, setIsRunning] = useState(false);
    const [progress, setProgress] = useState(0);
    const [metrics, setMetrics] = useState<any>(null);
    const [trades, setTrades] = useState<BacktestTrade[]>([]);
    const [equityCurve, setEquityCurve] = useState<{ time: string, value: number }[]>([]);

    const runBacktest = async () => {
        setIsRunning(true);
        setProgress(0);
        setMetrics(null);
        setTrades([]);
        setEquityCurve([]);

        // Simulation Loop
        let balance = 10000;
        const curve = [{ time: 'Start', value: balance }];
        const generatedTrades: BacktestTrade[] = [];
        let wins = 0;
        let maxDD = 0;
        let peak = balance;

        for (let i = 0; i <= 100; i++) {
            await new Promise(r => setTimeout(r, 20)); // UI visualization delay
            setProgress(i);

            // Simulate Trade Logic
            if (Math.random() > 0.7) {
                const isWin = Math.random() > 0.45; // 55% Win Rate Strategy
                const pnl = isWin ? (Math.random() * 200 + 50) : (Math.random() * -150 - 50);

                balance += pnl;
                if (balance > peak) peak = balance;
                const dd = (peak - balance) / peak * 100;
                if (dd > maxDD) maxDD = dd;
                if (pnl > 0) wins++;

                const trade: BacktestTrade = {
                    id: i,
                    time: `Day ${Math.floor(i / 3)}`,
                    type: Math.random() > 0.5 ? 'BUY' : 'SELL',
                    price: 64000 + (Math.random() * 2000),
                    size: 0.5,
                    pnl: parseFloat(pnl.toFixed(2)),
                    balance: parseFloat(balance.toFixed(2))
                };
                generatedTrades.unshift(trade);
                curve.push({ time: `Trade ${generatedTrades.length}`, value: balance });
            }
        }

        setTrades(generatedTrades);
        setEquityCurve(curve);
        setMetrics({
            totalTrades: generatedTrades.length,
            winRate: parseFloat(((wins / generatedTrades.length) * 100).toFixed(1)),
            profitFactor: 1.54,
            maxDrawdown: parseFloat(maxDD.toFixed(2)),
            totalReturn: parseFloat(((balance - 10000) / 10000 * 100).toFixed(2)),
            sharpeRatio: 1.85,
            cagr: 42.5
        });

        setIsRunning(false);
    };

    return (
        <div className="h-full flex flex-col space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Config Panel */}
                <div className="bg-omni-panel border border-slate-700 rounded-xl p-6 h-fit">
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                        <Settings size={20} className="text-omni-accent" /> Strategy Config
                    </h3>
                    <div className="space-y-4">
                        <div>
                            <label className="text-xs text-slate-400 block mb-1">Initial Capital</label>
                            <input type="number" defaultValue={10000} className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white font-mono" />
                        </div>
                        <div>
                            <label className="text-xs text-slate-400 block mb-1">Timeframe</label>
                            <select className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white font-mono">
                                <option>1 Hour (H1)</option>
                                <option>4 Hour (H4)</option>
                                <option>Daily (D1)</option>
                            </select>
                        </div>
                        <div>
                            <label className="text-xs text-slate-400 block mb-1">Strategy Logic</label>
                            <select className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white font-mono">
                                <option>Mean Reversion (RSI)</option>
                                <option>Trend Following (MACD)</option>
                                <option>Breakout (Bollinger)</option>
                            </select>
                        </div>

                        <button
                            onClick={runBacktest}
                            disabled={isRunning}
                            className={`w-full py-3 rounded-lg font-bold flex items-center justify-center gap-2 mt-4 transition-all ${isRunning ? 'bg-slate-700 text-slate-400' : 'bg-omni-accent hover:bg-blue-400 text-omni-bg'
                                }`}
                        >
                            {isRunning ? <RefreshCw className="animate-spin" /> : <Play fill="currentColor" />}
                            {isRunning ? `Simulating ${progress}%` : 'Run Backtest'}
                        </button>
                    </div>
                </div>

                {/* Results Area */}
                <div className="lg:col-span-3 space-y-6">
                    {metrics ? (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-in fade-in slide-in-from-bottom-4">
                            <MetricCard label="Total Return" value={`${metrics.totalReturn}%`} positive={metrics.totalReturn > 0} icon={TrendingUp} />
                            <MetricCard label="Win Rate" value={`${metrics.winRate}%`} positive={metrics.winRate > 50} icon={Activity} />
                            <MetricCard label="Max Drawdown" value={`-${metrics.maxDrawdown}%`} positive={metrics.maxDrawdown < 15} icon={TrendingDown} />
                            <MetricCard label="Sharpe Ratio" value={metrics.sharpeRatio} positive={metrics.sharpeRatio > 1.5} icon={AlertTriangle} />
                        </div>
                    ) : (
                        <div className="h-24 bg-omni-panel border border-slate-700 rounded-xl flex items-center justify-center text-slate-500 border-dashed">
                            Awaiting Simulation Run...
                        </div>
                    )}

                    {/* Equity Curve */}
                    <div className="bg-omni-panel border border-slate-700 rounded-xl p-6 h-[350px]">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="font-semibold text-white">Equity Curve</h3>
                            {metrics && <button className="text-xs flex items-center gap-1 text-slate-400 hover:text-white"><Download size={12} /> Export CSV</button>}
                        </div>
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={equityCurve}>
                                <defs>
                                    <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                <XAxis dataKey="time" hide />
                                <YAxis domain={['auto', 'auto']} stroke="#64748b" tick={{ fontSize: 12 }} />
                                <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569' }} />
                                <Area type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} fill="url(#equityGrad)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Trade Log */}
                    <div className="bg-omni-panel border border-slate-700 rounded-xl overflow-hidden max-h-[300px] overflow-y-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-slate-800 text-slate-400 sticky top-0">
                                <tr>
                                    <th className="px-4 py-2">ID</th>
                                    <th className="px-4 py-2">Type</th>
                                    <th className="px-4 py-2 text-right">Price</th>
                                    <th className="px-4 py-2 text-right">PnL</th>
                                    <th className="px-4 py-2 text-right">Balance</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-700">
                                {trades.map(t => (
                                    <tr key={t.id} className="hover:bg-slate-700/50 font-mono">
                                        <td className="px-4 py-2 text-slate-500">#{t.id}</td>
                                        <td className={`px-4 py-2 font-bold ${t.type === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>{t.type}</td>
                                        <td className="px-4 py-2 text-right text-slate-300">${t.price.toFixed(2)}</td>
                                        <td className={`px-4 py-2 text-right font-bold ${t.pnl && t.pnl > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            {t.pnl && t.pnl > 0 ? '+' : ''}{t.pnl}
                                        </td>
                                        <td className="px-4 py-2 text-right text-white">${t.balance.toLocaleString()}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};

const MetricCard = ({ label, value, positive, icon: Icon }: any) => (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 flex items-center justify-between">
        <div>
            <div className="text-xs text-slate-400 mb-1">{label}</div>
            <div className={`text-xl font-bold font-mono ${positive ? 'text-omni-success' : 'text-omni-danger'}`}>{value}</div>
        </div>
        <div className={`p-2 rounded-lg ${positive ? 'bg-omni-success/10 text-omni-success' : 'bg-omni-danger/10 text-omni-danger'}`}>
            <Icon size={20} />
        </div>
    </div>
);
