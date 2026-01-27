import React, { useState, useEffect, useMemo, useCallback } from 'react';
import api from '@/services/client';
import {
    ResponsiveContainer, PieChart, Pie, Cell, ComposedChart, Line, Area,
    XAxis, YAxis, CartesianGrid, Tooltip, Bar, Treemap, Legend
} from 'recharts';
import { useTheme } from '@/context/ThemeContext';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import type { SentimentSource, SentimentLabel, SentimentHeatmapItem } from '@/types';
import { useToast } from '@/context/ToastContext';
import { Loader2, RefreshCw, Maximize2, ThumbsUp, ThumbsDown, User, Twitter } from 'lucide-react';
import SocialDominanceChart from '@/components/features/sentiment/SocialDominanceChart';
import InfluencerWatchlist, { Influencer } from '@/components/features/sentiment/InfluencerWatchlist';
import SentimentGeoMap from '@/components/features/sentiment/SentimentGeoMap';

const pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'];
const PIE_COLORS = { 'Positive': '#10B981', 'Negative': '#F43F5E', 'Neutral': '#64748B' };

// --- Sub Components ---

// --- Sub Components ---

const VerifyButton = ({ content }: { content: string }) => {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);

    const handleVerify = async (e: any) => {
        e.preventDefault();
        e.stopPropagation();
        setLoading(true);
        try {
            const res = await api.post('/sentiment/verify-news', { content });
            setResult(res.data);
        } catch (error) {
            console.error("Verification failed", error);
        } finally {
            setLoading(false);
        }
    };

    if (result) {
        return (
            <div className={`mt-2 p-2 rounded text-[10px] border ${result.score > 70 ? 'bg-green-500/10 border-green-500/20 text-green-600' : 'bg-red-500/10 border-red-500/20 text-red-600'}`}>
                <div className="font-bold flex items-center gap-1">
                    {result.score > 70 ? '✅ Credible' : '⚠️ Potential FUD'} ({result.score}/100)
                </div>
                <div className="opacity-80 mt-1">{result.reason}</div>
            </div>
        );
    }

    return (
        <button
            onClick={handleVerify}
            disabled={loading}
            className="text-[10px] flex items-center gap-1 text-slate-400 hover:text-brand-primary transition-colors border border-slate-200 dark:border-slate-800 px-2 py-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800"
        >
            {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <span className="text-blue-500">🛡️</span>}
            {loading ? 'Analyzing...' : 'Verify Fact'}
        </button>
    );
};

const ModernHeatmapContent = (props: any) => {
    const { x, y, width, height, name, sentimentScore, marketCap, symbol } = props;
    const score = typeof sentimentScore === 'number' ? sentimentScore : 0;

    if (!width || !height || width < 0 || height < 0) return null;

    // Dynamic Styling based on Score
    let gradient = "from-slate-700/50 to-slate-900/90";
    let borderColor = "border-slate-600/30";
    let glow = "";
    let textColor = "text-slate-200";
    let scoreColor = "text-slate-400";

    if (score > 0.5) {
        gradient = "from-emerald-500/30 via-emerald-600/20 to-emerald-900/90";
        borderColor = "border-emerald-500/50";
        glow = "shadow-[0_0_15px_rgba(16,185,129,0.3)]";
        textColor = "text-emerald-100";
        scoreColor = "text-emerald-400";
    } else if (score > 0.1) {
        gradient = "from-teal-500/20 via-teal-600/10 to-slate-900/90";
        borderColor = "border-teal-500/40";
        textColor = "text-teal-50";
        scoreColor = "text-teal-400";
    } else if (score < -0.5) {
        gradient = "from-rose-500/30 via-rose-600/20 to-rose-900/90";
        borderColor = "border-rose-500/50";
        glow = "shadow-[0_0_15px_rgba(244,63,94,0.3)]";
        textColor = "text-rose-100";
        scoreColor = "text-rose-400";
    } else if (score < -0.1) {
        gradient = "from-orange-500/20 via-orange-600/10 to-slate-900/90";
        borderColor = "border-orange-500/40";
        textColor = "text-orange-50";
        scoreColor = "text-orange-400";
    }

    // Only render detail if box is big enough
    const showDetail = width > 60 && height > 50;
    const showMini = width > 30 && height > 30;

    return (
        <foreignObject x={x + 2} y={y + 2} width={width - 4} height={height - 4}>
            <div
                className={`w-full h-full rounded-xl border ${borderColor} bg-gradient-to-br ${gradient} backdrop-blur-md flex flex-col items-center justify-center transition-all duration-300 hover:scale-[0.98] hover:brightness-110 ${glow} overflow-hidden relative group`}
            >
                {/* Background Grid Pattern Overlay */}
                <div className="absolute inset-0 opacity-10 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] mix-blend-overlay"></div>

                {/* Content */}
                <div className="z-10 flex flex-col items-center text-center p-1">
                    {showMini && (
                        <span className={`font-black tracking-tighter ${width < 50 ? 'text-[10px]' : 'text-sm'} ${textColor} drop-shadow-md`}>
                            {name}
                        </span>
                    )}

                    {showDetail && (
                        <>
                            <span className={`text-[10px] font-mono mt-0.5 font-bold ${scoreColor}`}>
                                {score > 0 ? '+' : ''}{score.toFixed(2)}
                            </span>
                            <span className="text-[8px] opacity-60 text-white mt-1 uppercase tracking-widest scale-75">
                                {(marketCap / 1_000_000_000).toFixed(0)}B
                            </span>
                        </>
                    )}
                </div>
            </div>
        </foreignObject>
    );
};

const AnimatedNumber = ({ value, prefix = '', suffix = '', className = '' }: any) => {
    return <span className={className}>{prefix}{typeof value === 'number' ? value.toFixed(2) : value}{suffix}</span>;
};

const SentimentOrb = ({ score, momentum, volume }: any) => {
    // Determine State
    const mood = score > 0.2 ? "Bullish" : score < -0.2 ? "Bearish" : "Neutral";

    // Advanced Color Palettes for Neon/Holographic Effect
    const themes = {
        Bullish: {
            primary: "emerald",
            hex: "#10b981",
            gradient: "from-emerald-500 via-teal-400 to-green-300",
            shadow: "shadow-[0_0_50px_-12px_rgba(16,185,129,0.6)]",
            textGlow: "drop-shadow-[0_0_10px_rgba(16,185,129,0.8)]"
        },
        Bearish: {
            primary: "rose",
            hex: "#f43f5e",
            gradient: "from-rose-500 via-red-500 to-orange-400",
            shadow: "shadow-[0_0_50px_-12px_rgba(244,63,94,0.6)]",
            textGlow: "drop-shadow-[0_0_10px_rgba(244,63,94,0.8)]"
        },
        Neutral: {
            primary: "indigo",
            hex: "#6366f1",
            gradient: "from-indigo-500 via-blue-400 to-cyan-300",
            shadow: "shadow-[0_0_50px_-12px_rgba(99,102,241,0.6)]",
            textGlow: "drop-shadow-[0_0_10px_rgba(99,102,241,0.8)]"
        }
    };

    const theme = themes[mood as keyof typeof themes];
    const rotationSpeed = Math.max(3, 15 - Math.abs(momentum));

    return (
        <div className="relative w-full h-full flex flex-col items-center justify-center overflow-hidden bg-[#0f172a] rounded-2xl border border-slate-700/50">
            {/* --- Background Cyber Grid --- */}
            <div className="absolute inset-0 opacity-20 pointer-events-none"
                style={{
                    backgroundImage: `linear-gradient(${theme.hex}22 1px, transparent 1px), linear-gradient(90deg, ${theme.hex}22 1px, transparent 1px)`,
                    backgroundSize: '40px 40px',
                    maskImage: 'radial-gradient(circle at center, black 40%, transparent 80%)'
                }}>
            </div>

            {/* --- Main Reactor Core --- */}
            {/* --- Main Reactor Core --- */}
            <div className="relative flex items-center justify-center w-72 h-72">

                {/* 1. Outer Static Ring with Ticks */}
                <div className="absolute inset-0 border border-slate-700/50 rounded-full opacity-50"></div>

                {/* 2. Rotating Dash Ring (Clockwise) */}
                <div className="absolute inset-2 border-2 border-dashed border-slate-600/60 rounded-full animate-[spin_10s_linear_infinite]"
                    style={{ animationDuration: `${rotationSpeed * 1.5}s` }}></div>

                {/* 3. Counter-Rotating Arc Ring (Holographic) */}
                <div className={`absolute inset-4 rounded-full border-t-2 border-b-2 border-l-0 border-r-0 border-${theme.primary}-500/50 animate-[spin_8s_linear_infinite_reverse] blur-[1px]`}
                    style={{ animationDuration: `${rotationSpeed}s` }}>
                </div>

                {/* 4. Pulsing Glow Layer */}
                {/* 4. Pulsing Glow Layer */}
                <div className={`absolute w-56 h-56 bg-${theme.primary}-500/20 rounded-full blur-xl animate-pulse ${theme.shadow}`}></div>

                {/* 5. Center Core (Glassmorphism) */}
                <div className={`relative w-48 h-48 rounded-full bg-gradient-to-br from-slate-800/90 to-slate-900/90 flex flex-col items-center justify-center 
                    backdrop-blur-xl border border-white/10 shadow-2xl z-10 overflow-hidden group transition-all duration-500 hover:scale-105`}>

                    {/* Inner Shine */}
                    <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-white/10 to-transparent opacity-50 pointer-events-none"></div>

                    {/* Value Display */}
                    <div className="flex flex-col items-center z-20">
                        <span className={`text-[10px] uppercase font-bold tracking-[0.2em] text-slate-400 mb-1`}>Sentiment</span>
                        <span className={`text-6xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-b ${theme.gradient} ${theme.textGlow}`}>
                            {score.toFixed(2)}
                        </span>

                        <div className={`mt-2 px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest border border-${theme.primary}-500/30 bg-${theme.primary}-500/10 text-${theme.primary}-400`}>
                            {mood}
                        </div>
                    </div>

                    {/* Orbiting Particle */}
                    <div className="absolute inset-0 animate-[spin_3s_linear_infinite]">
                        <div className={`absolute top-2 left-1/2 w-1.5 h-1.5 bg-${theme.primary}-400 rounded-full shadow-[0_0_10px_currentColor]`}></div>
                    </div>
                </div>
            </div>

            {/* --- Bottom Status Panel (HUD Style) --- */}
            <div className="mt-8 w-full px-8 flex flex-col items-center gap-4 relative z-10">
                {/* Dynamic Unified Trade Button */}
                <button className={`w-full group relative overflow-hidden px-4 py-3 rounded-xl bg-${theme.primary}-500/10 border border-${theme.primary}-500/30 hover:bg-${theme.primary}-500/20 transition-all shadow-[0_0_20px_rgba(0,0,0,0.2)]`}>
                    <div className={`absolute inset-0 bg-${theme.primary}-500/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300`}></div>
                    <div className="relative flex items-center justify-center gap-3">
                        <span className="text-xl animate-bounce">
                            {score > 0.1 ? '🚀' : score < -0.1 ? '🔻' : '⚖️'}
                        </span>
                        <span className={`text-sm font-black uppercase tracking-widest text-${theme.primary}-400 group-hover:text-${theme.primary}-300`}>
                            {score > 0.1 ? 'LONG / BUY' : score < -0.1 ? 'SHORT / SELL' : 'HOLD'}
                        </span>
                    </div>
                </button>

                {/* Metrics HUD */}
                <div className="flex justify-between w-full text-xs font-mono border-t border-slate-700/50 pt-3 mt-1">
                    <div className="flex flex-col items-center gap-1 group cursor-default">
                        <span className="text-slate-500 uppercase text-[10px]">Momentum</span>
                        <span className={`text-slate-300 font-bold group-hover:text-${theme.primary}-400 transition-colors`}>{momentum.toFixed(2)}</span>
                    </div>
                    <div className={`w-px h-8 bg-gradient-to-b from-transparent via-slate-600 to-transparent`}></div>
                    <div className="flex flex-col items-center gap-1 group cursor-default">
                        <span className="text-slate-500 uppercase text-[10px]">Active Vol</span>
                        <div className="flex items-center gap-1">
                            <span className={`animate-pulse text-${theme.primary}-500`}>⚡</span>
                            <span className={`text-slate-300 font-bold group-hover:text-${theme.primary}-400 transition-colors`}>{volume}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

// ✅ UPDATED: Colorful Gauge Design with Countdown Timer
// ✅ UPDATED: Futuristic Segmented Arc Design
const FearGreedFlux = ({ score, classification }: any) => {
    const [timeLeft, setTimeLeft] = useState<string>('--h --m');

    // Countdown logic
    useEffect(() => {
        const updateTimer = () => {
            const now = new Date();
            const nextUpdate = new Date();
            nextUpdate.setUTCHours(24, 0, 0, 0);
            const diff = nextUpdate.getTime() - now.getTime();
            if (diff > 0) {
                const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
                const minutes = Math.floor((diff / (1000 * 60)) % 60);
                setTimeLeft(`${hours}h ${minutes}m`);
            } else {
                setTimeLeft('Updating...');
            }
        };
        updateTimer();
        const interval = setInterval(updateTimer, 60000);
        return () => clearInterval(interval);
    }, []);

    // Color Logic
    const getColor = (s: number) => {
        if (s < 25) return { hex: '#ef4444', label: 'Extreme Fear', tail: 'bg-red-500', text: 'text-red-500' };
        if (s < 45) return { hex: '#f97316', label: 'Fear', tail: 'bg-orange-500', text: 'text-orange-500' };
        if (s < 55) return { hex: '#eab308', label: 'Neutral', tail: 'bg-yellow-500', text: 'text-yellow-500' };
        if (s < 75) return { hex: '#84cc16', label: 'Greed', tail: 'bg-lime-500', text: 'text-lime-500' };
        return { hex: '#22c55e', label: 'Extreme Greed', tail: 'bg-emerald-500', text: 'text-emerald-500' };
    };

    const theme = getColor(score);
    const totalSegments = 40;
    const activeSegments = Math.round((score / 100) * totalSegments);

    return (
        <div className="flex flex-col items-center justify-center h-full relative overflow-hidden bg-slate-50 dark:bg-[#0f172a] p-4">
            {/* Background Noise */}
            <div className="absolute inset-0 opacity-20 bg-[url('https://grainy-gradients.vercel.app/noise.svg')]"></div>

            {/* Header */}
            <div className="relative z-10 flex flex-col items-center mb-4 mt-4">
                <h4 className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">
                    Fear & Greed
                </h4>
                <div className="flex items-center gap-2 mt-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
                    <span className="text-[9px] font-mono text-slate-500 uppercase">Live Index</span>
                </div>
            </div>

            {/* Main Gauge */}
            <div className="relative w-full max-w-[280px] aspect-[2/1] flex items-end justify-center mb-2">

                {/* SVG Segmented Arc */}
                <svg viewBox="0 0 300 160" className="w-full h-full overflow-visible">
                    <defs>
                        <filter id="glow-arc" x="-20%" y="-20%" width="140%" height="140%">
                            <feGaussianBlur stdDeviation="4" result="blur" />
                            <feComposite in="SourceGraphic" in2="blur" operator="over" />
                        </filter>
                    </defs>

                    {/* Render Segments */}
                    {Array.from({ length: totalSegments }).map((_, i) => {
                        const angle = 180 + (i / (totalSegments - 1)) * 180;
                        const radius = 120;
                        const x1 = 150 + radius * Math.cos((angle * Math.PI) / 180);
                        const y1 = 140 + radius * Math.sin((angle * Math.PI) / 180);

                        const innerRadius = 100;
                        const x2 = 150 + innerRadius * Math.cos((angle * Math.PI) / 180);
                        const y2 = 140 + innerRadius * Math.sin((angle * Math.PI) / 180);

                        const isActive = i < activeSegments;

                        return (
                            <line
                                key={i}
                                x1={x1} y1={y1} x2={x2} y2={y2}
                                stroke={isActive ? theme.hex : '#334155'}
                                strokeWidth="4"
                                strokeLinecap="round"
                                className={`transition-all duration-300 ${isActive ? 'opacity-100' : 'opacity-20'}`}
                                style={{ filter: isActive ? 'url(#glow-arc)' : 'none' }}
                            />
                        );
                    })}

                    {/* Inner Needle / Indicator Base */}
                    <circle cx="150" cy="140" r="80" className="fill-transparent stroke-slate-800/50 stroke-1" />
                </svg>

                {/* Central Digital Score */}
                <div className="absolute bottom-0 flex flex-col items-center transform translate-y-4">
                    <span className={`text-6xl font-black tracking-tighter transition-colors duration-500 drop-shadow-lg ${theme.text}`}
                        style={{ textShadow: `0 0 30px ${theme.hex}50` }}
                    >
                        {Math.round(score)}
                    </span>
                    <div className={`mt-2 px-3 py-1 rounded-lg border border-white/10 bg-white/5 backdrop-blur-md`}>
                        <span className={`text-xs font-bold uppercase tracking-widest ${theme.text}`}>
                            {classification}
                        </span>
                    </div>
                </div>
            </div>

            {/* Footer Timer */}
            <div className="mt-8 flex items-center gap-2 text-[10px] bg-slate-800/50 px-3 py-1.5 rounded-full border border-slate-700/50">
                <span className="text-slate-400">Next Update:</span>
                <span className="font-mono text-slate-200">{timeLeft}</span>
            </div>
        </div>
    );
};



// --- New Feature: Community Poll Component (Redesigned) ---
const CommunityPoll = ({ stats, onVote }: { stats: any, onVote: any }) => {
    const [hasVoted, setHasVoted] = useState(false);

    // Use props instead of local state
    const bullishPercent = stats.bullish_pct || 0;
    const bearishPercent = stats.bearish_pct || 0;
    const totalVotes = stats.total_votes || 0;

    const handleLocalVote = (type: 'bullish' | 'bearish') => {
        if (hasVoted) return;
        onVote(type);
        setHasVoted(true);
    };

    return (
        <div className="h-full flex flex-col relative overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 backdrop-blur-md shadow-sm p-5">
            <h3 className="text-sm font-bold text-slate-800 dark:text-white text-center mb-1">
                Market Sentiment Poll
            </h3>
            <p className="text-[10px] text-center text-slate-400 mb-6 uppercase tracking-wider">
                What's your outlook?
            </p>

            {!hasVoted && totalVotes === 0 ? (
                <div className="flex flex-col gap-3 h-full justify-center">
                    <button
                        onClick={() => handleLocalVote('bullish')}
                        className="group relative flex items-center justify-between p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10 transition-all overflow-hidden"
                    >
                        <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/0 via-emerald-500/0 to-emerald-500/5 group-hover:via-emerald-500/10 transition-all duration-700"></div>
                        <div className="flex items-center gap-3 z-10">
                            <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-500 group-hover:scale-110 transition-transform">
                                <ThumbsUp size={18} />
                            </div>
                            <span className="font-bold text-emerald-600 dark:text-emerald-400">Bullish</span>
                        </div>
                        <span className="text-xs font-mono text-emerald-500/60 opacity-0 group-hover:opacity-100 transition-opacity">VOTE</span>
                    </button>

                    <button
                        onClick={() => handleLocalVote('bearish')}
                        className="group relative flex items-center justify-between p-4 rounded-xl border border-rose-500/20 bg-rose-500/5 hover:bg-rose-500/10 transition-all overflow-hidden"
                    >
                        <div className="absolute inset-0 bg-gradient-to-r from-rose-500/0 via-rose-500/0 to-rose-500/5 group-hover:via-rose-500/10 transition-all duration-700"></div>
                        <div className="flex items-center gap-3 z-10">
                            <div className="p-2 bg-rose-500/10 rounded-lg text-rose-500 group-hover:scale-110 transition-transform">
                                <ThumbsDown size={18} />
                            </div>
                            <span className="font-bold text-rose-600 dark:text-rose-400">Bearish</span>
                        </div>
                        <span className="text-xs font-mono text-rose-500/60 opacity-0 group-hover:opacity-100 transition-opacity">VOTE</span>
                    </button>
                </div>
            ) : (
                <div className="flex flex-col gap-6 animate-fade-in-up mt-2">
                    {/* Visual Bar Representation */}
                    <div className="relative h-12 w-full bg-slate-100 dark:bg-slate-800/50 rounded-full overflow-hidden flex font-bold text-xs">
                        <div
                            style={{ width: `${bullishPercent}%` }}
                            className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 text-white flex items-center pl-3 transition-all duration-1000"
                        >
                            {bullishPercent > 15 && `Bullish ${bullishPercent}%`}
                        </div>
                        <div
                            style={{ width: `${bearishPercent}%` }}
                            className="h-full bg-gradient-to-l from-rose-500 to-pink-500 text-white flex items-center justify-end pr-3 transition-all duration-1000"
                        >
                            {bearishPercent > 15 && `${bearishPercent}% Bearish`}
                        </div>
                        {/* Center Thunder Icon */}
                        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-white dark:bg-slate-900 rounded-full flex items-center justify-center shadow-lg z-10 border-2 border-slate-100 dark:border-slate-800">
                            <span className="text-yellow-500 animate-pulse">⚡</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-center">
                        <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                            <p className="text-[10px] text-emerald-500/80 uppercase">Bulls</p>
                            <p className="text-lg font-black text-emerald-500">{bullishPercent}%</p>
                        </div>
                        <div className="p-3 rounded-lg bg-rose-500/5 border border-rose-500/10">
                            <p className="text-[10px] text-rose-500/80 uppercase">Bears</p>
                            <p className="text-lg font-black text-rose-500">{bearishPercent}%</p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

const SentimentEngine: React.FC = () => {
    const { theme } = useTheme();
    const { showToast } = useToast();
    const [activePair, setActivePair] = useState(pairs[0]);
    const [chartData, setChartData] = useState<any[]>([]);
    const [sentimentSources, setSentimentSources] = useState<SentimentSource[]>([]);
    const [fearGreedIndex, setFearGreedIndex] = useState(50);
    const [fearGreedLabel, setFearGreedLabel] = useState('Neutral');
    const [activeFilter, setActiveFilter] = useState<'All' | SentimentLabel>('All');
    const [aiSummary, setAiSummary] = useState('');
    const [isSummaryLoading, setIsSummaryLoading] = useState(false);

    const [selectedProvider, setSelectedProvider] = useState('gemini');

    // Timeframe State
    const [timeframe, setTimeframe] = useState('7d');
    const timeframes = [
        { label: '1H', value: '1h' },
        { label: '24H', value: '24h' },
        { label: '7D', value: '7d' },
        { label: '30D', value: '30d' }
    ];

    // Correlation Coefficient
    const [correlation, setCorrelation] = useState(0);

    // Heatmap State
    const [heatmapData, setHeatmapData] = useState<SentimentHeatmapItem[]>([]);
    const [isHeatmapLoading, setIsHeatmapLoading] = useState(false);

    // Narrative States
    const [narratives, setNarratives] = useState<string[]>([]);
    const [wordCloud, setWordCloud] = useState<{ text: string; weight: number }[]>([]);
    const [isNarrativeLoading, setIsNarrativeLoading] = useState(false);
    const [hasNarrativesLoaded, setHasNarrativesLoaded] = useState(false);
    const [newSourceId, setNewSourceId] = useState<string | null>(null);

    // New Features State
    const [pollStats, setPollStats] = useState({ bullish_pct: 0, bearish_pct: 0, total_votes: 0 });
    const [influencers, setInfluencers] = useState<Influencer[]>([]);
    const [socialDominance, setSocialDominance] = useState<any[]>([]);

    // --- Persistence & Manual Sync Logic ---

    // 1. Load from LocalStorage on Mount
    useEffect(() => {
        const loadPersistedData = () => {
            try {
                const savedSources = localStorage.getItem(`sentiment_sources_${activePair}`);
                const savedFearGreed = localStorage.getItem('sentiment_fear_greed');
                const savedChart = localStorage.getItem(`sentiment_chart_${activePair}`);
                const savedHeatmap = localStorage.getItem('sentiment_heatmap');
                // const savedNarratives = localStorage.getItem('sentiment_narratives'); // Optional if you want to persist narratives too

                if (savedSources) setSentimentSources(JSON.parse(savedSources));
                if (savedFearGreed) {
                    const fg = JSON.parse(savedFearGreed);
                    setFearGreedIndex(fg.index);
                    setFearGreedLabel(fg.label);
                }
                if (savedChart) setChartData(JSON.parse(savedChart));
                if (savedHeatmap) setHeatmapData(JSON.parse(savedHeatmap));

                // Recalculate correlation if chart data exists
                if (savedChart) {
                    const data = JSON.parse(savedChart);
                    calculateCorrelation(data);
                }

            } catch (e) {
                console.error("Failed to load persistence data", e);
            }
        };
        loadPersistedData();
    }, [activePair]);

    // Helper: Calculate Correlation
    const calculateCorrelation = (data: any[]) => {
        if (!data || data.length === 0) {
            setCorrelation(0);
            return;
        }
        const n = data.length;
        const x = data.map((d: any) => d.price);
        const y = data.map((d: any) => d.score);

        let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
        for (let i = 0; i < n; i++) {
            sumX += x[i];
            sumY += y[i];
            sumXY += x[i] * y[i];
            sumX2 += x[i] * x[i];
            sumY2 += y[i] * y[i];
        }

        const numerator = (n * sumXY) - (sumX * sumY);
        const denominator = Math.sqrt(((n * sumX2) - (sumX * sumX)) * ((n * sumY2) - (sumY * sumY)));

        if (denominator !== 0) {
            setCorrelation(numerator / denominator);
        } else {
            setCorrelation(0);
        }
    };

    // 2. Manual Sync Function
    const syncData = async () => {
        setIsHeatmapLoading(true); // Re-using heatmap loading state as a global "syncing" indicator for now, or create a new one
        try {
            console.log("☁️ Syncing Sentiment Data...");
            showToast('Syncing latest market sentiment...', 'info');

            // --- A. Fetch News ---
            const newsResponse = await api.get('/sentiment/news');
            const rawNews = Array.isArray(newsResponse.data) ? newsResponse.data : [];
            const formattedNews = rawNews.map((item: any) => ({
                id: item.id?.toString() || Math.random().toString(),
                source: item.source || 'Unknown',
                content: item.content || item.text,
                sentiment: item.sentiment || 'Neutral',
                timestamp: item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString(),
                url: item.url,
                type: item.type
            }));
            const finalNews = formattedNews.slice(0, 50);
            setSentimentSources(finalNews);
            localStorage.setItem(`sentiment_sources_${activePair}`, JSON.stringify(finalNews));

            // --- B. Fetch Fear & Greed ---
            const fgResponse = await api.get('/sentiment/fear-greed');
            if (fgResponse.data.value) {
                const idx = parseInt(fgResponse.data.value);
                const lbl = fgResponse.data.value_classification;
                setFearGreedIndex(idx);
                setFearGreedLabel(lbl);
                localStorage.setItem('sentiment_fear_greed', JSON.stringify({ index: idx, label: lbl }));
            }

            // --- C. Fetch Chart & Correlation ---
            const chartResponse = await api.get('/sentiment/correlation', {
                params: { symbol: activePair, period: timeframe }
            });
            if (Array.isArray(chartResponse.data)) {
                setChartData(chartResponse.data);
                localStorage.setItem(`sentiment_chart_${activePair}_${timeframe}`, JSON.stringify(chartResponse.data));
                calculateCorrelation(chartResponse.data);
            }

            // --- D. Fetch Heatmap ---
            const heatmapRes = await api.get('/sentiment/heatmap');
            const hData = heatmapRes.data || [];
            setHeatmapData(hData);
            localStorage.setItem('sentiment_heatmap', JSON.stringify(hData));

            // --- E. Fetch New Features ---
            const pollRes = await api.get('/sentiment/poll-stats');
            setPollStats(pollRes.data);

            const inflRes = await api.get('/sentiment/influencers');
            setInfluencers(inflRes.data);

            const domRes = await api.get('/sentiment/social-dominance');
            setSocialDominance(domRes.data || []);

            showToast('Sentiment Data Synced Successfully', 'success');

        } catch (err) {
            console.error("Failed to sync data", err);
            showToast('Sync Failed. Check connection.', 'error');
        } finally {
            setIsHeatmapLoading(false);
        }
    };

    const fetchHeatmap = async () => {
        setIsHeatmapLoading(true);
        try {
            const res = await api.get('/sentiment/heatmap');
            setHeatmapData(res.data || []);
        } catch (error) {
            console.error("Heatmap fetch error:", error);
        } finally {
            setIsHeatmapLoading(false);
        }
    };

    const handleGenerateSummary = useCallback(async () => {
        setIsSummaryLoading(true);
        setAiSummary('');
        try {
            const headlines = sentimentSources.slice(0, 10).map(s => s.content).join('. ');
            const response = await api.post('/sentiment/summary', {
                headlines: headlines,
                asset: activePair,
                provider: selectedProvider
            });
            setAiSummary(response.data.summary);
        } catch (error) {
            console.error("Error generating summary:", error);
            showToast('Failed to generate AI summary.', 'error');
        } finally {
            setIsSummaryLoading(false);
        }
    }, [sentimentSources, activePair, selectedProvider, showToast]);

    const handleGenerateNarratives = async () => {
        setIsNarrativeLoading(true);
        try {
            const res = await api.get('/sentiment/narratives');
            if (res.data) {
                setNarratives(res.data.narratives || []);
                setWordCloud(res.data.word_cloud || []);
                setHasNarrativesLoaded(true);
                showToast('Market Narratives Generated Successfully!', 'success');
            }
        } catch (error) {
            console.error("Failed to fetch narratives", error);
            showToast('Failed to generate narratives.', 'error');
        } finally {
            setIsNarrativeLoading(false);
        }
    };

    // Metrics Calculation (Safe access)
    const { currentScore, currentMomentum, currentVolume } = useMemo(() => {
        if (chartData.length === 0) return { currentScore: 0, currentMomentum: 0, currentVolume: 0 };
        const lastPoint = chartData[chartData.length - 1];
        return {
            currentScore: lastPoint.score || 0,
            currentMomentum: lastPoint.momentum || 0, // Backend now ensures this is calculated
            currentVolume: lastPoint.social_volume || 0 // Backend now ensures this is calculated
        };
    }, [chartData]);

    const combinedData = chartData;
    const sourceCounts = useMemo(() => sentimentSources.reduce((acc, s) => ({ ...acc, [s.sentiment]: (acc[s.sentiment] || 0) + 1 }), {} as Record<SentimentLabel, number>), [sentimentSources]);
    const sourceBreakdownData = Object.entries(sourceCounts).map(([name, value]) => ({ name, value }));
    const filteredSources = useMemo(() => activeFilter === 'All' ? sentimentSources : sentimentSources.filter(s => s.sentiment === activeFilter), [activeFilter, sentimentSources]);

    const handleVote = async (type: 'bullish' | 'bearish') => {
        try {
            await api.post('/sentiment/poll', { user_id: 1, vote_type: type }); // Mock user_id for now
            showToast('Vote submitted!', 'success');
            // Refresh stats
            const pollRes = await api.get('/sentiment/poll-stats');
            setPollStats(pollRes.data);
        } catch (error) {
            console.error("Vote error:", error);
            showToast('Failed to submit vote.', 'error');
        }
    };



    const axisColor = theme === 'dark' ? '#94A3B8' : '#64748B';
    const gridColor = theme === 'dark' ? '#334155' : '#E2E8F0';
    const getSentimentColor = (sentiment: SentimentLabel) => PIE_COLORS[sentiment] || '#64748B';

    return (
        <div className="space-y-8 animate-fade-in-slide-up">
            <Card className="!p-4 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-brand-primary/10 flex items-center justify-center text-brand-primary animate-pulse">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Sentiment Engine V2</h2>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Real-time social volume & momentum analysis</p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <Button
                        variant="primary"
                        size="sm"
                        onClick={syncData}
                        disabled={isHeatmapLoading}
                        className="bg-brand-primary hover:bg-brand-primary-hover text-white shadow-lg shadow-brand-primary/20"
                    >
                        {isHeatmapLoading ? (
                            <span className="flex items-center gap-2">
                                <Loader2 className="animate-spin w-4 h-4" /> Syncing...
                            </span>
                        ) : (
                            <span className="flex items-center gap-2">
                                <RefreshCw className="w-4 h-4" /> Sync Data
                            </span>
                        )}
                    </Button>

                    <div className="flex items-center gap-3 bg-gray-100 dark:bg-brand-darkest/50 p-1 rounded-xl">
                        {pairs.map(p => (
                            <button
                                key={p}
                                onClick={() => setActivePair(p)}
                                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activePair === p
                                    ? 'bg-white dark:bg-brand-primary text-brand-primary dark:text-white shadow-sm'
                                    : 'text-gray-500 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white'
                                    }`}
                            >
                                {p}
                            </button>
                        ))}
                    </div>
                </div>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-1 space-y-6">
                    <Card className="h-[420px] !p-0 overflow-hidden relative">
                        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10"></div>
                        <SentimentOrb score={currentScore} momentum={currentMomentum} volume={currentVolume} />
                    </Card>
                    <Card className="h-64 !p-0 overflow-hidden">
                        <FearGreedFlux score={fearGreedIndex} classification={fearGreedLabel} />
                    </Card>
                </div>

                <Card className="lg:col-span-2 flex flex-col h-[700px]">
                    <div className="flex justify-between items-center mb-6">
                        <div>
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Sentiment vs Price Correlation</h3>
                            <p className="text-xs text-gray-500">Dual-axis analysis of market sentiment and price action.</p>
                        </div>
                        <div className="flex gap-4 text-xs font-mono">
                            {/* Timeframe Selector */}
                            <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-1 mr-4">
                                {timeframes.map((tf) => (
                                    <button
                                        key={tf.value}
                                        onClick={() => {
                                            setTimeframe(tf.value);
                                            // Trigger fetch immediately or rely on useEffect if implemented
                                            // Ideally, useEffect [timeframe] handles this.
                                            // For now, let's call syncData or specific fetch
                                            api.get('/sentiment/correlation', { params: { symbol: activePair, period: tf.value } })
                                                .then(res => {
                                                    setChartData(res.data);
                                                    calculateCorrelation(res.data);
                                                });
                                        }}
                                        className={`px-3 py-1 rounded-md transition-all ${timeframe === tf.value
                                            ? 'bg-white dark:bg-slate-700 text-brand-primary shadow-sm font-bold'
                                            : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                            }`}
                                    >
                                        {tf.label}
                                    </button>
                                ))}
                            </div>

                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-brand-primary"></div> Sentiment
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-blue-400 opacity-50"></div> Volume
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-emerald-400"></div> Price
                            </div>
                        </div>
                    </div>
                    <div className="flex-grow w-full h-full min-h-[300px]" style={{ position: 'relative', width: '100%', height: '100%' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={combinedData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                                <defs>
                                    {/* Sentiment Area Gradient - Purple/Indigo */}
                                    <linearGradient id="sentimentGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#818cf8" stopOpacity={0.4} />
                                        <stop offset="50%" stopColor="#818cf8" stopOpacity={0.1} />
                                        <stop offset="95%" stopColor="#818cf8" stopOpacity={0} />
                                    </linearGradient>

                                    {/* Volume Bar Gradient - Blue */}
                                    <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                                        <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.05} />
                                    </linearGradient>

                                    {/* Neon Glow Filter */}
                                    <filter id="neonGlow" height="300%" width="300%" x="-75%" y="-75%">
                                        <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                                        <feMerge>
                                            <feMergeNode in="coloredBlur" />
                                            <feMergeNode in="SourceGraphic" />
                                        </feMerge>
                                    </filter>
                                </defs>

                                <CartesianGrid
                                    strokeDasharray="3 3"
                                    stroke={theme === 'dark' ? '#1e293b' : '#e2e8f0'}
                                    vertical={false}
                                    opacity={0.5}
                                />

                                <XAxis
                                    dataKey="time"
                                    stroke={theme === 'dark' ? '#475569' : '#94a3b8'}
                                    tickFormatter={time => new Date(time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    tick={{ fontSize: 10, fill: theme === 'dark' ? '#94a3b8' : '#64748b' }}
                                    minTickGap={60}
                                    axisLine={false}
                                    tickLine={false}
                                    dy={10}
                                />

                                <YAxis
                                    yAxisId="left"
                                    orientation="left"
                                    domain={[-1.5, 1.5]}
                                    hide
                                />
                                <YAxis
                                    yAxisId="right"
                                    orientation="right"
                                    domain={['auto', 'auto']}
                                    tickFormatter={val => `$${val.toLocaleString()}`}
                                    tick={{ fontSize: 11, fontWeight: 600, fill: '#10b981' }}
                                    axisLine={false}
                                    tickLine={false}
                                    width={60}
                                />
                                <YAxis
                                    yAxisId="vol"
                                    orientation="right"
                                    domain={[0, 'dataMax * 4']}
                                    hide
                                />

                                <Tooltip
                                    cursor={{ stroke: theme === 'dark' ? '#ffffff' : '#000000', strokeWidth: 1, strokeDasharray: '4 4', opacity: 0.3 }}
                                    content={({ active, payload, label }) => {
                                        if (active && payload && payload.length) {
                                            const score = Number(payload.find(p => p.dataKey === 'score')?.value || 0);
                                            const price = Number(payload.find(p => p.dataKey === 'price')?.value || 0);
                                            const netflowStatus = payload[0].payload.netflow_status;

                                            return (
                                                <div className="backdrop-blur-xl bg-white/80 dark:bg-slate-900/80 border border-white/20 dark:border-slate-700/30 p-4 rounded-2xl shadow-2xl ring-1 ring-black/5 dark:ring-white/10">
                                                    <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-2 font-bold flex justify-between items-center">
                                                        <span>{new Date(label).toLocaleTimeString()}</span>
                                                        <span className={score > 0 ? "text-emerald-500" : "text-rose-500"}>{score > 0 ? "BULLISH" : "BEARISH"}</span>
                                                    </div>

                                                    <div className="space-y-3">
                                                        <div className="flex items-center justify-between gap-6">
                                                            <div className="flex items-center gap-2">
                                                                <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"></div>
                                                                <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Price</span>
                                                            </div>
                                                            <span className="text-sm font-bold font-mono text-emerald-600 dark:text-emerald-400">${price.toLocaleString()}</span>
                                                        </div>

                                                        <div className="flex items-center justify-between gap-6">
                                                            <div className="flex items-center gap-2">
                                                                <div className="w-2 h-2 rounded-full bg-indigo-400 shadow-[0_0_8px_rgba(129,140,248,0.8)]"></div>
                                                                <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Sentiment Score</span>
                                                            </div>
                                                            <span className={`text-sm font-bold font-mono ${score > 0 ? 'text-indigo-500' : 'text-indigo-400'}`}>{score.toFixed(2)}</span>
                                                        </div>

                                                        {/* ✅ FIXED: Added Social Volume to Tooltip */}
                                                        <div className="flex items-center justify-between gap-6">
                                                            <div className="flex items-center gap-2">
                                                                <div className="w-2 h-2 rounded bg-blue-500/50 shadow-[0_0_8px_rgba(59,130,246,0.5)]"></div>
                                                                <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Social Vol</span>
                                                            </div>
                                                            <span className="text-sm font-bold font-mono text-blue-500">{Math.round(payload.find(p => p.dataKey === 'social_volume')?.value || 0)}</span>
                                                        </div>

                                                        {netflowStatus && (
                                                            <div className={`mt-2 text-[10px] uppercase font-black px-2 py-1 rounded text-center border border-dashed
                                                                ${netflowStatus === 'Accumulating' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500' :
                                                                    netflowStatus === 'Dumping' ? 'bg-rose-500/10 border-rose-500/30 text-rose-500' :
                                                                        'bg-slate-500/10 border-slate-500/30 text-slate-500'}`}>
                                                                DATA SIGNAL: {netflowStatus}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        }
                                        return null;
                                    }}
                                />

                                {/* Social Volume as futuristic bars at the bottom */}
                                <Bar
                                    yAxisId="vol"
                                    dataKey="social_volume"
                                    fill="url(#volumeGradient)"
                                    barSize={6}
                                    radius={[2, 2, 0, 0]}
                                />

                                {/* Sentiment Area with Glow */}
                                <Area
                                    yAxisId="left"
                                    type="monotone"
                                    dataKey="score"
                                    stroke="#818cf8"
                                    strokeWidth={3}
                                    fill="url(#sentimentGradient)"
                                    filter="url(#neonGlow)"
                                    activeDot={{ r: 6, strokeWidth: 0, fill: '#818cf8', filter: 'url(#neonGlow)' }}
                                />

                                {/* Price Line - Sharp Neon Green */}
                                <Line
                                    yAxisId="right"
                                    type="monotone"
                                    dataKey="price"
                                    stroke="#10b981"
                                    strokeWidth={2}
                                    dot={false}
                                    activeDot={{ r: 4, fill: '#fff', stroke: '#10b981', strokeWidth: 2, filter: 'url(#neonGlow)' }}
                                    style={{ filter: 'drop-shadow(0 0 4px rgba(16, 185, 129, 0.3))' }}
                                />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                </Card>
            </div>

            <Card className="lg:col-span-2">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h3 className="text-lg font-bold text-slate-900 dark:text-white">Smart Money vs Retail Divergence</h3>
                        <p className="text-xs text-gray-500">Deep Dive Analytics</p>
                    </div>

                    {/* Correlation Badge */}
                    <div className={`px-3 py-1 rounded-lg border flex items-center gap-2 ${correlation > 0.5 ? 'bg-green-500/10 border-green-500/20 text-green-500' : 'bg-yellow-500/10 border-yellow-500/20 text-yellow-500'}`}>
                        <span className="text-xs font-bold uppercase">Price-Sentiment Correlation:</span>
                        <span className="text-lg font-mono font-bold">{correlation.toFixed(2)}</span>
                    </div>
                </div>

                <div className="h-[350px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={chartData}>
                            <defs>
                                <linearGradient id="retailGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#F43F5E" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#F43F5E" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.1} stroke={gridColor} />
                            <XAxis dataKey="time" hide />
                            <Tooltip
                                contentStyle={theme === 'dark' ? { backgroundColor: '#0F172A', border: '1px solid #334155', borderRadius: '8px' } : { borderRadius: '8px' }}
                                itemStyle={{ fontSize: 12 }}
                                labelStyle={{ color: theme === 'dark' ? '#94A3B8' : '#64748B' }}
                            />
                            <Legend />

                            {/* Retail Sentiment (Noise/Chatter) */}
                            <Area
                                type="monotone"
                                dataKey="retail_score"
                                name="Retail (Twitter/Reddit)"
                                stroke="#F43F5E"
                                fill="url(#retailGradient)"
                                fillOpacity={0.3}
                            />

                            {/* Smart Money Sentiment (Signal) */}
                            <Line
                                type="monotone"
                                dataKey="smart_money_score"
                                name="Smart Money (Whales/News)"
                                stroke="#10B981"
                                strokeWidth={3}
                                dot={false}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>
            </Card>

            {/* --- REIMAGINED HEATMAP SECTION --- */}
            <Card className="min-h-[450px] flex flex-col relative overflow-hidden border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-[#0B1121]/80 backdrop-blur-xl">
                {/* Decorative Elements */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-brand-primary/5 rounded-full blur-3xl -z-10"></div>

                <div className="flex flex-col md:flex-row justify-between items-center mb-6 gap-4 z-10">
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl text-white shadow-lg shadow-indigo-500/20">
                            <Maximize2 size={18} />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">
                                Quantum Sentiment Map
                            </h3>
                            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                                Visualizing Market Emotions & Capital Flow
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <Button
                            variant="primary" // Changed to primary to be visible
                            size="sm"
                            onClick={syncData} // Call the main sync function
                            disabled={isHeatmapLoading}
                            className="bg-brand-primary hover:bg-brand-primary-hover text-white shadow-lg shadow-brand-primary/20"
                        >
                            {isHeatmapLoading ? (
                                <span className="flex items-center gap-2">
                                    <Loader2 className="animate-spin w-4 h-4" /> Syncing...
                                </span>
                            ) : (
                                <span className="flex items-center gap-2">
                                    <RefreshCw className="w-4 h-4" /> Sync Sentiment Data
                                </span>
                            )}
                        </Button>
                    </div>
                </div>

                {/* Heatmap Container */}
                <div className="flex-grow w-full h-[380px] min-h-[380px] bg-slate-100 dark:bg-[#0f1623] rounded-2xl p-1 overflow-hidden border border-slate-200 dark:border-slate-800/60 shadow-inner relative">
                    {isHeatmapLoading && heatmapData.length === 0 ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-white/80 dark:bg-[#0f1623]/80 backdrop-blur-sm">
                            <div className="relative">
                                <div className="w-12 h-12 border-4 border-brand-primary/30 border-t-brand-primary rounded-full animate-spin"></div>
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <div className="w-2 h-2 bg-brand-primary rounded-full animate-pulse"></div>
                                </div>
                            </div>
                            <p className="text-xs font-mono text-brand-primary mt-4 animate-pulse">INITIALIZING NEURAL GRID...</p>
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height="100%">
                            <Treemap
                                data={heatmapData}
                                dataKey="marketCap"
                                aspectRatio={4 / 3}
                                stroke="transparent"
                                fill="#8884d8"
                                content={<ModernHeatmapContent />}
                                animationDuration={800}
                            >
                                <Tooltip
                                    cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 2 }}
                                    content={({ active, payload }) => {
                                        if (active && payload && payload.length) {
                                            const data = payload[0].payload;
                                            return (
                                                <div className="bg-white/95 dark:bg-[#0F172A]/95 backdrop-blur-xl p-4 rounded-xl shadow-2xl border border-slate-100 dark:border-slate-700 min-w-[200px]">
                                                    <div className="flex justify-between items-start mb-2">
                                                        <div>
                                                            <h4 className="text-lg font-black text-slate-800 dark:text-white flex items-center gap-2">
                                                                {data.name}
                                                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700">{data.symbol}</span>
                                                            </h4>
                                                        </div>
                                                        <div className={`w-3 h-3 rounded-full ${data.sentimentScore > 0 ? 'bg-emerald-500 shadow-[0_0_10px_#10B981]' : 'bg-rose-500 shadow-[0_0_10px_#F43F5E]'}`}></div>
                                                    </div>

                                                    <div className="space-y-2 mt-3">
                                                        <div className="flex justify-between items-center text-xs p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                                                            <span className="text-slate-500">Sentiment Score</span>
                                                            <span className={`font-bold font-mono ${data.sentimentScore > 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                                                                {typeof data.sentimentScore === 'number' ? data.sentimentScore.toFixed(3) : 'N/A'}
                                                            </span>
                                                        </div>
                                                        <div className="flex justify-between items-center text-xs p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                                                            <span className="text-slate-500">Market Cap</span>
                                                            <span className="font-bold font-mono text-slate-700 dark:text-slate-300">
                                                                ${(data.marketCap / 1_000_000_000).toFixed(2)}B
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        }
                                        return null;
                                    }}
                                />
                            </Treemap>
                        </ResponsiveContainer>
                    )}
                </div>

                {/* Stylish Legend */}
                <div className="flex flex-wrap items-center justify-center gap-3 mt-5 px-4">
                    <div className="text-[10px] uppercase font-bold text-slate-400 mr-2">Sentiment Intensity:</div>

                    {[
                        { label: 'Bearish', color: 'bg-gradient-to-r from-rose-600 to-rose-500', glow: 'shadow-rose-500/20' },
                        { label: 'Neutral', color: 'bg-gradient-to-r from-slate-600 to-slate-500', glow: 'shadow-slate-500/20' },
                        { label: 'Bullish', color: 'bg-gradient-to-r from-teal-600 to-emerald-500', glow: 'shadow-emerald-500/20' },
                        { label: 'Extreme Hype', color: 'bg-gradient-to-r from-emerald-500 to-green-400', glow: 'shadow-green-500/40 animate-pulse' },
                    ].map((item, idx) => (
                        <div key={idx} className={`flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 ${item.glow} shadow-sm transition-transform hover:scale-105 cursor-default`}>
                            <div className={`w-2.5 h-2.5 rounded-full ${item.color}`}></div>
                            <span className="text-[10px] font-bold text-slate-600 dark:text-slate-300">{item.label}</span>
                        </div>
                    ))}
                </div>
            </Card>

            {/* --- SOCIAL LAYER SECTION START --- */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-[340px]">
                <InfluencerWatchlist influencers={influencers} />
                <CommunityPoll stats={pollStats} onVote={handleVote} />
            </div>
            {/* --- SOCIAL LAYER SECTION END --- */}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Card className="lg:col-span-2 relative overflow-hidden min-h-[250px] flex flex-col">
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500"></div>

                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <span className="p-1 bg-blue-100 dark:bg-blue-900 rounded text-blue-500">☁️</span>
                            Market Mindshare (Narrative Cloud)
                        </h3>

                        <Button
                            onClick={handleGenerateNarratives}
                            disabled={isNarrativeLoading}
                            variant="primary"
                            size="sm"
                            className="flex items-center gap-2"
                        >
                            {isNarrativeLoading ? (
                                <>
                                    <span className="animate-spin">⏳</span> Detecting...
                                </>
                            ) : (
                                <>
                                    <span>⚡</span> Generate Narratives
                                </>
                            )}
                        </Button>
                    </div>

                    {!hasNarrativesLoaded && !isNarrativeLoading ? (
                        <div className="flex flex-col items-center justify-center flex-grow text-center text-gray-500 p-8 opacity-70">
                            <div className="bg-slate-100 dark:bg-slate-800 p-4 rounded-full mb-3">
                                <span className="text-4xl">🧠</span>
                            </div>
                            <p className="font-medium">AI Narrative Engine is Ready</p>
                            <p className="text-xs max-w-xs mt-1">Click "Generate Narratives" to analyze millions of data points and detect emerging trends.</p>
                        </div>
                    ) : isNarrativeLoading ? (
                        <div className="flex flex-col items-center justify-center h-40 text-gray-400 animate-pulse">
                            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-3"></div>
                            Analyzing Global Sentiment Data...
                        </div>
                    ) : (
                        <div className="flex flex-wrap items-center justify-center gap-4 p-4 animate-fade-in-up">
                            {wordCloud.map((word, i) => {
                                const fontSize = Math.max(0.8, word.weight / 20) + 'rem';
                                const opacity = Math.max(0.5, word.weight / 100);
                                const colorClass = word.weight > 80 ? 'text-brand-primary font-bold' :
                                    word.weight > 60 ? 'text-blue-500 font-semibold' :
                                        'text-gray-500 dark:text-gray-400';

                                return (
                                    <span
                                        key={i}
                                        className={`transition-all duration-500 hover:scale-110 cursor-default ${colorClass}`}
                                        style={{ fontSize: fontSize, opacity: opacity }}
                                    >
                                        {word.text}
                                    </span>
                                );
                            })}
                            {wordCloud.length === 0 && <p className="text-gray-400 text-sm">No trending keywords detected.</p>}
                        </div>
                    )}
                </Card>

                <Card className="lg:col-span-1 bg-gradient-to-br from-slate-50 to-white dark:from-slate-900 dark:to-slate-800 border-l-4 border-l-purple-500">
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">🔥 Top Narratives</h3>

                    {!hasNarrativesLoaded && !isNarrativeLoading ? (
                        <div className="flex items-center justify-center h-full text-gray-400 text-sm italic">
                            Waiting for analysis...
                        </div>
                    ) : isNarrativeLoading ? (
                        <div className="space-y-3">
                            {[1, 2, 3].map(i => <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>)}
                        </div>
                    ) : (
                        <div className="space-y-4 animate-fade-in-right">
                            {narratives.map((narrative, index) => (
                                <div key={index} className="flex gap-3 items-start group">
                                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 flex items-center justify-center font-bold text-xs border border-purple-200 dark:border-purple-800 mt-0.5">
                                        {index + 1}
                                    </div>
                                    <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                                        {narrative}
                                    </p>
                                </div>
                            ))}
                            {narratives.length === 0 && <p className="text-gray-400 text-sm">No narratives extracted.</p>}
                        </div>
                    )}
                </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="flex flex-col">
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Signal Sources</h3>
                    <div className="flex items-center justify-between h-full">
                        <div className="h-48 w-48 relative">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={sourceBreakdownData}
                                        dataKey="value"
                                        nameKey="name"
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={60}
                                        outerRadius={80}
                                        paddingAngle={5}
                                        stroke="none"
                                    >
                                        {sourceBreakdownData.map(entry => <Cell key={`cell-${entry.name}`} fill={getSentimentColor(entry.name as SentimentLabel)} />)}
                                    </Pie>
                                    <Tooltip />
                                </PieChart>
                            </ResponsiveContainer>
                            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                <div className="text-center">
                                    <p className="text-2xl font-bold text-slate-900 dark:text-white">{sentimentSources.length}</p>
                                    <p className="text-[10px] text-gray-500 uppercase">Signals</p>
                                </div>
                            </div>
                        </div>
                        <div className="flex-1 ml-8 space-y-3">
                            {sourceBreakdownData.map(entry => (
                                <div key={entry.name} className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getSentimentColor(entry.name as SentimentLabel) }}></div>
                                        <span className="text-sm font-medium text-gray-600 dark:text-gray-300">{entry.name}</span>
                                    </div>
                                    <span className="text-sm font-bold text-slate-900 dark:text-white">{entry.value}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </Card>

                <Card className="flex flex-col bg-slate-900 border-slate-800 relative overflow-hidden">
                    <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] z-0 pointer-events-none bg-[length:100%_2px,3px_100%]"></div>

                    <div className="relative z-10 flex flex-col h-full">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                                AI Intelligence Stream
                            </h3>

                            <div className="flex items-center gap-2">
                                <select
                                    value={selectedProvider}
                                    onChange={(e) => setSelectedProvider(e.target.value)}
                                    className="bg-slate-800 text-white text-xs border border-slate-700 rounded px-2 py-1 outline-none focus:border-blue-500 cursor-pointer"
                                >
                                    <option value="gemini">Gemini 2.5</option>
                                    <option value="openai">GPT-4o</option>
                                    <option value="deepseek">DeepSeek V3</option>
                                </select>

                                <Button size="sm" variant="outline" className="text-xs border-blue-500/50 text-blue-400 hover:bg-blue-500/10" onClick={handleGenerateSummary} disabled={isSummaryLoading}>
                                    {isSummaryLoading ? 'Analyzing...' : 'Synthesize'}
                                </Button>
                            </div>
                        </div>

                        <div className="flex-grow bg-black/40 rounded-xl p-4 border border-white/5 font-mono text-sm text-blue-300 overflow-y-auto custom-scrollbar min-h-[150px]">
                            {isSummaryLoading ? (
                                <div className="flex items-center gap-2">
                                    <span className="animate-bounce">.</span>
                                    <span className="animate-bounce [animation-delay:0.1s]">.</span>
                                    <span className="animate-bounce [animation-delay:0.2s]">.</span>
                                    <span>Processing Neural Data via {selectedProvider.toUpperCase()}...</span>
                                </div>
                            ) : aiSummary ? (
                                <div className="animate-fade-in-up">
                                    <span className="text-blue-500 mr-2">{">"}</span>
                                    {aiSummary}
                                    <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse align-middle"></span>
                                </div>
                            ) : (
                                <div className="text-gray-500 italic">
                                    <span className="text-blue-500 mr-2">{">"}</span>
                                    System Ready. Awaiting command to analyze market sentiment.
                                    <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse align-middle"></span>
                                </div>
                            )}
                        </div>
                    </div>
                </Card>
            </div>

            <div className="mt-8">
                <div className="flex justify-between items-center mb-6">
                    <div className="flex items-center gap-3">
                        <div className="relative">
                            <div className="absolute inset-0 bg-blue-500 blur-lg opacity-20 animate-pulse"></div>
                            <h3 className="relative text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-400">
                                📡 Neural Data Stream
                            </h3>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-blue-500/10 text-blue-500 border border-blue-500/20">
                            LIVE
                        </span>
                    </div>

                    <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
                        {(['All', 'Positive', 'Negative', 'Neutral'] as const).map(filter => (
                            <button
                                key={filter}
                                onClick={() => setActiveFilter(filter)}
                                className={`px-4 py-1.5 text-xs font-bold uppercase rounded-md transition-all duration-300 ${activeFilter === filter
                                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm scale-105'
                                    : 'text-gray-500 hover:text-slate-700 dark:hover:text-slate-300'
                                    }`}
                            >
                                {filter}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredSources.map((source, index) => {
                        const isNew = source.id === newSourceId;

                        // Dynamic Styling based on Sentiment
                        const moodColor = source.sentiment === 'Positive' ? 'emerald' :
                            source.sentiment === 'Negative' ? 'rose' : 'slate';

                        const moodGradient = source.sentiment === 'Positive' ? 'from-emerald-500/20 to-transparent' :
                            source.sentiment === 'Negative' ? 'from-rose-500/20 to-transparent' :
                                'from-slate-500/20 to-transparent';

                        const Wrapper = source.url ? 'a' : 'div';
                        const wrapperProps = source.url ? { href: source.url, target: '_blank', rel: 'noopener noreferrer' } : {};

                        return (
                            <Wrapper
                                key={`${source.id}-${index}`}
                                {...wrapperProps}
                                className={`group relative overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 backdrop-blur-sm p-5 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:border-${moodColor}-500/30 ${isNew ? 'animate-pulse ring-2 ring-blue-500/50' : ''}`}
                            >
                                {/* Glowing Background Gradient */}
                                <div className={`absolute inset-0 bg-gradient-to-br ${moodGradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500`}></div>

                                <div className="relative z-10 flex flex-col h-full justify-between">
                                    <div>
                                        <div className="flex justify-between items-start mb-3">
                                            {/* Source Badge */}
                                            <div className="flex items-center gap-2">
                                                {source.source.includes('Reddit') ? (
                                                    <div className="w-6 h-6 rounded-full bg-[#FF4500]/10 flex items-center justify-center text-[#FF4500]">
                                                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z" /></svg>
                                                    </div>
                                                ) : source.source.includes('Google') ? (
                                                    <div className="w-6 h-6 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500 font-bold text-xs border border-blue-500/20">G</div>
                                                ) : (
                                                    <div className="w-6 h-6 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-500">
                                                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" /></svg>
                                                    </div>
                                                )}
                                                <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                                                    {source.source}
                                                </span>
                                            </div>

                                            {/* Sentiment Pill */}
                                            <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase border shadow-sm ${source.sentiment === 'Positive' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' :
                                                source.sentiment === 'Negative' ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20' :
                                                    'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20'
                                                }`}>
                                                {source.sentiment}
                                            </span>
                                        </div>

                                        <p className="text-sm font-medium text-slate-700 dark:text-slate-200 leading-relaxed line-clamp-3 mb-4 group-hover:text-slate-900 dark:group-hover:text-white transition-colors">
                                            {source.content}
                                        </p>

                                        {/* --- AI FUD Buster Button --- */}
                                        <div className="mb-3">
                                            <VerifyButton content={source.content} />
                                        </div>
                                    </div>

                                    {/* Footer Metadata */}
                                    <div className="flex items-center justify-between border-t border-gray-100 dark:border-slate-800 pt-3 mt-2">
                                        <div className="flex items-center gap-2 text-[10px] text-gray-400 font-mono">
                                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                            {source.timestamp}
                                        </div>
                                        {source.url && (
                                            <div className="opacity-0 group-hover:opacity-100 transition-opacity text-blue-500 text-xs flex items-center gap-1 font-bold">
                                                Read <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </Wrapper>
                        );
                    })}
                </div>

                {filteredSources.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-20 text-gray-400 opacity-50">
                        <svg className="w-16 h-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                        <p>No signal data available for this filter.</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SentimentEngine;
