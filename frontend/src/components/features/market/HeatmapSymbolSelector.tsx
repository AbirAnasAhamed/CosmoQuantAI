import React, { useState, useEffect } from 'react';
import api from '../../../services/api';

export interface HeatmapSymbolSelectorProps {
    symbol: string;
    exchange: string;
    onSymbolChange: (newSymbol: string) => void;
    onExchangeChange: (newExchange: string) => void;
}

export const HeatmapSymbolSelector: React.FC<HeatmapSymbolSelectorProps> = ({ symbol, exchange, onSymbolChange, onExchangeChange }) => {
    const [exchanges, setExchanges] = useState<string[]>(['binance']);
    const [markets, setMarkets] = useState<string[]>(['BTC/USDT']);
    const [loadingMarkets, setLoadingMarkets] = useState(false);

    // Fetch exchanges on mount
    useEffect(() => {
        const fetchExchanges = async () => {
            try {
                const res = await api.get('/market-depth/exchanges');
                if (res.data && Array.isArray(res.data)) {
                    setExchanges(res.data);
                }
            } catch (err) {
                console.error("Failed to fetch exchanges:", err);
            }
        };
        fetchExchanges();
    }, []);

    // Fetch markets when exchange changes
    useEffect(() => {
        const fetchMarkets = async () => {
            if (!exchange) return;
            setLoadingMarkets(true);
            try {
                const res = await api.get('/market-depth/markets', { params: { exchange } });
                if (res.data && Array.isArray(res.data)) {
                    // Filter popular base currencies for brevity initially, or just include all.
                    // For now let's just use all but sort them.
                    const allPairs = [...res.data].sort();
                    setMarkets(allPairs);
                }
            } catch (err) {
                console.error(`Failed to fetch markets for ${exchange}:`, err);
            } finally {
                setLoadingMarkets(false);
            }
        };
        fetchMarkets();
    }, [exchange]);

    // Handle standard input onChange
    const handleSymbolInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value.toUpperCase();
        onSymbolChange(val);
    };

    return (
        <div className="flex items-center gap-3">
            {/* Exchange Selector */}
            <div className="relative inline-block w-32">
                <select
                    value={exchange}
                    onChange={(e) => onExchangeChange(e.target.value)}
                    className="w-full appearance-none bg-gray-100 dark:bg-white/5 text-sm font-mono text-gray-800 dark:text-white px-3 py-1.5 pr-8 rounded border border-gray-200 dark:border-white/10 hover:border-brand-primary/50 dark:hover:border-brand-primary/50 focus:outline-none transition-colors cursor-pointer capitalize"
                >
                    {exchanges.map((ex) => (
                        <option key={ex} value={ex} className="bg-white dark:bg-[#0B1120] text-gray-900 dark:text-white capitalize">
                            {ex}
                        </option>
                    ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
                    <svg className="fill-current h-4 w-4" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" /></svg>
                </div>
            </div>

            {/* Symbol Selector (Searchable) */}
            <div className="relative inline-block w-40">
                <input
                    list="heatmap-symbol-options"
                    value={symbol}
                    onChange={handleSymbolInputChange}
                    placeholder={loadingMarkets ? "Loading..." : "Search pair..."}
                    title="Type to search for an asset pair"
                    className="w-full bg-gray-100 dark:bg-white/5 text-sm font-mono text-gray-800 dark:text-white px-3 py-1.5 rounded border border-gray-200 dark:border-white/10 hover:border-brand-primary/50 dark:hover:border-brand-primary/50 focus:outline-none transition-colors uppercase"
                />
                <datalist id="heatmap-symbol-options">
                    {markets.map((sym) => (
                        <option key={sym} value={sym} />
                    ))}
                </datalist>
            </div>
        </div>
    );
};
