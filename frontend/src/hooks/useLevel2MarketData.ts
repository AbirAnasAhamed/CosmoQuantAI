import { useState, useEffect } from 'react';

export interface OrderBookLevel {
    price: number;
    size: number;
    total: number;
}

export interface MarketDepthData {
    bids: OrderBookLevel[];
    asks: OrderBookLevel[];
    walls: { price: number; type: 'buy' | 'sell'; size: number }[];
    currentPrice: number;
}

export const useLevel2MarketData = (symbol: string, exchange: string = 'binance') => {
    const [data, setData] = useState<MarketDepthData>({ bids: [], asks: [], walls: [], currentPrice: 0 });

    useEffect(() => {
        let ws: WebSocket | null = null;
        let isSubscribed = true;
        let worker: Worker | null = null;

        const connectToBackend = () => {
            // Use relative URL or env var for production, fallback to localhost for dev
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const baseUrl = `${protocol}//${window.location.host}`;

            // Pass the exchange and the exact symbol (e.g. BTC/USDT) since backend uses {symbol:path}
            const encodedSymbol = encodeURIComponent(symbol).replace('%2F', '/'); // Ensure slash is kept raw if needed or just pass as is.
            const backendWsUrl = `${baseUrl}/api/v1/market-depth/ws/${exchange}/${symbol}`;

            try {
                // Initialize Web Worker
                worker = new Worker(new URL('../workers/marketDataWorker.ts', import.meta.url), { type: 'module' });

                worker.onmessage = (e) => {
                    if (!isSubscribed) return;
                    if (e.data.type === 'DATA_READY') {
                        setData(e.data.data);
                    }
                };

                worker.onerror = (err) => {
                    console.error("Worker encountered an error:", err);
                };

                ws = new WebSocket(backendWsUrl);

                ws.onopen = () => {
                    console.log(`Connected to Level 2 Market Data Stream for ${symbol} on ${exchange}`);
                };

                ws.onmessage = (event) => {
                    if (!isSubscribed || !worker) return;
                    // Offload processing to worker
                    worker.postMessage({ type: 'PROCESS_MESSAGE', payload: event.data });
                };

                ws.onerror = (err) => {
                    console.error("WebSocket error on market depth stream:", err);
                };

                ws.onclose = () => {
                    console.log(`Disconnected from market depth stream. Reconnecting in 5s...`);
                    if (isSubscribed) {
                        setTimeout(connectToBackend, 5000);
                    }
                };
            } catch (error) {
                console.error("Error creating WebSocket or Worker:", error);
                if (isSubscribed) {
                    setTimeout(connectToBackend, 5000);
                }
            }
        };

        if (symbol && exchange) {
            connectToBackend();
        }

        return () => {
            isSubscribed = false;
            if (ws) {
                ws.close();
            }
            if (worker) {
                worker.terminate();
            }
        };
    }, [symbol, exchange]);

    return data;
};
