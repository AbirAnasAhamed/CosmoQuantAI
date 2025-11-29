
import React from 'react';
import { LayoutDashboard, Database, Activity, BrainCircuit, Zap, Menu, Bell, LogOut, LineChart, History, Bot, CloudLightning } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onLogout: () => void;
}

export const Layout: React.FC<LayoutProps> = ({ children, activeTab, setActiveTab, onLogout }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'nexus', label: 'Data Nexus (UDN)', icon: Database },
    { id: 'features', label: 'Feature Lab', icon: Activity },
    { id: 'charting', label: 'Pro Charts', icon: LineChart },
    { id: 'brain', label: 'The Brain (AI)', icon: BrainCircuit },
    { id: 'vertex', label: 'Vertex Forge', icon: CloudLightning }, // New Item
    { id: 'bots', label: 'Bot Fleet', icon: Bot },
    { id: 'execution', label: 'Execution Engine', icon: Zap },
    { id: 'backtest', label: 'Strategy Backtester', icon: History },
  ];

  return (
    <div className="flex h-screen bg-omni-bg text-slate-200 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-omni-panel border-r border-slate-700 hidden md:flex flex-col">
        <div className="p-6 border-b border-slate-700 flex items-center space-x-3">
          <div className="w-8 h-8 bg-omni-accent rounded-lg flex items-center justify-center">
            <BrainCircuit className="text-omni-bg w-5 h-5" />
          </div>
          <span className="font-bold text-lg tracking-wider text-white">OmniTrade AI</span>
        </div>
        
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                activeTab === item.id 
                  ? 'bg-omni-accent/20 text-omni-accent border-l-4 border-omni-accent' 
                  : 'hover:bg-slate-700/50 text-slate-400 hover:text-white'
              }`}
            >
              <item.icon size={20} />
              <span className="font-medium">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-700 space-y-4">
           {/* Logout Button */}
           <button 
             onClick={onLogout}
             className="w-full flex items-center space-x-3 px-4 py-2 rounded-lg text-slate-400 hover:text-omni-danger hover:bg-omni-danger/10 transition-colors"
           >
             <LogOut size={20} />
             <span className="font-medium">Termin. Session</span>
           </button>

          <div className="pt-2">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
              <span>System Status</span>
              <span className="text-omni-success">ONLINE</span>
            </div>
            <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-omni-success w-full animate-pulse"></div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-omni-panel/50 border-b border-slate-700 flex items-center justify-between px-6 backdrop-blur-sm z-10">
          <div className="flex items-center space-x-4">
            <button className="md:hidden text-slate-400 hover:text-white">
              <Menu size={24} />
            </button>
            <h2 className="text-xl font-semibold text-white">
              {navItems.find(i => i.id === activeTab)?.label}
            </h2>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">
              <span className="w-2 h-2 rounded-full bg-omni-success animate-pulse"></span>
              <span className="text-xs font-mono text-omni-success">LIVE FEED</span>
            </div>
            <button className="relative p-2 text-slate-400 hover:text-white transition-colors">
              <Bell size={20} />
              <span className="absolute top-1 right-1 w-2 h-2 bg-omni-danger rounded-full"></span>
            </button>
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-omni-accent to-purple-500 ring-2 ring-slate-700"></div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-6 scroll-smooth">
          {children}
        </div>
      </main>
    </div>
  );
};
