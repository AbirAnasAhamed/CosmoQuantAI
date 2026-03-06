import React, { useEffect, useRef, useMemo, useState } from 'react';
import { createChart, ISeriesApi, CandlestickData, CandlestickSeries, LineSeries } from 'lightweight-charts';
import { useLevel2MarketData } from '@/hooks/useLevel2MarketData';
import { useOrderFlowData } from '../../hooks/useOrderFlowData';
import { useHeatmapData } from '../../hooks/useHeatmapData';
import { useVolumeFilter } from '../../hooks/useVolumeFilter';
import api from '../../services/api';
import { HeatmapSymbolSelector } from '../../components/features/market/HeatmapSymbolSelector';
import { TimeframeSelector } from '../../components/features/market/TimeframeSelector';
import { VolumeFilterControl } from '../../components/features/market/VolumeFilterControl';
import { LiquidityHeatmapRenderer, HeatmapDataPoint } from '../../components/features/market/LiquidityHeatmapRenderer';
import { VolumeProfileWidget, VPVRData } from '../../components/features/market/VolumeProfileWidget';
import { CVDChart, CVDDataPoint } from '../../components/features/market/CVDChart';
import { FootprintRenderer, FootprintCandleData, FootprintDataTick } from '../../components/features/market/FootprintRenderer';
import { IndicatorSelector, IndicatorSettings } from '../../components/features/market/IndicatorSelector';
import { calculateEMA, calculateBollingerBands, calculateRSI } from '../../utils/indicators';

// Chart Component
const OrderFlowChart: React.FC<{ exchange: string; symbol: string; interval: string; walls: { price: number, type: 'buy' | 'sell' }[]; currentPrice: number; showFootprint: boolean; indicatorSettings: IndicatorSettings }> = ({ exchange, symbol, interval, walls, currentPrice, showFootprint, indicatorSettings }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<any>(null);
    const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
    const emaSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
    const bbUpperSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
    const bbMiddleSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
    const bbLowerSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
    const rsiSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
    const wallLinesRef = useRef<any[]>([]);
    const lastCandleRef = useRef<CandlestickData | null>(null);
    const allCandlesRef = useRef<any[]>([]);
    const { vpvrData, cvdData, footprintData } = useOrderFlowData(symbol, exchange, interval);
    const { heatmapData: realHeatmapData } = useHeatmapData(symbol, exchange);

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
                scaleMargins: { top: 0.1, bottom: 0.2 }, // Leave bottom 20% for RSI
            },
            leftPriceScale: {
                visible: true,
                borderColor: 'rgba(255, 255, 255, 0.1)',
                scaleMargins: { top: 0.8, bottom: 0 }, // RSI takes bottom 20%
            },
        });

        const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#22c55e',
            downColor: '#ef4444',
            borderVisible: false,
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
            priceFormat: {
                type: 'custom',
                minMove: 0.00000001,
                formatter: (price: number) => {
                    if (price < 0.00001) return price.toFixed(8);
                    if (price < 0.001) return price.toFixed(6);
                    if (price < 1) return price.toFixed(5);
                    if (price < 10) return price.toFixed(4);
                    return price.toFixed(2);
                }
            }
        });

        const emaSeries = chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: false });
        const bbUpperSeries = chart.addSeries(LineSeries, { color: 'rgba(56, 189, 248, 0.5)', lineWidth: 1, crosshairMarkerVisible: false, lastValueVisible: false });
        const bbMiddleSeries = chart.addSeries(LineSeries, { color: 'rgba(56, 189, 248, 0.8)', lineWidth: 1, crosshairMarkerVisible: false, lastValueVisible: false });
        const bbLowerSeries = chart.addSeries(LineSeries, { color: 'rgba(56, 189, 248, 0.5)', lineWidth: 1, crosshairMarkerVisible: false, lastValueVisible: false });
        const rsiSeries = chart.addSeries(LineSeries, { color: '#db2777', lineWidth: 2, priceScaleId: 'left', crosshairMarkerVisible: false, lastValueVisible: false });

        chartRef.current = chart;
        candlestickSeriesRef.current = candlestickSeries;
        emaSeriesRef.current = emaSeries;
        bbUpperSeriesRef.current = bbUpperSeries;
        bbMiddleSeriesRef.current = bbMiddleSeries;
        bbLowerSeriesRef.current = bbLowerSeries;
        rsiSeriesRef.current = rsiSeries;

        // Fetch real historical data
        const fetchKlines = async () => {
            try {
                const res = await api.get('/market-data/klines', {
                    params: { symbol: symbol.toUpperCase(), interval: interval, limit: 200, exchange: exchange }
                });
                const candles = res.data.map((k: any) => ({
                    time: (k[0] / 1000) as any,
                    open: parseFloat(k[1]),
                    high: parseFloat(k[2]),
                    low: parseFloat(k[3]),
                    close: parseFloat(k[4]),
                    volume: parseFloat(k[5] || 100),
                }));
                if (candlestickSeriesRef.current) {
                    candlestickSeriesRef.current.setData(candles);
                    allCandlesRef.current = candles;
                    if (candles.length > 0) {
                        lastCandleRef.current = { ...candles[candles.length - 1] };
                    }

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
    }, [symbol, interval, exchange]);

    // Update Indicators
    useEffect(() => {
        if (!emaSeriesRef.current || !bbUpperSeriesRef.current || !bbMiddleSeriesRef.current || !bbLowerSeriesRef.current || !rsiSeriesRef.current) return;

        const data = allCandlesRef.current;
        if (data.length === 0) return;

        emaSeriesRef.current.applyOptions({ visible: indicatorSettings.showEMA });
        if (indicatorSettings.showEMA) {
            emaSeriesRef.current.setData(calculateEMA(data, indicatorSettings.emaPeriod) as any);
        }

        const showBB = indicatorSettings.showBB;
        bbUpperSeriesRef.current.applyOptions({ visible: showBB });
        bbMiddleSeriesRef.current.applyOptions({ visible: showBB });
        bbLowerSeriesRef.current.applyOptions({ visible: showBB });
        if (showBB) {
            const bbData = calculateBollingerBands(data, indicatorSettings.bbPeriod, indicatorSettings.bbStdDev);
            bbUpperSeriesRef.current.setData(bbData.map(d => ({ time: d.time, value: d.upper })) as any);
            bbMiddleSeriesRef.current.setData(bbData.map(d => ({ time: d.time, value: d.middle })) as any);
            bbLowerSeriesRef.current.setData(bbData.map(d => ({ time: d.time, value: d.lower })) as any);
        }

        rsiSeriesRef.current.applyOptions({ visible: indicatorSettings.showRSI });
        if (chartRef.current) {
            chartRef.current.priceScale('left').applyOptions({ visible: indicatorSettings.showRSI });
        }
        if (indicatorSettings.showRSI) {
            rsiSeriesRef.current.setData(calculateRSI(data, indicatorSettings.rsiPeriod) as any);
        }

    }, [indicatorSettings, allCandlesRef.current]);

    // Real-time candle update
    useEffect(() => {
        if (!candlestickSeriesRef.current || !lastCandleRef.current || !currentPrice) return;

        const lastCandle = lastCandleRef.current;
        const updatedCandle: CandlestickData = {
            ...lastCandle,
            close: currentPrice,
            high: Math.max(lastCandle.high, currentPrice),
            low: Math.min(lastCandle.low, currentPrice),
        };

        try {
            candlestickSeriesRef.current.update(updatedCandle);
            lastCandleRef.current = updatedCandle;

            // Update allCandles array so indicators can respond if needed
            const len = allCandlesRef.current.length;
            if (len > 0 && allCandlesRef.current[len - 1].time === updatedCandle.time) {
                allCandlesRef.current[len - 1] = updatedCandle;
            } else {
                allCandlesRef.current.push(updatedCandle);
            }

            // We could re-calculate the last indicator value here for performance, 
            // but for simplicity we rely on the indicator recalculation effect if we trigger it,
            // or we just let it update on the next full fetch/interval tick.
            // A fully accurate realtime indicator requires incrementally calculating the last point.

        } catch (e) {
            console.error("Failed to update realtime candle", e);
        }
    }, [currentPrice]);

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
        <div className="w-full h-full flex flex-col absolute inset-0">
            <div className="flex-1 relative">
                <div ref={chartContainerRef} className="w-full h-full absolute inset-0 z-0" />
                <div className="absolute inset-0 z-10 pointer-events-none overflow-hidden" style={{ right: 60, bottom: 26 }}>
                    <LiquidityHeatmapRenderer chart={chartRef.current} series={candlestickSeriesRef.current} data={realHeatmapData} />
                    {showFootprint && <FootprintRenderer chart={chartRef.current} series={candlestickSeriesRef.current} data={footprintData} visible={showFootprint} />}
                </div>
                <VolumeProfileWidget chart={chartRef.current} series={candlestickSeriesRef.current} data={vpvrData} />
            </div>
            <div className="h-[25%] border-t border-gray-200 dark:border-white/5 relative z-0">
                <CVDChart mainChart={chartRef.current} data={cvdData} />
            </div>
        </div>
    );
};

// Order Book Component
const OrderBook: React.FC<{ bids: any[], asks: any[], maxTotal: number }> = ({ bids, asks, maxTotal }) => {
    if (bids.length === 0 && asks.length === 0) return <div className="text-gray-500 p-4">Loading...</div>;

    const formatPrice = (price: number) => {
        if (price < 0.00001) return price.toFixed(8);
        if (price < 0.001) return price.toFixed(6);
        if (price < 1) return price.toFixed(5);
        if (price < 10) return price.toFixed(4);
        return price.toFixed(2);
    };
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

// Helper to format prices dynamically
const formatDisplayPrice = (price: number) => {
    if (price < 0.00001) return price.toFixed(8);
    if (price < 0.001) return price.toFixed(6);
    if (price < 1) return price.toFixed(5);
    if (price < 10) return price.toFixed(4);
    return price.toFixed(2);
};

// Main Page Component
const OrderFlowHeatmap: React.FC = () => {
    const [exchange, setExchange] = useState('binance');
    const [symbol, setSymbol] = useState('BTC/USDT');
    const [interval, setInterval] = useState('1m');
    const [showFootprint, setShowFootprint] = useState(false);
    const [indicatorSettings, setIndicatorSettings] = useState<IndicatorSettings>({
        showEMA: false,
        showBB: false,
        showRSI: false,
        emaPeriod: 20,
        bbPeriod: 20,
        bbStdDev: 2,
        rsiPeriod: 14,
    });
    const { bids, asks, walls, currentPrice } = useLevel2MarketData(symbol, exchange);
    const { volumeThreshold, setVolumeThreshold } = useVolumeFilter(1000);

    const filteredWalls = useMemo(() => {
        if (volumeThreshold <= 0) return walls;

        const newWalls: { price: number; type: 'buy' | 'sell'; size: number }[] = [];
        asks.forEach(ask => {
            if (ask.size >= volumeThreshold) {
                newWalls.push({ price: ask.price, type: 'sell', size: ask.size });
            }
        });
        bids.forEach(bid => {
            if (bid.size >= volumeThreshold) {
                newWalls.push({ price: bid.price, type: 'buy', size: bid.size });
            }
        });
        return newWalls;
    }, [walls, bids, asks, volumeThreshold]);

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
                    <HeatmapSymbolSelector symbol={symbol} exchange={exchange} onSymbolChange={setSymbol} onExchangeChange={setExchange} />
                    <TimeframeSelector interval={interval} onIntervalChange={setInterval} />
                    <IndicatorSelector settings={indicatorSettings} onSettingsChange={setIndicatorSettings} />
                    <VolumeFilterControl threshold={volumeThreshold} onThresholdChange={setVolumeThreshold} />
                    <span className="text-lg font-mono font-bold text-gray-800 dark:text-white">
                        {formatDisplayPrice(currentPrice)}
                    </span>
                </div>
                <div className="flex gap-2">
                    <span className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-lg bg-green-500/10 text-green-500 border border-green-500/20">
                        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                        Live Data Socket
                    </span>
                    <button
                        onClick={() => setShowFootprint(!showFootprint)}
                        className={`text-xs font-semibold px-4 py-2 rounded-lg border transition-all ${showFootprint
                            ? 'bg-brand-primary text-white border-brand-primary shadow-[0_0_15px_rgba(59,130,246,0.3)]'
                            : 'bg-white dark:bg-black/20 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-white/10 hover:bg-gray-50 dark:hover:bg-white/5'}`}
                    >
                        {showFootprint ? 'Hide Footprint' : 'Show Footprint'}
                    </button>
                </div>
            </header>
            <div className="flex-1 p-4 overflow-hidden bg-gray-50 dark:bg-[#050B14]">
                <div className="flex flex-row h-full gap-4">
                    <div className="w-[70%] bg-white dark:bg-[#0B1120] rounded-xl border border-gray-200 dark:border-white/5 overflow-hidden shadow-[0_4px_20px_rgba(0,0,0,0.05)] dark:shadow-[0_4px_20px_rgba(0,0,0,0.2)] flex flex-col">
                        <div className="p-3 border-b border-gray-200 dark:border-white/5 flex justify-between items-center">
                            <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Order Flow Chart</h3>
                        </div>
                        <div className="flex-1 relative">
                            <OrderFlowChart exchange={exchange} symbol={symbol} interval={interval} walls={filteredWalls} currentPrice={currentPrice} showFootprint={showFootprint} indicatorSettings={indicatorSettings} />
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
