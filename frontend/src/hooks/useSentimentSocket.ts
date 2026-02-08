import { useState, useEffect, useRef } from 'react';

// Define the shape of the data we expect from the socket
export interface VoteUpdatePayload {
    bullish_pct: number;
    bearish_pct: number;
    total_votes: number;
}

export interface WebSocketMessage {
    type: 'VOTE_UPDATE' | 'PRICE_UPDATE' | 'SENTIMENT_UPDATE';
    data: VoteUpdatePayload | any; // Use stricter types as needed
}

export const useSentimentSocket = (activePair: string) => {
    const [realTimeData, setRealTimeData] = useState<WebSocketMessage | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        if (!activePair) return;

        const connect = () => {
            // Close existing connection if any
            if (wsRef.current) {
                wsRef.current.close();
            }

            // Construct WebSocket URL
            // Assuming backend is at localhost:8000 for now based on context
            // In a real app, use environment variables or logic relative to API_BASE_URL
            const wsUrl = `ws://localhost:8000/api/v1/sentiment/ws/${activePair}`;

            console.log(`🔌 Connecting to Sentiment WS: ${wsUrl}`);
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('✅ Sentiment WS Connected');
                setIsConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data);
                    console.log('📩 WS Message:', message);
                    setRealTimeData(message);
                } catch (error) {
                    console.error('❌ Failed to parse WS message:', error);
                }
            };

            ws.onclose = () => {
                console.log('⚠️ Sentiment WS Disconnected');
                setIsConnected(false);
                // Attempt reconnect after 3 seconds
                reconnectTimeoutRef.current = setTimeout(() => {
                    console.log('🔄 Reconnecting...');
                    connect();
                }, 3000);
            };

            ws.onerror = (error) => {
                console.error('❌ Sentiment WS Error:', error);
                ws.close();
            };
        };

        connect();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
        };
    }, [activePair]);

    return { realTimeData, isConnected };
};
