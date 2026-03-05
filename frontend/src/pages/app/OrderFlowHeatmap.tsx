import React, { useEffect, useRef, useMemo, useState } from 'react';
import { createChart, ISeriesApi, CandlestickData, CandlestickSeries } from 'lightweight-charts';
import { useLevel2MarketData } from '@/hooks/useLevel2MarketData';
import api from '../../services/api';
import { HeatmapSymbolSelector } from '../../components/features/market/HeatmapSymbolSelector';
import { TimeframeSelector } from '../../components/features/market/TimeframeSelector';
import { LiquidityHeatmapRenderer, HeatmapDataPoint } from '../../components/features/market/LiquidityHeatmapRenderer';

// Chart Component
const OrderFlowChart: React.FC<{ symbol: string; interval: string; walls: { price: number, type: 'buy' | 'sell' }[] }> = ({ symbol, interval, walls }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<any>(null);
    const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
    const wallLinesRef = useRef<any[]>([]);
    const [heatmapData, setHeatmapData] = useState<HeatmapDataPoint[]>([]);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: 'solid', color: 'transparent' } as any,
                textColor: '#94a3b8',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
            },
        });

        const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#22c55e',
            downColor: '#ef4444',
            borderVisible: false,
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
        });

        chartRef.current = chart;
        candlestickSeriesRef.current = candlestickSeries;

        // Fetch real historical data
        const fetchKlines = async () => {
            try {
                const cleanSymbol = symbol.replace('/', '').replace('-', '').toUpperCase();
                const res = await api.get('/market-data/klines', {
                    params: { symbol: cleanSymbol, interval: interval, limit: 200, exchange: 'binance' }
                });
                const candles = res.data.map((k: any) => ({
                    time: (k[0] / 1000) as any,
                    open: parseFloat(k[1]),
                    high: parseFloat(k[2]),
                    low: parseFloat(k[3]),
                    close: parseFloat(k[4]),
                }));
                if (candlestickSeriesRef.current) {
                    candlestickSeriesRef.current.setData(candles);
                    // TODO: Provide real historical depth data here 
                    setHeatmapData([]);
                    chart.timeScale().fitContent();
                }
            } catch (err) {
                console.error("Failed to fetch klines for heatmap:", err);
            }
        };

        fetchKlines();

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth, height: chartContainerRef.current.clientHeight });
            }
        };
        window.addEventListener('resize', handleResize);
        setTimeout(handleResize, 100);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [symbol, interval]);

    // Update horizontal price lines for walls
    useEffect(() => {
        if (!candlestickSeriesRef.current || !chartRef.current) return;

        // Remove old lines
        wallLinesRef.current.forEach(line => candlestickSeriesRef.current?.removePriceLine(line));
        wallLinesRef.current = [];

        // Add new lines
        walls.forEach(wall => {
            const priceLine = candlestickSeriesRef.current?.createPriceLine({
                price: wall.price,
                color: wall.type === 'buy' ? 'rgba(34, 197, 94, 0.6)' : 'rgba(239, 68, 68, 0.6)',
                lineWidth: 4,
                lineStyle: 0,
                axisLabelVisible: true,
                title: `${wall.type.toUpperCase()} WALL`,
            });
            if (priceLine) wallLinesRef.current.push(priceLine);
        });
    }, [walls]);

    return (
        <div className="w-full h-full absolute inset-0">
            <div ref={chartContainerRef} className="w-full h-full absolute inset-0 z-0" />
            <div className="absolute inset-0 z-10 pointer-events-none overflow-hidden" style={{ right: 60, bottom: 26 }}>
                <LiquidityHeatmapRenderer chart={chartRef.current} series={candlestickSeriesRef.current} data={heatmapData} />
            </div>
        </div>
    );
};

// Order Book Component
const OrderBook: React.FC<{ bids: any[], asks: any[], maxTotal: number }> = ({ bids, asks, maxTotal }) => {
    if (bids.length === 0 && asks.length === 0) return <div className="text-gray-500 p-4">Loading...</div>;

    const formatPrice = (p: number) => p.toFixed(5);
    const formatSize = (s: number) => s.toFixed(2);

    return (
        <div className="flex flex-col h-full font-mono text-[11px] select-none">
            <div className="flex text-gray-500 pb-2 border-b border-gray-200 dark:border-white/10 px-2 uppercase tracking-wider font-bold">
                <div className="w-1/3 text-left">Price</div>
                <div className="w-1/3 text-right">Size</div>
                <div className="w-1/3 text-right">Total</div>
            </div>

            {/* Asks (Sell) */}
            <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col justify-end">
                {asks.slice().reverse().map((ask, i) => (
                    <div key={i} className="flex px-2 py-[2px] relative group hover:bg-white/5 cursor-pointer">
                        <div
                            className="absolute right-0 top-0 h-full bg-red-500/10 dark:bg-red-500/20 transition-all duration-300 pointer-events-none"
                            style={{ width: `${(ask.total / maxTotal) * 100}%` }}
                        />
                        <div className="w-1/3 text-left text-red-500 relative z-10 font-bold">{formatPrice(ask.price)}</div>
                        <div className="w-1/3 text-right text-gray-800 dark:text-gray-300 relative z-10">{formatSize(ask.size)}</div>
                        <div className="w-1/3 text-right text-gray-500 dark:text-gray-500 relative z-10">{formatSize(ask.total)}</div>
                    </div>
                ))}
            </div>

            <div className="py-2 flex items-center justify-between text-xs px-2 border-y border-gray-200 dark:border-white/10 my-1 bg-gray-50 dark:bg-black/20">
                <span className="text-gray-500 font-sans font-medium">Spread</span>
                {asks.length > 0 && bids.length > 0 && (
                    <span className="text-brand-primary font-bold">
                        {((asks[asks.length - 1].price - bids[0].price)).toFixed(5)}
                    </span>
                )}
            </div>

            {/* Bids (Buy) */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
                {bids.map((bid, i) => (
                    <div key={i} className="flex px-2 py-[2px] relative group hover:bg-white/5 cursor-pointer">
                        <div
                            className="absolute right-0 top-0 h-full bg-green-500/10 dark:bg-green-500/20 transition-all duration-300 pointer-events-none"
                            style={{ width: `${(bid.total / maxTotal) * 100}%` }}
                        />
                        <div className="w-1/3 text-left text-green-500 relative z-10 font-bold">{formatPrice(bid.price)}</div>
                        <div className="w-1/3 text-right text-gray-800 dark:text-gray-300 relative z-10">{formatSize(bid.size)}</div>
                        <div className="w-1/3 text-right text-gray-500 dark:text-gray-500 relative z-10">{formatSize(bid.total)}</div>
                    </div>
                ))}
            </div>
        </div>
    );
};

// Main Page Component
const OrderFlowHeatmap: React.FC = () => {
    const [symbol, setSymbol] = useState('DOGE/USDT');
    const [interval, setInterval] = useState('1m');
    const { bids, asks, walls, currentPrice } = useLevel2MarketData(symbol);

    const maxTotal = useMemo(() => {
        const maxBid = bids.length > 0 ? bids[bids.length - 1].total : 0;
        const maxAsk = asks.length > 0 ? asks[asks.length - 1].total : 0;
        return Math.max(maxBid, maxAsk, 1); // Avoid division by zero
    }, [bids, asks]);

    return (
        <div className="flex flex-col h-full bg-brand-light dark:bg-brand-darkest text-slate-900 dark:text-white overflow-hidden rounded-xl border border-gray-200 dark:border-white/10">
            <header className="flex-shrink-0 p-4 border-b border-gray-200 dark:border-white/10 flex justify-between items-center bg-white dark:bg-[#0B1120]">
                <div className="flex items-center gap-4">
                    <h2 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-brand-primary to-purple-500">Order Flow Heatmap</h2>
                    <HeatmapSymbolSelector symbol={symbol} onSymbolChange={setSymbol} />
                    <TimeframeSelector interval={interval} onIntervalChange={setInterval} />
                    <span className="text-lg font-mono font-bold text-gray-800 dark:text-white">
                        {currentPrice.toFixed(5)}
                    </span>
                </div>
                <div className="flex gap-2">
                    <span className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-lg bg-green-500/10 text-green-500 border border-green-500/20">
                        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                        Live Data Socket
                    </span>
                </div>
            </header>
            <div className="flex-1 p-4 overflow-hidden bg-gray-50 dark:bg-[#050B14]">
                <div className="flex flex-row h-full gap-4">
                    <div className="w-[70%] bg-white dark:bg-[#0B1120] rounded-xl border border-gray-200 dark:border-white/5 overflow-hidden shadow-[0_4px_20px_rgba(0,0,0,0.05)] dark:shadow-[0_4px_20px_rgba(0,0,0,0.2)] flex flex-col">
                        <div className="p-3 border-b border-gray-200 dark:border-white/5 flex justify-between items-center">
                            <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Order Flow Chart</h3>
                        </div>
                        <div className="flex-1 relative">
                            <OrderFlowChart symbol={symbol} interval={interval} walls={walls} />
                        </div>
                    </div>
                    <div className="w-[30%] bg-white dark:bg-[#0B1120] rounded-xl border border-gray-200 dark:border-white/5 overflow-hidden shadow-[0_4px_20px_rgba(0,0,0,0.05)] dark:shadow-[0_4px_20px_rgba(0,0,0,0.2)] flex flex-col">
                        <div className="p-3 border-b border-gray-200 dark:border-white/5 flex justify-between items-center">
                            <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Level 2 Order Book</h3>
                        </div>
                        <div className="flex-1 overflow-hidden p-2">
                            <OrderBook bids={bids} asks={asks} maxTotal={maxTotal} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default OrderFlowHeatmap;
