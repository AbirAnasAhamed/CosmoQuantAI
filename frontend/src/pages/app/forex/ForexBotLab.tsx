import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Play, Plus, Zap, AlertTriangle, ShieldCheck, Cpu, Target, Sliders, Globe } from 'lucide-react';
import Button from '@/components/common/Button';

const StrategyTemplateCard = ({ title, description, type, recommendedPairs, onSelect }: any) => (
  <div className="p-5 rounded-2xl bg-white/5 dark:bg-[#0A101D]/80 border border-gray-200 dark:border-white/10 hover:border-[#D4AF37]/50 transition-colors group cursor-pointer" onClick={onSelect}>
    <div className="flex justify-between items-start mb-3">
      <div className="p-2 rounded-lg bg-[#D4AF37]/10 text-[#D4AF37]">
        <Cpu size={20} />
      </div>
      <span className="text-xs font-mono px-2 py-1 bg-white/10 rounded-md text-gray-400">{type}</span>
    </div>
    <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-[#D4AF37] transition-colors">{title}</h3>
    <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 line-clamp-2">{description}</p>
    <div className="mt-4 flex flex-wrap gap-2">
      {recommendedPairs.map((pair: string) => (
        <span key={pair} className="text-[10px] px-2 py-1 bg-gray-100 dark:bg-white/5 rounded-md text-gray-500 font-bold">{pair}</span>
      ))}
    </div>
  </div>
);

const ForexBotLab = () => {
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);
  
  // Form State
  const [botName, setBotName] = useState('My Forex Algo');
  const [pair, setPair] = useState('EUR/USD');
  const [lotSize, setLotSize] = useState(0.1);
  const [leverage, setLeverage] = useState(100);
  const [maxDrawdown, setMaxDrawdown] = useState(5.0);
  const [useNewsFilter, setUseNewsFilter] = useState(true);
  const [maxSpread, setMaxSpread] = useState(2.5);
  const [isDeploying, setIsDeploying] = useState(false);

  const templates = [
    { title: 'News Straddle Pro', description: 'Automatically places buy/sell stops before high impact news (NFP, CPI) to catch massive volatility spikes.', type: 'Breakout', recommendedPairs: ['EUR/USD', 'GBP/USD'] },
    { title: 'London Session Scalper', description: 'High frequency scalping algorithm exploiting tight spreads during the London-NY overlap.', type: 'HFT', recommendedPairs: ['GBP/JPY', 'EUR/GBP'] },
    { title: 'Smart Grid & Hedge', description: 'Cost-averaging grid system with built-in hedging to survive ranging markets and capitalize on mean reversion.', type: 'Grid', recommendedPairs: ['AUD/CAD', 'NZD/USD'] },
  ];
  
  const handleTemplateSelect = (template: any) => {
      setSelectedStrategy(template.title);
      setBotName(template.title);
      setPair(template.recommendedPairs[0]);
  };

  const handleDeploy = async () => {
    setIsDeploying(true);
    try {
      const payload = {
        name: botName,
        pair: pair,
        strategy: selectedStrategy || 'Custom',
        lot_size: lotSize,
        leverage: leverage,
        max_drawdown_percent: maxDrawdown,
        use_news_filter: useNewsFilter,
        max_spread_pips: maxSpread
      };

      const response = await fetch('/api/v1/forex/bots', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) throw new Error('Failed to deploy bot');
      
      alert('Forex Bot deployed successfully! It is now running in the background.');
      // Reset or redirect as needed
    } catch (error) {
      console.error(error);
      alert('Error deploying bot. Check console.');
    } finally {
      setIsDeploying(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
            <Settings className="text-[#D4AF37]" size={28} />
            Forex Bot Laboratory
          </h1>
          <p className="text-gray-500 mt-1">Configure and deploy 100% automated trading algorithms.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column - Configuration */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-6 rounded-3xl border bg-white/5 dark:bg-[#0A101D]/90 border-gray-200 dark:border-white/10 shadow-xl">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Sliders className="text-[#D4AF37]" size={20} />
                Algorithm Parameters
                </h2>
                <input 
                    type="text" 
                    value={botName}
                    onChange={(e) => setBotName(e.target.value)}
                    className="bg-transparent border-b border-white/20 text-white font-bold text-right focus:outline-none focus:border-[#D4AF37]" 
                    placeholder="Bot Name"
                />
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              {/* Pair Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Currency Pair</label>
                <select 
                    value={pair} 
                    onChange={(e) => setPair(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:outline-none focus:border-[#D4AF37]"
                >
                  <option>EUR/USD</option>
                  <option>GBP/JPY</option>
                  <option>XAU/USD (Gold)</option>
                  <option>GBP/USD</option>
                  <option>EUR/GBP</option>
                </select>
              </div>

              {/* Lot Size */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Position Sizing (Lots)</label>
                <div className="flex gap-2">
                  <select 
                    onChange={(e) => setLotSize(parseFloat(e.target.value))}
                    className="w-1/2 bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:outline-none focus:border-[#D4AF37]"
                  >
                    <option value="1.0">Standard (1.0)</option>
                    <option value="0.1">Mini (0.1)</option>
                    <option value="0.01">Micro (0.01)</option>
                  </select>
                  <input 
                    type="number" 
                    value={lotSize} 
                    onChange={(e) => setLotSize(parseFloat(e.target.value))}
                    step="0.01"
                    className="w-1/2 bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:outline-none focus:border-[#D4AF37]" 
                  />
                </div>
              </div>

              {/* Leverage */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Maximum Leverage</label>
                <select 
                    value={leverage}
                    onChange={(e) => setLeverage(parseInt(e.target.value))}
                    className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:outline-none focus:border-[#D4AF37]"
                >
                  <option value="50">1:50 (Safe)</option>
                  <option value="100">1:100 (Standard)</option>
                  <option value="500">1:500 (Aggressive)</option>
                </select>
              </div>

              {/* Risk Management */}
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Max Drawdown Limit</label>
                <div className="relative">
                  <input 
                    type="number" 
                    value={maxDrawdown} 
                    onChange={(e) => setMaxDrawdown(parseFloat(e.target.value))}
                    className="w-full bg-white/5 border border-white/10 rounded-xl p-3 pl-4 pr-10 text-white focus:outline-none focus:border-[#D4AF37]" 
                  />
                  <span className="absolute right-4 top-3.5 text-gray-500">%</span>
                </div>
              </div>
            </div>

            <div className="border-t border-white/10 pt-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <Globe className="text-[#D4AF37]" size={18} />
                Macro Environment Filters
              </h3>
              
              <div className="bg-[#D4AF37]/5 border border-[#D4AF37]/20 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-white flex items-center gap-2">
                    High-Impact News Filter
                  </h4>
                  <p className="text-xs text-gray-400 mt-1">Automatically pause trading 30 mins before NFP, FOMC, and CPI events.</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked={useNewsFilter} onChange={(e) => setUseNewsFilter(e.target.checked)} className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#D4AF37]"></div>
                </label>
              </div>
              
              <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-4 flex items-center justify-between mt-3">
                <div>
                  <h4 className="font-bold text-white flex items-center gap-2">
                    Max Spread Protection
                  </h4>
                  <p className="text-xs text-gray-400 mt-1">Halt execution if broker spreads widen unexpectedly (e.g., during rollover).</p>
                </div>
                <div className="flex items-center gap-2">
                  <input 
                    type="number" 
                    value={maxSpread} 
                    onChange={(e) => setMaxSpread(parseFloat(e.target.value))}
                    step="0.1"
                    className="w-16 bg-white/10 border border-white/10 rounded-lg p-1.5 text-sm text-center text-white focus:outline-none" 
                  />
                  <span className="text-xs text-gray-500">Pips</span>
                </div>
              </div>
            </div>
            
            <div className="mt-8 flex justify-end">
              <Button 
                onClick={handleDeploy}
                disabled={isDeploying}
                className="bg-gradient-to-r from-[#D4AF37] to-[#B8942E] text-slate-900 font-bold px-8 py-3 rounded-xl hover:shadow-[0_0_20px_rgba(212,175,55,0.4)] border-none flex items-center gap-2 disabled:opacity-50"
              >
                <Play size={18} />
                {isDeploying ? 'Deploying...' : 'Deploy Automation'}
              </Button>
            </div>
          </div>
        </div>

        {/* Right Column - Templates */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-4">
            <Zap className="text-[#D4AF37]" size={20} />
            AI Strategy Templates
          </h2>
          {templates.map((template, idx) => (
            <StrategyTemplateCard 
              key={idx} 
              {...template} 
              onSelect={() => handleTemplateSelect(template)}
            />
          ))}
          <Button variant="outline" className="w-full mt-4 border-dashed border-gray-600 text-gray-400 hover:text-white hover:border-gray-400">
            <Plus size={16} className="mr-2" />
            Create Custom Strategy
          </Button>
        </div>
      </div>
    </motion.div>
  );
};

export default ForexBotLab;
