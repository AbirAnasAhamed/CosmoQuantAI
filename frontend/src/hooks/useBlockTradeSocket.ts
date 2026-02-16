
import { useEffect, useState, useRef } from 'react';
import { BlockTrade, BlockTradePayload } from '../types/blockTrade';
import { useToast } from '@chakra-ui/react';

export const useBlockTradeSocket = () => {
    const [trades, setTrades] = useState<BlockTrade[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const socketRef = useRef<WebSocket | null>(null);
    const toast = useToast();

    useEffect(() => {
        let isMounted = true;
        let reconnectTimeout: NodeJS.Timeout;

        // Correct WS URL based on environment (assuming localhost for dev or relative for prod)
        const wsUrl = process.env.NODE_ENV === 'production'
            ? `wss://${window.location.host}/ws/block_trades`
            : 'ws://localhost:8000/ws/block_trades';

        const connect = () => {
            if (!isMounted) return;

            const socket = new WebSocket(wsUrl);
            socketRef.current = socket;

            socket.onopen = () => {
                if (!isMounted) {
                    socket.close();
                    return;
                }
                console.log('✅ Connected to Block Trade WebSocket');
                setIsConnected(true);
            };

            socket.onmessage = (event) => {
                if (!isMounted) return;
                try {
                    const payload: BlockTradePayload = JSON.parse(event.data);

                    if (payload.type === 'block_trade' && payload.data) {
                        const newTrades = payload.data;

                        setTrades(prevTrades => {
                            // Keep buffer of last 50 trades
                            const updated = [...newTrades, ...prevTrades].slice(0, 50);
                            return updated;
                        });

                        // Optional: Show toast for Whale Activity
                        newTrades.forEach(trade => {
                            if (trade.is_whale) {
                                toast({
                                    title: "🐳 WHALE ALERT",
                                    description: `${trade.side.toUpperCase()} ${trade.amount} ${trade.symbol} ($${trade.value.toLocaleString()}) on ${trade.exchange}`,
                                    status: "info",
                                    duration: 5000,
                                    isClosable: true,
                                    position: "top-right"
                                });
                            }
                        });
                    }
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            socket.onclose = () => {
                console.log('❌ Disconnected from Block Trade WebSocket');
                if (isMounted) {
                    setIsConnected(false);
                    // Reconnect after 3 seconds
                    reconnectTimeout = setTimeout(connect, 3000);
                }
            };

            socket.onerror = (error) => {
                console.error('WebSocket Error:', error);
                socket.close();
            };
        };

        connect();

        return () => {
            isMounted = false;
            clearTimeout(reconnectTimeout);
            if (socketRef.current) {
                socketRef.current.close();
            }
        };
    }, [toast]);

    return { trades, isConnected };
};
