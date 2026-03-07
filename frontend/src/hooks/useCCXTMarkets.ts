import { useState, useCallback, useEffect } from 'react';
import ccxt from 'ccxt';

// Define the interface for the objects we want to return
export interface MarketPair {
    symbol: string;      // e.g. "BTC/USDT"
    baseId: string;      // e.g. "BTC"
    quoteId: string;     // e.g. "USDT"
    active: boolean;     // Whether the market is currently active
}

export const useCCXTMarkets = () => {
    const [exchanges] = useState<string[]>(ccxt.exchanges);
    const [selectedExchange, setSelectedExchange] = useState<string>('binance');

    // Status tracking
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    // Data tracking
    const [markets, setMarkets] = useState<MarketPair[]>([]);
    const [quoteCurrencies, setQuoteCurrencies] = useState<string[]>([]);
    const [selectedQuote, setSelectedQuote] = useState<string>('USDT');
    const [availablePairs, setAvailablePairs] = useState<MarketPair[]>([]);
    const [selectedPair, setSelectedPair] = useState<string>('BTC/USDT');

    // Load ALL markets for a given exchange
    const loadMarkets = useCallback(async (exchangeId: string) => {
        setIsLoading(true);
        setError(null);
        try {
            // Instantiate ccxt.exchange with error handling if exchange doesn't exist
            if (!ccxt.exchanges.includes(exchangeId)) {
                throw new Error(`Exchange ${exchangeId} is not supported by CCXT`);
            }

            // eslint-disable-next-line @typescript-eslint/ban-ts-comment
            // @ts-ignore
            const exchangeClass = ccxt[exchangeId];
            const exchangeInstance = new exchangeClass({ enableRateLimit: true });

            // Fetch raw markets from CCXT
            const rawMarkets = await exchangeInstance.loadMarkets();

            // Parse into our standard MarketPair format
            const parsedMarkets: MarketPair[] = [];
            const quotes = new Set<string>();

            Object.values(rawMarkets).forEach((market: any) => {
                if (market && market.symbol && market.base && market.quote) {
                    parsedMarkets.push({
                        symbol: market.symbol,
                        baseId: market.base,
                        quoteId: market.quote,
                        active: market.active !== false // assume active if not explicitly false
                    });
                    quotes.add(market.quote);
                }
            });

            // Sort everything alphabetically for clean UI
            parsedMarkets.sort((a, b) => a.symbol.localeCompare(b.symbol));
            const sortedQuotes = Array.from(quotes).sort();

            setMarkets(parsedMarkets);
            setQuoteCurrencies(sortedQuotes);

            // Set sensible defaults if USDT/USDC exists, otherwise first element
            let defaultQuote = sortedQuotes.includes('USDT') ? 'USDT'
                : sortedQuotes.includes('USDC') ? 'USDC'
                    : sortedQuotes[0] || '';

            setSelectedQuote(defaultQuote);
            filterPairsByQuote(defaultQuote, parsedMarkets);

        } catch (err: any) {
            console.error(`Error loading markets for ${exchangeId}:`, err);
            setError(err.message || 'Failed to fetch exchange pairs.');
            setMarkets([]);
            setQuoteCurrencies([]);
            setAvailablePairs([]);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Helper function to update the available pairs when a quote currency changes
    const filterPairsByQuote = (quote: string, allMarkets: MarketPair[] = markets) => {
        const filtered = allMarkets.filter(m => m.quoteId === quote);
        setAvailablePairs(filtered);

        // Auto-select BTC or first element 
        if (filtered.length > 0) {
            const btcPair = filtered.find(p => p.baseId === 'BTC' || p.baseId === 'XBT');
            setSelectedPair(btcPair ? btcPair.symbol : filtered[0].symbol);
        } else {
            setSelectedPair('');
        }
    };

    // Whenever the exchange changes, load the markets
    useEffect(() => {
        if (selectedExchange) {
            loadMarkets(selectedExchange);
        }
    }, [selectedExchange, loadMarkets]);

    // Whenever the selected Quote changes, immediately filter the available pairs
    useEffect(() => {
        filterPairsByQuote(selectedQuote);
    }, [selectedQuote]);

    return {
        // Exchange selection state
        exchanges,
        selectedExchange,
        setSelectedExchange,

        // Quote currency (Base pairing) state
        quoteCurrencies,
        selectedQuote,
        setSelectedQuote,

        // Asset Pair state
        availablePairs,
        selectedPair,
        setSelectedPair,

        // Loading & Error states
        isLoading,
        error
    };
};
