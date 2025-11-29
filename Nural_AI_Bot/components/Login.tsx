
import React, { useState } from 'react';
import { BrainCircuit, Lock, User, ArrowRight, ShieldCheck, Activity, AlertCircle, Info } from 'lucide-react';

interface LoginProps {
  onLogin: () => void;
}

export const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const validateEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Strict Client-Side Validation
    if (!email || !password) {
      setError('Credentials required for neural link access.');
      return;
    }

    if (!validateEmail(email)) {
      setError('Invalid identity syntax. Access denied.');
      return;
    }

    if (password.length < 8) {
      setError('Password entropy too low. Minimum 8 characters required.');
      return;
    }

    setIsLoading(true);

    // Simulate Secure Handshake & Latency
    setTimeout(() => {
      // In a real microservices architecture, this would hit the Python Auth Service
      onLogin();
      setIsLoading(false);
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-omni-bg flex items-center justify-center p-6 relative overflow-hidden font-sans">
      {/* Dynamic Background Decor */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] right-[-5%] w-[500px] h-[500px] bg-purple-600/10 rounded-full blur-[100px] animate-pulse"></div>
        <div className="absolute bottom-[-10%] left-[-10%] w-[600px] h-[600px] bg-omni-accent/10 rounded-full blur-[100px] animate-pulse" style={{ animationDuration: '4s' }}></div>
      </div>

      <div className="w-full max-w-md bg-omni-panel/80 backdrop-blur-xl border border-slate-700 rounded-2xl shadow-2xl p-8 relative z-10 animate-in fade-in zoom-in duration-500">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-tr from-omni-accent to-purple-600 rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-omni-accent/20 ring-1 ring-white/10">
            <BrainCircuit className="text-white w-8 h-8" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">OmniTrade AI</h1>
          <p className="text-slate-400 text-sm mt-2 font-mono">Core Access Terminal v2.0</p>
        </div>

        {/* Demo Credentials Box */}
        <div className="mb-6 p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-xs text-indigo-300 font-mono relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500"></div>
          <div className="flex items-center gap-2 mb-2 font-bold uppercase tracking-wider text-indigo-400">
            <Info size={12} /> Demo Access Override
          </div>
          <div className="flex justify-between items-center mb-1 group-hover:bg-indigo-500/10 p-1 rounded transition-colors cursor-pointer" onClick={() => setEmail('admin@omnitrade.ai')}>
            <span className="text-slate-400">Identity:</span>
            <span className="font-bold select-all">admin@omnitrade.ai</span>
          </div>
          <div className="flex justify-between items-center group-hover:bg-indigo-500/10 p-1 rounded transition-colors cursor-pointer" onClick={() => setPassword('admin12345')}>
            <span className="text-slate-400">Passcode:</span>
            <span className="font-bold select-all">admin12345</span>
          </div>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider ml-1">Identity</label>
            <div className="relative group">
              <User className="absolute left-3 top-3 text-slate-500 group-focus-within:text-omni-accent transition-colors" size={20} />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operative@omnitrade.ai"
                className="w-full bg-slate-800/50 border border-slate-700 rounded-xl py-3 pl-10 pr-4 text-white placeholder-slate-600 focus:outline-none focus:border-omni-accent focus:ring-1 focus:ring-omni-accent transition-all"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider ml-1">Passcode</label>
            <div className="relative group">
              <Lock className="absolute left-3 top-3 text-slate-500 group-focus-within:text-omni-accent transition-colors" size={20} />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-800/50 border border-slate-700 rounded-xl py-3 pl-10 pr-4 text-white placeholder-slate-600 focus:outline-none focus:border-omni-accent focus:ring-1 focus:ring-omni-accent transition-all"
              />
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-xs flex items-center gap-2 animate-in slide-in-from-top-2">
              <AlertCircle size={14} className="shrink-0" />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full py-4 rounded-xl font-bold text-lg tracking-wide shadow-lg transition-all flex items-center justify-center gap-2 group ${
              isLoading
                ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-omni-accent to-blue-600 hover:from-blue-500 hover:to-omni-accent text-white shadow-blue-900/20'
            }`}
          >
            {isLoading ? (
              <>
                <Activity className="animate-spin" size={20} /> VERIFYING NEURAL SIGNATURE...
              </>
            ) : (
              <>
                INITIATE SESSION <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-slate-700/50 text-center">
          <p className="text-xs text-slate-500 flex items-center justify-center gap-2">
            <ShieldCheck size={12} className="text-omni-success" />
            <span>End-to-End Encrypted</span>
            <span className="w-1 h-1 rounded-full bg-slate-600"></span>
            <span className="text-omni-success">System Online</span>
          </p>
        </div>
      </div>
    </div>
  );
};
