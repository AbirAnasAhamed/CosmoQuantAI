import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import api from '@/services/client';
import { ResponsiveContainer, PieChart, Pie, Cell, ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Bar } from 'recharts';
import { generateNewSentimentSource } from '@/constants';
import { useTheme } from '@/context/ThemeContext';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import type { SentimentSource, SentimentLabel } from '@/types';
import { useToast } from '@/context/ToastContext';
import { Loader2, RefreshCw } from 'lucide-react';

const pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'];
const PIE_COLORS = { 'Positive': '#10B981', 'Negative': '#F43F5E', 'Neutral': '#64748B' };

// Animated Number Component
const AnimatedNumber: React.FC<{ value: number; toFixed?: number; }> = ({ value, toFixed = 0 }) => {
    const [displayValue, setDisplayValue] = useState(value);
    const prevValueRef = useRef(value);

    useEffect(() => {
        const startValue = prevValueRef.current;
        const endValue = value;
        const duration = 800; // ms
        let startTime: number | null = null;

        const animate = (currentTime: number) => {
            if (!startTime) startTime = currentTime;
            const elapsedTime = currentTime - startTime;
            const progress = Math.min(elapsedTime / duration, 1);
            const ease = 1 - Math.pow(1 - progress, 4);

            const animatedValue = startValue + (endValue - startValue) * ease;
            setDisplayValue(animatedValue);

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                prevValueRef.current = endValue;
            }
        };

        requestAnimationFrame(animate);
        return () => { prevValueRef.current = value; };
    }, [value]);

    return <span>{displayValue.toFixed(toFixed)}</span>;
};

// ✅ Updated Holographic Orb with Momentum & Volume
const SentimentOrb: React.FC<{ score: number; momentum: number; volume: number }> = ({ score, momentum, volume }) => {
    let colorShadow = '';
    let coreColor = '';
    let label = '';

    if (score > 0.2) {
        colorShadow = 'shadow-[0_0_50px_rgba(16,185,129,0.6)]';
        coreColor = 'bg-gradient-to-br from-emerald-400 to-emerald-600';
        label = 'Bullish';
    } else if (score < -0.2) {
        colorShadow = 'shadow-[0_0_50px_rgba(244,63,94,0.6)]';
        coreColor = 'bg-gradient-to-br from-rose-400 to-rose-600';
        label = 'Bearish';
    } else {
        colorShadow = 'shadow-[0_0_30px_rgba(148,163,184,0.4)]';
        coreColor = 'bg-gradient-to-br from-slate-400 to-slate-600';
        label = 'Neutral';
    }

    return (
        <div className="flex flex-col items-center justify-center py-4 relative">
            {/* ✅ Stats Overlay */}
            <div className="absolute top-0 right-4 flex flex-col items-end text-xs font-mono opacity-70">
                <span className="text-gray-400">Velocity</span>
                <span className={momentum > 0 ? 'text-green-400' : momentum < 0 ? 'text-red-400' : 'text-gray-400'}>
                    {momentum > 0 ? '+' : ''}{momentum.toFixed(2)}/h
                </span>
            </div>

            <div className="absolute top-0 left-4 flex flex-col items-start text-xs font-mono opacity-70">
                <span className="text-gray-400">Social Vol</span>
                <span className="text-blue-400">{volume > 0 ? volume : '--'}</span>
            </div>

            <div className="relative mt-4">
                {/* Outer Ring */}
                <div className="absolute inset-[-10px] rounded-full border border-dashed border-gray-300 dark:border-gray-700 animate-[spin_10s_linear_infinite]"></div>

                {/* The Orb */}
                <div className={`w-32 h-32 rounded-full ${coreColor} ${colorShadow} flex items-center justify-center relative overflow-hidden transition-all duration-1000`}>
                    <div className="absolute top-0 left-0 w-full h-1/2 bg-white/20 blur-sm rounded-t-full pointer-events-none"></div>
                    <div className="text-white text-3xl font-bold drop-shadow-md z-10">
                        <AnimatedNumber value={score} toFixed={2} />
                    </div>
                </div>

                {/* Pulsing Ring based on Volume Intensity */}
                {volume > 50 && (
                    <div className={`absolute inset-0 rounded-full border-2 border-white/50 animate-ping opacity-20`}></div>
                )}
            </div>
            <div className="mt-4 text-center">
                <p className="text-sm uppercase tracking-widest text-gray-500 dark:text-gray-400 font-semibold">Social Sentiment</p>
                <p className={`text-lg font-bold mt-1 transition-colors duration-500 ${score > 0.2 ? 'text-emerald-500' : score < -0.2 ? 'text-rose-500' : 'text-slate-500'}`}>
                    {label}
                </p>
            </div>
        </div>
    );
};

// FearGreedFlux Component (Unchanged)
const FearGreedFlux: React.FC<{ score: number, classification?: string }> = ({ score, classification }) => {
    let label = classification || 'Neutral';
    let colorClass = 'bg-yellow-500';

    if (!classification) {
        if (score >= 75) { label = 'Extreme Greed'; colorClass = 'bg-green-500'; }
        else if (score >= 55) { label = 'Greed'; colorClass = 'bg-emerald-400'; }
        else if (score <= 25) { label = 'Extreme Fear'; colorClass = 'bg-red-600'; }
        else if (score <= 45) { label = 'Fear'; colorClass = 'bg-rose-400'; }
    } else {
        if (score >= 75) colorClass = 'bg-green-500';
        else if (score >= 55) colorClass = 'bg-emerald-400';
        else if (score <= 25) colorClass = 'bg-red-600';
        else if (score <= 45) colorClass = 'bg-rose-400';
    }

    return (
        <div className="flex flex-col justify-center h-full px-4 py-6">
            <div className="flex justify-between items-end mb-2">
                <span className="text-sm uppercase tracking-widest text-gray-500 dark:text-gray-400 font-semibold">Fear & Greed Index</span>
                <span className={`text-2xl font-bold ${colorClass.replace('bg-', 'text-')}`}>
                    <AnimatedNumber value={score} toFixed={0} />
                </span>
            </div>
            <div className="w-full h-4 flex gap-1">
                {[...Array(20)].map((_, i) => {
                    const threshold = (i + 1) * 5;
                    const isActive = score >= threshold;
                    let segColor = 'bg-gray-200 dark:bg-gray-800';
                    if (isActive) {
                        if (i < 5) segColor = 'bg-red-500';
                        else if (i < 10) segColor = 'bg-orange-400';
                        else if (i < 15) segColor = 'bg-yellow-400';
                        else segColor = 'bg-green-500';
                    }
                    return (
                        <div key={i} className={`flex-1 rounded-sm transition-colors duration-300 ${segColor} ${isActive ? 'shadow-[0_0_5px_currentColor]' : ''}`}></div>
                    )
                })}
            </div>
            <p className="text-right text-xs mt-2 text-gray-400 font-mono">{label}</p>
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

    const [newSourceId, setNewSourceId] = useState<string | null>(null);

    // Narrative Layer States
    const [narratives, setNarratives] = useState<string[]>([]);
    const [wordCloud, setWordCloud] = useState<{ text: string; weight: number }[]>([]);
    const [isNarrativeLoading, setIsNarrativeLoading] = useState(false);
    const [hasNarrativesLoaded, setHasNarrativesLoaded] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // 1. Fetch News
                const newsResponse = await api.get('/v1/sentiment/news');
                // Handle different response structures if needed
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
                setSentimentSources(formattedNews.slice(0, 50));

                // 2. Fetch Fear & Greed
                const fgResponse = await api.get('/v1/sentiment/fear-greed');
                if (fgResponse.data.value) {
                    setFearGreedIndex(parseInt(fgResponse.data.value));
                    setFearGreedLabel(fgResponse.data.value_classification);
                }

                // 3. Fetch Chart Data (With new metrics)
                const chartResponse = await api.get('/v1/sentiment/correlation', {
                    params: { symbol: activePair, timeframe: '1h', days: 7 }
                });

                if (Array.isArray(chartResponse.data)) {
                    setChartData(chartResponse.data);
                }

                // 4. Fetch Narratives & Word Cloud (AI Generated)
                // fetchNarratives(); -> Removed for manual trigger

            } catch (err) {
                console.error("Failed to fetch live data", err);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 60000);
        return () => clearInterval(interval);
    }, [activePair]);

    const handleGenerateSummary = useCallback(async () => {
        setIsSummaryLoading(true);
        setAiSummary('');
        try {
            const headlines = sentimentSources.slice(0, 10).map(s => s.content).join('. ');
            const response = await api.post('/v1/sentiment/summary', {
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
            const res = await api.get('/v1/sentiment/narratives');
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

    // ✅ Extract Current Stats from Chart Data
    const { currentScore, currentMomentum, currentVolume } = useMemo(() => {
        if (chartData.length === 0) return { currentScore: 0, currentMomentum: 0, currentVolume: 0 };
        const lastPoint = chartData[chartData.length - 1];
        return {
            currentScore: lastPoint.score || 0,
            currentMomentum: lastPoint.momentum || 0,
            currentVolume: lastPoint.social_volume || 0
        };
    }, [chartData]);

    const combinedData = chartData;
    const sourceCounts = useMemo(() => sentimentSources.reduce((acc, s) => ({ ...acc, [s.sentiment]: (acc[s.sentiment] || 0) + 1 }), {} as Record<SentimentLabel, number>), [sentimentSources]);
    const sourceBreakdownData = Object.entries(sourceCounts).map(([name, value]) => ({ name, value }));
    const filteredSources = useMemo(() => activeFilter === 'All' ? sentimentSources : sentimentSources.filter(s => s.sentiment === activeFilter), [activeFilter, sentimentSources]);

    const axisColor = theme === 'dark' ? '#94A3B8' : '#64748B';
    const gridColor = theme === 'dark' ? '#334155' : '#E2E8F0';
    const getSentimentColor = (sentiment: SentimentLabel) => PIE_COLORS[sentiment] || '#64748B';

    return (
        <div className="space-y-8 animate-fade-in-slide-up">
            {/* Header */}
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
            </Card>

            {/* Intelligence Dashboard */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left Column: Metrics */}
                <div className="lg:col-span-1 space-y-6">
                    <Card className="h-64 !p-0 overflow-hidden relative">
                        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10"></div>
                        {/* ✅ Pass extra metrics to Orb */}
                        <SentimentOrb score={currentScore} momentum={currentMomentum} volume={currentVolume} />
                    </Card>
                    <Card className="h-40 !p-0 overflow-hidden">
                        <FearGreedFlux score={fearGreedIndex} classification={fearGreedLabel} />
                    </Card>
                </div>

                {/* Center Column: Main Chart */}
                <Card className="lg:col-span-2 flex flex-col h-[500px]">
                    <div className="flex justify-between items-center mb-6">
                        <div>
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Sentiment vs Price Correlation</h3>
                            <p className="text-xs text-gray-500">Dual-axis analysis of market sentiment and price action.</p>
                        </div>
                        <div className="flex gap-4 text-xs font-mono">
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
                    <div className="flex-grow w-full h-full min-h-[300px]" style={{ position: 'relative' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={combinedData}>
                                <defs>
                                    <linearGradient id="sentimentGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} opacity={0.4} />
                                <XAxis dataKey="time" stroke={axisColor} tickFormatter={time => new Date(time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} tick={{ fontSize: 10 }} minTickGap={50} axisLine={false} tickLine={false} dy={10} />

                                <YAxis yAxisId="left" orientation="left" stroke="#6366F1" domain={[-1.5, 1.5]} tick={{ fontSize: 10 }} hide />
                                <YAxis yAxisId="right" orientation="right" stroke="#10B981" domain={['auto', 'auto']} tickFormatter={val => `$${Math.round(val / 1000)}k`} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                                {/* Hidden YAxis for Volume Bar scaling */}
                                <YAxis yAxisId="vol" orientation="right" domain={[0, 'dataMax * 3']} hide />

                                <Tooltip
                                    contentStyle={theme === 'dark' ? { backgroundColor: '#0F172A', border: '1px solid #334155', borderRadius: '8px' } : { borderRadius: '8px' }}
                                    labelStyle={{ color: theme === 'dark' ? '#94A3B8' : '#64748B', marginBottom: '5px' }}
                                />

                                {/* ✅ Volume Bars Background */}
                                <Bar yAxisId="vol" dataKey="social_volume" fill="#3B82F6" opacity={0.1} barSize={20} />

                                <Area yAxisId="left" type="monotone" dataKey="score" stroke="#6366F1" strokeWidth={2} fill="url(#sentimentGrad)" />
                                <Line yAxisId="right" type="monotone" dataKey="price" stroke="#10B981" strokeWidth={2} dot={false} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                </Card>
            </div>

            {/* --- Narrative Layer (New Feature) --- */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Word Cloud Section */}
                <Card className="lg:col-span-2 relative overflow-hidden min-h-[250px] flex flex-col">
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500"></div>

                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <span className="p-1 bg-blue-100 dark:bg-blue-900 rounded text-blue-500">☁️</span>
                            Market Mindshare (Narrative Cloud)
                        </h3>

                        {/* ✅ Manual Trigger Button */}
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

                    {/* Content Display */}
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

                {/* Trending Narratives List */}
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

            {/* Stats & AI Unit */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Source Breakdown (Same as before but cleaner) */}
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

                {/* AI Intelligence Unit */}
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

            {/* Live Feed */}
            <div className="mt-8">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">Live Data Stream</h3>
                    <div className="flex gap-2">
                        {(['All', 'Positive', 'Negative', 'Neutral'] as const).map(filter => (
                            <button
                                key={filter}
                                onClick={() => setActiveFilter(filter)}
                                className={`px-3 py-1 text-xs font-bold uppercase rounded-full transition-colors border ${activeFilter === filter
                                    ? 'bg-brand-primary text-white border-brand-primary'
                                    : 'bg-transparent text-gray-500 border-gray-300 dark:border-gray-700 hover:border-brand-primary'
                                    }`}
                            >
                                {filter}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="space-y-3">
                    {filteredSources.map((source, index) => {
                        const isNew = source.id === newSourceId;
                        const borderColor = source.sentiment === 'Positive' ? 'border-l-emerald-500' : source.sentiment === 'Negative' ? 'border-l-rose-500' : 'border-l-gray-400';
                        const Wrapper = source.url ? 'a' : 'div';
                        const wrapperProps = source.url ? { href: source.url, target: '_blank', rel: 'noopener noreferrer' } : {};

                        return (
                            <Wrapper
                                key={`${source.id}-${index}`}
                                {...wrapperProps}
                                className={`block relative bg-white dark:bg-brand-dark border border-gray-100 dark:border-brand-border-dark rounded-lg p-4 pl-5 border-l-4 shadow-sm hover:shadow-md transition-all duration-500 ${borderColor} ${isNew ? 'animate-fade-in-right bg-blue-50/50 dark:bg-blue-900/10' : ''} ${source.url ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-slate-800' : ''}`}
                            >
                                <div className="flex justify-between items-start">
                                    <div>
                                        <div className="flex items-center gap-2 mb-1">
                                            {source.source.includes('Reddit') || source.source.includes('r/') ? (
                                                <span className="text-[10px] bg-orange-500/10 text-orange-500 px-1.5 py-0.5 rounded border border-orange-500/20">REDDIT</span>
                                            ) : (
                                                <span className="text-[10px] bg-blue-500/10 text-blue-500 px-1.5 py-0.5 rounded border border-blue-500/20">NEWS</span>
                                            )}
                                            <span className="text-xs font-bold uppercase tracking-wider text-gray-400">{source.source}</span>
                                            <span className="text-gray-300">•</span>
                                            <span className="text-xs text-gray-500 font-mono">{source.timestamp}</span>
                                        </div>
                                        <p className="text-slate-800 dark:text-slate-200 font-medium">{source.content}</p>
                                    </div>
                                    <span className={`text-xs font-bold px-2 py-1 rounded uppercase ${source.sentiment === 'Positive' ? 'bg-emerald-500/10 text-emerald-500' :
                                        source.sentiment === 'Negative' ? 'bg-rose-500/10 text-rose-500' :
                                            'bg-gray-500/10 text-gray-500'
                                        }`}>
                                        {source.sentiment}
                                    </span>
                                </div>
                            </Wrapper>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default SentimentEngine;
