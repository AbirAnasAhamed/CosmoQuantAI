
import React, { useState, useEffect } from 'react';
import { Layout } from './components/Layout';
import { Dashboard } from './components/Dashboard';
import { DataNexus } from './components/DataNexus';
import { FeatureLab } from './components/FeatureLab';
import { BrainCore } from './components/BrainCore';
import { ExecutionEngine } from './components/ExecutionEngine';
import { Charting } from './components/Charting';
import { Backtest } from './components/Backtest';
import { BotManager } from './components/BotManager';
import { VertexForge } from './components/VertexForge';
import { Login } from './components/Login';
import { IndicatorData, TradingBot } from './types';
import { BrainCircuit } from 'lucide-react';

export default function App() {
  // Auth State
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authChecking, setAuthChecking] = useState(true);

  // App State
  const [activeTab, setActiveTab] = useState('dashboard');
  const [streamData, setStreamData] = useState<IndicatorData[]>([]);

  // GLOBAL BOT STATE (Lifted for Interconnectivity)
  const [bots, setBots] = useState<TradingBot[]>([
    {
      id: 'BOT-OMEGA',
      name: 'GENESIS-01 [Omni-Link]',
      pair: 'MULTI-ASSET',
      strategy: 'Ensemble (Full Swarm)',
      status: 'RUNNING',
      pnl: 5420.50,
      winRate: 88.5,
      tradesToday: 112,
      uptime: '15d 02h',
      allocation: 50000,
      modelVersion: 'v1.0.4-stable',
      lastTraining: '2023-10-24 14:00'
    },
    {
      id: 'BOT-001',
      name: 'Alpha Scalper X',
      pair: 'BTC/USDT',
      strategy: 'Scalping',
      status: 'RUNNING',
      pnl: 1245.50,
      winRate: 68.5,
      tradesToday: 42,
      uptime: '4d 12h',
      allocation: 5000,
      modelVersion: 'v2.1-light',
    },
    {
      id: 'BOT-002',
      name: 'Grid Master V2',
      pair: 'ETH/USDT',
      strategy: 'Grid',
      status: 'RUNNING',
      pnl: 340.20,
      winRate: 92.1,
      tradesToday: 156,
      uptime: '12d 04h',
      allocation: 8000,
      modelVersion: 'v1.8-grid',
    },
    {
      id: 'BOT-004',
      name: 'Arb Hunter',
      pair: 'ETH/BTC',
      strategy: 'Arbitrage',
      status: 'RUNNING',
      pnl: 56.70,
      winRate: 100,
      tradesToday: 3,
      uptime: '1d 08h',
      allocation: 10000
    },
    {
      id: 'BOT-006',
      name: 'Macro Sentiment',
      pair: 'EUR/USD',
      strategy: 'Swing',
      status: 'RUNNING',
      pnl: 890.10,
      winRate: 55.4,
      tradesToday: 5,
      uptime: '22d 10h',
      allocation: 15000
    }
  ]);

  // Check for persistent session on mount
  useEffect(() => {
    const session = localStorage.getItem('omni_auth_token');
    if (session) {
      setIsAuthenticated(true);
    }
    // Artificial delay for effect
    setTimeout(() => {
        setAuthChecking(false);
    }, 1000);
  }, []);

  // Simulate global stream data for Feature Lab and Brain Core
  useEffect(() => {
    if (!isAuthenticated) return;

    let price = 64000;
    const initialData: IndicatorData[] = [];
    
    // Generate initial history
    for(let i = 0; i < 50; i++) {
      price = price + (Math.random() - 0.5) * 200;
      initialData.push({
        time: new Date(Date.now() - (50-i) * 60000).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
        price,
        ma7: price * (1 + (Math.random() - 0.5) * 0.01),
        ma25: price * (1 + (Math.random() - 0.5) * 0.02),
        rsi: 40 + Math.random() * 40,
        macd: (Math.random() - 0.5) * 100,
        signal: (Math.random() - 0.5) * 80
      });
    }
    setStreamData(initialData);

    const interval = setInterval(() => {
      setStreamData(prev => {
        const lastPrice = prev[prev.length - 1].price;
        const newPrice = lastPrice + (Math.random() - 0.5) * 100;
        const newEntry: IndicatorData = {
          time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
          price: newPrice,
          ma7: newPrice * (1 + (Math.random() - 0.5) * 0.01),
          ma25: newPrice * (1 + (Math.random() - 0.5) * 0.02),
          rsi: 30 + Math.random() * 60,
          macd: (Math.random() - 0.5) * 50,
          signal: (Math.random() - 0.5) * 40
        };
        return [...prev.slice(1), newEntry];
      });
      
      // Update Bot PnL occasionally
      setBots(currentBots => 
        currentBots.map(bot => {
          if (bot.status !== 'RUNNING') return bot;
          // Randomly fluctuate PnL and trade count for running bots
          const pnlChange = (Math.random() - 0.4) * 5;
          const tradeIncrement = Math.random() > 0.95 ? 1 : 0;
          return {
            ...bot,
            pnl: bot.pnl + pnlChange,
            tradesToday: bot.tradesToday + tradeIncrement
          };
        })
      );
    }, 2000);

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const handleLogin = () => {
    localStorage.setItem('omni_auth_token', 'secure_session_v1');
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('omni_auth_token');
    setIsAuthenticated(false);
    setActiveTab('dashboard'); // Reset tab
  };

  // Vertex Forge Interconnect: Deploy new model to a specific bot
  const handleDeployModel = (botId: string, modelVersion: string, computeNode: string) => {
    setBots(prev => prev.map(b => 
      b.id === botId ? { 
        ...b, 
        modelVersion, 
        computeNode, 
        lastTraining: new Date().toLocaleTimeString() 
      } : b
    ));
    // Optionally switch to bots tab to show result
    // setActiveTab('bots'); 
  };

  const getGenesisBot = () => bots.find(b => b.id === 'BOT-OMEGA');

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard': return <Dashboard />;
      case 'nexus': return <DataNexus onNavigate={setActiveTab} />;
      case 'features': return <FeatureLab data={streamData} />;
      case 'charting': return <Charting />;
      case 'brain': return <BrainCore currentData={streamData[streamData.length - 1]} genesisBot={getGenesisBot()} />;
      case 'vertex': return <VertexForge bots={bots} onDeploy={handleDeployModel} />; // Connected
      case 'bots': return <BotManager bots={bots} setBots={setBots} />; // Connected
      case 'execution': return <ExecutionEngine />;
      case 'backtest': return <Backtest />;
      default: return <Dashboard />;
    }
  };

  if (authChecking) {
    return (
        <div className="h-screen w-screen bg-omni-bg flex flex-col items-center justify-center space-y-4">
            <div className="relative">
                <div className="w-16 h-16 bg-omni-accent/20 rounded-full animate-ping absolute top-0 left-0"></div>
                <div className="w-16 h-16 bg-gradient-to-tr from-omni-accent to-purple-600 rounded-full flex items-center justify-center shadow-lg shadow-omni-accent/50 relative z-10">
                    <BrainCircuit className="text-white w-8 h-8 animate-pulse" />
                </div>
            </div>
            <div className="text-omni-accent font-mono text-sm tracking-widest animate-pulse">INITIALIZING CORE SYSTEMS...</div>
        </div>
    );
  }

  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <Layout activeTab={activeTab} setActiveTab={setActiveTab} onLogout={handleLogout}>
      {renderContent()}
    </Layout>
  );
}
