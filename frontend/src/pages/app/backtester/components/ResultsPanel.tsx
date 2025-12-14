import React, { useState, useEffect } from 'react';
import { Activity, Layers } from 'lucide-react';
import BacktestChart from '@/components/features/backtest/BacktestChart';
import UnderwaterChart from '@/components/features/backtest/UnderwaterChart';
import EquityChart from '@/components/features/backtest/EquityChart';
import MonteCarloCard from './MonteCarloCard';
import { BacktestResult } from '@/types';

// --- Helper Components ---
const MetricCard: React.FC<{ label: string; value: string | number; decimals?: number; prefix?: string; suffix?: string; positive?: boolean }> = ({ label, value, decimals = 2, prefix = '', suffix = '', positive }) => {
    const numericValue = typeof value === 'number' ? value : parseFloat(value as string);
    const isPositive = positive !== undefined ? positive : numericValue >= 0;
    const colorClass = positive !== undefined ? (isPositive ? 'text-green-500' : 'text-red-500') : 'text-slate-900 dark:text-white';

    return (
        <div className="bg-white dark:bg-[#131722] p-4 rounded-lg border border-gray-200 dark:border-[#2A2E39] shadow-sm">
            <p className="text-xs text-gray-500 uppercase font-semibold mb-1">{label}</p>
            <p className={`text-xl font-bold ${colorClass}`}>
                {typeof value === 'number' ? <AnimatedNumber value={value} decimals={decimals} prefix={prefix} suffix={suffix} /> : value}
            </p>
        </div>
    );
};

const AnimatedNumber: React.FC<{ value: number; decimals?: number; prefix?: string; suffix?: string }> = ({ value, decimals = 2, prefix = '', suffix = '' }) => {
    const [displayValue, setDisplayValue] = useState(0);

    useEffect(() => {
        let start = 0;
        const end = value;
        if (start === end) return;
        const duration = 1000;
        const startTime = performance.now();
        const animate = (currentTime: number) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = start + (end - start) * easeOut;
            setDisplayValue(current);
            if (progress < 1) requestAnimationFrame(animate);
            else setDisplayValue(end);
        };
        requestAnimationFrame(animate);
    }, [value]);

    return (
        <span className="animate-count-up">
            {prefix}{displayValue.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}{suffix}
        </span>
    );
};

// Helper to calculate simple drawdown
const calculateDrawdownFromCandles = (candles: any[]) => {
    if (!candles || !Array.isArray(candles) || candles.length === 0) return [];
    let peak = -Infinity;
    return candles.map(c => {
        if (c.close > peak) peak = c.close;
        const drawdown = ((c.close - peak) / peak) * 100;
        return { time: c.time, value: drawdown };
    });
};

interface ResultsPanelProps {
    singleResult: BacktestResult;
    resultsTab: string;
    setResultsTab: (tab: string) => void;
}

export const ResultsPanel: React.FC<ResultsPanelProps> = ({ singleResult, resultsTab, setResultsTab }) => {
    if (!singleResult) return null;

    return (
        <div className="animate-fade-in space-y-6 mt-6">
            {/* A. Chart Section */}
            <div className="bg-[#131722] border border-[#2A2E39] rounded-lg overflow-hidden shadow-lg p-1">
                {/* Main Price Chart */}
                <div className="h-[450px]">
                    {singleResult.candle_data && singleResult.candle_data.length > 0 ? (
                        <BacktestChart
                            data={singleResult.candle_data}
                            trades={singleResult.trades_log || []}
                        />
                    ) : (
                        <div className="flex items-center justify-center h-full text-gray-500">
                            No Candle Data Available
                        </div>
                    )}
                </div>

                {/* Equity Curve Chart */}
                <div className="mt-4">
                    {singleResult.equity_curve && singleResult.equity_curve.length > 0 ? (
                        <EquityChart data={singleResult.equity_curve} />
                    ) : (
                        <p className="text-center text-gray-500 py-4">No equity data available</p>
                    )}
                </div>

                {/* Underwater Drawdown Chart */}
                <div className="h-[200px] border-t border-[#2A2E39] mt-1">
                    <UnderwaterChart
                        data={
                            (singleResult.underwater_data && singleResult.underwater_data.length > 0)
                                ? singleResult.underwater_data
                                : calculateDrawdownFromCandles(singleResult.candle_data || [])
                        }
                        height={200}
                    />
                </div>
            </div>

            {/* ✅ NEW: Monte Carlo Section */}
            {singleResult.monte_carlo && (
                <div className="mt-6 h-[400px]">
                    <MonteCarloCard metrics={singleResult.monte_carlo} />
                </div>
            )}

            {/* B. Performance Summary Panel */}
            <div className="bg-[#131722] border border-[#2A2E39] rounded-lg overflow-hidden shadow-lg animate-fade-in">
                {/* Header Tabs */}
                <div className="flex border-b border-[#2A2E39] px-4 bg-[#1e222d] overflow-x-auto">
                    {['overview', 'performance', 'traders_analysis', 'trades'].map(tab => (
                        <button
                            key={tab}
                            onClick={() => setResultsTab(tab)}
                            className={`px-4 py-3 text-sm font-medium transition-colors capitalize ${resultsTab === tab ? 'text-[#2962FF] border-b-2 border-[#2962FF]' : 'text-gray-400 hover:text-gray-200'}`}
                        >
                            {tab.replace('_', ' ')}
                        </button>
                    ))}
                </div>

                {/* OVERVIEW TAB CONTENT */}
                {resultsTab === 'overview' && (
                    <div className="p-6 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 animate-fade-in">
                        <MetricCard label="Total P&L" value={singleResult.trade_analysis?.net_profit || 0} prefix="$" positive={(singleResult.trade_analysis?.net_profit || 0) >= 0} />
                        <MetricCard label="Gross Profit" value={singleResult.trade_analysis?.gross_profit || 0} prefix="$" positive={true} />
                        <MetricCard label="Max Drawdown" value={singleResult.maxDrawdown || singleResult.advanced_metrics?.max_drawdown || 0} suffix="%" positive={false} />
                        <MetricCard label="Sharpe Ratio" value={singleResult.sharpeRatio || singleResult.advanced_metrics?.sharpe || 0} positive={true} />
                        <MetricCard label="Profit Factor" value={singleResult.advanced_metrics?.profit_factor || 0} />
                        <MetricCard label="Win Rate" value={singleResult.winRate || singleResult.trade_analysis?.win_rate || singleResult.advanced_metrics?.win_rate || 0} suffix="%" />
                    </div>
                )}

                {/* TRADERS ANALYSIS CONTENT */}
                {resultsTab === 'traders_analysis' && singleResult.trade_analysis && (
                    <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-fade-in">
                        {/* Row 1: Trade Counts Breakdown */}
                        <div className="col-span-1 md:col-span-2 lg:col-span-4 grid grid-cols-1 md:grid-cols-3 gap-6 mb-4">
                            <div className="bg-[#1e222d] p-4 rounded border border-[#2A2E39] text-center">
                                <p className="text-gray-400 text-xs uppercase mb-1">Total Trades</p>
                                <p className="text-3xl font-bold text-white">{singleResult.trade_analysis.total_closed}</p>
                            </div>
                            <div className="bg-[#1e222d] p-4 rounded border border-[#2A2E39] text-center">
                                <p className="text-gray-400 text-xs uppercase mb-1">Long Trades</p>
                                <p className="text-3xl font-bold text-green-400">{singleResult.trade_analysis.long_trades_total}</p>
                                <p className="text-xs text-green-600">Won: {singleResult.trade_analysis.long_trades_won}</p>
                            </div>
                            <div className="bg-[#1e222d] p-4 rounded border border-[#2A2E39] text-center">
                                <p className="text-gray-400 text-xs uppercase mb-1">Short Trades</p>
                                <p className="text-3xl font-bold text-red-400">{singleResult.trade_analysis.short_trades_total}</p>
                                <p className="text-xs text-red-600">Won: {singleResult.trade_analysis.short_trades_won}</p>
                            </div>
                        </div>

                        {/* Detailed Metrics Grid */}
                        <MetricCard label="Win Rate" value={singleResult.trade_analysis.win_rate} suffix="%" />
                        <MetricCard label="Total Won" value={singleResult.trade_analysis.total_won} positive={true} />
                        <MetricCard label="Total Lost" value={singleResult.trade_analysis.total_lost} positive={false} />
                        <MetricCard label="Avg PnL" value={singleResult.trade_analysis.avg_pnl} prefix="$" positive={singleResult.trade_analysis.avg_pnl >= 0} />

                        <MetricCard label="Avg Win" value={singleResult.trade_analysis.avg_win} prefix="$" positive={true} />
                        <MetricCard label="Avg Loss" value={singleResult.trade_analysis.avg_loss} prefix="$" positive={false} />
                        <MetricCard label="Win/Loss Ratio" value={singleResult.trade_analysis.ratio_avg_win_loss} />
                        <MetricCard label="Largest Win" value={singleResult.trade_analysis.largest_win_value} prefix="$" positive={true} />

                        <MetricCard label="Largest Loss" value={singleResult.trade_analysis.largest_loss_value} prefix="$" positive={false} />
                        <MetricCard label="Largest Win %" value={singleResult.trade_analysis.largest_win_percent} suffix="%" positive={true} />
                        <MetricCard label="Largest Loss %" value={singleResult.trade_analysis.largest_loss_percent} suffix="%" positive={false} />
                        <MetricCard label="Net Profit" value={singleResult.trade_analysis.net_profit} prefix="$" positive={singleResult.trade_analysis.net_profit >= 0} />
                    </div>
                )}

                {/* PERFORMANCE MATRIX */}
                {resultsTab === 'performance' && (
                    <div className="bg-[#131722] animate-fade-in">
                        <div className="px-6 py-4 border-b border-[#2A2E39] bg-[#1e222d] flex items-center gap-2">
                            <Activity className="h-4 w-4 text-[#2962FF]" />
                            <h3 className="text-sm font-semibold text-gray-200">Key Metrics Matrix</h3>
                        </div>
                        <div className="p-0">
                            <table className="w-full text-sm text-left">
                                <tbody>
                                    {singleResult.advanced_metrics && Object.entries(singleResult.advanced_metrics).map(([key, value], index) => (
                                        <tr key={key} className={`border-b border-[#2A2E39] last:border-0 ${index % 2 === 0 ? 'bg-[#1e222d]' : 'bg-[#131722]'}`}>
                                            <td className="px-6 py-3 text-gray-400 capitalize font-medium">{key.replace(/_/g, ' ')}</td>
                                            <td className="px-6 py-3 text-right text-gray-100 font-mono">{(typeof value === 'number') ? value.toFixed(2) : value}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* TRADE LIST */}
                {resultsTab === 'trades' && (
                    <div className="bg-[#131722] animate-fade-in flex flex-col h-[600px]">
                        <div className="px-6 py-4 border-b border-[#2A2E39] bg-[#1e222d] flex items-center gap-2">
                            <Layers className="h-4 w-4 text-[#2962FF]" />
                            <h3 className="text-sm font-semibold text-gray-200">Trade List</h3>
                        </div>
                        <div className="flex-1 overflow-auto custom-scrollbar">
                            <table className="w-full text-xs text-left">
                                <thead className="bg-[#1e222d] text-gray-400 sticky top-0 z-10">
                                    <tr>
                                        <th className="px-4 py-2 bg-[#1e222d]">Type</th>
                                        <th className="px-4 py-2 bg-[#1e222d]">Price</th>
                                        <th className="px-4 py-2 bg-[#1e222d]">Size</th>
                                        <th className="px-4 py-2 bg-[#1e222d]">Time</th>
                                        <th className="px-4 py-2 text-right bg-[#1e222d]">P/L</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {singleResult.trades_log?.map((trade: any, idx: number) => (
                                        <tr key={idx} className="border-b border-[#2A2E39] hover:bg-[#2A2E39] transition-colors">
                                            <td className={`px-4 py-2 font-bold ${trade.side === 'BUY' || trade.type === 'buy' ? 'text-[#089981]' : 'text-[#F23645]'}`}>
                                                {trade.side || trade.type || (trade.size > 0 ? 'BUY' : 'SELL')}
                                            </td>
                                            <td className="px-4 py-2 font-mono text-gray-300">{trade.price?.toFixed(2)}</td>
                                            <td className="px-4 py-2 font-mono text-gray-300">{trade.size?.toFixed(4) || '-'}</td>
                                            <td className="px-4 py-2 font-mono text-gray-400">{new Date(trade.time * 1000).toLocaleString()}</td>
                                            <td className={`px-4 py-2 text-right font-mono ${trade.pnl >= 0 ? 'text-[#089981]' : (trade.pnl < 0 ? 'text-[#F23645]' : 'text-gray-400')}`}>
                                                {trade.pnl !== undefined ? trade.pnl.toFixed(2) : '-'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
