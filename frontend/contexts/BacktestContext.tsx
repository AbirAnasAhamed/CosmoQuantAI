import React, { createContext, useState, useContext, ReactNode } from 'react';
import { BacktestResult } from '../types';
import { MOCK_STRATEGIES } from '../constants';
// নতুন ইম্পোর্ট getBacktestStatus যোগ করা হয়েছে
import { runBacktestApi, fetchCustomStrategyList, getBacktestStatus } from '../services/backtester';
import { useToast } from './ToastContext';

interface BacktestContextType {
    // States
    strategy: string;
    setStrategy: (s: string) => void;
    symbol: string;
    setSymbol: (s: string) => void;
    timeframe: string;
    setTimeframe: (t: string) => void;
    startDate: string;
    setStartDate: (d: string) => void;
    endDate: string;
    setEndDate: (d: string) => void;
    params: Record<string, any>;
    setParams: (p: Record<string, any>) => void;
    optimizableParams: Record<string, any>;
    setOptimizableParams: (p: Record<string, any>) => void;
    optimizationParams: Record<string, any>;
    setOptimizationParams: (p: Record<string, any>) => void;

    strategies: string[];
    setStrategies: React.Dispatch<React.SetStateAction<string[]>>;
    customStrategies: string[];
    setCustomStrategies: React.Dispatch<React.SetStateAction<string[]>>;

    // Results & Status
    singleResult: BacktestResult | null;
    setSingleResult: (r: BacktestResult | null) => void;
    isLoading: boolean;
    setIsLoading: (l: boolean) => void;
    statusMessage: string; // ইউজারের জন্য স্ট্যাটাস মেসেজ

    // Actions
    runBacktest: () => Promise<void>;
    refreshStrategyList: () => Promise<void>;
}

const BacktestContext = createContext<BacktestContextType | undefined>(undefined);

export const BacktestProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const { showToast } = useToast();

    // --- States ---
    const [strategies, setStrategies] = useState<string[]>(MOCK_STRATEGIES);
    const [customStrategies, setCustomStrategies] = useState<string[]>([]);
    const [strategy, setStrategy] = useState('RSI Crossover');
    const [symbol, setSymbol] = useState('BTC/USDT');
    const [timeframe, setTimeframe] = useState('1h');
    const [startDate, setStartDate] = useState('2023-01-01');
    const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);

    const [params, setParams] = useState<Record<string, any>>({});
    const [optimizableParams, setOptimizableParams] = useState<Record<string, any>>({});
    const [optimizationParams, setOptimizationParams] = useState<Record<string, any>>({});

    const [singleResult, setSingleResult] = useState<BacktestResult | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [statusMessage, setStatusMessage] = useState(''); // নতুন স্টেট

    // --- Actions ---

    const refreshStrategyList = async () => {
        try {
            const list = await fetchCustomStrategyList();
            setCustomStrategies(list);
        } catch (error) {
            console.error("Failed to load custom strategies", error);
        }
    };

    // 🔴 নতুন পোলিং লজিক সহ Run Backtest
    const runBacktest = async () => {
        setIsLoading(true);
        setSingleResult(null);
        setStatusMessage('Initializing Backtest...');

        try {
            // ১. ব্যাকটেস্ট টাস্ক শুরু করা
            const initialResponse = await runBacktestApi({
                symbol,
                timeframe,
                strategy,
                initial_cash: 10000,
                start_date: startDate,
                end_date: endDate,
                params
            });

            const taskId = initialResponse.task_id;
            setStatusMessage('Backtest Running in Background...');

            // ২. পোলিং শুরু (প্রতি ২ সেকেন্ডে চেক করবে)
            const pollInterval = setInterval(async () => {
                try {
                    const statusData = await getBacktestStatus(taskId);

                    if (statusData.status === 'Completed') {
                        clearInterval(pollInterval); // পোলিং বন্ধ

                        const apiResult = statusData.result;

                        // রেজাল্ট ম্যাপিং
                        const mappedResult: BacktestResult = {
                            id: Date.now().toString(),
                            market: apiResult.symbol || symbol,
                            strategy: apiResult.strategy || strategy,
                            timeframe: timeframe,
                            date: new Date().toISOString().split('T')[0],
                            profitPercent: apiResult.profit_percent,
                            maxDrawdown: apiResult.max_drawdown,
                            winRate: apiResult.win_rate,
                            sharpeRatio: apiResult.sharpe_ratio,
                            profit_percent: apiResult.profit_percent,
                            // max_drawdown: apiResult.max_drawdown, // Removed: Not in type
                            // win_rate: apiResult.win_rate, // Removed: Not in type
                            // sharpe_ratio: apiResult.sharpe_ratio, // Removed: Not in type
                            trades_log: apiResult.trades_log,
                            candle_data: apiResult.candle_data,
                            advanced_metrics: apiResult.advanced_metrics,
                            heatmap_data: apiResult.histogram_data,
                            underwater_data: apiResult.underwater_data
                        };

                        setSingleResult(mappedResult);
                        setIsLoading(false);
                        setStatusMessage('');
                        showToast('Backtest completed successfully!', 'success');

                    } else if (statusData.status === 'Failed') {
                        clearInterval(pollInterval);
                        setIsLoading(false);
                        setStatusMessage('');
                        showToast(`Backtest Failed: ${statusData.error}`, 'error');
                    } else {
                        // এখনও প্রসেস হচ্ছে
                        setStatusMessage('Crunching Numbers... Please wait.');
                    }
                } catch (pollError) {
                    console.error("Polling Error:", pollError);
                    // নেটওয়ার্ক এরর হলেও আমরা চেষ্টা চালিয়ে যেতে পারি, বা বন্ধ করে দিতে পারি
                    // এখানে আপাতত কন্টিনিউ রাখা হলো
                }
            }, 2000); // ২ সেকেন্ড পর পর চেক

        } catch (error: any) {
            console.error(error);
            const msg = error.response?.data?.detail || "Failed to start backtest.";
            showToast(msg, 'error');
            setIsLoading(false);
            setStatusMessage('');
        }
    };

    return (
        <BacktestContext.Provider value={{
            strategy, setStrategy,
            symbol, setSymbol,
            timeframe, setTimeframe,
            startDate, setStartDate,
            endDate, setEndDate,
            params, setParams,
            optimizableParams, setOptimizableParams,
            optimizationParams, setOptimizationParams,
            strategies, setStrategies,
            customStrategies, setCustomStrategies,
            singleResult, setSingleResult,
            isLoading, setIsLoading,
            statusMessage, // এক্সপোর্ট করা হলো যাতে UI তে দেখানো যায়
            runBacktest,
            refreshStrategyList
        }}>
            {children}
        </BacktestContext.Provider>
    );
};

export const useBacktest = (): BacktestContextType => {
    const context = useContext(BacktestContext);
    if (context === undefined) {
        throw new Error('useBacktest must be used within a BacktestProvider');
    }
    return context;
};
