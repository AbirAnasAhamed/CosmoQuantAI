import React, { useState, useEffect } from 'react';
import { useSettings } from '../../../context/SettingsContext';
import { useCCXTMarkets } from '../../../hooks/useCCXTMarkets';

export const BotSettingsTab: React.FC = () => {
    const { apiKeys } = useSettings();
    const {
        exchanges, selectedExchange, setSelectedExchange,
        quoteCurrencies, selectedQuote, setSelectedQuote,
        availablePairs, selectedPair, setSelectedPair,
        isLoading, error
    } = useCCXTMarkets();

    const [isEnabled, setIsEnabled] = useState(false);
    const [isRealTrading, setIsRealTrading] = useState(false);
    const [tradeSize, setTradeSize] = useState('0.1');
    const [strategy, setStrategy] = useState('imbalance_breakout');
    const [selectedApiKey, setSelectedApiKey] = useState('');

    useEffect(() => {
        if (apiKeys.length > 0 && !selectedApiKey) {
            setSelectedApiKey(apiKeys[0].id?.toString() || '');
        }
    }, [apiKeys, selectedApiKey]);

    return (
        <div className="w-full h-full p-6 flex flex-col items-center justify-start overflow-y-auto">
            <div className="w-full max-w-2xl bg-white dark:bg-[#0B1120] rounded-xl border border-gray-200 dark:border-white/5 shadow-lg p-6">
                <div className="mb-6 flex justify-between items-center border-b border-gray-200 dark:border-white/10 pb-4">
                    <h2 className="text-xl font-bold text-gray-800 dark:text-white">Order Flow Bot Configuration</h2>
                    <div className="flex items-center space-x-3">
                        <span className={`text-sm font-bold ${isEnabled ? 'text-green-500' : 'text-gray-500'}`}>
                            {isEnabled ? 'ACTIVE' : 'INACTIVE'}
                        </span>
                        <button
                            onClick={() => setIsEnabled(!isEnabled)}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isEnabled ? 'bg-green-500' : 'bg-gray-400 dark:bg-gray-600'}`}
                        >
                            <span className={`${isEnabled ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ease-in-out`} />
                        </button>
                    </div>
                </div>

                {/* Secure Paper/Real Trading Toggle */}
                <div className="mb-6 bg-gray-50 dark:bg-black/20 rounded-xl p-4 border border-gray-200 dark:border-white/10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                        <h3 className="text-lg font-bold text-gray-800 dark:text-white flex items-center gap-2">
                            Trading Mode
                            {isRealTrading ? (
                                <span className="px-2 py-0.5 text-[10px] font-bold bg-red-500 text-white rounded uppercase tracking-wider animate-pulse">Live</span>
                            ) : (
                                <span className="px-2 py-0.5 text-[10px] font-bold bg-blue-500 text-white rounded uppercase tracking-wider">Simulated</span>
                            )}
                        </h3>
                        <p className="text-xs text-gray-500 mt-1 max-w-sm">
                            {isRealTrading
                                ? "Warning: Trading with real funds. Losses can exceed your initial deposit."
                                : "Paper trading mode. No real orders will be placed."}
                        </p>
                    </div>

                    <div className="flex bg-gray-200 dark:bg-gray-800 rounded-lg p-1 relative border border-gray-300 dark:border-gray-700">
                        <button
                            onClick={() => setIsRealTrading(false)}
                            className={`relative px-4 py-2 text-sm font-semibold rounded-md transition-all z-10 ${!isRealTrading
                                    ? 'text-white shadow-sm'
                                    : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                                }`}
                        >
                            Paper Trading
                            {!isRealTrading && (
                                <span className="absolute inset-0 bg-blue-500 rounded-md -z-10 shadow-[0_0_10px_rgba(59,130,246,0.5)]"></span>
                            )}
                        </button>
                        <button
                            onClick={() => setIsRealTrading(true)}
                            className={`relative px-4 py-2 text-sm font-semibold rounded-md transition-all z-10 ${isRealTrading
                                    ? 'text-white shadow-sm'
                                    : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                                }`}
                        >
                            Real Trading
                            {isRealTrading && (
                                <span className="absolute inset-0 bg-red-500 rounded-md -z-10 shadow-[0_0_10px_rgba(239,68,68,0.5)]"></span>
                            )}
                        </button>
                    </div>
                </div>

                {isRealTrading && (
                    <div className="mb-6 bg-red-50 dark:bg-red-900/10 rounded-xl p-4 border border-red-200 dark:border-red-500/20 animate-in fade-in slide-in-from-top-2">
                        <label className="block text-sm font-bold text-red-700 dark:text-red-400 mb-2">Live Execution API Key</label>
                        {apiKeys.length > 0 ? (
                            <select
                                value={selectedApiKey}
                                onChange={(e) => setSelectedApiKey(e.target.value)}
                                className="w-full bg-white dark:bg-black/40 border border-red-300 dark:border-red-500/30 text-gray-900 dark:text-white rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-red-500"
                            >
                                {apiKeys.map((key) => (
                                    <option key={key.id} value={key.id?.toString()}>
                                        {key.name} ({key.exchange.charAt(0).toUpperCase() + key.exchange.slice(1)})
                                    </option>
                                ))}
                            </select>
                        ) : (
                            <div className="p-3 bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-500/30 rounded text-red-800 dark:text-red-300 text-sm">
                                No API keys found. Please configure an API key in the Settings page to enable real trading.
                            </div>
                        )}
                        <p className="mt-2 text-xs text-red-600 dark:text-red-400/80">
                            Ensure your selected API key matches your trading exchange and has appropriate permissions.
                        </p>
                    </div>
                )}

                <div className="space-y-6">
                    {/* --- CCXT Market Selection Core --- */}
                    <div className="bg-gray-50 dark:bg-black/20 p-4 rounded-xl border border-gray-200 dark:border-white/5 space-y-4">
                        <h3 className="text-sm font-bold text-gray-800 dark:text-white border-b border-gray-200 dark:border-white/10 pb-2">Market Selection</h3>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Exchange Box */}
                            <div>
                                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Exchange</label>
                                <select
                                    value={selectedExchange}
                                    onChange={(e) => setSelectedExchange(e.target.value)}
                                    className="w-full bg-white dark:bg-[#0B1120] border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white rounded-lg px-3 py-2 outline-none focus:ring-1 focus:ring-brand-primary"
                                >
                                    {exchanges.slice(0, 100).map(ex => (
                                        <option key={ex} value={ex}>{ex.charAt(0).toUpperCase() + ex.slice(1)}</option>
                                    ))}
                                </select>
                            </div>

                            {/* Quote Box */}
                            <div>
                                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Base Currency</label>
                                <select
                                    value={selectedQuote}
                                    onChange={(e) => setSelectedQuote(e.target.value)}
                                    disabled={isLoading || quoteCurrencies.length === 0}
                                    className="w-full bg-white dark:bg-[#0B1120] border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white rounded-lg px-3 py-2 outline-none focus:ring-1 focus:ring-brand-primary disabled:opacity-50"
                                >
                                    {quoteCurrencies.map(q => (
                                        <option key={q} value={q}>{q}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {/* Pair Box */}
                        <div>
                            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                                Asset Pair {isLoading && <span className="text-[10px] text-brand-primary animate-pulse ml-2">Loading...</span>}
                            </label>
                            <select
                                value={selectedPair}
                                onChange={(e) => setSelectedPair(e.target.value)}
                                disabled={isLoading || availablePairs.length === 0}
                                className="w-full bg-white dark:bg-[#0B1120] border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white rounded-lg px-3 py-2 outline-none focus:ring-1 focus:ring-brand-primary disabled:opacity-50"
                            >
                                {availablePairs.map(p => (
                                    <option key={p.symbol} value={p.symbol}>{p.symbol}</option>
                                ))}
                            </select>
                            {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
                        </div>
                    </div>
                    {/* --------------------------------- */}

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Algorithm Strategy</label>
                        <select
                            value={strategy}
                            onChange={(e) => setStrategy(e.target.value)}
                            className="w-full bg-gray-50 dark:bg-black/20 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-brand-primary"
                        >
                            <option value="imbalance_breakout">Order Imbalance Breakout</option>
                            <option value="liquidity_sniping">Liquidity Wall Sniping</option>
                            <option value="cvd_divergence">CVD Divergence Trading</option>
                        </select>
                        <p className="mt-2 text-xs text-gray-500">Select the logic the bot will use to interpret the incoming Order Flow heatmap data.</p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Trade Size (BTC)</label>
                        <input
                            type="number"
                            step="0.01"
                            value={tradeSize}
                            onChange={(e) => setTradeSize(e.target.value)}
                            className="w-full bg-gray-50 dark:bg-black/20 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-brand-primary"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Risk Parameters</label>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <span className="text-xs text-gray-500 mb-1 block">Stop Loss (%)</span>
                                <input type="number" defaultValue="2.5" className="w-full bg-gray-50 dark:bg-black/20 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 outline-none" />
                            </div>
                            <div>
                                <span className="text-xs text-gray-500 mb-1 block">Take Profit (%)</span>
                                <input type="number" defaultValue="5.0" className="w-full bg-gray-50 dark:bg-black/20 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 outline-none" />
                            </div>
                        </div>
                    </div>

                    <div className="pt-4 border-t border-gray-200 dark:border-white/10">
                        <button className={`w-full text-white font-bold py-3 px-4 rounded-lg shadow-md transition-all ${isRealTrading
                                ? 'bg-red-600 hover:bg-red-700 shadow-[0_4px_15px_rgba(220,38,38,0.4)]'
                                : 'bg-brand-primary hover:bg-blue-600'
                            }`}>
                            {isRealTrading ? 'Save REAL Trading Configuration' : 'Save Bot Configuration'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
