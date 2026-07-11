import React, { useEffect, useState } from 'react';
import { Activity, TrendingUp, TrendingDown } from 'lucide-react';
import { motion } from 'framer-motion';

interface LiveMarketPulseProps {
    symbol: string;
    exchange: string;
}

const LiveMarketPulse: React.FC<LiveMarketPulseProps> = ({ symbol, exchange }) => {
    const [price, setPrice] = useState<number | null>(null);
    const [change, setChange] = useState<number>(0);
    const [volume, setVolume] = useState<number>(0);
    const [isPulsing, setIsPulsing] = useState(false);
    const [prevPrice, setPrevPrice] = useState<number | null>(null);

    useEffect(() => {
        // We use Binance public WS as a universal live data feed for the UI effect
        // Format symbol: remove anything after colon (like :USDT) and remove slash
        const isFutures = symbol.includes(':');
        const formattedSymbol = symbol.split(':')[0].replace('/', '').toLowerCase();
        
        // Route to Futures stream if it's a futures pair, else Spot stream
        const wsUrl = isFutures 
            ? `wss://fstream.binance.com/ws/${formattedSymbol}@ticker`
            : `wss://stream.binance.com:9443/ws/${formattedSymbol}@ticker`;
        
        let ws: WebSocket | null = null;
        let isMounted = true;

        // Fetch initial data via REST (Crucial for weekends when TradFi websockets are silent)
        const fetchInitialData = async () => {
            try {
                const restUrl = isFutures
                    ? `https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=${formattedSymbol.toUpperCase()}`
                    : `https://api.binance.com/api/v3/ticker/24hr?symbol=${formattedSymbol.toUpperCase()}`;
                const res = await fetch(restUrl);
                const data = await res.json();
                if (isMounted && data && data.lastPrice) {
                    setPrice(prev => prev === null ? parseFloat(data.lastPrice) : prev);
                    setChange(prev => prev === 0 ? parseFloat(data.priceChangePercent) : prev);
                    setVolume(prev => prev === 0 ? parseFloat(data.volume) : prev);
                }
            } catch (e) {
                console.warn('Failed to fetch initial REST data for', symbol, e);
            }
        };
        fetchInitialData();

        try {
            ws = new WebSocket(wsUrl);

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data && data.c) {
                    const newPrice = parseFloat(data.c);
                    setPrice(prev => {
                        setPrevPrice(prev);
                        return newPrice;
                    });
                    setChange(parseFloat(data.P));
                    setVolume(parseFloat(data.v));
                    
                    setIsPulsing(true);
                    setTimeout(() => setIsPulsing(false), 150);
                }
            };
            
            ws.onerror = () => {
                console.warn(`WebSocket error for ${symbol}`);
            }
        } catch (e) {
            console.error(e);
        }

        return () => {
            isMounted = false;
            if (ws) {
                ws.close();
            }
            setPrice(null);
            setChange(0);
            setVolume(0);
        };
    }, [symbol]);

    const isUp = change >= 0;
    const priceColor = !prevPrice || !price ? 'text-white' : price >= prevPrice ? 'text-emerald-400' : 'text-red-400';

    return (
        <div className="bg-black/30 backdrop-blur-xl border border-white/5 rounded-xl p-4 flex flex-col justify-center h-[76px] relative overflow-hidden group transition-all hover:border-cyan-500/30">
            {/* Background glowing orb */}
            <div className={`absolute -right-6 -top-6 w-24 h-24 rounded-full blur-[30px] opacity-20 transition-colors duration-1000 ${isUp ? 'bg-emerald-500' : 'bg-red-500'}`}></div>

            <div className="flex items-center justify-between z-10">
                <div className="flex items-center gap-2">
                    <Activity className={`w-4 h-4 ${isPulsing ? 'text-cyan-400 opacity-100' : 'text-slate-500 opacity-50'} transition-all`} />
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Live Pulse</span>
                </div>
                
                <div className={`flex items-center gap-1 text-[10px] font-bold ${isUp ? 'text-emerald-400' : 'text-red-400'} bg-black/50 px-2 py-0.5 rounded-full border border-white/5`}>
                    {isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    {Math.abs(change).toFixed(2)}%
                </div>
            </div>

            <div className="flex items-end justify-between mt-2 z-10">
                <motion.div 
                    key={price}
                    initial={{ opacity: 0.8, y: -2 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`text-xl font-black font-mono tracking-tighter ${priceColor} drop-shadow-[0_0_8px_rgba(255,255,255,0.1)]`}
                >
                    {price ? `$${price > 10 ? price.toFixed(2) : price.toFixed(4)}` : 'Connecting...'}
                </motion.div>

                {volume > 0 && (
                    <div className="text-[9px] font-mono text-slate-500 font-bold uppercase tracking-wider text-right">
                        Vol: {volume > 1000000 ? (volume / 1000000).toFixed(2) + 'M' : volume > 1000 ? (volume / 1000).toFixed(2) + 'K' : volume.toFixed(0)}
                    </div>
                )}
            </div>
        </div>
    );
};

export default LiveMarketPulse;
