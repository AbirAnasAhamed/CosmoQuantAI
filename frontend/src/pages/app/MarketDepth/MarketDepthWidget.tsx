
import React, { useEffect, useState, useMemo } from 'react';
import { Activity, ArrowDown, ArrowUp, RefreshCcw, Layers } from 'lucide-react';
import Button from '@/components/common/Button';  // Assuming this exists based on AppDashboard import
import { useSettings } from '@/context/SettingsContext';
import { useTheme } from '@/context/ThemeContext';

interface OrderBucket {
    price: number;
    volume: number;
}

interface MarketDepthData {
    symbol: string;
    exchange: string;
    current_price: number;
    bids: OrderBucket[];
    asks: OrderBucket[];
}

const MarketDepthWidget: React.FC = () => {
    const { theme } = useTheme();
    const isDarkMode = theme === 'dark';
    const [symbol, setSymbol] = useState('BTC/USDT');
    const [exchange, setExchange] = useState('binance');
    const [bucketSize, setBucketSize] = useState(50);
    const [data, setData] = useState<MarketDepthData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

    const availableSymbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT'];
    const bucketSizes = {
        'BTC/USDT': [10, 50, 100],
        'ETH/USDT': [1, 5, 10],
        'SOL/USDT': [0.1, 0.5, 1],
        'BNB/USDT': [0.5, 1, 5],
        'XRP/USDT': [0.001, 0.005, 0.01]
    };

    const currentBucketOptions = bucketSizes[symbol as keyof typeof bucketSizes] || [1, 10, 50];

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            // Assuming API proxy is set up or full URL is needed. 
            // Using relative path based on settings.API_V1_STR usually being /api/v1
            const response = await fetch(`http://localhost:8000/api/v1/market-depth/heatmap?symbol=${symbol}&exchange=${exchange}&bucket_size=${bucketSize}`);

            if (!response.ok) {
                throw new Error('Failed to fetch market depth data');
            }

            const jsonData: MarketDepthData = await response.json();
            setData(jsonData);
            setLastUpdated(new Date());
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An unknown error occurred');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000); // Auto-refresh every 5s
        return () => clearInterval(interval);
    }, [symbol, exchange, bucketSize]);

    // Calculations for visualization
    const maxVolume = useMemo(() => {
        if (!data) return 0;
        const maxBid = Math.max(...data.bids.map(b => b.volume), 0);
        const maxAsk = Math.max(...data.asks.map(a => a.volume), 0);
        return Math.max(maxBid, maxAsk);
    }, [data]);

    return (
        <div className="h-full flex flex-col p-6 space-y-6">
            {/* Header Section */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-[#1e293b] p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
                <div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <Activity className="text-brand-primary" />
                        Market Depth Heatmap
                    </h2>
                    <p className="text-sm text-slate-500 dark:text-gray-400 mt-1">
                        Visualize real-time order book liquidity and support/resistance levels.
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                    {/* Symbol Selector */}
                    <select
                        value={symbol}
                        onChange={(e) => {
                            setSymbol(e.target.value);
                            // Reset bucket size to default for new symbol
                            const newBuckets = bucketSizes[e.target.value as keyof typeof bucketSizes] || [1];
                            setBucketSize(newBuckets[1] || newBuckets[0]);
                        }}
                        className="px-4 py-2 rounded-xl bg-gray-50 dark:bg-[#0f172a] border border-gray-200 dark:border-gray-700 text-sm font-medium focus:ring-2 focus:ring-brand-primary outline-none text-slate-700 dark:text-gray-200"
                    >
                        {availableSymbols.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>

                    {/* Bucket Size Selector */}
                    <div className="flex items-center gap-2 bg-gray-50 dark:bg-[#0f172a] px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700">
                        <span className="text-xs text-gray-500 uppercase font-bold">Bucket:</span>
                        <select
                            value={bucketSize}
                            onChange={(e) => setBucketSize(parseFloat(e.target.value))}
                            className="bg-transparent text-sm font-bold text-brand-primary focus:outline-none cursor-pointer"
                        >
                            {currentBucketOptions.map(size => (
                                <option key={size} value={size}>${size}</option>
                            ))}
                        </select>
                    </div>

                    <Button variant="secondary" onClick={fetchData} className="!p-2.5">
                        <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    </Button>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 bg-white dark:bg-[#1e293b] rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden flex flex-col relative">
                {error && (
                    <div className="absolute inset-0 z-10 bg-white/80 dark:bg-black/50 flex items-center justify-center p-8 text-center text-red-500 font-bold">
                        {error}
                    </div>
                )}

                {!data && !error && (
                    <div className="absolute inset-0 z-10 bg-white/80 dark:bg-black/50 flex items-center justify-center p-8">
                        <div className="animate-pulse text-gray-400 font-medium">Loading Market Data...</div>
                    </div>
                )}

                {data && (
                    <>
                        {/* Price Header */}
                        <div className="py-4 px-6 border-b border-gray-100 dark:border-gray-700 flex justify-center items-center bg-gray-50/50 dark:bg-[#161e2e]/50 backdrop-blur-sm sticky top-0 z-10">
                            <div className="text-center">
                                <span className="text-xs text-gray-400 font-mono uppercase tracking-widest block mb-1">Current Price ({data.exchange})</span>
                                <div className="text-3xl font-black tracking-tight text-slate-900 dark:text-white font-mono">
                                    ${data.current_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </div>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                            <div className="max-w-4xl mx-auto">
                                <div className="flex gap-8">

                                    {/* BIDS (Green) - Left Side */}
                                    <div className="flex-1 flex flex-col gap-1">
                                        <div className="text-right text-xs font-bold text-emerald-500 mb-2 uppercase tracking-wider flex justify-end items-center gap-1">
                                            Bids (Support) <ArrowUp size={12} />
                                        </div>
                                        {data.bids.map((bid, idx) => {
                                            const widthPercent = (bid.volume / maxVolume) * 100;
                                            return (
                                                <div key={bid.price} className="flex items-center justify-end h-8 group relative">
                                                    <div className="absolute right-0 top-0 bottom-0 bg-emerald-500/10 dark:bg-emerald-500/20 rounded-l-md transition-all duration-500 ease-out" style={{ width: `${widthPercent}%` }}></div>
                                                    <div className="relative z-10 flex items-center gap-4 pr-3">
                                                        <span className="text-xs font-medium text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                                                            Vol: {bid.volume.toFixed(4)}
                                                        </span>
                                                        <span className="text-sm font-bold font-mono text-slate-700 dark:text-emerald-100">
                                                            {bid.price.toLocaleString()}
                                                        </span>
                                                    </div>
                                                </div>
                                            )
                                        })}
                                    </div>

                                    {/* Center Axis */}
                                    <div className="w-px bg-gray-200 dark:bg-gray-700 relative"></div>

                                    {/* ASKS (Red) - Right Side */}
                                    <div className="flex-1 flex flex-col gap-1">
                                        <div className="text-left text-xs font-bold text-rose-500 mb-2 uppercase tracking-wider flex items-center gap-1">
                                            <ArrowDown size={12} /> Asks (Resistance)
                                        </div>
                                        {data.asks.map((ask, idx) => {
                                            const widthPercent = (ask.volume / maxVolume) * 100;
                                            return (
                                                <div key={ask.price} className="flex items-center h-8 group relative">
                                                    <div className="absolute left-0 top-0 bottom-0 bg-rose-500/10 dark:bg-rose-500/20 rounded-r-md transition-all duration-500 ease-out" style={{ width: `${widthPercent}%` }}></div>
                                                    <div className="relative z-10 flex items-center gap-4 pl-3">
                                                        <span className="text-sm font-bold font-mono text-slate-700 dark:text-rose-100">
                                                            {ask.price.toLocaleString()}
                                                        </span>
                                                        <span className="text-xs font-medium text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                                                            Vol: {ask.volume.toFixed(4)}
                                                        </span>
                                                    </div>
                                                </div>
                                            )
                                        })}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="py-2 px-6 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-[#0f172a] flex justify-between items-center text-[10px] text-gray-400">
                            <span>Source: {exchange.toUpperCase()} (CCXT)</span>
                            <span>Last Updated: {lastUpdated ? lastUpdated.toLocaleTimeString() : 'Never'}</span>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default MarketDepthWidget;
