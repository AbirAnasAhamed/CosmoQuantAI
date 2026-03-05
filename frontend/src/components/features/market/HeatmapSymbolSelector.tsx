import React from 'react';

export interface HeatmapSymbolSelectorProps {
    symbol: string;
    onSymbolChange: (newSymbol: string) => void;
}

const SYMBOL_LIST = [
    'BTC/USDT',
    'ETH/USDT',
    'SOL/USDT',
    'BNB/USDT',
    'XRP/USDT',
    'DOGE/USDT',
    'ADA/USDT',
    'AVAX/USDT',
    'LINK/USDT',
    'DOT/USDT'
];

export const HeatmapSymbolSelector: React.FC<HeatmapSymbolSelectorProps> = ({ symbol, onSymbolChange }) => {
    return (
        <div className="relative inline-block w-40">
            <select
                value={symbol}
                onChange={(e) => onSymbolChange(e.target.value)}
                className="w-full appearance-none bg-gray-100 dark:bg-white/5 text-sm font-mono text-gray-800 dark:text-white px-3 py-1.5 pr-8 rounded border border-gray-200 dark:border-white/10 hover:border-brand-primary/50 dark:hover:border-brand-primary/50 focus:outline-none focus:ring-2 focus:ring-brand-primary/50 transition-colors cursor-pointer"
            >
                {SYMBOL_LIST.map((sym) => (
                    <option key={sym} value={sym} className="bg-white dark:bg-[#0B1120] text-gray-900 dark:text-white">
                        {sym}
                    </option>
                ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500 dark:text-gray-400">
                <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                    <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
                </svg>
            </div>
        </div>
    );
};
