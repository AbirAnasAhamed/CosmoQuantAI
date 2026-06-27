import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { LineChart, Activity, TrendingUp, TrendingDown, Maximize2, AlertTriangle, ArrowRightLeft } from 'lucide-react';
import Button from '@/components/common/Button';
import { TradingViewWidget } from '@/components/features/market/TradingViewWidget';

const ForexPairs = () => {
  const [selectedPair, setSelectedPair] = useState('EUR/USD');

  const pairs = [
    { symbol: 'EUR/USD', bid: '1.09245', ask: '1.09247', spread: 0.2, change: '+0.15%' },
    { symbol: 'GBP/USD', bid: '1.26410', ask: '1.26413', spread: 0.3, change: '-0.08%' },
    { symbol: 'USD/JPY', bid: '149.325', ask: '149.328', spread: 0.3, change: '+0.42%' },
    { symbol: 'XAU/USD', bid: '2024.50', ask: '2024.75', spread: 2.5, change: '+1.20%' },
    { symbol: 'AUD/USD', bid: '0.65210', ask: '0.65214', spread: 0.4, change: '-0.25%' },
  ];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="h-[calc(100vh-120px)] flex flex-col gap-6"
    >
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
            <LineChart className="text-[#D4AF37]" size={28} />
            Forex Advanced Charting
          </h1>
          <p className="text-gray-500 mt-1">Live market data, spread monitoring, and institutional order flow.</p>
        </div>
        
        <div className="flex gap-3">
          <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 flex items-center gap-3">
            <span className="text-xs text-gray-500">Broker:</span>
            <span className="text-sm font-bold text-[#D4AF37]">OANDA (Live)</span>
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse ml-2" />
          </div>
        </div>
      </div>

      {/* Main Content Area - Split Layout */}
      <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
        
        {/* Left Sidebar - Pairs List */}
        <div className="w-full lg:w-80 flex flex-col gap-4">
          <div className="p-4 rounded-2xl bg-white/5 dark:bg-[#0A101D]/80 border border-gray-200 dark:border-white/10 flex-1 overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-slate-900 dark:text-white">Watchlist</h3>
              <Button variant="outline" className="!p-1.5 border-white/10 text-gray-400 hover:text-white">
                <Maximize2 size={14} />
              </Button>
            </div>
            
            <div className="space-y-2">
              {pairs.map((pair) => (
                <div 
                  key={pair.symbol} 
                  onClick={() => setSelectedPair(pair.symbol)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    selectedPair === pair.symbol 
                      ? 'bg-[#D4AF37]/10 border-[#D4AF37]/30 shadow-[0_0_15px_rgba(212,175,55,0.05)]' 
                      : 'bg-transparent border-transparent hover:bg-white/5'
                  }`}
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className={`font-bold ${selectedPair === pair.symbol ? 'text-[#D4AF37]' : 'text-white'}`}>{pair.symbol}</span>
                    <span className={`text-xs font-bold ${pair.change.startsWith('+') ? 'text-emerald-500' : 'text-red-500'}`}>{pair.change}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs font-mono">
                    <div className="flex gap-2">
                      <span className="text-red-400">{pair.bid}</span>
                      <span className="text-gray-500">/</span>
                      <span className="text-emerald-400">{pair.ask}</span>
                    </div>
                    <span className="text-gray-500 bg-white/5 px-1.5 py-0.5 rounded">{pair.spread}p</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Live Spread Warning Widget */}
          <div className="p-4 rounded-2xl bg-orange-500/5 border border-orange-500/20">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="text-orange-500" size={16} />
              <h4 className="font-bold text-orange-500 text-sm">Spread Monitor</h4>
            </div>
            <p className="text-xs text-gray-400 mb-3">Monitoring real-time spreads across all active algorithmic pairs.</p>
            <div className="flex items-center justify-between text-sm">
              <span className="text-white">Avg Spread: <span className="font-mono text-emerald-400">0.8 pips</span></span>
              <span className="px-2 py-1 bg-emerald-500/10 text-emerald-500 rounded text-xs font-bold">NORMAL</span>
            </div>
          </div>
        </div>

        {/* Right Area - Chart and Order Entry (Read Only for Bots) */}
        <div className="flex-1 flex flex-col gap-6">
          {/* Chart Area */}
          <div className="flex-1 rounded-2xl bg-[#131722] border border-white/10 relative overflow-hidden group">
            <TradingViewWidget 
                symbol={selectedPair} 
                interval="15m" 
                exchange="OANDA" 
                theme="dark"
            />
          </div>
          
          {/* Active Bot Operations panel under the chart */}
          <div className="h-32 rounded-2xl bg-white/5 border border-white/10 p-4 flex gap-6 overflow-x-auto">
             <div className="flex-shrink-0 w-64 p-3 rounded-xl bg-white/5 border border-white/5 flex flex-col justify-between">
               <div className="flex justify-between items-center">
                 <span className="text-xs text-gray-400">Current Algorithm</span>
                 <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
               </div>
               <h4 className="text-sm font-bold text-white mt-1">London Scalper v2</h4>
               <div className="flex justify-between items-end mt-2">
                 <span className="text-xs text-gray-500">Status: <span className="text-emerald-400">Searching setup...</span></span>
               </div>
             </div>
             
             <div className="flex-shrink-0 w-64 p-3 rounded-xl bg-white/5 border border-white/5 flex flex-col justify-between opacity-50">
               <div className="flex justify-between items-center">
                 <span className="text-xs text-gray-400">Manual Override</span>
               </div>
               <h4 className="text-sm font-bold text-white mt-1">Direct Execution</h4>
               <div className="flex gap-2 mt-2">
                 <button className="flex-1 py-1 bg-red-500/20 text-red-500 text-xs font-bold rounded">SELL</button>
                 <button className="flex-1 py-1 bg-emerald-500/20 text-emerald-500 text-xs font-bold rounded">BUY</button>
               </div>
             </div>
          </div>
        </div>

      </div>
    </motion.div>
  );
};

export default ForexPairs;
