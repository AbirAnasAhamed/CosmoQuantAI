import React, { useEffect, useState, useRef } from 'react';
import { IChartApi, ISeriesApi } from 'lightweight-charts';

export interface VPVRData {
    price: number;
    volume: number;
    buyVolume: number;
    sellVolume: number;
}

interface VolumeProfileWidgetProps {
    chart: IChartApi | null;
    series: ISeriesApi<'Candlestick'> | null;
    data: VPVRData[];
}

export const VolumeProfileWidget: React.FC<VolumeProfileWidgetProps> = ({ chart, series, data }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [renderData, setRenderData] = useState<{ y: number; width: number; totalWidth: number; buyRatio: number; price: number }[]>([]);

    useEffect(() => {
        if (!chart || !series || data.length === 0) return;

        const updatePositions = () => {
            if (!chart || !series || !containerRef.current) return;

            const maxVol = Math.max(...data.map(d => d.volume), 1);

            const newData = data.map(d => {
                const y = series.priceToCoordinate(d.price);
                return {
                    y: y !== null ? y : -1,
                    price: d.price,
                    width: (d.volume / maxVol) * 100, // percentage max width
                    totalWidth: d.volume,
                    buyRatio: d.buyVolume / (d.volume || 1)
                };
            }).filter(d => d.y !== -1);

            setRenderData(newData);
        };

        updatePositions();

        // Subscribe to relevant chart events to update coordinates
        chart.timeScale().subscribeVisibleTimeRangeChange(updatePositions);
        chart.timeScale().subscribeVisibleLogicalRangeChange(updatePositions);
        chart.subscribeCrosshairMove(updatePositions);

        // Periodically poll to catch price scale animations
        const interval = setInterval(updatePositions, 100);

        return () => {
            chart.timeScale().unsubscribeVisibleTimeRangeChange(updatePositions);
            chart.timeScale().unsubscribeVisibleLogicalRangeChange(updatePositions);
            chart.unsubscribeCrosshairMove(updatePositions);
            clearInterval(interval);
        };
    }, [chart, series, data]);

    if (!chart || !series) return null;

    return (
        <div
            ref={containerRef}
            className="absolute top-0 right-[60px] w-[120px] h-full pointer-events-none z-10"
        >
            {renderData.map((d, i) => (
                <div
                    key={i}
                    className="absolute right-0 flex"
                    style={{
                        top: `${d.y - 4}px`,
                        height: '8px',
                        width: `${d.width}%`,
                        opacity: 0.6
                    }}
                >
                    <div
                        className="h-full bg-green-500"
                        style={{ width: `${d.buyRatio * 100}%` }}
                    />
                    <div
                        className="h-full bg-red-500"
                        style={{ width: `${(1 - d.buyRatio) * 100}%` }}
                    />
                </div>
            ))}
        </div>
    );
};
