import { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { downloadCandles, downloadTrades, revokeBacktestTask } from '@/services/backtester';
import { useBacktestSocket } from '@/hooks/useBacktestSocket';
import { getExchangeMarkets } from '@/services/backtester';

export const useDownloadData = () => {
    const { showToast } = useToast();
    const { lastMessage } = useBacktestSocket();

    // Modal State
    const [isDownloadModalOpen, setIsDownloadModalOpen] = useState(false);

    // Form State
    const [downloadType, setDownloadType] = useState<'candles' | 'trades'>('candles');
    const [dlExchange, setDlExchange] = useState('binance');
    const [dlMarkets, setDlMarkets] = useState<string[]>([]);
    const [dlSymbol, setDlSymbol] = useState('BTC/USDT');
    const [dlTimeframe, setDlTimeframe] = useState('1h');
    const [dlStartDate, setDlStartDate] = useState('2024-01-01');
    const [dlEndDate, setDlEndDate] = useState('');

    // Status State
    const [isDownloading, setIsDownloading] = useState(false);
    const [downloadProgress, setDownloadProgress] = useState(0);
    const [isLoadingDlMarkets, setIsLoadingDlMarkets] = useState(false);
    const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

    // Load Markets when Exchange Changes in Modal
    useEffect(() => {
        const loadDlMarkets = async () => {
            if (!dlExchange || !isDownloadModalOpen) return;
            setIsLoadingDlMarkets(true);
            try {
                const pairs = await getExchangeMarkets(dlExchange);
                setDlMarkets(pairs);
                if (pairs.includes('BTC/USDT')) setDlSymbol('BTC/USDT');
                else if (pairs.length > 0) setDlSymbol(pairs[0]);
            } catch (error) {
                console.error("Failed to load markets for downloader", error);
            } finally {
                setIsLoadingDlMarkets(false);
            }
        };
        loadDlMarkets();
    }, [dlExchange, isDownloadModalOpen]);

    // WebSocket Listener
    useEffect(() => {
        if (!lastMessage || !activeTaskId) return;

        if (lastMessage.type === 'DOWNLOAD' && lastMessage.task_id === activeTaskId) {
            if (lastMessage.status === 'processing') {
                setDownloadProgress(lastMessage.progress);
            }
            if (lastMessage.status === 'completed') {
                setIsDownloading(false);
                setDownloadProgress(100);
                setActiveTaskId(null);
                showToast('Download Completed Successfully! 🎉', 'success');
            }
            if (lastMessage.status === 'failed' || lastMessage.status === 'Revoked') {
                setIsDownloading(false);
                setActiveTaskId(null);
                showToast(lastMessage.status === 'Revoked' ? 'Download Stopped' : 'Download Failed', 'error');
            }
        }
    }, [lastMessage, activeTaskId]);

    // Handlers
    const handleStartDownload = async () => {
        setIsDownloading(true);
        setDownloadProgress(0);

        try {
            if (!dlStartDate) {
                showToast('Please select a Start Date', 'warning');
                setIsDownloading(false);
                return;
            }

            const payload = {
                exchange: dlExchange,
                symbol: dlSymbol,
                start_date: `${dlStartDate} 00:00:00`,
                end_date: dlEndDate ? `${dlEndDate} 23:59:59` : undefined
            };

            let res;
            if (downloadType === 'candles') {
                res = await downloadCandles({ ...payload, timeframe: dlTimeframe });
            } else {
                res = await downloadTrades(payload);
            }

            if (res.task_id) {
                setActiveTaskId(res.task_id);
                showToast('Download Started...', 'info');
            } else {
                throw new Error("No Task ID returned");
            }
        } catch (e) {
            console.error(e);
            setIsDownloading(false);
            showToast('Failed to start download', 'error');
        }
    };

    const handleStopDownload = async () => {
        if (!activeTaskId) return;
        try {
            await revokeBacktestTask(activeTaskId);
            showToast('Stopping download...', 'warning');
        } catch (e) {
            console.error(e);
            showToast('Failed to stop task.', 'error');
        }
    };

    return {
        isDownloadModalOpen,
        setIsDownloadModalOpen,
        downloadType,
        setDownloadType,
        dlExchange,
        setDlExchange,
        dlMarkets,
        dlSymbol,
        setDlSymbol,
        dlTimeframe,
        setDlTimeframe,
        dlStartDate,
        setDlStartDate,
        dlEndDate,
        setDlEndDate,
        isDownloading,
        downloadProgress,
        isLoadingDlMarkets,
        handleStartDownload,
        handleStopDownload
    };
};
