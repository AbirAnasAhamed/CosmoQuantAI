import React, { useEffect, useState } from 'react';
import { X, TrendingUp, TrendingDown, Flame, Sparkles, BarChart2 } from 'lucide-react';
import { useBinanceMarketData, TokenData } from '../hooks/useBinanceMarketData';

interface TopTokensModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export const TopTokensModal: React.FC<TopTokensModalProps> = ({ isOpen, onClose }) => {
    const [isVisible, setIsVisible] = useState(false);
    const data = useBinanceMarketData(isOpen);

    // Handle animation timing
    useEffect(() => {
        if (isOpen) {
            setIsVisible(true);
        } else {
            const timer = setTimeout(() => setIsVisible(false), 300);
            return () => clearTimeout(timer);
        }
    }, [isOpen]);

    if (!isVisible) return null;

    const renderTokenList = (tokens: TokenData[], title: string, icon: React.ReactNode, colorClass: string) => (
        <div className={`bg-black/40 backdrop-blur-md rounded-xl border border-white/10 p-4 flex flex-col h-full overflow-hidden`}>
            <div className={`flex items-center gap-2 mb-4 pb-2 border-b border-white/10 ${colorClass}`}>
                {icon}
                <h3 className="font-bold text-lg">{title}</h3>
            </div>
            <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar space-y-2">
                {tokens.length === 0 ? (
                    <div className="text-gray-500 text-sm text-center py-4 animate-pulse">Loading data...</div>
                ) : (
                    tokens.map((token, index) => {
                        const isPositive = token.priceChangePercent >= 0;
                        return (
                            <div key={token.symbol} className="flex justify-between items-center p-2 rounded-lg hover:bg-white/5 transition-colors group">
                                <div className="flex items-center gap-2">
                                    <span className="text-gray-500 text-xs w-4">{index + 1}.</span>
                                    <span className="font-semibold text-white group-hover:text-blue-400 transition-colors">
                                        {token.symbol.replace('USDT', '')}
                                    </span>
                                </div>
                                <div className="flex flex-col items-end">
                                    <span className="text-sm font-medium text-gray-200">
                                        ${token.lastPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
                                    </span>
                                    <span className={`text-xs font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                                        {isPositive ? '+' : ''}{token.priceChangePercent.toFixed(2)}%
                                    </span>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-6">
            {/* Backdrop */}
            <div 
                className={`absolute inset-0 bg-black/80 backdrop-blur-sm transition-opacity duration-300 ${isOpen ? 'opacity-100' : 'opacity-0'}`}
                onClick={onClose}
            />
            
            {/* Modal Content */}
            <div 
                className={`relative w-full max-w-7xl h-[85vh] bg-gradient-to-br from-gray-900 to-black rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.5)] border border-gray-700 overflow-hidden flex flex-col transform transition-all duration-300 ${isOpen ? 'scale-100 opacity-100 translate-y-0' : 'scale-95 opacity-0 translate-y-8'}`}
            >
                {/* Header */}
                <div className="flex justify-between items-center p-5 border-b border-white/10 shrink-0 bg-white/5">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg shadow-lg shadow-orange-500/20">
                            <Flame className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-orange-400 to-red-500">Market Movers</h2>
                            <p className="text-xs text-gray-400">Real-time Binance top performing tokens</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-all focus:outline-none focus:ring-2 focus:ring-orange-500/50"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>
                
                {/* Dashboard Grid */}
                <div className="flex-1 p-5 overflow-hidden">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-5 h-full">
                        {renderTokenList(
                            data.gainers, 
                            "Top Gainers", 
                            <TrendingUp className="w-5 h-5" />, 
                            "text-green-400 border-green-400/30"
                        )}
                        {renderTokenList(
                            data.losers, 
                            "Top Losers", 
                            <TrendingDown className="w-5 h-5" />, 
                            "text-red-400 border-red-400/30"
                        )}
                        {renderTokenList(
                            data.hot, 
                            "Hot Tokens", 
                            <Flame className="w-5 h-5" />, 
                            "text-orange-400 border-orange-400/30"
                        )}
                        {renderTokenList(
                            data.newTokens, 
                            "Trending / Volatile", 
                            <Sparkles className="w-5 h-5" />, 
                            "text-purple-400 border-purple-400/30"
                        )}
                        {renderTokenList(
                            data.volume, 
                            "Highest Volume", 
                            <BarChart2 className="w-5 h-5" />, 
                            "text-blue-400 border-blue-400/30"
                        )}
                    </div>
                </div>
            </div>
            
            <style dangerouslySetInnerHTML={{__html: `
                .custom-scrollbar::-webkit-scrollbar {
                    width: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background-color: rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                }
                .custom-scrollbar:hover::-webkit-scrollbar-thumb {
                    background-color: rgba(255, 255, 255, 0.2);
                }
            `}} />
        </div>
    );
};
