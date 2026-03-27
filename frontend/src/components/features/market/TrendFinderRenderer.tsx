import React, { useEffect, useRef } from 'react';
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

    return null; // This is a virtual component that renders on canvas
};
