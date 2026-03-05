import { useState, useEffect } from 'react';
import api from '../services/api';
import { VPVRData } from '../components/features/market/VolumeProfileWidget';
import { CVDDataPoint } from '../components/features/market/CVDChart';
import { FootprintCandleData } from '../components/features/market/FootprintRenderer';
import { HeatmapDataPoint } from '../components/features/market/LiquidityHeatmapRenderer';

interface OrderFlowData {
    heatmapData: HeatmapDataPoint[];
    vpvrData: VPVRData[];
    cvdData: CVDDataPoint[];
    footprintData: FootprintCandleData[];
    loading: boolean;
    error: string | null;
}

export const useOrderFlowData = (symbol: string, exchange: string, interval: string): OrderFlowData => {
    const [heatmapData, setHeatmapData] = useState<HeatmapDataPoint[]>([]);
    const [vpvrData, setVpvrData] = useState<VPVRData[]>([]);
    const [cvdData, setCvdData] = useState<CVDDataPoint[]>([]);
    const [footprintData, setFootprintData] = useState<FootprintCandleData[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;

        const fetchOrderFlowData = async () => {
            if (!symbol || !exchange || !interval) return;

            setLoading(true);
            setError(null);

            try {
                const params = { symbol: symbol.toUpperCase(), exchange, interval, limit: 200 };

                // Fetch real historic klines and order book heatmap data
                const [klinesRes, heatmapRes] = await Promise.all([
                    api.get('/market-data/klines', { params }).catch(() => ({ data: [] })),
                    api.get('/market-depth/heatmap', { params: { symbol: symbol.toUpperCase(), exchange, bucket_size: 50.0, depth: 100 } }).catch(() => ({ data: { bids: [], asks: [] } }))
                ]);

                if (!isMounted) return;

                const rawKlines = klinesRes.data;
                const heatmap = heatmapRes.data?.bids ? [...heatmapRes.data.bids, ...heatmapRes.data.asks] : [];
                setHeatmapData(heatmap);

                if (rawKlines && rawKlines.length > 0) {
                    const parsedKlines = rawKlines.map((k: any) => ({
                        time: k[0] / 1000,
                        open: parseFloat(k[1]),
                        high: parseFloat(k[2]),
                        low: parseFloat(k[3]),
                        close: parseFloat(k[4]),
                        volume: parseFloat(k[5] || 0),
                    }));

                    // 1. Calculate realistic VPVR (Volume Profile Visible Range) from real klines
                    const minPrice = Math.min(...parsedKlines.map((c: any) => c.low));
                    const maxPrice = Math.max(...parsedKlines.map((c: any) => c.high));
                    const step = (maxPrice - minPrice) / 60;

                    const priceBuckets = new Map<number, { vol: number; buy: number; sell: number }>();
                    let currentCvd = 0;
                    const cvd: CVDDataPoint[] = [];
                    const footprints: FootprintCandleData[] = [];

                    parsedKlines.forEach((c: any) => {
                        // Estimate buy/sell proportion based on price action within the candle (no Math.random)
                        const range = c.high - c.low || 1;
                        const buyRatio = Math.max(0, Math.min(1, (c.close - c.low) / range));
                        const sellRatio = 1 - buyRatio;

                        const buyVol = c.volume * buyRatio;
                        const sellVol = c.volume * sellRatio;

                        // 2. Accumulate CVD
                        // Delta is buy limits hit (market buys) minus sell limits hit (market sells)
                        const delta = buyVol - sellVol;
                        currentCvd += delta;
                        cvd.push({ time: c.time as any, value: currentCvd });

                        // Distribute volume into VPVR buckets
                        const bucketPrice = Math.floor(c.close / step) * step;
                        const existing = priceBuckets.get(bucketPrice) || { vol: 0, buy: 0, sell: 0 };
                        priceBuckets.set(bucketPrice, {
                            vol: existing.vol + c.volume,
                            buy: existing.buy + buyVol,
                            sell: existing.sell + sellVol
                        });

                        // 3. Generate deterministic Footprint from real candle data
                        const candleFootprint: FootprintCandleData = {
                            time: c.time as any,
                            high: c.high,
                            low: c.low,
                            ticks: []
                        };

                        const numTicks = Math.max(2, Math.min(5, Math.floor(range / 0.5)));
                        const tickStep = range / numTicks;

                        if (range > 0 && tickStep > 0) {
                            for (let p = c.low; p <= c.high; p += tickStep) {
                                // Deterministic logic: more volume near the close price
                                const distanceToClose = Math.abs(c.close - p);
                                const weight = 1 - (distanceToClose / range);

                                const tickVol = (c.volume / numTicks) * weight;
                                const tickBuyVol = tickVol * buyRatio;
                                const tickSellVol = tickVol * sellRatio;

                                const isImbalance = Math.max(tickBuyVol, tickSellVol) > Math.min(tickBuyVol, tickSellVol) * 2;

                                candleFootprint.ticks.push({
                                    price: p,
                                    bidVolume: tickBuyVol,
                                    askVolume: tickSellVol,
                                    isImbalance
                                });
                            }
                        }
                        footprints.push(candleFootprint);
                    });

                    // Format VPVR Data
                    const vpvr: VPVRData[] = Array.from(priceBuckets.entries()).map(([price, data]) => ({
                        price,
                        volume: data.vol,
                        buyVolume: data.buy,
                        sellVolume: data.sell
                    }));

                    setVpvrData(vpvr);
                    setCvdData(cvd);
                    setFootprintData(footprints);
                } else {
                    setVpvrData([]);
                    setCvdData([]);
                    setFootprintData([]);
                }
            } catch (err) {
                console.error("Failed to fetch order flow data:", err);
                if (isMounted) setError("Failed to load order flow data.");
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        fetchOrderFlowData();

        return () => {
            isMounted = false;
        };
    }, [symbol, exchange, interval]);

    return { heatmapData, vpvrData, cvdData, footprintData, loading, error };
};
