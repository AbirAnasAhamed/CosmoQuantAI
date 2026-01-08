import React, { useState, useEffect, useMemo, useCallback } from 'react';
import api from '@/services/client';
import {
    ResponsiveContainer, PieChart, Pie, Cell, ComposedChart, Line, Area,
    XAxis, YAxis, CartesianGrid, Tooltip, Bar, Treemap
} from 'recharts';
import { useTheme } from '@/context/ThemeContext';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import type { SentimentSource, SentimentLabel, SentimentHeatmapItem } from '@/types';
import { useToast } from '@/context/ToastContext';
import { Loader2, RefreshCw, Maximize2 } from 'lucide-react';

const pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'];
const PIE_COLORS = { 'Positive': '#10B981', 'Negative': '#F43F5E', 'Neutral': '#64748B' };

// --- Sub Components ---

const HeatmapContent = (props: any) => {
    const { x, y, width, height, name, sentimentScore } = props;
    const score = typeof sentimentScore === 'number' ? sentimentScore : 0;

    if (!width || !height || width < 0 || height < 0) return null;

    let backgroundColor = '#64748B';
    if (score > 0.5) backgroundColor = '#059669';
    else if (score > 0.2) backgroundColor = '#10B981';
    else if (score < -0.5) backgroundColor = '#E11D48';
    else if (score < -0.2) backgroundColor = '#F43F5E';

    return (
        <g>
            <rect
                x={x}
                y={y}
                width={width}
                height={height}
                fill={backgroundColor}
                stroke="#fff"
                strokeWidth={2}
                rx={4}
                ry={4}
                style={{ transition: 'all 0.3s ease' }}
            />
            {width > 40 && height > 30 && (
                <foreignObject x={x} y={y} width={width} height={height}>
                    <div className="flex flex-col items-center justify-center h-full overflow-hidden p-1 text-center pointer-events-none">
                        <span className="font-bold text-xs truncate w-full px-1 text-white">{name}</span>
                        {height > 50 && (
                            <span className="text-[10px] opacity-80 text-white">
                                {score.toFixed(2)}
                            </span>
                        )}
                    </div>
                </foreignObject>
            )}
        </g>
    );
};

const AnimatedNumber = ({ value, prefix = '', suffix = '', className = '' }: any) => {
    return <span className={className}>{prefix}{typeof value === 'number' ? value.toFixed(2) : value}{suffix}</span>;
};

const SentimentOrb = ({ score, momentum, volume }: any) => {
    const mood = score > 0 ? "Bullish" : score < 0 ? "Bearish" : "Neutral";
    const color = score > 0 ? "text-green-500" : score < 0 ? "text-red-500" : "text-gray-500";

    // Fallback display if volume/momentum is 0
    const displayMomentum = momentum === 0 ? "Stable" : momentum.toFixed(2);
    const displayVolume = volume === 0 ? "Low" : volume;

    return (
        <div className="flex flex-col items-center justify-center h-full">
            <div className={`text-4xl font-bold ${color} mb-2`}>{mood}</div>
            <div className="text-sm text-gray-500 font-mono">Score: {score.toFixed(2)}</div>
            <div className="flex gap-4 mt-2 text-xs text-gray-400">
                <span className="bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">Mom: {displayMomentum}</span>
                <span className="bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">Vol: {displayVolume}</span>
            </div>
        </div>
    );
};

// ✅ UPDATED: Colorful Gauge Design
const FearGreedFlux = ({ score, classification }: any) => {
    const rotation = (score / 100) * 180 - 90;

    const getColor = (s: number) => {
        if (s < 25) return '#ef4444';
        if (s < 45) return '#f97316';
        if (s < 55) return '#eab308';
        if (s < 75) return '#84cc16';
        return '#22c55e';
    };
    const currentColor = getColor(score);

    return (
        <div className="flex flex-col items-center justify-center h-full relative overflow-hidden p-2">
            <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1 absolute top-3">
                Fear & Greed Index
            </h4>
            <div className="relative w-48 h-28 mt-4 flex items-center justify-center">
                <svg viewBox="0 0 200 110" className="w-full h-full overflow-visible">
                    <defs>
                        <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#ef4444" />
                            <stop offset="25%" stopColor="#f97316" />
                            <stop offset="50%" stopColor="#eab308" />
                            <stop offset="75%" stopColor="#84cc16" />
                            <stop offset="100%" stopColor="#22c55e" />
                        </linearGradient>
                        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                            <feGaussianBlur stdDeviation="2" result="blur" />
                            <feComposite in="SourceGraphic" in2="blur" operator="over" />
                        </filter>
                    </defs>
                    <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#334155" strokeWidth="12" strokeLinecap="round" className="opacity-20" />
                    <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="url(#gaugeGradient)" strokeWidth="12" strokeLinecap="round" filter="url(#glow)" />
                    <g style={{ transformOrigin: "100px 100px", transform: `rotate(${rotation}deg)`, transition: "transform 1s cubic-bezier(0.4, 0, 0.2, 1)" }}>
                        <path d="M 100 100 L 100 25" stroke="#slate-800" strokeWidth="4" className="dark:stroke-white stroke-slate-800 drop-shadow-md" strokeLinecap="round" />
                        <circle cx="100" cy="100" r="8" className="fill-slate-800 dark:fill-white" />
                    </g>
                </svg>
                <div className="absolute bottom-6 left-0 right-0 text-center">
                    <span className="text-3xl font-extrabold transition-colors duration-500 drop-shadow-sm" style={{ color: currentColor }}>
                        {Math.round(score)}
                    </span>
                </div>
            </div>
            <div
                className="mt-[-10px] text-xs font-bold px-3 py-1 rounded-full border bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm transition-colors duration-500"
                style={{ color: currentColor, borderColor: currentColor }}
            >
                {classification}
            </div>
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

    // Heatmap State
    const [heatmapData, setHeatmapData] = useState<SentimentHeatmapItem[]>([]);
    const [isHeatmapLoading, setIsHeatmapLoading] = useState(false);

    // Narrative States
    const [narratives, setNarratives] = useState<string[]>([]);
    const [wordCloud, setWordCloud] = useState<{ text: string; weight: number }[]>([]);
    const [isNarrativeLoading, setIsNarrativeLoading] = useState(false);
    const [hasNarrativesLoaded, setHasNarrativesLoaded] = useState(false);
    const [newSourceId, setNewSourceId] = useState<string | null>(null);

    // Data Fetching
    useEffect(() => {
        const fetchData = async () => {
            try {
                const newsResponse = await api.get('/v1/sentiment/news');
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

                const fgResponse = await api.get('/v1/sentiment/fear-greed');
                if (fgResponse.data.value) {
                    setFearGreedIndex(parseInt(fgResponse.data.value));
                    setFearGreedLabel(fgResponse.data.value_classification);
                }

                const chartResponse = await api.get('/v1/sentiment/correlation', {
                    params: { symbol: activePair, timeframe: '1h', days: 7 }
                });
                if (Array.isArray(chartResponse.data)) {
                    setChartData(chartResponse.data);
                }

                fetchHeatmap();
            } catch (err) {
                console.error("Failed to fetch live data", err);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 60000);
        return () => clearInterval(interval);
    }, [activePair]);

    const fetchHeatmap = async () => {
        setIsHeatmapLoading(true);
        try {
            const res = await api.get('/v1/sentiment/heatmap');
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

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-1 space-y-6">
                    <Card className="h-64 !p-0 overflow-hidden relative">
                        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10"></div>
                        <SentimentOrb score={currentScore} momentum={currentMomentum} volume={currentVolume} />
                    </Card>
                    <Card className="h-40 !p-0 overflow-hidden">
                        <FearGreedFlux score={fearGreedIndex} classification={fearGreedLabel} />
                    </Card>
                </div>

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
                    <div className="flex-grow w-full h-full min-h-[300px]" style={{ position: 'relative', width: '100%', height: '100%' }}>
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
                                <YAxis yAxisId="vol" orientation="right" domain={[0, 'dataMax * 3']} hide />

                                <Tooltip
                                    contentStyle={theme === 'dark' ? { backgroundColor: '#0F172A', border: '1px solid #334155', borderRadius: '8px' } : { borderRadius: '8px' }}
                                    labelStyle={{ color: theme === 'dark' ? '#94A3B8' : '#64748B', marginBottom: '5px' }}
                                />

                                <Bar yAxisId="vol" dataKey="social_volume" fill="#3B82F6" opacity={0.1} barSize={20} />
                                <Area yAxisId="left" type="monotone" dataKey="score" stroke="#6366F1" strokeWidth={2} fill="url(#sentimentGrad)" />
                                <Line yAxisId="right" type="monotone" dataKey="price" stroke="#10B981" strokeWidth={2} dot={false} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                </Card>
            </div>

            <Card className="min-h-[400px] flex flex-col">
                <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center gap-2">
                        <div className="p-2 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg text-white">
                            <Maximize2 size={18} />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Crypto Sentiment Heatmap</h3>
                            <p className="text-xs text-gray-500">Global market sentiment visualization (Top 50 Assets)</p>
                        </div>
                    </div>
                    <Button variant="outline" size="sm" onClick={fetchHeatmap} disabled={isHeatmapLoading}>
                        {isHeatmapLoading ? <Loader2 className="animate-spin w-4 h-4" /> : <RefreshCw className="w-4 h-4" />}
                    </Button>
                </div>

                <div className="flex-grow w-full h-[350px] min-h-[350px] bg-slate-50 dark:bg-slate-900/50 rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 relative">
                    {isHeatmapLoading && heatmapData.length === 0 ? (
                        <div className="flex items-center justify-center h-full text-gray-400">
                            <Loader2 className="w-8 h-8 animate-spin mb-2" />
                            Loading Market Data...
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height="100%">
                            <Treemap
                                data={heatmapData}
                                dataKey="marketCap"
                                aspectRatio={4 / 3}
                                stroke="#fff"
                                fill="#8884d8"
                                content={<HeatmapContent />}
                            >
                                <Tooltip
                                    content={({ active, payload }) => {
                                        if (active && payload && payload.length) {
                                            const data = payload[0].payload;
                                            return (
                                                <div className="bg-white dark:bg-slate-800 p-3 rounded-lg shadow-xl border border-slate-200 dark:border-slate-700">
                                                    <p className="font-bold text-slate-900 dark:text-white">{data.name} ({data.symbol})</p>
                                                    <div className="mt-2 space-y-1 text-xs">
                                                        <div className="flex justify-between gap-4">
                                                            <span className="text-gray-500">Sentiment:</span>
                                                            <span className={data.sentimentScore > 0 ? 'text-green-500' : 'text-red-500'}>
                                                                {typeof data.sentimentScore === 'number' ? data.sentimentScore.toFixed(2) : 'N/A'}
                                                            </span>
                                                        </div>
                                                        <div className="flex justify-between gap-4">
                                                            <span className="text-gray-500">Market Cap:</span>
                                                            <span className="text-slate-700 dark:text-slate-300">
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

                <div className="flex items-center justify-center gap-4 mt-4 text-xs font-mono text-gray-500">
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-[#E11D48] rounded"></div> Extreme Bearish</div>
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-[#F43F5E] rounded"></div> Bearish</div>
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-[#64748B] rounded"></div> Neutral</div>
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-[#10B981] rounded"></div> Bullish</div>
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-[#059669] rounded"></div> Extreme Bullish</div>
                </div>
            </Card>

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
