import { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import { HeatmapDataPoint } from '../components/features/market/LiquidityHeatmapRenderer';

export const useHeatmapData = (symbol: string, exchange: string) => {
    const [heatmapData, setHeatmapData] = useState<HeatmapDataPoint[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const intervalRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        let isMounted = true;
        setHeatmapData([]); // Clear previous data when symbol/exchange changes

        const fetchHeatmap = async () => {
            if (!symbol || !exchange) return;

            try {
                const res = await api.get('/market-depth/heatmap', {
                    params: {
                        symbol: symbol.toUpperCase(),
                        exchange,
                        bucket_size: 50.0,
                        depth: 100
                    }
                });

                if (!isMounted) return;

                const { bids, asks } = res.data;
                const now = Math.floor(Date.now() / 1000); // Unix timestamp

                const newPoint: HeatmapDataPoint = {
                    time: now,
                    levels: []
                };

                if (bids && Array.isArray(bids)) {
                    bids.forEach((bid: any) => {
                        newPoint.levels.push({
                            price: bid.price,
                            volume: bid.volume,
                            type: 'bid'
                        });
                    });
                }

                if (asks && Array.isArray(asks)) {
                    asks.forEach((ask: any) => {
                        newPoint.levels.push({
                            price: ask.price,
                            volume: ask.volume,
                            type: 'ask'
                        });
                    });
                }

                setHeatmapData(prev => {
                    const newData = [...prev, newPoint];
                    // Keep last 200 points to prevent memory leak
                    if (newData.length > 200) {
                        return newData.slice(newData.length - 200);
                    }
                    return newData;
                });

                setError(null);
            } catch (err: any) {
                console.error("Failed to fetch heatmap data:", err);
                if (isMounted) setError("Failed to load heatmap data.");
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        // Initial fetch
        setLoading(true);
        fetchHeatmap();

        // Poll every 5 seconds (matching Redis TTL in backend)
        intervalRef.current = setInterval(fetchHeatmap, 5000);

        return () => {
            isMounted = false;
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        };
    }, [symbol, exchange]);

    return { heatmapData, loading, error };
};
