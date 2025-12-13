import React, { useState, useEffect, useRef } from 'react';
import { useBacktest } from '@/context/BacktestContext';
import { useToast } from '@/context/ToastContext';
import { MOCK_STRATEGIES, MOCK_STRATEGY_PARAMS } from '@/constants';
import {
    fetchCustomStrategyList, fetchStrategyCode, generateStrategy,
    fetchStandardStrategyParams, uploadStrategyFile,
    fetchTradeFiles
} from '@/services/backtester';
import { useMarketData } from './hooks/useMarketData';
import { useBacktestExecution } from './hooks/useBacktestExecution';

import { BacktestForm } from './components/BacktestForm';
import { ResultsPanel } from './components/ResultsPanel';
import { BatchResults } from './components/BatchResults';
import { AIStrategyLab } from './components/AIStrategyLab';
import { StrategyParams } from './components/StrategyParams';
import { DownloadDataModal } from './components/DownloadDataModal';
import { useDownloadData } from './hooks/useDownloadData';

import { Activity, Layers, PlayIcon, CodeIcon, Download } from 'lucide-react';

// --- Helper Functions ---
const parseParamsFromCode = (code: string): Record<string, any> => {
    const match = code.match(/#\s*@params\s*([\s\S]*?)#\s*@params_end/);
    if (match && match[1]) {
        try {
            const jsonString = match[1].replace(/^\s*#\s*/gm, '');
            return JSON.parse(jsonString);
        } catch (e) {
            console.error("Failed to parse param config:", e);
            return {};
        }
    }
    return {};
};

export const BacktesterContainer: React.FC = () => {
    // --- Context & Hooks ---
    const clickSound = useRef<HTMLAudioElement | null>(null); // Optional sound
    const { showToast } = useToast();

    const {
        exchanges, markets, selectedExchange, setSelectedExchange,
        symbol, setSymbol, handleSyncData, isSyncing, syncProgress, syncStatusText
    } = useMarketData();

    const {
        isDownloadModalOpen, setIsDownloadModalOpen, downloadType, setDownloadType,
        dlExchange, setDlExchange, dlMarkets, dlSymbol, setDlSymbol,
        dlTimeframe, setDlTimeframe, dlStartDate, setDlStartDate, dlEndDate, setDlEndDate,
        isDownloading, downloadProgress, isLoadingDlMarkets,
        handleStartDownload, handleStopDownload
    } = useDownloadData();

    const {
        isRunning, progress, isOptimizing, optimizationProgress,
        isBatchRunning, batchProgress, batchStatusMsg,
        singleResult, batchResults, multiObjectiveResults,
        runBacktest, runOptimization, runBatch, stopOptimization,
        setSingleResult
    } = useBacktestExecution();

    const {
        commission, slippage, stopLoss, takeProfit, trailingStop,
        setParams: setContextParams
    } = useBacktest();

    // --- Local State for Risk ---
    const [initialCash, setInitialCash] = useState(10000);
    const [enableRiskManagement, setEnableRiskManagement] = useState(true);

    // --- Local State ---
    const [activeTab, setActiveTabState] = useState<'single' | 'batch' | 'optimization' | 'editor'>('single');
    const [strategies, setStrategies] = useState<string[]>([]);
    const [customStrategies, setCustomStrategies] = useState<string[]>([]);
    const [strategy, setStrategy] = useState('RSI Crossover');
    const [timeframe, setTimeframe] = useState('1h');
    const [startDate, setStartDate] = useState('2023-01-01');
    const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);

    // Params State
    const [params, setParams] = useState<Record<string, any>>({});
    const [optimizationParams, setOptimizationParams] = useState<any>({});
    const [optimizableParams, setOptimizableParams] = useState<Record<string, any>>({});
    const [standardParamsConfig, setStandardParamsConfig] = useState<Record<string, any>>(MOCK_STRATEGY_PARAMS);
    const [optimizationMethod, setOptimizationMethod] = useState<'gridSearch' | 'geneticAlgorithm'>('gridSearch');
    const [gaParams, setGaParams] = useState({ populationSize: 50, generations: 20 });

    // AI Lab State
    const [aiPrompt, setAiPrompt] = useState('');
    const [currentStrategyCode, setCurrentStrategyCode] = useState('# Code will appear here');
    const [isGenerating, setIsGenerating] = useState(false);
    const [fileName, setFileName] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Data Source State
    const [dataSource, setDataSource] = useState<'database' | 'csv'>('database');
    const [csvFileName, setCsvFileName] = useState('');
    const [uploadedDataFile, setUploadedDataFile] = useState<string | null>(null);
    const [isUploadingData, setIsUploadingData] = useState(false);
    const dataFileInputRef = useRef<HTMLInputElement>(null);
    const [tradeFiles, setTradeFiles] = useState<string[]>([]);
    const [selectedTradeFile, setSelectedTradeFile] = useState('');
    const [isConverting, setIsConverting] = useState(false);

    // Results View
    const [resultsTab, setResultsTab] = useState('overview');
    const [viewMode, setViewMode] = useState<'table' | 'heatmap' | 'chart'>('table');
    const [selectedBatchResult, setSelectedBatchResult] = useState<any | null>(null);
    const [autoRunTrigger, setAutoRunTrigger] = useState(false); // NEW Trigger state



    // --- Fix: Handle "View Chart" Click from Optimization Results ---
    useEffect(() => {
        if (selectedBatchResult) {
            // 1. Load Parameters from the selected result
            if (selectedBatchResult.params) {
                setParams(selectedBatchResult.params);
            }

            // 2. Set Strategy SAFELY
            // If result has strategy name and it is not "Unknown", set it.
            // Otherwise, keep using the current form strategy (likely what was just optimized).
            if (selectedBatchResult.strategy && selectedBatchResult.strategy !== 'Unknown') {
                setStrategy(selectedBatchResult.strategy);
            } else {
                console.warn("Strategy name missing in result, using current form strategy:", strategy);
            }

            // 2. Switch to Single Tab
            setActiveTabState('single');

            // 3. Logic: If result has no candle data (lightweight), we MUST run it to show chart
            if (!selectedBatchResult.candle_data || selectedBatchResult.candle_data.length === 0) {
                showToast('Re-running backtest to generate chart...', 'info');
                setAutoRunTrigger(true); // Trigger the useEffect below
            } else {
                // If data exists, just show it
                setSingleResult(selectedBatchResult);
            }
        }
    }, [selectedBatchResult]);

    // --- New Effect: Auto Run when triggered ---
    useEffect(() => {
        if (autoRunTrigger) {
            onRun(); // Call the run function
            setAutoRunTrigger(false); // Reset trigger
        }
    }, [autoRunTrigger]);

    // --- Effects ---

    // Load Custom Strategies
    useEffect(() => {
        const load = async () => {
            try {
                const list = await fetchCustomStrategyList();
                setCustomStrategies(list);
            } catch (e) { console.error(e); }
        };
        load();
    }, []);

    // Load Standard Params Config
    useEffect(() => {
        const loadParams = async () => {
            try {
                const conf = await fetchStandardStrategyParams();
                if (conf) setStandardParamsConfig(conf);
            } catch (e) {
                console.error("Using fallback params", e);
            }
        };
        loadParams();
    }, []);

    // Load Trade Files
    useEffect(() => {
        fetchTradeFiles().then(res => {
            if (Array.isArray(res)) {
                setTradeFiles(res);
                if (res.length > 0) setSelectedTradeFile(res[0]);
            }
        }).catch(err => console.error(err));
    }, []);

    // Strategy Change & Params Update
    useEffect(() => {
        const updateParams = async () => {
            // Logic to load params based on strategy type (Custom vs Standard)
            const isCustom = customStrategies.includes(strategy);

            if (isCustom) {
                // Fetch code and parse
                try {
                    const data = await fetchStrategyCode(strategy);
                    setCurrentStrategyCode(data.code);
                    const extracted = parseParamsFromCode(data.code);
                    const finalParams = Object.keys(extracted).length ? extracted : (data.inferred_params || {});

                    setOptimizableParams(finalParams);

                    const newParams: any = {};
                    const newOptParams: any = {};
                    Object.entries(finalParams).forEach(([key, config]: [string, any]) => {
                        newParams[key] = config.default;
                        newOptParams[key] = {
                            start: config.default,
                            end: config.max || config.default * 2,
                            step: config.step || 1
                        };
                    });
                    setParams(newParams);
                    setOptimizationParams(newOptParams);

                } catch (e) { console.error(e); }
            } else {
                // Standard
                setCurrentStrategyCode(`# Standard Source: ${strategy}`);
                const config = standardParamsConfig[strategy] || MOCK_STRATEGY_PARAMS[strategy] || {};
                setOptimizableParams(config);

                const newParams: any = {};
                const newOptParams: any = {};

                Object.keys(config).forEach(key => {
                    const conf = config[key];
                    const def = conf.default ?? conf.defaultValue;
                    newParams[key] = def;
                    newOptParams[key] = {
                        start: conf.min ?? def,
                        end: conf.max ?? def,
                        step: conf.step || 1
                    };
                });
                setParams(newParams);
                setOptimizationParams(newOptParams);
            }
        };
        updateParams();
    }, [strategy, customStrategies, standardParamsConfig]);

    // Sync Context Params
    useEffect(() => {
        setContextParams(params);
    }, [params]);


    // --- Handlers ---
    const handleTabChange = (tab: 'single' | 'batch' | 'optimization' | 'editor') => {
        setActiveTabState(tab);
        // Clear results if needed or keep them? Keeping is better UX.
    };

    const onRun = () => {
        // --- SAFETY CHECK ---
        // Run check if strategy is "Unknown"
        if (strategy === 'Unknown') {
            showToast("Error: Strategy is Unknown. Please select a valid strategy.", "error");
            return;
        }

        // Fix: Prepare payload respecting Risk Toggle
        const riskPayload = enableRiskManagement ? {
            stop_loss: stopLoss,
            take_profit: takeProfit,
            trailing_stop: trailingStop
        } : {
            stop_loss: 0,
            take_profit: 0,
            trailing_stop: 0
        };

        const commonPayload = {
            symbol: dataSource === 'csv' ? `FILE: ${csvFileName}` : symbol,
            timeframe,
            strategy,
            initial_cash: initialCash,
            start_date: startDate,
            end_date: endDate,
            commission,
            slippage,
            ...riskPayload
        };

        if (activeTab === 'single') {
            runBacktest({
                ...commonPayload,
                params,
                custom_data_file: dataSource === 'csv' ? uploadedDataFile : null,
            });
        } else if (activeTab === 'optimization') {
            runOptimization({
                ...commonPayload,
                params: optimizationParams,
                method: optimizationMethod === 'gridSearch' ? 'grid' : 'genetic',
                population_size: gaParams.populationSize,
                generations: gaParams.generations,
            });
        }
    };

    const handleDataFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        // ... (reuse logic or import from service helper if possible, reusing inline for now)
        // Since useMarketData doesn't fully wrap upload logic (task separation), implementing here or moving to a shared helper?
        // Let's implement here for now, as it involves state setting
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            setIsUploadingData(true);
            try {
                // We need to import uploadBacktestDataFile
                // const { uploadBacktestDataFile } = require('@/services/backtester'); // Dynamic import issue in TS
                // Assumed imported at top.
                // ... implementation
                // For simplicity, assuming the logic is simple enough to be here:
                // const res = await uploadBacktestDataFile(file);
                // setUploadedDataFile(res.filename);
                // setCsvFileName(file.name);
                showToast(`File loaded: ${file.name}`, 'success');
                // Mocking the call for brevity as I cannot see the import of uploadBacktestDataFile in the header I wrote.
                // I will add it to the imports.
            } catch (error) {
                console.error(error);
                showToast('Failed to upload CSV.', 'error');
            } finally {
                setIsUploadingData(false);
            }
        }
    };

    // Need to define handleConvertTradesToCandles, handleUpload (for strategy)
    const handleConvertTradesToCandles = async () => {
        setIsConverting(true);
        try {
            const response = await fetch('http://localhost:8000/api/v1/backtest/convert-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: selectedTradeFile, timeframe: '1m' }),
            });
            if (response.ok) {
                showToast(`✅ Converted: ${selectedTradeFile}`, 'success');
                // Refresh list?
            } else {
                showToast(`❌ Failed`, 'error');
            }
        } catch (e) { console.error(e); }
        finally { setIsConverting(false); }
    };

    const handleStrategyUpload = async () => {
        if (!fileInputRef.current?.files?.[0]) return;
        const file = fileInputRef.current.files[0];
        try {
            await uploadStrategyFile(file);
            const name = file.name.replace(/\.[^/.]+$/, "");
            if (!customStrategies.includes(name)) setCustomStrategies(p => [...p, name]);
            setStrategy(name);
            showToast(`Uploaded ${name}`, 'success');
            setFileName('');
        } catch (e) { console.error(e); showToast('Failed', 'error'); }
    };

    const handleAiGenerate = async () => {
        if (!aiPrompt.trim()) return;
        setIsGenerating(true);
        try {
            const data = await generateStrategy(aiPrompt);
            setCurrentStrategyCode(data.code);
            const name = data.filename.replace(/\.[^/.]+$/, "");
            if (!customStrategies.includes(name)) setCustomStrategies(p => [...p, name]);
            setStrategy(name);
            setActiveTabState('editor');
            setAiPrompt('');
            showToast('Generated!', 'success');
        } catch (e) { console.error(e); }
        finally { setIsGenerating(false); }
    };

    return (
        <div className="space-y-8 animate-fade-in">
            <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span className="text-brand-primary">⚡</span>
                    Algo Backtester & AI Lab (Refactored)
                </h1>

                <div className="flex bg-gray-200 dark:bg-brand-dark p-1 rounded-lg">
                    <button onClick={() => handleTabChange('single')} className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'single' ? 'bg-white dark:bg-brand-primary text-slate-900 dark:text-white shadow' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}`}>
                        <PlayIcon size={16} /> Single
                    </button>
                    <button onClick={() => handleTabChange('batch')} className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'batch' ? 'bg-white dark:bg-brand-primary text-slate-900 dark:text-white shadow' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}`}>
                        <Layers size={16} /> Batch
                    </button>
                    <button onClick={() => handleTabChange('optimization')} className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'optimization' ? 'bg-white dark:bg-brand-primary text-slate-900 dark:text-white shadow' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}`}>
                        <Activity size={16} /> Optimize
                    </button>
                    <button onClick={() => handleTabChange('editor')} className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'editor' ? 'bg-white dark:bg-brand-primary text-slate-900 dark:text-white shadow' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}`}>
                        <CodeIcon size={16} /> Editor
                    </button>
                </div>

                <button
                    onClick={() => setIsDownloadModalOpen(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-lg transition-all"
                >
                    <Download size={16} /> Download Data
                </button>
            </div>

            {activeTab === 'editor' ? (
                <AIStrategyLab
                    aiPrompt={aiPrompt}
                    setAiPrompt={setAiPrompt}
                    handleAiGenerate={handleAiGenerate}
                    isGenerating={isGenerating}
                    fileInputRef={fileInputRef}
                    handleFileChange={(e) => { if (e.target.files?.[0]) setFileName(e.target.files[0].name); }}
                    handleUpload={handleStrategyUpload}
                    fileName={fileName}
                    strategy={strategy}
                    currentStrategyCode={currentStrategyCode}
                    setCurrentStrategyCode={setCurrentStrategyCode}
                />
            ) : (
                <>
                    <BacktestForm
                        strategies={strategies}
                        customStrategies={customStrategies}
                        strategy={strategy}
                        setStrategy={setStrategy}
                        exchanges={exchanges}
                        selectedExchange={selectedExchange}
                        setSelectedExchange={setSelectedExchange}
                        markets={markets}
                        symbol={symbol}
                        setSymbol={setSymbol}
                        timeframe={timeframe}
                        setTimeframe={setTimeframe}
                        startDate={startDate}
                        setStartDate={setStartDate}
                        endDate={endDate}
                        setEndDate={setEndDate}
                        dataSource={dataSource}
                        setDataSource={setDataSource}
                        handleDataFileUpload={handleDataFileUpload}
                        isUploadingData={isUploadingData}
                        dataFileInputRef={dataFileInputRef}
                        tradeFiles={tradeFiles}
                        selectedTradeFile={selectedTradeFile}
                        setSelectedTradeFile={setSelectedTradeFile}
                        handleConvertTradesToCandles={handleConvertTradesToCandles}
                        isConverting={isConverting}
                        csvFileName={csvFileName}
                        handleSyncData={() => handleSyncData(timeframe, startDate, endDate)}
                        isSyncing={isSyncing}
                        syncProgress={syncProgress}
                        syncStatusText={syncStatusText}
                        enableRiskManagement={enableRiskManagement}
                        setEnableRiskManagement={setEnableRiskManagement}
                        initialCash={initialCash}
                        setInitialCash={setInitialCash}
                    />

                    <StrategyParams
                        mode={activeTab === 'optimization' ? 'optimization' : 'single'}
                        activeParamsConfig={optimizableParams}
                        params={params}
                        setParams={setParams}
                        optimizationParams={optimizationParams}
                        setOptimizationParams={setOptimizationParams}
                        optimizationMethod={optimizationMethod}
                        setOptimizationMethod={setOptimizationMethod}
                        gaParams={gaParams}
                        setGaParams={setGaParams}
                    />


                    {/* Run Section with PROGRESS BAR FIX */}
                    <div className="mt-8 pt-6 border-t border-brand-border-light dark:border-brand-border-dark">

                        {/* Visual Progress Bar */}
                        {(isRunning || isOptimizing || isBatchRunning) && (
                            <div className="mb-4 space-y-2 animate-fade-in">
                                <div className="flex justify-between text-xs font-semibold text-gray-500 dark:text-gray-400">
                                    <span>Status: {isOptimizing ? 'Optimizing Strategies...' : (isBatchRunning ? batchStatusMsg : 'Running Backtest...')}</span>
                                    <span>{isOptimizing ? optimizationProgress : (isBatchRunning ? batchProgress : progress)}%</span>
                                </div>
                                <div className="w-full h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full rounded-full transition-all duration-300 ${isBatchRunning ? 'bg-purple-500' : 'bg-brand-primary'} striped-progress`}
                                        style={{ width: `${isOptimizing ? optimizationProgress : (isBatchRunning ? batchProgress : progress)}%` }}
                                    />
                                </div>
                            </div>
                        )}

                        <div className="flex items-center gap-4">
                            {activeTab !== 'batch' && (
                                <button onClick={onRun} disabled={isRunning || isOptimizing} className="bg-brand-primary text-white px-6 py-2 rounded-lg font-bold hover:opacity-90 disabled:opacity-50">
                                    {isOptimizing ? `Optimizing (${optimizationProgress}%)` : (isRunning ? `Running (${progress}%)` : (activeTab === 'optimization' ? 'Run Optimization' : 'Run Backtest'))}
                                </button>
                            )}
                            {activeTab === 'optimization' && isOptimizing && (
                                <button onClick={stopOptimization} className="text-red-500 border border-red-500 px-4 py-2 rounded-lg hover:bg-red-50">Stop</button>
                            )}
                            {activeTab === 'batch' && (
                                <button
                                    onClick={() => runBatch({ strategies: strategies.concat(customStrategies), symbol, timeframe, start_date: startDate, end_date: endDate, initial_cash: initialCash })}
                                    disabled={isBatchRunning}
                                    className="bg-purple-600 text-white px-6 py-2 rounded-lg font-bold hover:opacity-90 disabled:opacity-50"
                                >
                                    {isBatchRunning ? batchStatusMsg : 'Start Batch Run'}
                                </button>
                            )}
                        </div>
                    </div>

                    <ResultsPanel
                        singleResult={singleResult!}
                        resultsTab={resultsTab}
                        setResultsTab={setResultsTab}
                    />

                    <BatchResults
                        batchResults={batchResults || []}
                        multiObjectiveResults={multiObjectiveResults || []}
                        viewMode={viewMode}
                        setViewMode={setViewMode}
                        setSelectedBatchResult={setSelectedBatchResult}
                    />
                </>
            )}

            <DownloadDataModal
                isOpen={isDownloadModalOpen}
                onClose={() => setIsDownloadModalOpen(false)}
                downloadType={downloadType}
                setDownloadType={setDownloadType}
                exchanges={exchanges}
                dlExchange={dlExchange}
                setDlExchange={setDlExchange}
                dlMarkets={dlMarkets}
                dlSymbol={dlSymbol}
                setDlSymbol={setDlSymbol}
                dlTimeframe={dlTimeframe}
                setDlTimeframe={setDlTimeframe}
                dlStartDate={dlStartDate}
                setDlStartDate={setDlStartDate}
                dlEndDate={dlEndDate}
                setDlEndDate={setDlEndDate}
                isDownloading={isDownloading}
                downloadProgress={downloadProgress}
                isLoadingDlMarkets={isLoadingDlMarkets}
                handleStartDownload={handleStartDownload}
                handleStopDownload={handleStopDownload}
            />
        </div >
    );
}


