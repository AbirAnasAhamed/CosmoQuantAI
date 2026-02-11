
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Activity, Play, Square, Terminal, TrendingUp, DollarSign, Clock, BarChart2, FastForward } from 'lucide-react';
import Button from '@/components/common/Button';
import Card from '@/components/common/Card';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface LogMessage {
    time: string;
    message: string;
    type: 'INFO' | 'fill' | 'market'; // Simplified types
}

const EventDrivenSimulator: React.FC = () => {
    const [isRunning, setIsRunning] = useState(false);
    const [symbol, setSymbol] = useState('BTC/USDT');
    const [logs, setLogs] = useState<LogMessage[]>([]);
    const [marketData, setMarketData] = useState<any[]>([]);
    const [pnl, setPnl] = useState(0);
    const [holdings, setHoldings] = useState(0);
    const [price, setPrice] = useState(0);
    const [playbackSpeed, setPlaybackSpeed] = useState<number>(0); // 0 = Max

    const socketRef = useRef<WebSocket | null>(null);
    const logEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        logEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [logs]);

    // WebSocket Connection Logic
    const connect = useCallback(() => {
        if (socketRef.current?.readyState === WebSocket.OPEN) return;

        const wsParams = isRunning ? `?symbol=${symbol}` : "";
        const ws = new WebSocket(`ws://localhost:8000/api/v1/simulation/ws/simulation${wsParams}`);

        ws.onopen = () => {
            addLog("System: Connected to Simulation Server", 'INFO');
            if (isRunning) {
                ws.send(JSON.stringify({ action: "START", symbol }));
                // Send initial speed
                ws.send(JSON.stringify({ type: "UPDATE_SPEED", speed: playbackSpeed }));
            }
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === "MARKET") {
                setPrice(data.price);
                setMarketData(prev => {
                    const newData = [...prev, { time: data.time.split('T')[1].split('.')[0], price: data.price }];
                    if (newData.length > 50) return newData.slice(newData.length - 50);
                    return newData;
                });
            } else if (data.type === "LOG") {
                addLog(data.message, 'INFO');
            } else if (data.type === "FILL") {
                addLog(`FILLED: ${data.direction} ${data.quantity} @ ${data.price}`, 'fill');

                // Simple PnL/Holdings Simulation update (Logic normally on backend, but visualization here)
                if (data.direction === 'BUY') {
                    setHoldings(h => h + data.quantity);
                    setPnl(p => p - data.commission); // Commission cost
                } else {
                    setHoldings(h => h - data.quantity);
                    setPnl(p => p - data.commission);
                }
            } else if (data.type === "SYSTEM") {
                addLog(data.message, 'INFO');
            }
        };

        ws.onclose = () => {
            addLog("System: Disconnected", 'INFO');
            setIsRunning(false);
        };

        socketRef.current = ws;
    }, [isRunning, symbol]);

    // Handle Speed Change properly
    useEffect(() => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify({ type: "UPDATE_SPEED", speed: playbackSpeed }));
        }
    }, [playbackSpeed]);

    useEffect(() => {
        return () => {
            if (socketRef.current) {
                socketRef.current.close();
            }
        };
    }, []);

    const addLog = (message: string, type: 'INFO' | 'fill' | 'market') => {
        setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), message, type }]);
    };

    const handleStart = () => {
        setIsRunning(true);
        setLogs([]);
        setMarketData([]);
        setPnl(0);
        setHoldings(0);

        if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
            connect();
            setTimeout(() => {
                if (socketRef.current?.readyState === WebSocket.OPEN) {
                    socketRef.current.send(JSON.stringify({ action: "START", symbol }));
                    socketRef.current.send(JSON.stringify({ type: "UPDATE_SPEED", speed: playbackSpeed }));
                }
            }, 100);
        } else {
            socketRef.current.send(JSON.stringify({ action: "START", symbol }));
            socketRef.current.send(JSON.stringify({ type: "UPDATE_SPEED", speed: playbackSpeed }));
        }
    };

    const handleStop = () => {
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify({ action: "STOP" }));
        }
        setIsRunning(false);
    };

    const speedOptions = [
        { label: '1x', value: 1.0 },
        { label: '10x', value: 10.0 },
        { label: '100x', value: 100.0 },
        { label: 'MAX', value: 0 },
    ];

    return (
        <div className="flex h-[calc(100vh-8rem)] gap-6 p-2">
            {/* Left Configuration Panel */}
            <div className="w-1/3 flex flex-col gap-6">
                <Card className="p-6 bg-white dark:bg-[#1e293b] border-slate-200 dark:border-slate-700 shadow-xl">
                    <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
                        <Activity className="text-brand-primary" />
                        Simulation Config
                    </h2>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Asset Symbol</label>
                            <input
                                type="text"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value)}
                                className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-primary outline-none transaction-all"
                            />
                        </div>

                        {/* Speed Control */}
                        <div>
                            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-2 flex items-center gap-2">
                                <FastForward size={16} />
                                Playback Speed
                            </label>
                            <div className="flex bg-slate-100 dark:bg-slate-900 p-1 rounded-lg">
                                {speedOptions.map((opt) => (
                                    <button
                                        key={opt.label}
                                        onClick={() => setPlaybackSpeed(opt.value)}
                                        className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${playbackSpeed === opt.value
                                                ? 'bg-white dark:bg-slate-700 text-brand-primary shadow-sm'
                                                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                                            }`}
                                    >
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Timeframe</label>
                                <select className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-primary outline-none">
                                    <option>1m</option>
                                    <option>5m</option>
                                    <option>1h</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Initial Cash</label>
                                <input
                                    type="number"
                                    defaultValue={10000}
                                    className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-primary outline-none"
                                />
                            </div>
                        </div>

                        {!isRunning ? (
                            <Button
                                onClick={handleStart}
                                className="w-full mt-4 bg-brand-primary hover:bg-brand-secondary text-white py-3 rounded-xl font-bold text-lg shadow-lg shadow-brand-primary/20 flex items-center justify-center gap-2"
                            >
                                <Play size={20} fill="currentColor" />
                                START SIMULATION
                            </Button>
                        ) : (
                            <Button
                                onClick={handleStop}
                                className="w-full mt-4 bg-red-500 hover:bg-red-600 text-white py-3 rounded-xl font-bold text-lg shadow-lg shadow-red-500/20 flex items-center justify-center gap-2"
                            >
                                <Square size={20} fill="currentColor" />
                                STOP SIMULATION
                            </Button>
                        )}
                    </div>
                </Card>

                {/* Real-time Stats */}
                <div className="grid grid-cols-2 gap-4">
                    <Card className="p-4 bg-white dark:bg-[#1e293b] border-l-4 border-emerald-500">
                        <p className="text-sm text-slate-500">Net PnL</p>
                        <p className={`text-2xl font-bold ${pnl >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                            ${pnl.toFixed(2)}
                        </p>
                    </Card>
                    <Card className="p-4 bg-white dark:bg-[#1e293b] border-l-4 border-blue-500">
                        <p className="text-sm text-slate-500">Holdings</p>
                        <p className="text-2xl font-bold text-slate-800 dark:text-white">
                            {holdings}
                        </p>
                    </Card>
                </div>
            </div>

            {/* Right Monitor Panel */}
            <div className="flex-1 flex flex-col gap-6">
                {/* Live Chart */}
                <Card className="h-1/3 bg-white dark:bg-[#1e293b] p-4 relative overflow-hidden">
                    <div className="absolute top-4 left-4 z-10 bg-white/10 backdrop-blur-md px-3 py-1 rounded-full border border-white/10">
                        <span className="text-xs font-mono text-white flex items-center gap-2">
                            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                            LIVE FEED {playbackSpeed === 0 ? '(MAX)' : `(${playbackSpeed}x)`}
                        </span>
                    </div>
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={marketData}>
                            <defs>
                                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                            <XAxis dataKey="time" hide />
                            <YAxis domain={['auto', 'auto']} orientation="right" tick={{ fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#fff' }}
                                itemStyle={{ color: '#10b981' }}
                            />
                            <Area type="monotone" dataKey="price" stroke="#10b981" fillOpacity={1} fill="url(#colorPrice)" strokeWidth={2} />
                        </AreaChart>
                    </ResponsiveContainer>
                </Card>

                {/* System Terminal */}
                <Card className="flex-1 bg-black border-slate-800 font-mono text-sm p-0 flex flex-col shadow-2xl overflow-hidden relative">
                    <div className="bg-slate-900/50 p-2 border-b border-slate-800 flex justify-between items-center px-4">
                        <span className="text-slate-400 flex items-center gap-2">
                            <Terminal size={14} />
                            Event Loop Output
                        </span>
                        <span className="text-xs text-slate-600">v1.0.0</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 space-y-1 custom-scrollbar">
                        {logs.length === 0 && (
                            <div className="h-full flex flex-col items-center justify-center text-slate-600 opacity-50">
                                <Terminal size={48} className="mb-4" />
                                <p>Waiting for simulation start...</p>
                            </div>
                        )}
                        {logs.map((log, i) => (
                            <div key={i} className={`flex gap-3 ${log.type === 'fill' ? 'text-yellow-400' : 'text-green-500'}`}>
                                <span className="text-slate-600 select-none">[{log.time}]</span>
                                <span>{log.type === 'fill' ? '⚡' : '>'} {log.message}</span>
                            </div>
                        ))}
                        <div ref={logEndRef} />
                    </div>
                </Card>
            </div>
        </div>
    );
};

export default EventDrivenSimulator;
