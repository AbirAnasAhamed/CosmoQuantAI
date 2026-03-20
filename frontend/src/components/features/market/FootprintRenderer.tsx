import React, { useEffect, useRef } from 'react';
import { IChartApi, ISeriesApi } from 'lightweight-charts';
import { formatFootprintVolume } from '../../../utils/volumeFormatter';

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
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        if (!visible || !chart || !series || !canvasRef.current || data.length === 0) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let animationFrameId: number;

        const drawFootprint = () => {
            const timeScale = chart.timeScale();
            const timeWidth = timeScale.width();

            // Sync canvas size to fit its own bounding box mapped to the inner pane space
            if (canvas.width !== canvas.clientWidth) canvas.width = canvas.clientWidth;
            if (canvas.height !== canvas.clientHeight) canvas.height = canvas.clientHeight;

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            const logicalRange = timeScale.getVisibleLogicalRange();
            if (!logicalRange) return;

            const fromIdx = Math.max(0, Math.floor(logicalRange.from || 0) - 5);
            const toIdx = Math.min(data.length - 1, Math.ceil(logicalRange.to || data.length - 1) + 5);

            ctx.font = 'bold 9px monospace';
            ctx.textBaseline = 'middle';

            // Optimization: Measure rough monospace char width once instead of thousands of times
            const charWidth = ctx.measureText("0").width;

            for (let i = fromIdx; i <= toIdx; i++) {
                if (!data[i]) continue;
                const candle = data[i];

                const x = timeScale.timeToCoordinate(candle.time as any);
                if (x === null) continue;

                // Optimization: Don't draw if clearly outside horizontal canvas area
                if (x < -100 || x > canvas.width + 100) continue;

                for (let j = 0; j < candle.ticks.length; j++) {
                    const tick = candle.ticks[j];
                    const y = series.priceToCoordinate(tick.price);
                    if (y === null) continue;

                    // Optimization: Don't draw if outside vertical canvas area
                    if (y < -20 || y > canvas.height + 20) continue;

                    const bidStr = formatFootprintVolume(tick.bidVolume);
                    const askStr = formatFootprintVolume(tick.askVolume);
                    const sepStr = ' x ';

                    const totalStrLength = bidStr.length + sepStr.length + askStr.length;
                    const textWidth = totalStrLength * charWidth;
                    const boxWidth = textWidth + 8; // 4px padding on each side
                    const boxHeight = 14;
                    const boxX = x - boxWidth / 2;
                    const boxY = y - boxHeight / 2;

                    // Draw Background
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
                    ctx.beginPath();
                    if (ctx.roundRect) {
                        ctx.roundRect(boxX, boxY, boxWidth, boxHeight, 2);
                    } else {
                        ctx.rect(boxX, boxY, boxWidth, boxHeight);
                    }
                    ctx.fill();

                    // Draw Imbalance Highlight
                    if (tick.isImbalance) {
                        ctx.strokeStyle = 'rgba(251, 191, 36, 0.5)';
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    }

                    // Draw Texts manually spaced out
                    let currentX = boxX + 4; // Add left padding origin
                    ctx.textAlign = 'left';

                    // Bid Volume (Red)
                    ctx.fillStyle = '#f87171';
                    ctx.fillText(bidStr, currentX, y);
                    currentX += bidStr.length * charWidth;

                    // Divider (Gray)
                    ctx.fillStyle = '#9ca3af';
                    ctx.fillText(sepStr, currentX, y);
                    currentX += sepStr.length * charWidth;

                    // Ask Volume (Green)
                    ctx.fillStyle = '#4ade80';
                    ctx.fillText(askStr, currentX, y);
                }
            }
        };

        const renderLoop = () => {
            drawFootprint();
            animationFrameId = requestAnimationFrame(renderLoop);
        };
        renderLoop();

        return () => {
            cancelAnimationFrame(animationFrameId);
        };
    }, [chart, series, data, visible]);

    if (!visible) return null;

    return (
        <canvas
            ref={canvasRef}
            className="absolute inset-0 pointer-events-none z-20"
            style={{ right: 60, bottom: 26 }} // Account for scales
        />
    );
};
