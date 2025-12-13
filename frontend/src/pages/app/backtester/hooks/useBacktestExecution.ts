import { useState, useEffect, useRef, useCallback } from 'react';
import { useToast } from '@/context/ToastContext';
import { useBacktestSocket } from '@/hooks/useBacktestSocket';
import { runBacktestApi, runOptimizationApi, runBatchBacktest, revokeBacktestTask } from '@/services/backtester';
import { BacktestResult } from '@/types';

// Ensure this path matches where your general connection hook resides.
// Since we are in `src/pages/app/backtester/hooks`, and `useBacktestSocket` is likely in `src/hooks`.
// Adjust import if necessary. Assuming `src/hooks/useBacktestSocket.ts` exists.

export const useBacktestExecution = () => {
    const { showToast } = useToast();
    const { lastMessage } = useBacktestSocket();

    // States
    const [isRunning, setIsRunning] = useState(false);
    const [progress, setProgress] = useState(0);
    const [isOptimizing, setIsOptimizing] = useState(false);
    const [optimizationProgress, setOptimizationProgress] = useState(0);
    const [isBatchRunning, setIsBatchRunning] = useState(false);
    const [batchProgress, setBatchProgress] = useState(0);
    const [batchStatusMsg, setBatchStatusMsg] = useState("");

    // Results
    const [singleResult, setSingleResult] = useState<BacktestResult | null>(null);
    const [batchResults, setBatchResults] = useState<BacktestResult[] | null>(null);
    const [multiObjectiveResults, setMultiObjectiveResults] = useState<BacktestResult[] | null>(null);
    const [backtestResult, setBacktestResult] = useState<any>(null); // Raw result

    // Task Tracking
    const [backtestTaskId, setBacktestTaskId] = useState<string | null>(null);
    const [optimizationTaskId, setOptimizationTaskId] = useState<string | null>(null);
    const [batchTaskId, setBatchTaskId] = useState<string | null>(null);

    // --- NEW: Track the strategy name being run ---
    const lastRunStrategy = useRef<string>("Unknown");

    // WebSocket Event Listener
    useEffect(() => {
        if (!lastMessage) return;

        // 1. Backtest Updates
        if (lastMessage.type === 'BACKTEST' && backtestTaskId && lastMessage.task_id === backtestTaskId) {
            if (lastMessage.status === 'processing') {
                setProgress(lastMessage.progress);
            }
            if (lastMessage.status === 'completed') {
                setBacktestResult(lastMessage.payload);
                setSingleResult(lastMessage.payload);
                setIsRunning(false);
                setProgress(100);
                showToast('Backtest Completed!', 'success');
                setBacktestTaskId(null);
            }
            if (lastMessage.status === 'failed') {
                setIsRunning(false);
                showToast(`Backtest Failed: ${lastMessage.payload?.error || 'Unknown error'}`, 'error');
                setBacktestTaskId(null);
            }
        }

        // 2. Optimization Updates
        if (lastMessage.type === 'OPTIMIZE' && optimizationTaskId && lastMessage.task_id === optimizationTaskId) {
            if (lastMessage.status === 'processing') {
                setOptimizationProgress(lastMessage.progress);
            }
            if (lastMessage.status === 'completed') {
                setIsOptimizing(false);
                setOptimizationProgress(100);
                localStorage.removeItem('activeOptimizationId');

                const rawResults = lastMessage.payload;
                // --- FIX: Use stored strategy name if missing in result ---
                const strategyName = lastRunStrategy.current;

                const formattedResults: BacktestResult[] = Array.isArray(rawResults) ? rawResults.map((res: any, index: number) => ({
                    id: `opt-${index}`,
                    market: res.market || 'Unknown',
                    // If backend sends generic result, enforce the strategy name we ran
                    strategy: res.strategy && res.strategy !== 'Unknown' ? res.strategy : strategyName,
                    timeframe: res.timeframe || '1h',
                    date: res.date || '',
                    profitPercent: res.profitPercent,
                    maxDrawdown: res.maxDrawdown,
                    winRate: res.winRate || 0,
                    sharpeRatio: res.sharpeRatio,
                    profit_percent: res.profitPercent,
                    params: res.params,
                    total_trades: res.total_trades || 0,
                    candle_data: res.candle_data || [] // Ensure array
                })) : [];

                setBatchResults(formattedResults); // Or multiObjectiveResults
                showToast('Optimization Completed!', 'success');
                setOptimizationTaskId(null);
            }
            if (lastMessage.status === 'failed') {
                setIsOptimizing(false);
                localStorage.removeItem('activeOptimizationId');
                showToast(`Optimization Failed: ${lastMessage.payload?.error}`, 'error');
                setOptimizationTaskId(null);
            }
        }

        // 3. Batch Updates
        if (lastMessage.type === 'BATCH' && batchTaskId && lastMessage.task_id === batchTaskId) {
            if (lastMessage.status === 'processing') {
                setBatchProgress(lastMessage.progress);
                setBatchStatusMsg(`Processing... (${lastMessage.progress}%)`);
            }
            if (lastMessage.status === 'completed') {
                setIsBatchRunning(false);
                setBatchProgress(100);
                setBatchStatusMsg("✅ Batch Test Completed!");
                setBatchResults(lastMessage.payload?.results || []);
                showToast('Batch Analysis Completed!', 'success');
                setBatchTaskId(null);
            }
            if (lastMessage.status === 'failed') {
                setIsBatchRunning(false);
                setBatchStatusMsg("❌ Batch Test Failed");
                showToast(`Batch Failed: ${lastMessage.payload?.error}`, 'error');
                setBatchTaskId(null);
            }
        }
    }, [lastMessage, backtestTaskId, optimizationTaskId, batchTaskId]);

    // Cleanup LocalStorage Optimization ID on Mount/Unmount if need check
    useEffect(() => {
        const savedTaskId = localStorage.getItem('activeOptimizationId');
        if (savedTaskId) {
            // Restore state if possible, or just clear it since we don't have persistence fully
            // Actually, we can try to re-attach if we had a way to check status, 
            // but for now let's just assume we might want to poll or wait for WS.
            setOptimizationTaskId(savedTaskId);
            setIsOptimizing(true);
        }
    }, []);

    // Handlers
    const runBacktest = async (payload: any) => {
        setIsRunning(true);
        setBacktestResult(null);
        setSingleResult(null);
        setProgress(0);
        // Save strategy name
        if (payload.strategy) lastRunStrategy.current = payload.strategy;

        try {
            const res = await runBacktestApi(payload);
            setBacktestTaskId(res.task_id);
        } catch (error) {
            console.error(error);
            setIsRunning(false);
            showToast('Failed to start backtest.', 'error');
        }
    };

    const runOptimization = async (payload: any) => {
        setIsOptimizing(true);
        setOptimizationProgress(0);
        // --- FIX: Save strategy name before running ---
        if (payload.strategy) lastRunStrategy.current = payload.strategy;

        try {
            const res = await runOptimizationApi(payload);
            const taskId = res.task_id;
            localStorage.setItem('activeOptimizationId', taskId);
            setOptimizationTaskId(taskId);
            showToast('Optimization Started!', 'success');
        } catch (error) {
            console.error(error);
            setIsOptimizing(false);
            showToast('Failed to start optimization.', 'error');
        }
    };

    const runBatch = async (payload: any) => {
        setIsBatchRunning(true);
        setBatchResults(null);
        setBatchProgress(0);
        setBatchStatusMsg("Initializing Batch Run...");
        try {
            const res = await runBatchBacktest(payload);
            setBatchTaskId(res.task_id);
            showToast('Batch Analysis Started!', 'success');
        } catch (error) {
            console.error(error);
            setIsBatchRunning(false);
            showToast('Failed to start batch analysis.', 'error');
        }
    };

    const stopOptimization = async () => {
        const taskId = localStorage.getItem('activeOptimizationId') || optimizationTaskId;
        if (taskId) {
            try { await revokeBacktestTask(taskId); showToast('Optimization stopped by user.', 'warning'); }
            catch (error) { console.error("Error stopping task:", error); }
        }
        setIsOptimizing(false);
        setOptimizationProgress(0);
        localStorage.removeItem('activeOptimizationId');
        setOptimizationTaskId(null);
    };

    return {
        isRunning,
        progress,
        isOptimizing,
        optimizationProgress,
        isBatchRunning,
        batchProgress,
        batchStatusMsg,
        singleResult,
        setSingleResult,
        batchResults,
        setBatchResults,
        multiObjectiveResults, // Just in case
        runBacktest,
        runOptimization,
        stopOptimization,
        runBatch,
        backtestResult
    };
};
