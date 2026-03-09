import React, { useEffect, useRef, useMemo, useState } from 'react';
import { createChart, ISeriesApi, CandlestickData, CandlestickSeries, LineSeries, HistogramSeries, HistogramData, createSeriesMarkers } from 'lightweight-charts';
import { useLevel2MarketData } from '@/hooks/useLevel2MarketData';
import { useOrderFlowData } from '../../hooks/useOrderFlowData';
import { useHeatmapData } from '../../hooks/useHeatmapData';
import { useVolumeFilter } from '../../hooks/useVolumeFilter';
import { marketDepthService } from '../../services/marketDepthService';
import { HeatmapSymbolSelector } from '../../components/features/market/HeatmapSymbolSelector';
import { TimeframeSelector } from '../../components/features/market/TimeframeSelector';
import { VolumeFilterControl } from '../../components/features/market/VolumeFilterControl';
import { LiquidityHeatmapRenderer, HeatmapDataPoint } from '../../components/features/market/LiquidityHeatmapRenderer';
import { VolumeProfileWidget, VPVRData } from '../../components/features/market/VolumeProfileWidget';
import { CVDChart, CVDDataPoint } from '../../components/features/market/CVDChart';
import { FootprintRenderer, FootprintCandleData, FootprintDataTick } from '../../components/features/market/FootprintRenderer';
import { IndicatorSelector, IndicatorSettings } from '../../components/features/market/IndicatorSelector';
import { calculateEMA, calculateBollingerBands, calculateRSI } from '../../utils/indicators';
import { HeatmapSubNav } from '../../components/features/market/HeatmapSubNav';
import { BotSettingsTab } from '../../components/features/market/BotSettingsTab';
import { BotLogsTab } from '../../components/features/market/BotLogsTab';
import { WallHunterModal } from '../../components/features/market/WallHunterModal';
import { botService } from '../../services/botService';
import { useWallHunterStatus } from '@/hooks/useWallHunterStatus';

// Helper to convert interval string to ms
const parseIntervalToMs = (interval: string): number => {
    const value = parseInt(interval) || 1;
    const unit = interval.replace(/[0-9]/g, '').toLowerCase() || 'm';
    switch (unit) {
        case 'm': return value * 60 * 1000;
        case 'h': return value * 60 * 60 * 1000;
        case 'd': return value * 24 * 60 * 60 * 1000;
        case 'w': return value * 7 * 24 * 60 * 60 * 1000;
        default: return value * 60 * 1000; // default to minutes
    }
};

// Chart Component
const OrderFlowChart: React.FC<{ exchange: string; symbol: string; interval: string; walls: { price: number, type: 'buy' | 'sell' }[]; currentPrice: number; showFootprint: boolean; indicatorSettings: IndicatorSettings; tradeEvent: any; botStatus: any }> = ({ exchange, symbol, interval, walls, currentPrice, showFootprint, indicatorSettings, tradeEvent, botStatus }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<any>(null);
    const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
    const emaSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
    const bbUpperSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
    const bbMiddleSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
    const bbLowerSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
    const rsiSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
    const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
    const wallLinesRef = useRef<any[]>([]);
    const lastCandleRef = useRef<CandlestickData | null>(null);
    const allCandlesRef = useRef<any[]>([]);
    const lastTradeEventRef = useRef<any>(null);
    const lastProcessedPriceRef = useRef<number>(0);
    const prevPositionRef = useRef<boolean>(false);
    const markersRef = useRef<any[]>([]);
    const markersPluginRef = useRef<any>(null);
    const [countdownFormatted, setCountdownFormatted] = useState<string>('');
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
        const volumeSeries = chart.addSeries(HistogramSeries, {
            color: '#26a69a',
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: 'volume', // Give it a separate scale
        });

        // Configure the volume price scale
        chart.priceScale('volume').applyOptions({
            scaleMargins: {
                top: 0.8, // dock to bottom 20%
                bottom: 0,
            },
            visible: false, // Don't show volume numbers on the axis to reduce clutter
        });

        chartRef.current = chart;
        candlestickSeriesRef.current = candlestickSeries;
        markersPluginRef.current = createSeriesMarkers(candlestickSeries, []);
        emaSeriesRef.current = emaSeries;
        bbUpperSeriesRef.current = bbUpperSeries;
        bbMiddleSeriesRef.current = bbMiddleSeries;
        bbLowerSeriesRef.current = bbLowerSeries;
        rsiSeriesRef.current = rsiSeries;
        volumeSeriesRef.current = volumeSeries;

        // Fetch real historical data
        const fetchKlines = async () => {
            try {
                const data = await marketDepthService.getOHLCV(
                    symbol.toUpperCase(),
                    exchange,
                    interval,
                    200
                );
                const candles = data.map((k: any) => ({
                    time: k.time as any,
                    open: parseFloat(k.open),
                    high: parseFloat(k.high),
                    low: parseFloat(k.low),
                    close: parseFloat(k.close),
                    volume: parseFloat(k.volume || 100),
                }));
                if (candlestickSeriesRef.current) {
                    candlestickSeriesRef.current.setData(candles);
                    allCandlesRef.current = candles;
                    if (candles.length > 0) {
                        lastCandleRef.current = { ...candles[candles.length - 1] };
                    }

                    // Format and set volume data
                    if (volumeSeriesRef.current) {
                        const volumeData = candles.map((k: any) => ({
                            time: k.time,
                            value: k.volume,
                            color: k.close >= k.open ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)'
                        }));
                        volumeSeriesRef.current.setData(volumeData);
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

        if (volumeSeriesRef.current) {
            volumeSeriesRef.current.applyOptions({ visible: indicatorSettings.showVolume });
        }

    }, [indicatorSettings, allCandlesRef.current]);

    // Real-time candle update
    useEffect(() => {
        if (!candlestickSeriesRef.current || !lastCandleRef.current) return;

        let needsUpdate = false;
        let isNewCandle = false;
        const lastCandle = lastCandleRef.current as any;
        let newClose = lastCandle.close;
        let newHigh = lastCandle.high;
        let newLow = lastCandle.low;
        let newVolume = lastCandle.volume || 0;
        let eventTimestamp = Date.now();

        // Update from exact trades (gives us volume and exact price)
        if (tradeEvent && tradeEvent !== lastTradeEventRef.current) {
            newClose = tradeEvent.price;
            newHigh = Math.max(newHigh, tradeEvent.price);
            newLow = Math.min(newLow, tradeEvent.price);
            newVolume += tradeEvent.volume;
            eventTimestamp = tradeEvent.timestamp || Date.now();
            lastTradeEventRef.current = tradeEvent;
            needsUpdate = true;
        }

        // Update from order book tick (mid-price update)
        if (currentPrice && currentPrice !== lastProcessedPriceRef.current) {
            newClose = currentPrice;
            newHigh = Math.max(newHigh, currentPrice);
            newLow = Math.min(newLow, currentPrice);
            lastProcessedPriceRef.current = currentPrice;
            needsUpdate = true;
        }

        if (needsUpdate) {
            const intervalMs = parseIntervalToMs(interval);
            let candleTimeMs = lastCandle.time as number;
            const isSeconds = candleTimeMs < 10000000000;
            if (isSeconds) {
                candleTimeMs *= 1000;
            }

            let updatedCandle: any;

            if (eventTimestamp >= candleTimeMs + intervalMs) {
                // Crosses the timeframe boundary, create a new candle
                const nextCandleTimeMs = Math.floor(eventTimestamp / intervalMs) * intervalMs;
                updatedCandle = {
                    time: isSeconds ? Math.floor(nextCandleTimeMs / 1000) : nextCandleTimeMs,
                    open: lastCandle.close,
                    high: tradeEvent ? tradeEvent.price : currentPrice,
                    low: tradeEvent ? tradeEvent.price : currentPrice,
                    close: tradeEvent ? tradeEvent.price : currentPrice,
                    volume: tradeEvent ? tradeEvent.volume : 0,
                };
                isNewCandle = true;
            } else {
                // Update existing candle
                updatedCandle = {
                    ...lastCandle,
                    close: newClose,
                    high: newHigh,
                    low: newLow,
                    volume: newVolume,
                };
            }

            try {
                candlestickSeriesRef.current.update(updatedCandle);
                lastCandleRef.current = updatedCandle;

                // Update real-time volume
                if (volumeSeriesRef.current) {
                    volumeSeriesRef.current.update({
                        time: updatedCandle.time,
                        value: updatedCandle.volume,
                        color: updatedCandle.close >= updatedCandle.open ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)'
                    });
                }

                // Update allCandles array so indicators can respond if needed
                const len = allCandlesRef.current.length;
                if (isNewCandle) {
                    allCandlesRef.current.push(updatedCandle);
                } else if (len > 0 && allCandlesRef.current[len - 1].time === updatedCandle.time) {
                    allCandlesRef.current[len - 1] = updatedCandle;
                }
            } catch (e) {
                console.error("Failed to update realtime candle", e);
            }
        }
    }, [currentPrice, tradeEvent, interval]);

    // Update horizontal price lines for walls
    useEffect(() => {
        if (!candlestickSeriesRef.current || !chartRef.current) return;

        // Helper to draw lines
        const drawLines = () => {
            // Remove old lines
            wallLinesRef.current.forEach(line => {
                try { candlestickSeriesRef.current?.removePriceLine(line); } catch (e) { }
            });
            wallLinesRef.current = [];

            // Add Wall Lines
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

            // Add Active Bot Lines
            if (botStatus && botStatus.position) {
                if (botStatus.entry_price && botStatus.entry_price > 0) {
                    const epLine = candlestickSeriesRef.current?.createPriceLine({
                        price: botStatus.entry_price,
                        color: '#f59e0b', // Golden
                        lineWidth: 2,
                        lineStyle: 2, // Dashed
                        axisLabelVisible: true,
                        title: 'BOT ENTRY',
                    });
                    if (epLine) wallLinesRef.current.push(epLine);
                }
                if (botStatus.tp_price && botStatus.tp_price > 0) {
                    const tpLine = candlestickSeriesRef.current?.createPriceLine({
                        price: botStatus.tp_price,
                        color: '#22c55e', // Green
                        lineWidth: 2,
                        lineStyle: 1, // Dotted
                        axisLabelVisible: true,
                        title: 'BOT TP',
                    });
                    if (tpLine) wallLinesRef.current.push(tpLine);
                }
                if (botStatus.sl_price && botStatus.sl_price > 0) {
                    const slLine = candlestickSeriesRef.current?.createPriceLine({
                        price: botStatus.sl_price,
                        color: '#ef4444', // Red
                        lineWidth: 2,
                        lineStyle: 1, // Dotted
                        axisLabelVisible: true,
                        title: 'BOT TSL',
                    });
                    if (slLine) wallLinesRef.current.push(slLine);
                }
            }
        };

        drawLines();

        // Redraw periodically to ensure they aren't wiped out by lightweight-charts internal redraws
        const drawInterval = setInterval(drawLines, 2000);
        return () => clearInterval(drawInterval);

    }, [walls, botStatus]);

    // Update Trade Markers
    useEffect(() => {
        if (!botStatus || !candlestickSeriesRef.current || !lastCandleRef.current) return;

        const isPositionOpen = botStatus.position;
        const wasPositionOpen = prevPositionRef.current;

        if (isPositionOpen && !wasPositionOpen) {
            markersRef.current.push({
                time: lastCandleRef.current.time,
                position: 'belowBar',
                color: '#22c55e',
                shape: 'arrowUp',
                text: 'BUY',
            });
            // Sort markers by time as required by lightweight-charts
            markersRef.current.sort((a, b) => a.time - b.time);
            markersPluginRef.current?.setMarkers(markersRef.current);
        } else if (!isPositionOpen && wasPositionOpen) {
            markersRef.current.push({
                time: lastCandleRef.current.time,
                position: 'aboveBar',
                color: '#ef4444',
                shape: 'arrowDown',
                text: 'SELL',
            });
            markersRef.current.sort((a, b) => a.time - b.time);
            markersPluginRef.current?.setMarkers(markersRef.current);
        }

        prevPositionRef.current = isPositionOpen;
    }, [botStatus]);

    // Countdown Timer logic
    useEffect(() => {
        const intervalMs = parseIntervalToMs(interval);

        const tick = () => {
            const now = Date.now();
            let remaining = 0;

            if (lastCandleRef.current && lastCandleRef.current.time) {
                let candleTimeMs = lastCandleRef.current.time as number;
                // If the timestamp is in seconds, convert to ms
                if (candleTimeMs < 10000000000) {
                    candleTimeMs = candleTimeMs * 1000;
                }
                const nextCandleTimeMs = candleTimeMs + intervalMs;
                remaining = nextCandleTimeMs - now;
            } else {
                const nextBoundary = Math.ceil(now / intervalMs) * intervalMs;
                remaining = nextBoundary - now;
            }

            if (remaining < 0) remaining = 0;

            const h = Math.floor(remaining / (1000 * 60 * 60));
            const m = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));
            const s = Math.floor((remaining % (1000 * 60)) / 1000);

            if (h > 0) {
                setCountdownFormatted(`${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`);
            } else {
                setCountdownFormatted(`${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`);
            }
        };

        tick();
        const timerId = setInterval(tick, 1000);
        return () => clearInterval(timerId);
    }, [interval]);

    return (
        <div className="w-full h-full flex flex-col absolute inset-0">
            <div className="flex-1 relative">
                <div ref={chartContainerRef} className="w-full h-full absolute inset-0 z-0" />
                <div className="absolute inset-0 z-10 pointer-events-none overflow-hidden" style={{ right: 60, bottom: 26 }}>
                    <LiquidityHeatmapRenderer chart={chartRef.current} series={candlestickSeriesRef.current} data={realHeatmapData} />
                    {showFootprint && <FootprintRenderer chart={chartRef.current} series={candlestickSeriesRef.current} data={footprintData} visible={showFootprint} />}
                </div>
                <VolumeProfileWidget chart={chartRef.current} series={candlestickSeriesRef.current} data={vpvrData} />
                {countdownFormatted && (
                    <div className="absolute bottom-[40px] right-[75px] z-20 pointer-events-none bg-black/60 dark:bg-black/60 border border-white/10 text-[#d1d5db] text-[20px] font-mono font-bold px-3 py-1.5 rounded shadow-lg backdrop-blur-md">
                        {countdownFormatted}
                    </div>
                )}
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
    const [activeTab, setActiveTab] = useState<'heatmap' | 'bot_settings' | 'bot_logs'>('heatmap');
    const [isWallHunterOpen, setIsWallHunterOpen] = useState(false);
    const [activeWallHunterId, setActiveWallHunterId] = useState<number | null>(null);
    const [exchange, setExchange] = useState('binance');
    const [symbol, setSymbol] = useState('DOGE/USDT');
    const [interval, setInterval] = useState('1m');
    const [showFootprint, setShowFootprint] = useState(false);
    const [indicatorSettings, setIndicatorSettings] = useState<IndicatorSettings>({
        showEMA: false,
        showBB: false,
        showRSI: false,
        showVolume: true,
        emaPeriod: 20,
        bbPeriod: 20,
        bbStdDev: 2,
        rsiPeriod: 14,
    });
    const { bids, asks, walls, currentPrice, tradeEvent } = useLevel2MarketData(symbol, exchange);
    const { volumeThreshold, setVolumeThreshold } = useVolumeFilter(1000);
    const { statusData: botStatus, isConnected: botWsConnected } = useWallHunterStatus(activeWallHunterId);

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
            <header className="relative z-40 flex-shrink-0 p-4 border-b border-gray-200 dark:border-white/10 flex justify-between items-center bg-white dark:bg-[#0B1120]">
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
                    <span className={`flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-lg border transition-colors ${botWsConnected ? 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20' : 'bg-green-500/10 text-green-500 border-green-500/20'}`}>
                        <span className={`w-2 h-2 rounded-full animate-pulse ${botWsConnected ? 'bg-indigo-500' : 'bg-green-500'}`}></span>
                        {botWsConnected ? `Bot ${activeWallHunterId} Connected` : 'Live Data Socket'}
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

            <HeatmapSubNav activeTab={activeTab} onChange={setActiveTab} />

            <div className="flex-1 p-4 overflow-hidden relative bg-gray-50 dark:bg-[#050B14]">
                {/* ALWAYS RENDER HEATMAP */}
                <div className="flex flex-row h-full gap-4">
                    <div className="w-[70%] bg-white dark:bg-[#0B1120] rounded-xl border border-gray-200 dark:border-white/5 overflow-hidden shadow-[0_4px_20px_rgba(0,0,0,0.05)] dark:shadow-[0_4px_20px_rgba(0,0,0,0.2)] flex flex-col">
                        <div className="p-3 border-b border-gray-200 dark:border-white/5 flex justify-between items-center">
                            <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Order Flow Chart</h3>
                        </div>
                        <div className="flex-1 relative">
                            <OrderFlowChart exchange={exchange} symbol={symbol} interval={interval} walls={filteredWalls} currentPrice={currentPrice} showFootprint={showFootprint} indicatorSettings={indicatorSettings} tradeEvent={tradeEvent} botStatus={botStatus} />
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

                {/* ACTIVE BOT STATUS HUD */}
                {activeWallHunterId && botStatus && (
                    <div className="absolute top-6 right-6 z-50 pointer-events-none">
                        <div className="bg-white/10 dark:bg-black/40 backdrop-blur-xl border border-white/20 dark:border-white/10 p-4 rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.3)] w-64">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2 flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${botStatus.position ? 'bg-yellow-400 animate-pulse' : 'bg-indigo-500 animate-pulse'}`}></span>
                                {botStatus.position ? 'In Trade' : 'Monitoring L2 Wall'}
                            </h4>
                            <div className="flex flex-col gap-2">
                                <div className="flex justify-between items-center bg-black/20 p-2 rounded-lg border border-white/5">
                                    <span className="text-gray-400 font-mono text-xs">Unrealized PnL:</span>
                                    <span className={`font-mono font-bold text-lg ${botStatus.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                        ${botStatus.pnl.toFixed(2)} ({botStatus.pnl_percent > 0 ? '+' : ''}{botStatus.pnl_percent.toFixed(2)}%)
                                    </span>
                                </div>
                                {botStatus.position && (
                                    <>
                                        <div className="flex justify-between text-xs font-mono">
                                            <span className="text-gray-500">Target TP:</span>
                                            <span className="text-green-400 font-bold">{formatDisplayPrice(botStatus.tp_price)}</span>
                                        </div>
                                        <div className="flex justify-between text-xs font-mono">
                                            <span className="text-gray-500">Trailing SL:</span>
                                            <span className="text-red-400 font-bold">{formatDisplayPrice(botStatus.sl_price)}</span>
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* BOT SETTINGS MODAL */}
                {activeTab === 'bot_settings' && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                        <div className="relative w-[90%] md:w-[70%] lg:w-[60%] max-w-4xl max-h-[90vh] bg-white dark:bg-[#0B1120] rounded-xl shadow-2xl border border-gray-200 dark:border-white/10 overflow-hidden flex flex-col transform transition-all scale-100">
                            <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-white/10 shrink-0">
                                <h2 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-brand-primary to-purple-500">OrderBlockBot Configuration</h2>
                                <button
                                    onClick={() => setActiveTab('heatmap')}
                                    className="p-2 text-gray-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                                </button>
                            </div>
                            <div className="flex-1 overflow-y-auto custom-scrollbar relative">
                                <BotSettingsTab />
                            </div>
                        </div>
                    </div>
                )}

                {/* BOT LOGS MODAL */}
                {activeTab === 'bot_logs' && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                        <div className="relative w-[90%] md:w-[70%] lg:w-[60%] max-w-4xl max-h-[90vh] bg-white dark:bg-[#0B1120] rounded-xl shadow-2xl border border-gray-200 dark:border-white/10 overflow-hidden flex flex-col transform transition-all scale-100">
                            <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-white/10 shrink-0">
                                <h2 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-brand-primary to-purple-500">OrderBlockBot Terminal Logs</h2>
                                <button
                                    onClick={() => setActiveTab('heatmap')}
                                    className="p-2 text-gray-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                                </button>
                            </div>
                            <div className="flex-1 overflow-y-auto custom-scrollbar relative">
                                <BotLogsTab />
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* WALLHUNTER FLOATING ACTION BUTTON */}
            {activeWallHunterId ? (
                <button
                    onClick={async () => {
                        try {
                            await botService.controlBot(activeWallHunterId, 'stop');
                            setActiveWallHunterId(null);
                        } catch (err) {
                            console.error("Failed to stop WallHunter bot", err);
                        }
                    }}
                    className="fixed bottom-8 right-8 z-[100] group"
                    title="Abort WallHunter"
                >
                    <div className="absolute inset-0 bg-red-500 rounded-full blur-xl opacity-40 group-hover:opacity-100 transition-opacity animate-pulse" />
                    <div className="relative w-16 h-16 bg-gradient-to-br from-red-500 to-red-700 rounded-full flex items-center justify-center border-4 border-white/20 shadow-[0_0_30px_rgba(239,68,68,0.5)] group-hover:scale-110 transition-transform cursor-pointer">
                        <svg className="w-8 h-8 text-white group-hover:rotate-180 transition-transform duration-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </div>
                </button>
            ) : (
                <button
                    onClick={() => setIsWallHunterOpen(true)}
                    className="fixed bottom-8 right-8 z-[100] group"
                    title="Deploy WallHunter"
                >
                    <div className="absolute inset-0 bg-yellow-500 rounded-full blur-xl opacity-40 group-hover:opacity-100 transition-opacity animate-pulse" />
                    <div className="relative w-16 h-16 bg-gradient-to-br from-yellow-400 to-orange-600 rounded-full flex items-center justify-center border-4 border-white/20 shadow-2xl group-hover:scale-110 transition-transform cursor-pointer">
                        <svg className="w-8 h-8 text-white group-hover:rotate-12 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                    </div>
                </button>
            )}

            <WallHunterModal
                isOpen={isWallHunterOpen}
                onClose={() => setIsWallHunterOpen(false)}
                symbol={symbol}
                bids={bids}
                asks={asks}
                onDeploySuccess={(botId) => {
                    setActiveWallHunterId(botId);
                    setIsWallHunterOpen(false);
                }}
            />
        </div>
    );
};

export default OrderFlowHeatmap;
