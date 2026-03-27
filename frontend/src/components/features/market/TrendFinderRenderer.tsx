import React, { useEffect, useRef, useCallback } from 'react';
import { IChartApi, ISeriesApi, LineSeries } from 'lightweight-charts';
import { TrendFinderResult } from '../../../utils/indicators';

interface TrendFinderRendererProps {
    chart: IChartApi | null;
    series: ISeriesApi<'Candlestick'> | null;
    data: TrendFinderResult | null;
    visible: boolean;
}

export const TrendFinderRenderer: React.FC<TrendFinderRendererProps> = ({ chart, series, data, visible }) => {
    const midlineRef = useRef<ISeriesApi<'Line'> | null>(null);
    const upperLineRef = useRef<ISeriesApi<'Line'> | null>(null);
    const lowerLineRef = useRef<ISeriesApi<'Line'> | null>(null);
    const initedRef = useRef(false);
    
    // Canvas variables for Cloud Fill
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const drawRequested = useRef<boolean>(false);

    useEffect(() => {
        if (!chart || !series) return;

        if (!initedRef.current) {
            midlineRef.current = chart.addSeries(LineSeries, {
                color: 'rgba(59, 130, 246, 0.8)', // Blue
                lineWidth: 2,
                lineStyle: 2, // Dashed
                crosshairMarkerVisible: false,
                lastValueVisible: false,
                priceLineVisible: false,
            });

            upperLineRef.current = chart.addSeries(LineSeries, {
                color: 'rgba(156, 163, 175, 0.4)', // Gray
                lineWidth: 1,
                lineStyle: 0, // Solid
                crosshairMarkerVisible: false,
                lastValueVisible: false,
                priceLineVisible: false,
            });

            lowerLineRef.current = chart.addSeries(LineSeries, {
                color: 'rgba(156, 163, 175, 0.4)', // Gray
                lineWidth: 1,
                lineStyle: 0, // Solid
                crosshairMarkerVisible: false,
                lastValueVisible: false,
                priceLineVisible: false,
            });

            initedRef.current = true;
        }

        return () => {
            if (chart && initedRef.current) {
                if (midlineRef.current) {
                    try { chart.removeSeries(midlineRef.current); } catch(e) {}
                    midlineRef.current = null;
                }
                if (upperLineRef.current) {
                    try { chart.removeSeries(upperLineRef.current); } catch(e) {}
                    upperLineRef.current = null;
                }
                if (lowerLineRef.current) {
                    try { chart.removeSeries(lowerLineRef.current); } catch(e) {}
                    lowerLineRef.current = null;
                }
                initedRef.current = false;
            }
        };
    }, [chart, series]);

    useEffect(() => {
        if (!visible || !data || !initedRef.current) {
            midlineRef.current?.setData([]);
            upperLineRef.current?.setData([]);
            lowerLineRef.current?.setData([]);
            return;
        }

        try {
            const validPoints = data.points.filter((p: any) => 
                p && p.time && 
                !isNaN(p.value) && isFinite(p.value) &&
                !isNaN(p.upper) && isFinite(p.upper) &&
                !isNaN(p.lower) && isFinite(p.lower)
            );

            // Deduplicate by time and ensure strict ascending order
            const deduplicated: any[] = [];
            const seenTimes = new Set<number>();
            
            for (const p of validPoints) {
                const t = Number(p.time);
                if (!seenTimes.has(t)) {
                    seenTimes.add(t);
                    deduplicated.push(p);
                }
            }
            
            deduplicated.sort((a, b) => Number(a.time) - Number(b.time));

            if (deduplicated.length > 0) {
                const midData = deduplicated.map(p => ({ time: p.time as any, value: p.value }));
                const upperData = deduplicated.map(p => ({ time: p.time as any, value: p.upper }));
                const lowerData = deduplicated.map(p => ({ time: p.time as any, value: p.lower }));

                midlineRef.current?.setData(midData);
                upperLineRef.current?.setData(upperData);
                lowerLineRef.current?.setData(lowerData);
            } else {
                midlineRef.current?.setData([]);
                upperLineRef.current?.setData([]);
                lowerLineRef.current?.setData([]);
            }
        } catch (err) {
            console.error('[TrendFinderRenderer] Error setting data:', err);
        }

    }, [data, visible]);

    // --- CANVAS CLOUD FILL LOGIC ---
    
    const drawCloud = useCallback(() => {
        if (!canvasRef.current) return;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (!chart || !series || !visible || !data || data.points.length === 0) return;

        const timeScale = chart.timeScale();
        const priceScale = series.priceScale();
        if (!timeScale || !priceScale) return;

        const parent = canvas.parentElement;
        if (parent) {
            if (canvas.width !== parent.clientWidth) canvas.width = parent.clientWidth;
            if (canvas.height !== parent.clientHeight) canvas.height = parent.clientHeight;
        }

        const logicalRange = timeScale.getVisibleLogicalRange();
        if (!logicalRange) return;

        const isBearish = data.trendDirection === 'bearish';
        ctx.fillStyle = isBearish ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)';

        ctx.beginPath();
        let started = false;
        
        // 1. Draw top band going FORWARDS
        for (let i = 0; i < data.points.length; i++) {
            const pt = data.points[i];
            const x = timeScale.timeToCoordinate(pt.time as any);
            const yTop = series.priceToCoordinate(pt.upper);
            if (x !== null && yTop !== null) {
                if (!started) {
                    ctx.moveTo(x, yTop);
                    started = true;
                } else {
                    ctx.lineTo(x, yTop);
                }
            }
        }
        
        // 2. Draw bottom band going BACKWARDS
        for (let i = data.points.length - 1; i >= 0; i--) {
            const pt = data.points[i];
            const x = timeScale.timeToCoordinate(pt.time as any);
            const yBot = series.priceToCoordinate(pt.lower);
            if (x !== null && yBot !== null) {
                ctx.lineTo(x, yBot);
            }
        }
        
        if (started) {
            ctx.closePath();
            ctx.fill();
        }
    }, [chart, series, data, visible]);

    const requestDraw = useCallback(() => {
        if (!drawRequested.current) {
            drawRequested.current = true;
            requestAnimationFrame(() => {
                drawRequested.current = false;
                drawCloud();
            });
        }
    }, [drawCloud]);

    useEffect(() => {
        if (!chart || !series || !visible) {
            if (canvasRef.current) {
                const ctx = canvasRef.current.getContext('2d');
                if (ctx) ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
            }
            return;
        }
        requestDraw();
        const timeScale = chart.timeScale();
        timeScale.subscribeVisibleTimeRangeChange(requestDraw);
        chart.subscribeCrosshairMove(requestDraw);
        return () => {
            timeScale.unsubscribeVisibleTimeRangeChange(requestDraw);
            chart.unsubscribeCrosshairMove(requestDraw);
        };
    }, [chart, series, requestDraw, visible]);

    return (
        <canvas
            ref={canvasRef}
            className="absolute top-0 left-0 pointer-events-none"
            style={{ zIndex: 1,  width: '100%', height: '100%' }}
        />
    );
};
