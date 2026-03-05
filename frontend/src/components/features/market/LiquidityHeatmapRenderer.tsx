import React, { useEffect, useRef } from 'react';
import { IChartApi, ISeriesApi } from 'lightweight-charts';

export interface HeatmapDataPoint {
    time: number; // Unix timestamp
    levels: { price: number; volume: number; type: 'bid' | 'ask' }[];
}

interface LiquidityHeatmapRendererProps {
    chart: IChartApi | null;
    series: ISeriesApi<'Candlestick'> | null;
    data: HeatmapDataPoint[];
}

export const LiquidityHeatmapRenderer: React.FC<LiquidityHeatmapRendererProps> = ({ chart, series, data }) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        if (!chart || !series || !canvasRef.current || data.length === 0) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let animationFrameId: number;

        const drawHeatmap = () => {
            // get exact dimensions from time scale and price scale
            const timeScale = chart.timeScale();
            const priceScale = series.priceScale();

            // Sync canvas size to fit the chart pane
            const timeWidth = timeScale.width();
            const priceHeight = canvas.parentElement?.clientHeight || 0;

            // Match exact bounding box of chart container to cover the main pane correctly
            const parent = canvas.parentElement;
            if (parent) {
                if (canvas.width !== parent.clientWidth) canvas.width = parent.clientWidth;
                if (canvas.height !== parent.clientHeight) canvas.height = parent.clientHeight;
            }

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            const logicalRange = timeScale.getVisibleLogicalRange();
            if (!logicalRange) return;

            // Global or local max? We use visible range max for dynamic contrast
            let maxVol = 1;
            const fromIdx = Math.max(0, Math.floor(logicalRange.from || 0));
            const toIdx = Math.min(data.length - 1, Math.ceil(logicalRange.to || data.length - 1));

            for (let i = fromIdx; i <= toIdx; i++) {
                if (data[i]) {
                    for (const lv of data[i].levels) {
                        maxVol = Math.max(maxVol, lv.volume);
                    }
                }
            }

            // Small caching of scaled time points
            const len = data.length;

            // Use alpha composition for blending over candles
            ctx.globalCompositeOperation = 'source-over';

            for (let i = fromIdx - 5; i <= toIdx + 5; i++) {
                if (i < 0 || i >= len) continue;

                const pt = data[i];
                const x = timeScale.timeToCoordinate(pt.time as any);
                if (x === null) continue;

                let nextX = x + (timeWidth / (toIdx - fromIdx + 1)); // Default width estimate
                if (i < len - 1) {
                    const nx = timeScale.timeToCoordinate(data[i + 1].time as any);
                    if (nx !== null) nextX = nx;
                }
                const barWidth = Math.max(1.5, Math.abs(nextX - x));

                for (let j = 0; j < pt.levels.length; j++) {
                    const level = pt.levels[j];
                    const y = series.priceToCoordinate(level.price);
                    if (y === null) continue;

                    const intensity = level.volume / maxVol;
                    if (intensity < 0.05) continue; // Skip very low liquidity to keep clean

                    // Gradient color mapping
                    let r, g, b, a;
                    if (intensity < 0.5) {
                        r = 239; g = 68; b = 68; // Red
                        a = intensity * 2 * 0.4; // Max 0.4 opacity for lower half
                    } else if (intensity < 0.8) {
                        r = 249; g = 115; b = 22; // Orange
                        a = 0.4 + (intensity - 0.5) * 2 * 0.4; // Max 0.8 opacity
                    } else {
                        r = 253; g = 224; b = 71; // Yellow
                        a = 0.8 + (intensity - 0.8) * 5 * 0.2; // Max 1.0 opacity
                    }

                    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${a})`;

                    // Fixed height for better visibility at all scales
                    const cellHeight = 4;

                    // Only draw inside main pane width (avoid painting over scales on right)
                    if (x >= -barWidth && x <= timeWidth) {
                        ctx.fillRect(Math.floor(x - barWidth / 2), Math.floor(y - cellHeight / 2), Math.ceil(barWidth), cellHeight);
                    }
                }
            }
        };

        const renderLoop = () => {
            drawHeatmap();
            animationFrameId = requestAnimationFrame(renderLoop);
        };
        renderLoop();

        return () => {
            cancelAnimationFrame(animationFrameId);
        };
    }, [chart, series, data]);

    return (
        <canvas
            ref={canvasRef}
            className="absolute top-0 left-0 pointer-events-none"
            style={{ zIndex: 1 }}
        />
    );
};
