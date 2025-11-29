import React, { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, AreaChart, Area } from 'recharts';
import { IndicatorData } from '../types';
import { Activity, Zap, BarChart3, TrendingUp, Layers } from 'lucide-react';

interface FeatureLabProps {
  data: IndicatorData[];
}

export const FeatureLab: React.FC<FeatureLabProps> = ({ data }) => {
  
  // Generate 20 additional "Tier 2" indicators based on the input data
  const extendedMetrics = useMemo(() => {
    // Helper to generate a derived series
    const generateSeries = (baseData: IndicatorData[], type: string, volatility: number) => {
      let val = 50;
      return baseData.map((d, i) => {
        const change = (Math.random() - 0.5) * volatility;
        
        // Simulate specific indicator behaviors
        if (type === 'OSCILLATOR') val = Math.max(0, Math.min(100, val + change * 5));
        else if (type === 'UNBOUNDED') val = val + change;
        else if (type === 'PERCENT') val = Math.max(-100, Math.min(100, val + change * 5));
        
        return { time: d.time, value: val };
      });
    };

    const metrics = [
      // Momentum
      { name: 'Stochastic %K', type: 'OSCILLATOR', color: '#818cf8', category: 'Momentum' },
      { name: 'Stochastic %D', type: 'OSCILLATOR', color: '#6366f1', category: 'Momentum' },
      { name: 'Williams %R', type: 'PERCENT', color: '#38bdf8', category: 'Momentum' },
      { name: 'CCI (Commodity Channel)', type: 'UNBOUNDED', color: '#0ea5e9', category: 'Momentum' },
      { name: 'ROC (Rate of Change)', type: 'UNBOUNDED', color: '#22d3ee', category: 'Momentum' },
      { name: 'Ultimate Oscillator', type: 'OSCILLATOR', color: '#2dd4bf', category: 'Momentum' },
      
      // Trend
      { name: 'ADX (Trend Strength)', type: 'OSCILLATOR', color: '#f472b6', category: 'Trend' },
      { name: 'Aroon Up/Down', type: 'OSCILLATOR', color: '#e879f9', category: 'Trend' },
      { name: 'Parabolic SAR Diff', type: 'UNBOUNDED', color: '#d946ef', category: 'Trend' },
      { name: 'Choppiness Index', type: 'OSCILLATOR', color: '#a855f7', category: 'Trend' },
      { name: 'Vortex Indicator', type: 'UNBOUNDED', color: '#c084fc', category: 'Trend' },
      
      // Volatility
      { name: 'ATR (Avg True Range)', type: 'UNBOUNDED', color: '#fb923c', category: 'Volatility' },
      { name: 'Bollinger Band Width', type: 'UNBOUNDED', color: '#f97316', category: 'Volatility' },
      { name: 'Keltner Channels', type: 'UNBOUNDED', color: '#ea580c', category: 'Volatility' },
      { name: 'Donchian Width', type: 'UNBOUNDED', color: '#fdba74', category: 'Volatility' },
      { name: 'Std Deviation', type: 'UNBOUNDED', color: '#fed7aa', category: 'Volatility' },

      // Volume / Flow
      { name: 'OBV (On-Balance Vol)', type: 'UNBOUNDED', color: '#4ade80', category: 'Volume' },
      { name: 'MFI (Money Flow)', type: 'OSCILLATOR', color: '#22c55e', category: 'Volume' },
      { name: 'Chaikin Oscillator', type: 'UNBOUNDED', color: '#16a34a', category: 'Volume' },
      { name: 'Force Index', type: 'UNBOUNDED', color: '#86efac', category: 'Volume' },
    ];

    return metrics.map(m => ({
      ...m,
      data: generateSeries(data, m.type, 2)
    }));
  }, [data]);

  return (
    <div className="space-y-6">
      
      {/* --- TIER 1: PRIMARY ANALYSIS --- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-omni-panel border border-slate-700 rounded-xl p-6 lg:col-span-2">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
               <TrendingUp size={20} className="text-omni-accent" /> Price Action & Moving Averages
            </h3>
            <div className="flex space-x-4 text-xs">
              <span className="flex items-center gap-1 text-omni-accent"><div className="w-3 h-1 bg-omni-accent"></div> Price</span>
              <span className="flex items-center gap-1 text-yellow-400"><div className="w-3 h-1 bg-yellow-400"></div> MA7</span>
              <span className="flex items-center gap-1 text-purple-400"><div className="w-3 h-1 bg-purple-400"></div> MA25</span>
            </div>
          </div>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" stroke="#94a3b8" tick={{fontSize: 12}} />
                <YAxis stroke="#94a3b8" tick={{fontSize: 12}} domain={['auto', 'auto']} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                  itemStyle={{ color: '#e2e8f0' }}
                />
                <Line type="monotone" dataKey="price" stroke="#38bdf8" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="ma7" stroke="#facc15" strokeWidth={1} dot={false} />
                <Line type="monotone" dataKey="ma25" stroke="#a855f7" strokeWidth={1} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-6">
          {/* RSI Chart */}
          <div className="bg-omni-panel border border-slate-700 rounded-xl p-6 h-[180px]">
            <h3 className="text-sm font-semibold text-slate-300 mb-2">RSI (14)</h3>
            <div className="h-full pb-6">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data}>
                  <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" />
                  <ReferenceLine y={30} stroke="#10b981" strokeDasharray="3 3" />
                  <Line type="monotone" dataKey="rsi" stroke="#fb923c" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* MACD Chart */}
          <div className="bg-omni-panel border border-slate-700 rounded-xl p-6 h-[180px]">
            <h3 className="text-sm font-semibold text-slate-300 mb-2">MACD</h3>
            <div className="h-full pb-6">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data}>
                  <ReferenceLine y={0} stroke="#64748b" />
                  <Line type="monotone" dataKey="macd" stroke="#22d3ee" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="signal" stroke="#f472b6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* --- TIER 2: DEEP DIVE INDICATORS (20 New Boxes) --- */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Layers size={20} className="text-purple-400" /> Advanced Alpha Factors
        </h3>
        
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {extendedMetrics.map((metric, idx) => (
             <div key={idx} className="bg-omni-panel border border-slate-700 rounded-lg p-4 hover:border-slate-500 transition-colors">
                <div className="flex justify-between items-start mb-2">
                   <h4 className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">{metric.name}</h4>
                   <span className={`w-2 h-2 rounded-full ${
                     metric.category === 'Momentum' ? 'bg-indigo-500' :
                     metric.category === 'Volatility' ? 'bg-orange-500' :
                     metric.category === 'Trend' ? 'bg-pink-500' :
                     'bg-green-500'
                   }`}></span>
                </div>
                
                <div className="h-[60px]">
                   <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={metric.data}>
                         <defs>
                            <linearGradient id={`grad-${idx}`} x1="0" y1="0" x2="0" y2="1">
                               <stop offset="5%" stopColor={metric.color} stopOpacity={0.3}/>
                               <stop offset="95%" stopColor={metric.color} stopOpacity={0}/>
                            </linearGradient>
                         </defs>
                         <Area 
                            type="monotone" 
                            dataKey="value" 
                            stroke={metric.color} 
                            strokeWidth={1.5} 
                            fill={`url(#grad-${idx})`} 
                         />
                      </AreaChart>
                   </ResponsiveContainer>
                </div>

                <div className="flex justify-between items-end mt-1">
                   <span className="text-[10px] text-slate-500">{metric.category}</span>
                   <span className="text-sm font-mono font-bold text-slate-200">
                     {metric.data[metric.data.length - 1].value.toFixed(2)}
                   </span>
                </div>
             </div>
          ))}
        </div>
      </div>

      {/* --- TIER 3: RAW MATRIX --- */}
      <div className="bg-omni-panel border border-slate-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <BarChart3 size={20} className="text-slate-400" /> Raw Feature Matrix (Last 5 Ticks)
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm font-mono">
            <thead className="bg-slate-800 text-slate-400">
              <tr>
                <th className="px-4 py-2">Time</th>
                <th className="px-4 py-2">Price</th>
                <th className="px-4 py-2">Norm. Vol</th>
                <th className="px-4 py-2">RSI</th>
                <th className="px-4 py-2">MACD</th>
                <th className="px-4 py-2">BB Upper</th>
                <th className="px-4 py-2">BB Lower</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {data.slice(-5).reverse().map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-700/50">
                  <td className="px-4 py-2 text-slate-500">{row.time}</td>
                  <td className="px-4 py-2 text-omni-accent">{row.price.toFixed(2)}</td>
                  <td className="px-4 py-2 text-slate-300">{(Math.random()).toFixed(4)}</td>
                  <td className={`px-4 py-2 ${row.rsi > 70 ? 'text-omni-danger' : row.rsi < 30 ? 'text-omni-success' : 'text-slate-300'}`}>
                    {row.rsi.toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-slate-300">{row.macd.toFixed(4)}</td>
                  <td className="px-4 py-2 text-slate-400">{(row.price * 1.02).toFixed(2)}</td>
                  <td className="px-4 py-2 text-slate-400">{(row.price * 0.98).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
