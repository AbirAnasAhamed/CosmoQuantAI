import React, { useEffect, useState, useRef } from 'react';
import { IChartApi, ISeriesApi } from 'lightweight-charts';

export interface FootprintDataTick {
    price: number;
    bidVolume: number;
    askVolume: number;
    isImbalance?: boolean;
}

export interface FootprintCandleData {
    time: number;
    high: number;
    low: number;
    ticks: FootprintDataTick[];
}

interface FootprintRendererProps {
    chart: IChartApi | null;
    series: ISeriesApi<'Candlestick'> | null;
    data: FootprintCandleData[];
    visible: boolean;
}

export const FootprintRenderer: React.FC<FootprintRendererProps> = ({ chart, series, data, visible }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [renderData, setRenderData] = useState<{ x: number; y: number; price: number; bid: number; ask: number; isImbalance: boolean }[]>([]);

    useEffect(() => {
        if (!chart || !series || !visible || data.length === 0) {
            setRenderData([]);
            return;
        }

        const updatePositions = () => {
            if (!chart || !series || !containerRef.current) return;

            const timeScale = chart.timeScale();
            const logicalRange = timeScale.getVisibleLogicalRange();
            if (!logicalRange) return;

            const newRenderData: { x: number; y: number; price: number; bid: number; ask: number; isImbalance: boolean }[] = [];

            // Only process data within the visible logical range to save performance
            const startIndex = Math.max(0, Math.floor(logicalRange.from) - 5);
            const endIndex = Math.min(data.length - 1, Math.ceil(logicalRange.to) + 5);

            for (let i = startIndex; i <= endIndex; i++) {
                const candle = data[i];
                if (!candle) continue;

                const x = timeScale.timeToCoordinate(candle.time as any);
                if (x === null) continue;

                candle.ticks.forEach(tick => {
                    const y = series.priceToCoordinate(tick.price);
                    if (y === null) return;

                    newRenderData.push({
                        x,
                        y,
                        price: tick.price,
                        bid: tick.bidVolume,
                        ask: tick.askVolume,
                        isImbalance: !!tick.isImbalance
                    });
                });
            }

            setRenderData(newRenderData);
        };

        updatePositions();

        chart.timeScale().subscribeVisibleTimeRangeChange(updatePositions);
        chart.timeScale().subscribeVisibleLogicalRangeChange(updatePositions);

        // Also need to subscribe to price scale changes if user drags vertically
        const interval = setInterval(updatePositions, 100);

        return () => {
            chart.timeScale().unsubscribeVisibleTimeRangeChange(updatePositions);
            chart.timeScale().unsubscribeVisibleLogicalRangeChange(updatePositions);
            clearInterval(interval);
        };
    }, [chart, series, data, visible]);

    if (!visible || !chart || !series) return null;

    return (
        <div
            ref={containerRef}
            className="absolute inset-0 pointer-events-none z-20 overflow-hidden"
            style={{ right: 60, bottom: 26 }} // Account for scales
        >
            {renderData.map((d, i) => (
                <div
                    key={i}
                    className="absolute flex items-center justify-center font-mono text-[9px] font-bold leading-none transform -translate-x-1/2 -translate-y-1/2 bg-black/40 px-1 rounded backdrop-blur-sm whitespace-nowrap"
                    style={{
                        left: `${d.x}px`,
                        top: `${d.y}px`,
                        color: d.isImbalance ? '#fbbf24' : '#e2e8f0', // yellow-400 for imbalance, slate-200 normal
                        border: d.isImbalance ? '1px solid rgba(251, 191, 36, 0.5)' : 'none',
                    }}
                >
                    <span className="text-red-400">{d.bid.toFixed(0)}</span>
                    <span className="mx-[2px] text-gray-400">x</span>
                    <span className="text-green-400">{d.ask.toFixed(0)}</span>
                </div>
            ))}
        </div>
    );
};
