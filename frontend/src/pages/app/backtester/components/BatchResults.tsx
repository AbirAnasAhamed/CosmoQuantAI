import React, { useMemo } from 'react';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import { FileText, List, LayoutGrid, BarChart2, Eye, Download } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import ParameterHeatmap from '@/components/features/backtest/ParameterHeatmap';

// Helper: Safely extract values
const getSafeValue = (item: any, keys: string[]) => {
    if (!item) return 0;
    for (const key of keys) {
        const val = item[key];
        if (val !== undefined && val !== null && !isNaN(Number(val))) {
            return Number(val);
        }
    }
    return 0;
};

// Helper: Convert Data to CSV and Download
const downloadCSV = (data: any[], filename = 'backtest_results.csv') => {
    if (!data || !data.length) return;

    const flattenRow = (row: any) => {
        const { params, ...rest } = row;
        return { ...rest, ...params };
    };

    const flatData = data.map(flattenRow);
    const headers = Object.keys(flatData[0]);

    const csvRows = [
        headers.join(','),
        ...flatData.map(row => headers.map(header => {
            const val = row[header];
            const escaped = ('' + (val ?? '')).replace(/"/g, '""');
            return `"${escaped}"`;
        }).join(','))
    ];

    const csvString = csvRows.join('\n');
    const blob = new Blob([csvString], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.setAttribute('hidden', '');
    a.setAttribute('href', url);
    a.setAttribute('download', filename);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
};

interface BatchResultsProps {
    batchResults: any[];
    multiObjectiveResults: any[];
    viewMode: 'table' | 'heatmap' | 'chart';
    setViewMode: (mode: 'table' | 'heatmap' | 'chart') => void;
    setSelectedBatchResult: (res: any) => void;
}

export const BatchResults: React.FC<BatchResultsProps> = ({
    batchResults,
    multiObjectiveResults,
    viewMode,
    setViewMode,
    setSelectedBatchResult
}) => {
    const rawResults = batchResults || multiObjectiveResults;

    // Sort by Profit (Highest First) and take Top 100
    const results = useMemo(() => {
        if (!rawResults) return [];
        return [...rawResults]
            .sort((a, b) => {
                const profitA = getSafeValue(a, ['profitPercent', 'profit_percent']);
                const profitB = getSafeValue(b, ['profitPercent', 'profit_percent']);
                return profitB - profitA;
            })
            .slice(0, 100);
    }, [rawResults]);

    if (!results || results.length === 0) return null;

    return (
        <Card className="animate-fade-in mt-6">
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-purple-400">
                        🏆 Top Strategy Leaderboard
                    </h2>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => downloadCSV(results, `optimization_results_${new Date().toISOString().slice(0, 10)}.csv`)}
                        className="flex items-center gap-2"
                    >
                        <Download size={14} /> Export CSV
                    </Button>
                </div>

                {/* View Toggles */}
                <div className="flex bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
                    <button onClick={() => setViewMode('table')} className={`p-2 rounded-md ${viewMode === 'table' ? 'bg-white dark:bg-brand-primary text-brand-primary dark:text-white shadow' : 'text-gray-400'}`}><List size={18} /></button>
                    <button onClick={() => setViewMode('heatmap')} className={`p-2 rounded-md ${viewMode === 'heatmap' ? 'bg-white dark:bg-brand-primary text-brand-primary dark:text-white shadow' : 'text-gray-400'}`}><LayoutGrid size={18} /></button>
                    <button onClick={() => setViewMode('chart')} className={`p-2 rounded-md ${viewMode === 'chart' ? 'bg-white dark:bg-brand-primary text-brand-primary dark:text-white shadow' : 'text-gray-400'}`}><BarChart2 size={18} /></button>
                </div>
            </div>

            {/* CHART VIEW */}
            {viewMode === 'chart' && (
                <div className="mb-8 bg-[#131722] p-4 rounded-lg border border-[#2A2E39] h-[350px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={results}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#2A2E39" vertical={false} />
                            <XAxis dataKey="id" tickFormatter={(val, idx) => `#${idx + 1}`} stroke="#9CA3AF" fontSize={12} />
                            <YAxis stroke="#9CA3AF" fontSize={12} />
                            <Tooltip contentStyle={{ backgroundColor: '#1F2937', borderColor: '#374151', color: '#fff' }} />
                            <Bar dataKey="profitPercent" name="Profit %" radius={[4, 4, 0, 0]}>
                                {results.map((entry: any, index: number) => (
                                    <Cell key={`cell-${index}`} fill={getSafeValue(entry, ['profitPercent']) >= 0 ? '#10B981' : '#EF4444'} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* HEATMAP VIEW */}
            {viewMode === 'heatmap' && <ParameterHeatmap results={results} />}

            {/* TABLE VIEW */}
            {viewMode === 'table' && (
                <div className="overflow-x-auto custom-scrollbar">
                    <table className="w-full text-left text-sm text-slate-900 dark:text-white">
                        <thead className="bg-gray-100 dark:bg-gray-800 uppercase text-xs text-gray-500">
                            <tr>
                                <th className="px-4 py-3">Rank</th>
                                <th className="px-4 py-3">Strategy / Params</th>
                                <th className="px-4 py-3 text-right">Profit %</th>
                                <th className="px-4 py-3 text-right">Win Rate</th>
                                <th className="px-4 py-3 text-right">Drawdown</th>
                                {/* Added Trades Column Header */}
                                <th className="px-4 py-3 text-right">Trades</th>
                                <th className="px-4 py-3 text-center">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                            {results.map((res: any, idx: number) => {
                                const profit = getSafeValue(res, ['profitPercent', 'profit_percent']);
                                const winRate = getSafeValue(res, ['winRate', 'win_rate']);
                                const drawdown = getSafeValue(res, ['maxDrawdown', 'max_drawdown']);
                                // Extract Trades Count
                                const trades = getSafeValue(res, ['total_trades', 'totalTrades']);

                                const paramString = res.params
                                    ? Object.entries(res.params).map(([k, v]) => `${k}: ${v}`).join(', ')
                                    : 'No params';

                                return (
                                    <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors group">
                                        <td className="px-4 py-3 font-bold text-gray-500">#{idx + 1}</td>
                                        <td className="px-4 py-3">
                                            <div className="font-medium text-brand-primary">{res.strategy || "Unknown"}</div>
                                            <div className="text-xs text-gray-500 mt-1 font-mono break-all">{paramString}</div>
                                        </td>
                                        <td className={`px-4 py-3 text-right font-bold ${profit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                            {profit.toFixed(2)}%
                                        </td>
                                        <td className="px-4 py-3 text-right text-blue-400">{winRate.toFixed(1)}%</td>
                                        <td className="px-4 py-3 text-right text-red-400">{Math.abs(drawdown).toFixed(2)}%</td>

                                        {/* Added Trades Column Data */}
                                        <td className="px-4 py-3 text-right text-gray-500 font-mono">{trades}</td>

                                        <td className="px-4 py-3 text-center">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setSelectedBatchResult(res);
                                                }}
                                                className="flex items-center justify-center gap-1 bg-brand-primary/10 hover:bg-brand-primary text-brand-primary hover:text-white px-3 py-1.5 rounded transition-all mx-auto"
                                            >
                                                <Eye size={14} /> View Chart
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </Card>
    );
}
