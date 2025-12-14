import { useState, useCallback } from 'react';
import { backtestService, BacktestRequest, OptimizationRequest, WalkForwardRequest } from '@/services/backtester';
import { useToast } from '@/context/ToastContext';

export const useBacktestExecution = () => {
    const [isLoading, setIsLoading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [results, setResults] = useState<any>(null);
    const [mode, setMode] = useState<'backtest' | 'optimization' | 'walk_forward' | 'batch'>('backtest'); // ✅ Added 'batch'
    const { showToast } = useToast();

    const [taskId, setTaskId] = useState<string | null>(null); // ✅ Store Task ID

    const pollStatus = async (taskId: string) => {
        const interval = setInterval(async () => {
            try {
                const statusData = await backtestService.getStatus(taskId);

                if (statusData.percent !== undefined) {
                    setProgress(statusData.percent);
                }

                const status = statusData.status?.toUpperCase(); // Case insensitive check

                if (status === 'COMPLETED' || status === 'SUCCESS') {
                    clearInterval(interval);
                    setIsLoading(false);
                    setResults(statusData.result);
                    showToast('Analysis Completed Successfully!', 'success');
                } else if (status === 'FAILED' || status === 'FAILURE') {
                    clearInterval(interval);
                    setIsLoading(false);
                    showToast(`Analysis Failed: ${statusData.error}`, 'error');
                }
                // ✅ REVOKED Handling Fix
                else if (status === 'REVOKED') {
                    clearInterval(interval);
                    setIsLoading(false);
                    setProgress(0);
                    showToast('Analysis Stopped by User', 'info');
                }
            } catch (error) {
                console.error("Polling error:", error);
            }
        }, 1000);
    };

    // ✅ NEW: Execute Logic
    const execute = useCallback(async (
        payload: any, // Relaxed type to include batch
        currentMode: 'backtest' | 'optimization' | 'walk_forward' | 'batch'
    ) => {
        setIsLoading(true);
        setResults(null);
        setProgress(0);
        setMode(currentMode);
        setTaskId(null);

        try {
            let response;
            if (currentMode === 'optimization') {
                response = await backtestService.runOptimization(payload as OptimizationRequest);
            } else if (currentMode === 'walk_forward') {
                // ✅ Call Walk-Forward Service
                response = await backtestService.runWalkForward(payload as WalkForwardRequest);
            } else if (currentMode === 'batch') {
                // ✅ Call Batch API
                response = await backtestService.runBatchBacktest(payload);
            } else {
                response = await backtestService.runBacktest(payload as BacktestRequest);
            }

            if (response.task_id) {
                setTaskId(response.task_id); // ✅ Set Task ID
                pollStatus(response.task_id);
            } else {
                setIsLoading(false);
                showToast('Failed to start task', 'error');
            }
        } catch (error) {
            setIsLoading(false);
            showToast('Execution Error', 'error');
            console.error(error);
        }
    }, [showToast]);

    return {
        execute,
        isLoading,
        progress,
        results,
        mode,
        taskId // ✅ Return Task ID
    };
};
