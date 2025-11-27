
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { EQUITY_CURVE_DATA, MOCK_BACKTEST_RESULTS, MOCK_STRATEGIES, MOCK_STRATEGY_PARAMS, MOCK_CUSTOM_MODELS } from '../../constants';
import { useTheme } from '../../contexts/ThemeContext';
import CodeEditor from '../../components/ui/CodeEditor';
import type { BacktestResult } from '../../types';

import { useToast } from '../../contexts/ToastContext';
import { syncMarketData, runBacktestApi, getExchangeList, getExchangeMarkets } from '../../services/backtester';
import SearchableSelect from '../../components/ui/SearchableSelect';
import BacktestChart from '../../components/ui/BacktestChart';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

// Animated Number Component (Same as Dashboard)
const AnimatedNumber: React.FC<{ value: number; decimals?: number; prefix?: string; suffix?: string }> = ({ value, decimals = 2, prefix = '', suffix = '' }) => {
    const [displayValue, setDisplayValue] = useState(0);

    useEffect(() => {
        let start = 0;
        const end = value;
        if (start === end) return;

        const duration = 1000;
        const startTime = performance.now();

        const animate = (currentTime: number) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            // Ease out function
            const easeOut = 1 - Math.pow(1 - progress, 3);

            const current = start + (end - start) * easeOut;
            setDisplayValue(current);

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                setDisplayValue(end);
            }
        };

        requestAnimationFrame(animate);
    }, [value]);

    return (
        <span className="animate-count-up">
            {prefix}{displayValue.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}{suffix}
        </span>
    );
};

const MetricCard: React.FC<{ label: string; value: number; prefix?: string; suffix?: string; positive?: boolean }> = ({ label, value, prefix = '', suffix = '', positive }) => (
    <Card className="text-center bg-gray-50 dark:bg-brand-dark/50 transform hover:scale-105 transition-transform duration-200">
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">{label}</p>
        <p className={`text-2xl font-bold ${positive === true ? 'text-brand-success' : positive === false ? 'text-brand-danger' : 'text-slate-900 dark:text-white'}`}>
            <AnimatedNumber value={value} prefix={prefix} suffix={suffix} decimals={label.includes('Ratio') ? 2 : 1} />
        </p>
    </Card>
);

const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload;
        return (
            <div className="p-3 bg-white/80 dark:bg-brand-dark/80 backdrop-blur-sm rounded-lg shadow-lg border border-brand-border-light dark:border-brand-border-dark text-sm animate-fade-in-right">
                <p className="font-bold text-slate-900 dark:text-white mb-2">{label}</p>
                <div className="space-y-1">
                    <div className="flex justify-between items-center">
                        <span className="text-gray-500 dark:text-gray-400 mr-4">Equity:</span>
                        <span className="font-semibold text-slate-900 dark:text-white">${data.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-gray-500 dark:text-gray-400 mr-4">Profit:</span>
                        <span className={`font-semibold ${data.profitPercent >= 0 ? 'text-brand-success' : 'text-brand-danger'}`}>{data.profitPercent.toFixed(2)}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-gray-500 dark:text-gray-400 mr-4">Drawdown:</span>
                        <span className="font-semibold text-brand-danger">{data.drawdown.toFixed(2)}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-gray-500 dark:text-gray-400 mr-4">Win Rate:</span>
                        <span className="font-semibold text-slate-900 dark:text-white">{data.winRate.toFixed(1)}%</span>
                    </div>
                </div>
            </div>
        );
    }

    return null;
};

type OptimizationParamValue = {
    start: number | string;
    end: number | string;
    step: number | string;
};

type OptimizationParams = Record<string, OptimizationParamValue>;

const RangeSliderInput: React.FC<{
    config: { label: string; min?: number; max?: number; step?: number };
    value: OptimizationParamValue;
    onChange: (newValue: OptimizationParamValue) => void;
    hideStepInput?: boolean;
}> = ({ config, value, onChange, hideStepInput = false }) => {
    const { min = 0, max = 100, step = 1 } = config;
    const { start, end, step: stepValue } = value;
    const startNum = Number(start);
    const endNum = Number(end);
    const rangeRef = useRef<HTMLDivElement>(null);

    const getPercent = useCallback((val: number) => Math.round(((val - min) / (max - min)) * 100), [min, max]);

    useEffect(() => {
        const startPercent = getPercent(startNum);
        const endPercent = getPercent(endNum);
        if (rangeRef.current) {
            rangeRef.current.style.left = `${startPercent}%`;
            rangeRef.current.style.width = `${endPercent - startPercent}%`;
        }
    }, [startNum, endNum, getPercent]);

    const handleValueChange = (field: 'start' | 'end' | 'step', val: string | number) => {
        const newValues = { ...value, [field]: val };

        let s = Number(newValues.start);
        let e = Number(newValues.end);

        if (field === 'start') {
            s = Math.min(s, e);
        } else if (field === 'end') {
            e = Math.max(e, s);
        }

        onChange({ ...newValues, start: s, end: e });
    };

    const handleRangeChange = (field: 'start' | 'end', e: React.ChangeEvent<HTMLInputElement>) => {
        const val = Number(e.target.value);
        if (field === 'start') {
            const newStart = Math.min(val, endNum - Number(stepValue));
            if (newStart !== startNum) {
                onChange({ ...value, start: newStart });
            }
        } else {
            const newEnd = Math.max(val, startNum + Number(stepValue));
            if (newEnd !== endNum) {
                onChange({ ...value, end: newEnd });
            }
        }
    };

    const inputClasses = "w-24 bg-white dark:bg-brand-dark/50 border border-brand-border-light dark:border-brand-border-dark rounded-md p-1.5 text-slate-900 dark:text-white text-sm focus:ring-brand-primary focus:border-brand-primary";

    return (
        <div className="space-y-3">
            <div className="range-slider-container">
                <input type="range" min={min} max={max} step={step} value={startNum} onChange={(e) => handleRangeChange('start', e)} className="thumb thumb--left" aria-label="Start value" />
                <input type="range" min={min} max={max} step={step} value={endNum} onChange={(e) => handleRangeChange('end', e)} className="thumb thumb--right" aria-label="End value" />
                <div className="range-slider-track"></div>
                <div ref={rangeRef} className="range-slider-range"></div>
            </div>
            <div className={`flex items-center gap-2 ${hideStepInput ? 'justify-between' : 'justify-evenly'}`}>
                <div>
                    <label className="block text-xs text-gray-400 dark:text-gray-500 mb-1">Start</label>
                    <input type="number" min={min} max={max} step={step} value={start} onChange={(e) => handleValueChange('start', e.target.value)} className={inputClasses} />
                </div>
                {!hideStepInput && (
                    <div>
                        <label className="block text-xs text-gray-400 dark:text-gray-500 mb-1 text-center">Step</label>
                        <input type="number" min={step} step={step} value={stepValue} onChange={(e) => handleValueChange('step', e.target.value)} className={inputClasses} />
                    </div>
                )}
                <div className="text-right">
                    <label className="block text-xs text-gray-400 dark:text-gray-500 mb-1">End</label>
                    <input type="number" min={min} max={max} step={step} value={end} onChange={(e) => handleValueChange('end', e.target.value)} className={inputClasses} />
                </div>
            </div>
        </div>
    );
};


const CalendarIcon = () => (
    <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
);


const Backtester: React.FC = () => {
    const { theme } = useTheme();
    const { showToast } = useToast();
    const [strategies, setStrategies] = useState(MOCK_STRATEGIES);
    const [strategy, setStrategy] = useState('RSI Crossover');
    const [symbol, setSymbol] = useState('');
    const [timeframe, setTimeframe] = useState('1h');
    const [exchanges, setExchanges] = useState<string[]>([]);
    const [markets, setMarkets] = useState<string[]>([]);
    const [selectedExchange, setSelectedExchange] = useState('binance');
    const [isLoadingMarkets, setIsLoadingMarkets] = useState(false);

    useEffect(() => {
        const loadExchanges = async () => {
            try {
                const list = await getExchangeList();
                setExchanges(list);
                if (list.length > 0) setSelectedExchange(list[0]);
            } catch (error) {
                console.error("Failed to load exchanges", error);
            }
        };
        loadExchanges();
    }, []);

    useEffect(() => {
        const loadMarkets = async () => {
            if (!selectedExchange) return;
            setIsLoadingMarkets(true);
            try {
                const pairs = await getExchangeMarkets(selectedExchange);
                setMarkets(pairs);
                const defaultPair = pairs.includes('BTC/USDT') ? 'BTC/USDT' : pairs[0];
                setSymbol(defaultPair || '');
            } catch (error) {
                showToast('Failed to load market pairs', 'error');
                setMarkets([]);
            } finally {
                setIsLoadingMarkets(false);
            }
        };
        loadMarkets();
    }, [selectedExchange]);
    const [params, setParams] = useState<Record<string, any>>({});
    const [optimizationParams, setOptimizationParams] = useState<OptimizationParams>({});
    const [showResults, setShowResults] = useState(false);
    const [backtestMode, setBacktestMode] = useState<'single' | 'optimization'>('single');
    const [startDate, setStartDate] = useState('2023-01-01');
    const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);

    // Loading States
    const [isSyncing, setIsSyncing] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    // State for portfolio backtesting
    const [isPortfolioBacktest, setIsPortfolioBacktest] = useState(false);
    const [portfolioAssets, setPortfolioAssets] = useState(['BTC/USDT', 'ETH/USDT']);
    const [newPortfolioAsset, setNewPortfolioAsset] = useState('');

    // State for Genetic Algorithm
    const [optimizationMethod, setOptimizationMethod] = useState<'gridSearch' | 'geneticAlgorithm'>('gridSearch');
    const [gaParams, setGaParams] = useState({ populationSize: 50, generations: 20 });
    const [isOptimizing, setIsOptimizing] = useState(false);
    const [optimizationProgress, setOptimizationProgress] = useState(0);

    // State for advanced optimization methods
    const [isWalkForwardEnabled, setIsWalkForwardEnabled] = useState(true);
    const [walkForwardConfig, setWalkForwardConfig] = useState({ inSample: 6, outOfSample: 2 });
    const [isMultiObjectiveEnabled, setIsMultiObjectiveEnabled] = useState(false);
    const [multiObjectiveGoals, setMultiObjectiveGoals] = useState<string[]>(['Net Profit']);

    // State for different result types
    const [singleResult, setSingleResult] = useState<BacktestResult | null>(null);
    const [multiObjectiveResults, setMultiObjectiveResults] = useState<BacktestResult[] | null>(null);
    const [batchResults, setBatchResults] = useState<BacktestResult[] | null>(null);


    // State for Python-powered features
    const [showAdvancedPythonFeatures, setShowAdvancedPythonFeatures] = useState(false);
    const [customObjectiveCode, setCustomObjectiveCode] = useState(
        `# Example: Prioritize Sharpe and low Drawdown
def custom_objective(stats):
    sharpe = stats.get('sharpe_ratio', 0)
    drawdown = stats.get('max_drawdown', 100)
    # A higher score is better
    score = (sharpe * 2) - (drawdown * 0.5)
    return score
`);
    const [selectedMlModel, setSelectedMlModel] = useState<string>('1');
    const [altDataSource, setAltDataSource] = useState('');

    const fileInputRef = useRef<HTMLInputElement>(null);
    const [fileName, setFileName] = useState('');

    // State for batch backtesting
    const [isBatchRunning, setIsBatchRunning] = useState(false);

    // State for Bar Replay
    const [isReplayActive, setIsReplayActive] = useState(false);
    const [replayIndex, setReplayIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);
    const [replaySpeed, setReplaySpeed] = useState(1);
    const replayIntervalRef = useRef<number | null>(null);



    const replayData = useMemo(() => EQUITY_CURVE_DATA.slice(0, replayIndex + 1), [replayIndex]);

    useEffect(() => {
        const strategyParamsConfig = MOCK_STRATEGY_PARAMS[strategy as keyof typeof MOCK_STRATEGY_PARAMS];
        if (strategyParamsConfig) {
            const defaultParams = Object.keys(strategyParamsConfig).reduce((acc, key) => {
                acc[key] = strategyParamsConfig[key].defaultValue;
                return acc;
            }, {} as Record<string, any>);
            setParams(defaultParams);

            const defaultOptParams = Object.keys(strategyParamsConfig).reduce((acc, key) => {
                acc[key] = {
                    start: strategyParamsConfig[key].min ?? strategyParamsConfig[key].defaultValue,
                    end: strategyParamsConfig[key].max ?? strategyParamsConfig[key].defaultValue,
                    step: strategyParamsConfig[key].step || 1,
                };
                return acc;
            }, {} as OptimizationParams);
            setOptimizationParams(defaultOptParams);
        } else {
            setParams({});
            setOptimizationParams({});
        }
    }, [strategy]);

    const handleParamChange = (key: string, value: string) => {
        // নম্বর কিনা চেক করা হচ্ছে
        const numValue = Number(value);

        setParams(prev => ({
            ...prev,
            // যদি ভ্যালিড নম্বর হয় তাহলে নম্বর সেভ হবে, না হলে স্ট্রিং
            [key]: isNaN(numValue) ? value : numValue
        }));
    };

    const handleOptimizationParamChange = (key: string, newValue: OptimizationParamValue) => {
        setOptimizationParams(prev => ({
            ...prev,
            [key]: newValue,
        }));
    };

    const handleGoalToggle = (goal: string) => {
        setMultiObjectiveGoals(prev =>
            prev.includes(goal)
                ? prev.filter(g => g !== goal)
                : [...prev, goal]
        );
    };

    const handleLoadParams = (paramsToLoad: Record<string, number | string>) => {
        setParams(paramsToLoad);
        setBacktestMode('single');
    };




    const axisColor = theme === 'dark' ? '#9CA3AF' : '#6B7280';
    const gridColor = theme === 'dark' ? '#334155' : '#E2E8F0';

    // ১. মার্কেট ডেটা সিঙ্ক হ্যান্ডেলার (Sync Data)
    const handleSyncData = async () => {
        setIsSyncing(true);
        try {
            await syncMarketData(symbol, timeframe, startDate, endDate);
            showToast(`Synced historical data for ${symbol}`, 'success');
        } catch (error) {
            console.error(error);
            showToast('Failed to sync market data.', 'error');
        } finally {
            setIsSyncing(false);
        }
    };

    // ২. ব্যাকটেস্ট রান হ্যান্ডেলার (Run Backtest)
    const handleRunBacktest = async () => {
        // Reset all result states for a clean run
        setBatchResults(null);
        setMultiObjectiveResults(null);
        setSingleResult(null);
        setIsReplayActive(false);
        setReplayIndex(0);
        setShowResults(false);

        if (backtestMode === 'single') {
            setIsLoading(true);
            try {
                // রিয়েল এপিআই কল
                const apiResult = await runBacktestApi({
                    symbol: symbol,
                    timeframe: timeframe,
                    strategy: strategy,
                    initial_cash: 10000, // হার্ডকোড বা ইনপুট নিতে পারেন
                    start_date: startDate,
                    end_date: endDate,
                    params: params // ফর্ম থেকে নেয়া প্যারামিটার
                });

                // ব্যাকএন্ড ডেটাকে ফ্রন্টএন্ড মডেলে কনভার্ট
                const mappedResult: BacktestResult = {
                    id: Date.now().toString(),
                    market: apiResult.symbol || symbol,
                    strategy: apiResult.strategy || strategy,
                    timeframe: timeframe,
                    date: new Date().toISOString().split('T')[0],

                    // আমাদের Types ফাইলে যে নাম আছে, সেই অনুযায়ী ম্যাপ করছি
                    profitPercent: apiResult.profit_percent,
                    maxDrawdown: apiResult.max_drawdown,
                    winRate: apiResult.win_rate,
                    sharpeRatio: apiResult.sharpe_ratio,

                    // সাপোর্টের জন্য অরিজিনাল ভ্যালুও রাখা যেতে পারে
                    profit_percent: apiResult.profit_percent,
                    max_drawdown: apiResult.max_drawdown,
                    win_rate: apiResult.win_rate,
                    sharpe_ratio: apiResult.sharpe_ratio,
                    trades_log: apiResult.trades_log,
                    candle_data: apiResult.candle_data
                };

                setSingleResult(mappedResult);
                setShowResults(true);
                showToast('Backtest completed successfully!', 'success');

            } catch (error: any) {
                console.error(error);
                const msg = error.response?.data?.detail || "Backtest failed. Did you sync data?";
                showToast(msg, 'error');
            } finally {
                setIsLoading(false);
            }
            return;
        }

        if (backtestMode === 'optimization') {
            if (optimizationMethod === 'geneticAlgorithm') {
                setIsOptimizing(true);
                setOptimizationProgress(0);

                const totalGenerations = gaParams.generations;
                let currentGeneration = 0;
                const interval = setInterval(() => {
                    currentGeneration++;
                    const progress = (currentGeneration / totalGenerations) * 100;
                    setOptimizationProgress(progress);
                    if (currentGeneration >= totalGenerations) {
                        clearInterval(interval);
                        setIsOptimizing(false);
                        if (isMultiObjectiveEnabled) {
                            const paretoFront: BacktestResult[] = [
                                { id: 'mo1', market: 'BTC/USDT', strategy, timeframe: '4h', date: new Date().toISOString().split('T')[0], profitPercent: 125.5, maxDrawdown: 22.1, winRate: 68, sharpeRatio: 2.1, profit_percent: 125.5, max_drawdown: 22.1, win_rate: 68, sharpe_ratio: 2.1, params: { period: 10, overbought: 80, oversold: 25 } },
                                { id: 'mo2', market: 'BTC/USDT', strategy, timeframe: '4h', date: new Date().toISOString().split('T')[0], profitPercent: 92.3, maxDrawdown: 11.5, winRate: 65, sharpeRatio: 2.8, profit_percent: 92.3, max_drawdown: 11.5, win_rate: 65, sharpe_ratio: 2.8, params: { period: 14, overbought: 75, oversold: 30 } },
                                { id: 'mo3', market: 'BTC/USDT', strategy, timeframe: '4h', date: new Date().toISOString().split('T')[0], profitPercent: 61.8, maxDrawdown: 5.2, winRate: 61, sharpeRatio: 1.9, profit_percent: 61.8, max_drawdown: 5.2, win_rate: 61, sharpe_ratio: 1.9, params: { period: 20, overbought: 70, oversold: 35 } },
                            ];
                            setMultiObjectiveResults(paretoFront);
                        } else {
                            setSingleResult(MOCK_BACKTEST_RESULTS[1]); // Show the best result
                        }
                        setShowResults(true);
                    }
                }, 200);
            } else { // Grid Search
                if (isMultiObjectiveEnabled) {
                    const paretoFront: BacktestResult[] = [

                        { id: 'mo1', market: 'BTC/USDT', strategy, timeframe: '4h', date: new Date().toISOString().split('T')[0], profitPercent: 110.2, maxDrawdown: 19.8, winRate: 67, sharpeRatio: 2.3, profit_percent: 110.2, max_drawdown: 19.8, win_rate: 67, sharpe_ratio: 2.3, params: { period: 12, overbought: 78, oversold: 28 } },
                        { id: 'mo2', market: 'BTC/USDT', strategy, timeframe: '4h', date: new Date().toISOString().split('T')[0], profitPercent: 78.6, maxDrawdown: 9.1, winRate: 64, sharpeRatio: 2.6, profit_percent: 78.6, max_drawdown: 9.1, win_rate: 64, sharpe_ratio: 2.6, params: { period: 16, overbought: 72, oversold: 32 } },
                        { id: 'mo3', market: 'BTC/USDT', strategy, timeframe: '4h', date: new Date().toISOString().split('T')[0], profitPercent: 45.1, maxDrawdown: 4.8, winRate: 59, sharpeRatio: 1.7, profit_percent: 45.1, max_drawdown: 4.8, win_rate: 59, sharpe_ratio: 1.7, params: { period: 22, overbought: 68, oversold: 38 } },
                    ];
                    setMultiObjectiveResults(paretoFront);
                } else {
                    setSingleResult(MOCK_BACKTEST_RESULTS[1]); // Show the best result
                }
                setShowResults(true);
            }
        }
    };

    const handleRunAllStrategies = () => {
        setIsBatchRunning(true);
        setShowResults(false);
        setBatchResults(null);
        setSingleResult(null);
        setMultiObjectiveResults(null);
        setIsReplayActive(false);

        setTimeout(() => {
            const allStrategies = MOCK_STRATEGIES.filter(s => s !== 'Custom ML Model');
            const newBatchResults: BacktestResult[] = allStrategies.map((strategyName, index) => ({
                id: `${index + 1}`,
                market: 'BTC/USDT',
                strategy: strategyName,
                timeframe: '4h',
                date: new Date().toISOString().split('T')[0],
                profitPercent: (Math.random() * 150) - 25,
                maxDrawdown: Math.random() * 30,
                winRate: 40 + Math.random() * 50,
                sharpeRatio: Math.random() * 3,
                profit_percent: (Math.random() * 150) - 25,
                max_drawdown: Math.random() * 30,
                win_rate: 40 + Math.random() * 50,
                sharpe_ratio: Math.random() * 3,
            }));

            setBatchResults(newBatchResults);
            setIsBatchRunning(false);
            setShowResults(true);
        }, 1500);
    };

    // Bar Replay Logic
    useEffect(() => {
        if (isPlaying) {
            replayIntervalRef.current = window.setInterval(() => {
                setReplayIndex(prev => {
                    if (prev < EQUITY_CURVE_DATA.length - 1) {
                        return prev + 1;
                    }
                    setIsPlaying(false);
                    return prev;
                });
            }, 1000 / replaySpeed);
        } else {
            if (replayIntervalRef.current) {
                clearInterval(replayIntervalRef.current);
            }
        }
        return () => {
            if (replayIntervalRef.current) {
                clearInterval(replayIntervalRef.current);
            }
        };
    }, [isPlaying, replaySpeed]);

    const handlePlayPause = () => {
        if (replayIndex >= EQUITY_CURVE_DATA.length - 1) {
            setReplayIndex(0);
        }
        setIsPlaying(!isPlaying);
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setFileName(e.target.files[0].name);
        }
    };

    const handleUpload = () => {
        if (!fileName) return;
        const newStrategyName = fileName.replace(/\.[^/.]+$/, "");
        if (!strategies.includes(newStrategyName)) {
            setStrategies(prev => [...prev, newStrategyName]);
            setStrategy(newStrategyName);
        }
        setFileName('');
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const inputBaseClasses = "w-full bg-white dark:bg-brand-dark/50 border border-brand-border-light dark:border-brand-border-dark rounded-md p-2 text-slate-900 dark:text-white focus:ring-brand-primary focus:border-brand-primary";

    const renderSingleParams = () => {
        const strategyParamsConfig = MOCK_STRATEGY_PARAMS[strategy as keyof typeof MOCK_STRATEGY_PARAMS];
        if (!strategyParamsConfig || Object.keys(strategyParamsConfig).length === 0) return null;

        return (
            <div className="mt-6 pt-6 border-t border-brand-border-light dark:border-brand-border-dark animate-fade-in-down">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Strategy Parameters</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {Object.entries(strategyParamsConfig).map(([key, config]) => (
                        <div key={key}>
                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">{config.label}</label>
                            <input
                                type={config.type}
                                value={params[key] || ''}
                                onChange={(e) => handleParamChange(key, e.target.value)}
                                min={config.min}
                                max={config.max}
                                step={config.step}
                                className={inputBaseClasses}
                            />
                        </div>
                    ))}
                </div>
            </div>
        );
    };

    const renderOptimizationParams = () => {
        const strategyParamsConfig = MOCK_STRATEGY_PARAMS[strategy as keyof typeof MOCK_STRATEGY_PARAMS];
        if (!strategyParamsConfig || Object.keys(strategyParamsConfig).length === 0) return null;

        const objectives = ['Net Profit', 'Max Drawdown', 'Sharpe Ratio'];

        return (
            <div className="mt-6 pt-6 border-t border-brand-border-light dark:border-brand-border-dark animate-fade-in-down">
                <div className="mb-6">
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">Optimization Method</h3>
                    <div className="inline-flex bg-gray-100 dark:bg-brand-dark/50 rounded-lg p-1 space-x-1">
                        <button onClick={() => setOptimizationMethod('gridSearch')} className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${optimizationMethod === 'gridSearch' ? 'bg-white dark:bg-brand-dark shadow text-brand-primary' : 'text-gray-500 dark:text-gray-300'}`}>Grid Search</button>
                        <button onClick={() => setOptimizationMethod('geneticAlgorithm')} className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${optimizationMethod === 'geneticAlgorithm' ? 'bg-white dark:bg-brand-dark shadow text-brand-primary' : 'text-gray-500 dark:text-gray-300'}`}>Genetic Algorithm</button>
                    </div>
                </div>

                {optimizationMethod === 'gridSearch' ? (
                    <div>
                        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Grid Search Parameters</h3>
                        {Object.entries(strategyParamsConfig).map(([key, config]) => (
                            <div key={key} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-start mb-6 pb-4 border-b border-brand-border-light/50 dark:border-brand-border-dark/50 last:border-b-0 last:mb-0 last:pb-0">
                                <label className="md:col-span-1 block text-sm font-medium text-gray-500 dark:text-gray-400 pt-1.5">{config.label}</label>
                                <div className="md:col-span-3">
                                    <RangeSliderInput
                                        config={config}
                                        value={optimizationParams[key]}
                                        onChange={(newValue) => handleOptimizationParamChange(key, newValue)}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div>
                        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Genetic Algorithm Parameters</h3>
                        <div className="grid grid-cols-2 gap-4 mb-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Population Size</label>
                                <input type="number" value={gaParams.populationSize} onChange={(e) => setGaParams(p => ({ ...p, populationSize: parseInt(e.target.value) }))} step="10" className={inputBaseClasses} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Generations</label>
                                <input type="number" value={gaParams.generations} onChange={(e) => setGaParams(p => ({ ...p, generations: parseInt(e.target.value) }))} step="5" className={inputBaseClasses} />
                            </div>
                        </div>
                        {Object.entries(strategyParamsConfig).map(([key, config]) => (
                            <div key={key} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-start mb-6 pb-4 border-b border-brand-border-light/50 dark:border-brand-border-dark/50 last:border-b-0 last:mb-0 last:pb-0">
                                <label className="md:col-span-1 block text-sm font-medium text-gray-500 dark:text-gray-400 pt-1.5">{config.label} Range</label>
                                <div className="md:col-span-3">
                                    <RangeSliderInput
                                        config={config}
                                        value={optimizationParams[key]}
                                        onChange={(newValue) => handleOptimizationParamChange(key, newValue)}
                                        hideStepInput={true}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Advanced Optimization Methods */}
                <div className="mt-8 pt-6 border-t border-brand-border-light dark:border-brand-border-dark">
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Advanced Optimization Methods <span className="text-xs font-bold text-brand-primary bg-brand-primary/20 px-2 py-1 rounded-full align-middle">PREMIUM</span></h3>
                    <div className="space-y-6">
                        {/* Walk-Forward Optimization */}
                        <div className="bg-gray-50 dark:bg-brand-dark/30 p-4 rounded-lg">
                            <div className="flex items-center justify-between">
                                <label htmlFor="walk-forward-toggle" className="font-medium text-slate-900 dark:text-white cursor-pointer">
                                    Walk-Forward Optimization
                                </label>
                                <input
                                    type="checkbox"
                                    id="walk-forward-toggle"
                                    className="form-checkbox h-5 w-5 rounded bg-slate-300 dark:bg-slate-700 border-brand-border-light dark:border-brand-border-dark text-brand-primary focus:ring-brand-primary focus:ring-offset-0"
                                    checked={isWalkForwardEnabled}
                                    onChange={() => setIsWalkForwardEnabled(!isWalkForwardEnabled)}
                                />
                            </div>
                            {isWalkForwardEnabled && (
                                <div className="mt-4 pt-4 border-t border-brand-border-light dark:border-brand-border-dark grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm text-gray-500 dark:text-gray-400 mb-1">In-Sample Periods</label>
                                        <input type="number" value={walkForwardConfig.inSample} onChange={(e) => setWalkForwardConfig(p => ({ ...p, inSample: parseInt(e.target.value) }))} className={inputBaseClasses} />
                                    </div>
                                    <div>
                                        <label className="block text-sm text-gray-500 dark:text-gray-400 mb-1">Out-of-Sample Periods</label>
                                        <input type="number" value={walkForwardConfig.outOfSample} onChange={(e) => setWalkForwardConfig(p => ({ ...p, outOfSample: parseInt(e.target.value) }))} className={inputBaseClasses} />
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Multi-Objective Optimization */}
                        <div className="bg-gray-50 dark:bg-brand-dark/30 p-4 rounded-lg">
                            <div className="flex items-center justify-between">
                                <label htmlFor="multi-obj-toggle" className="font-medium text-slate-900 dark:text-white cursor-pointer">
                                    Multi-Objective Optimization
                                </label>
                                <input
                                    type="checkbox"
                                    id="multi-obj-toggle"
                                    className="form-checkbox h-5 w-5 rounded bg-slate-300 dark:bg-slate-700 border-brand-border-light dark:border-brand-border-dark text-brand-primary focus:ring-brand-primary focus:ring-offset-0"
                                    checked={isMultiObjectiveEnabled}
                                    onChange={() => setIsMultiObjectiveEnabled(!isMultiObjectiveEnabled)}
                                />
                            </div>
                            {isMultiObjectiveEnabled && (
                                <div className="mt-4 pt-4 border-t border-brand-border-light dark:border-brand-border-dark">
                                    <label className="block text-sm text-gray-500 dark:text-gray-400 mb-2">Select Objectives:</label>
                                    <div className="flex flex-wrap gap-3">
                                        {objectives.map(goal => (
                                            <button
                                                key={goal}
                                                type="button"
                                                onClick={() => handleGoalToggle(goal)}
                                                className={`px-3 py-1.5 text-xs font-semibold rounded-full border transition-colors ${multiObjectiveGoals.includes(goal)
                                                    ? 'bg-brand-primary border-transparent text-white'
                                                    : 'bg-transparent border-brand-border-light dark:border-brand-border-dark text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-brand-dark'
                                                    }`}
                                            >
                                                {goal}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Advanced Python-Powered Features */}
                <div className="mt-8 pt-6 border-t border-brand-border-light dark:border-brand-border-dark">
                    <div className="flex items-center justify-between cursor-pointer" onClick={() => setShowAdvancedPythonFeatures(!showAdvancedPythonFeatures)}>
                        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                            Advanced Python-Powered Features
                            <span className="text-xs font-bold text-brand-primary bg-brand-primary/20 px-2 py-1 rounded-full align-middle ml-2">PREMIUM</span>
                        </h3>
                        <svg className={`h-5 w-5 text-gray-400 transform transition-transform ${showAdvancedPythonFeatures ? 'rotate-180' : ''}`} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                    </div>
                    {showAdvancedPythonFeatures && (
                        <div className="mt-6 space-y-6 animate-fade-in-down">
                            <div className="bg-gray-50 dark:bg-brand-dark/30 p-4 rounded-lg">
                                <label className="font-medium text-slate-900 dark:text-white block mb-2">Custom Objective Function</label>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Define your optimization goal in Python. The function should accept a stats dictionary and return a single score to maximize.</p>
                                <div className="h-48">
                                    <CodeEditor value={customObjectiveCode} onChange={setCustomObjectiveCode} />
                                </div>
                            </div>

                            <div className="bg-gray-50 dark:bg-brand-dark/30 p-4 rounded-lg">
                                <label className="font-medium text-slate-900 dark:text-white block mb-2">Machine Learning Integration</label>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Use a pre-trained model from your Model Hub as a signal in your strategy.</p>
                                <select value={selectedMlModel || ''} onChange={(e) => setSelectedMlModel(e.target.value)} className={inputBaseClasses}>
                                    <option value="">Select a model...</option>
                                    {MOCK_CUSTOM_MODELS.filter(model => model.versions.find(v => v.id === model.activeVersionId)?.status === 'Ready').map(model => (
                                        <option key={model.id} value={model.id}>{model.name} ({model.modelType})</option>
                                    ))}
                                </select>
                            </div>

                            <div className="bg-gray-50 dark:bg-brand-dark/30 p-4 rounded-lg">
                                <label className="font-medium text-slate-900 dark:text-white block mb-2">Alternative Data Integration</label>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Incorporate external data sources via API into your backtest (e.g., sentiment data, on-chain metrics).</p>
                                <div className="flex gap-2">
                                    <input type="text" value={altDataSource} onChange={(e) => setAltDataSource(e.target.value)} placeholder="Enter API URL..." className={inputBaseClasses} />
                                    <Button type="button" variant="secondary">Add Source</Button>
                                </div>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Note: This is a UI demo. Backend integration is required.</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="space-y-8">

            <Card className="staggered-fade-in" style={{ animationDelay: '100ms' }}>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4">Upload New Strategy</h2>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            className="hidden"
                            accept=".py"
                        />
                        <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
                            Choose file
                        </Button>
                        <span className="text-sm text-gray-500 dark:text-gray-400">{fileName || 'No file chosen'}</span>
                    </div>
                    <Button onClick={handleUpload} disabled={!fileName}>
                        Upload
                    </Button>
                </div>
            </Card>

            <Card className="staggered-fade-in" style={{ animationDelay: '200ms' }}>
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white">Backtest Configuration</h2>

                    <Button
                        variant="secondary"
                        onClick={handleSyncData}
                        disabled={isSyncing}
                        className="border border-brand-primary/30 text-brand-primary hover:bg-brand-primary/10"
                    >
                        {isSyncing ? (
                            <span className="flex items-center gap-2">
                                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                                Syncing Data...
                            </span>
                        ) : (
                            "☁ Sync Market Data"
                        )}
                    </Button>

                    <div className="flex items-center space-x-3">
                        <label htmlFor="portfolio-toggle" className="text-sm font-medium text-gray-500 dark:text-gray-400">Portfolio Backtest</label>
                        <input
                            type="checkbox"
                            id="portfolio-toggle"
                            className="form-checkbox h-5 w-5 rounded bg-slate-300 dark:bg-slate-700 border-brand-border-light dark:border-brand-border-dark text-brand-primary focus:ring-brand-primary focus:ring-offset-0"
                            checked={isPortfolioBacktest}
                            onChange={() => setIsPortfolioBacktest(!isPortfolioBacktest)}
                        />
                    </div>
                </div>

                <div className="mb-6">
                    <div className="inline-flex bg-gray-100 dark:bg-brand-dark/50 rounded-lg p-1 space-x-1">
                        <button
                            onClick={() => setBacktestMode('single')}
                            className={`px-4 py-2 text-sm font-semibold rounded-md transition-colors ${backtestMode === 'single'
                                ? 'bg-white dark:bg-brand-dark shadow text-brand-primary'
                                : 'text-gray-500 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-brand-dark/80'
                                }`}
                        >
                            Single Backtest
                        </button>
                        <button
                            onClick={() => setBacktestMode('optimization')}
                            className={`px-4 py-2 text-sm font-semibold rounded-md transition-colors ${backtestMode === 'optimization'
                                ? 'bg-white dark:bg-brand-dark shadow text-brand-primary'
                                : 'text-gray-500 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-brand-dark/80'
                                }`}
                        >
                            Optimization
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Exchange</label>
                        <select
                            className={inputBaseClasses}
                            value={selectedExchange}
                            onChange={(e) => setSelectedExchange(e.target.value)}
                        >
                            {exchanges.map(ex => (
                                <option key={ex} value={ex}>{ex.toUpperCase()}</option>
                            ))}
                        </select>
                    </div>
                    {isPortfolioBacktest ? (
                        <div className="md:col-span-2 lg:col-span-2">
                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Portfolio Assets</label>
                            <div className="flex gap-2">
                                <input
                                    type="text"
                                    value={newPortfolioAsset}
                                    onChange={(e) => setNewPortfolioAsset(e.target.value)}
                                    placeholder="e.g. ADA/USDT"
                                    className={inputBaseClasses}
                                />
                                <Button type="button" onClick={() => {
                                    if (newPortfolioAsset && !portfolioAssets.includes(newPortfolioAsset.toUpperCase())) {
                                        setPortfolioAssets(prev => [...prev, newPortfolioAsset.toUpperCase()]);
                                        setNewPortfolioAsset('');
                                    }
                                }}>Add</Button>
                            </div>
                            <div className="flex flex-wrap gap-2 mt-2">
                                {portfolioAssets.map(asset => (
                                    <div key={asset} className="flex items-center gap-2 bg-gray-100 dark:bg-brand-dark/50 rounded-full px-3 py-1 text-xs">
                                        <span className="text-slate-900 dark:text-white">{asset}</span>
                                        <button onClick={() => setPortfolioAssets(prev => prev.filter(a => a !== asset))} className="text-gray-400 hover:text-brand-danger">&times;</button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div>
                            <SearchableSelect
                                label="Market Pair"
                                options={markets}
                                value={symbol}
                                onChange={(val) => setSymbol(val)}
                                placeholder={isLoadingMarkets ? "Loading..." : "Search pair (e.g. BTC)"}
                                disabled={isLoadingMarkets}
                            />
                        </div>
                    )}
                    <div>
                        <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Start Date</label>
                        <div className="relative">
                            <DatePicker
                                selected={startDate ? new Date(startDate) : null}
                                onChange={(date: Date | null) => setStartDate(date ? date.toISOString().split('T')[0] : '')}
                                className={`${inputBaseClasses} pr-10`}
                                dateFormat="yyyy-MM-dd"
                                placeholderText="Select start date"
                                wrapperClassName="w-full"
                            />
                            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                                <CalendarIcon />
                            </div>
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">End Date</label>
                        <div className="relative">
                            <DatePicker
                                selected={endDate ? new Date(endDate) : null}
                                onChange={(date: Date | null) => setEndDate(date ? date.toISOString().split('T')[0] : '')}
                                className={`${inputBaseClasses} pr-10`}
                                dateFormat="yyyy-MM-dd"
                                placeholderText="Select end date"
                                wrapperClassName="w-full"
                            />
                            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                                <CalendarIcon />
                            </div>
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Timeframe</label>
                        <select
                            value={timeframe}
                            onChange={(e) => setTimeframe(e.target.value)}
                            className={inputBaseClasses}
                        >
                            <optgroup label="Minutes">
                                <option value="1m">1 Minute</option>
                                <option value="3m">3 Minutes</option>
                                <option value="5m">5 Minutes</option>
                                <option value="15m">15 Minutes</option>
                                <option value="30m">30 Minutes</option>
                            </optgroup>
                            <optgroup label="Hours">
                                <option value="1h">1 Hour</option>
                                <option value="2h">2 Hours</option>
                                <option value="4h">4 Hours</option>
                                <option value="6h">6 Hours</option>
                                <option value="8h">8 Hours</option>
                                <option value="12h">12 Hours</option>
                            </optgroup>
                            <optgroup label="Days">
                                <option value="1d">1 Day</option>
                                <option value="3d">3 Days</option>
                            </optgroup>
                            <optgroup label="Weeks & Months">
                                <option value="1w">1 Week</option>
                                <option value="1M">1 Month</option>
                            </optgroup>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Strategy</label>
                        <select onChange={(e) => setStrategy(e.target.value)} value={strategy} className={`${inputBaseClasses} flex-grow`}>
                            {strategies.map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                    </div>
                </div>

                {backtestMode === 'single' ? renderSingleParams() : renderOptimizationParams()}

                <div className="mt-8 pt-6 border-t border-brand-border-light dark:border-brand-border-dark flex items-center gap-4">
                    <Button onClick={handleRunBacktest} className="w-full md:w-auto" disabled={isLoading || isSyncing || isOptimizing || isBatchRunning}>
                        {isLoading ? 'Running Strategy...' : isOptimizing ? 'Optimizing...' : backtestMode === 'single' ? 'Run Backtest' : 'Run Optimization'}
                    </Button>
                    <Button variant="secondary" onClick={handleRunAllStrategies} disabled={isOptimizing || isBatchRunning}>
                        {isBatchRunning ? 'Running All...' : 'Run All Strategies'}
                    </Button>
                </div>
            </Card >

            {isOptimizing && (
                <Card className="staggered-fade-in" style={{ animationDelay: '300ms' }}>
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4">Genetic Algorithm Progress</h2>
                    <div className="w-full bg-gray-200 rounded-full h-4 dark:bg-brand-dark">
                        <div className="bg-brand-primary h-4 rounded-full" style={{ width: `${optimizationProgress}%`, transition: 'width 0.2s ease-in-out' }}></div>
                    </div>
                    <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-2">{Math.round(optimizationProgress)}% Complete</p>
                </Card>
            )}

            {
                isBatchRunning && (
                    <Card className="staggered-fade-in" style={{ animationDelay: '300ms' }}>
                        <div className="flex flex-col items-center justify-center p-8 text-center">
                            <svg className="animate-spin h-8 w-8 text-brand-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <h2 className="mt-4 text-xl font-bold text-slate-900 dark:text-white">Running Batch Backtest</h2>
                            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Please wait while we process all strategies...</p>
                        </div>
                    </Card>
                )
            }

            {
                showResults && !isOptimizing && !isBatchRunning && (
                    <>
                        {batchResults ? (
                            <Card className="staggered-fade-in" style={{ animationDelay: '300ms' }}>
                                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-6">Batch Backtest Results</h2>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left">
                                        <thead>
                                            <tr className="border-b border-brand-border-light dark:border-brand-border-dark">
                                                <th className="p-4 text-sm font-semibold text-gray-500 dark:text-gray-400">Strategy</th>
                                                <th className="p-4 text-sm font-semibold text-gray-500 dark:text-gray-400 text-right">Profit %</th>
                                                <th className="p-4 text-sm font-semibold text-gray-500 dark:text-gray-400 text-right">Max Drawdown %</th>
                                                <th className="p-4 text-sm font-semibold text-gray-500 dark:text-gray-400 text-right">Win Rate %</th>
                                                <th className="p-4 text-sm font-semibold text-gray-500 dark:text-gray-400 text-right">Sharpe Ratio</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {batchResults.sort((a, b) => b.profitPercent - a.profitPercent).map((result, index) => (
                                                <tr key={result.id} className="border-b border-brand-border-light/80 dark:border-brand-border-dark/50 hover:bg-gray-50 dark:hover:bg-brand-dark/30 stagger-fade-in" style={{ animationDelay: `${index * 50}ms` }}>
                                                    <td className="p-4 font-medium text-slate-900 dark:text-white">{result.strategy}</td>
                                                    <td className={`p-4 font-semibold text-right ${result.profitPercent >= 0 ? 'text-brand-success' : 'text-brand-danger'}`}>
                                                        {result.profitPercent.toFixed(2)}%
                                                    </td>
                                                    <td className="p-4 text-gray-600 dark:text-gray-300 text-right">{result.maxDrawdown.toFixed(2)}%</td>
                                                    <td className="p-4 text-gray-600 dark:text-gray-300 text-right">{result.winRate.toFixed(1)}%</td>
                                                    <td className="p-4 text-gray-600 dark:text-gray-300 text-right">{result.sharpeRatio.toFixed(2)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </Card>
                        ) : multiObjectiveResults ? (
                            <Card className="staggered-fade-in" style={{ animationDelay: '300ms' }}>
                                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Multi-Objective Optimization Results</h2>
                                <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">The following results represent the best trade-offs (Pareto Front) found for your selected objectives.</p>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left">
                                        <thead>
                                            <tr className="border-b border-brand-border-light dark:border-brand-border-dark">
                                                {Object.values(MOCK_STRATEGY_PARAMS[strategy] || {}).map(p => <th key={p.label} className="p-4 text-sm font-semibold text-gray-500 dark:text-gray-400">{p.label}</th>)}
                                                {multiObjectiveGoals.map(goal => <th key={goal} className="p-4 text-sm font-semibold text-gray-500 dark:text-gray-400 text-right">{goal}</th>)}
                                                <th className="p-4 text-sm font-semibold text-gray-500 dark:text-gray-400 text-center">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {multiObjectiveResults.map((res, index) => (
                                                <tr key={res.id} className="border-b border-brand-border-light/80 dark:border-brand-border-dark/50 hover:bg-gray-50 dark:hover:bg-brand-dark/30 stagger-fade-in" style={{ animationDelay: `${index * 50}ms` }}>
                                                    {Object.keys(MOCK_STRATEGY_PARAMS[strategy] || {}).map(paramKey => <td key={paramKey} className="p-4 font-mono text-slate-900 dark:text-white">{res.params?.[paramKey]}</td>)}
                                                    {multiObjectiveGoals.includes('Net Profit') && <td className={`p-4 font-semibold text-right ${res.profitPercent >= 0 ? 'text-brand-success' : 'text-brand-danger'}`}>{res.profitPercent.toFixed(2)}%</td>}
                                                    {multiObjectiveGoals.includes('Max Drawdown') && <td className="p-4 font-semibold text-right text-brand-danger">{res.maxDrawdown.toFixed(2)}%</td>}
                                                    {multiObjectiveGoals.includes('Sharpe Ratio') && <td className="p-4 font-semibold text-right text-slate-900 dark:text-white">{res.sharpeRatio.toFixed(2)}</td>}
                                                    <td className="p-4 text-center">
                                                        <Button variant="outline" className="px-3 py-1 text-xs" onClick={() => handleLoadParams(res.params || {})}>
                                                            Load Params
                                                        </Button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </Card>
                        ) : singleResult ? (
                            <Card className="staggered-fade-in" style={{ animationDelay: '300ms' }}>
                                <div className="flex flex-wrap gap-4 justify-between items-center mb-6">
                                    <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                                        {backtestMode === 'optimization' ? 'Best Optimization Result' : 'Backtest Results'}
                                    </h2>
                                    <Button variant="outline" onClick={() => setIsReplayActive(!isReplayActive)}>
                                        {isReplayActive ? 'Exit Replay' : 'Start Bar Replay'}
                                    </Button>
                                </div>

                                {!isReplayActive && (
                                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                                        <MetricCard
                                            label="Total Profit"
                                            value={singleResult.profitPercent || 0}
                                            prefix={singleResult.profitPercent! > 0 ? "+" : ""}
                                            suffix="%"
                                            positive={singleResult.profitPercent! >= 0}
                                        />
                                        <MetricCard
                                            label="Max Drawdown"
                                            value={singleResult.maxDrawdown || 0}
                                            suffix="%"
                                            positive={false}
                                        />
                                        <MetricCard
                                            label="Win Rate"
                                            value={singleResult.winRate || 0}
                                            suffix="%"
                                        />
                                        <MetricCard
                                            label="Sharpe Ratio"
                                            value={singleResult.sharpeRatio || 0}
                                        />
                                    </div>
                                )}

                                <div className="mt-8 animate-fade-in-down">
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Trade Visualization</h3>

                                    {/* ডেটা থাকলে রিয়েল চার্ট, না থাকলে লোডিং বা এরর */}
                                    {singleResult && singleResult.candle_data && singleResult.candle_data.length > 0 ? (
                                        <BacktestChart
                                            data={singleResult.candle_data}
                                            trades={singleResult.trades_log || []}
                                        />
                                    ) : (
                                        <div className="h-64 bg-gray-100 dark:bg-white/5 rounded-xl flex items-center justify-center text-gray-500">
                                            Chart data visualization not available for this test.
                                        </div>
                                    )}
                                </div>

                                {isReplayActive && (
                                    <div className="mt-6 pt-6 border-t border-brand-border-light dark:border-brand-border-dark animate-fade-in-down">
                                        <div className="flex items-center gap-6">
                                            <Button onClick={handlePlayPause}>
                                                {isPlaying ? 'Pause' : 'Play'}
                                            </Button>
                                            <div className="flex-1">
                                                <input
                                                    type="range"
                                                    min="0"
                                                    max={EQUITY_CURVE_DATA.length - 1}
                                                    value={replayIndex}
                                                    onChange={(e) => setReplayIndex(Number(e.target.value))}
                                                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-brand-dark slider-thumb"
                                                />
                                            </div>
                                            <div>
                                                <label className="text-sm mr-2 text-gray-500 dark:text-gray-400">Speed:</label>
                                                <select value={replaySpeed} onChange={(e) => setReplaySpeed(Number(e.target.value))} className="bg-white dark:bg-brand-dark/50 border border-brand-border-light dark:border-brand-border-dark rounded-md py-1 px-2 text-sm">
                                                    <option value={1}>1x</option>
                                                    <option value={2}>2x</option>
                                                    <option value={5}>5x</option>
                                                </select>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </Card>
                        ) : null}
                    </>
                )
            }
        </div >
    );
};

export default Backtester;
