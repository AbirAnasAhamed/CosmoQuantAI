import React, { useState, useEffect } from 'react';
import { marketDataService } from '@/services/marketData';
import { useBacktest } from '@/context/BacktestContext';
import SearchableSelect from '@/components/common/SearchableSelect';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { UploadCloud, RefreshCw, ShieldCheck, ShieldAlert, Wallet, Calendar, Clock, History, ChevronLeft, ChevronRight, PlusCircle, Play, Layers, GitMerge } from 'lucide-react';
import { StrategyBuilderModal } from './StrategyBuilderModal';
import { getYear, getMonth } from 'date-fns';
import Button from '@/components/common/Button';

// Constants
const range = (start: number, end: number, step = 1) => {
    const result = [];
    for (let i = start; i <= end; i += step) {
        result.push(i);
    }
    return result;
};

// ডিফল্ট টাইমফ্রেম লিস্ট (যদি লোড হতে দেরি হয়)
const DEFAULT_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"];

interface BacktestFormProps {
    strategies: string[];
    customStrategies: string[];
    strategy: string;
    setStrategy: (s: string) => void;
    exchanges: string[];
    selectedExchange: string;
    setSelectedExchange: (e: string) => void;
    markets: string[];
    symbol: string;
    setSymbol: (s: string) => void;
    timeframe: string;
    setTimeframe: (t: string) => void;
    startDate: string;
    setStartDate: (d: string) => void;
    endDate: string;
    setEndDate: (d: string) => void;
    dataSource: 'database' | 'csv';
    setDataSource: (source: 'database' | 'csv') => void;
    handleDataFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
    isUploadingData: boolean;
    dataFileInputRef: React.RefObject<HTMLInputElement>;
    tradeFiles: string[];
    selectedTradeFile: string;
    setSelectedTradeFile: (f: string) => void;
    handleConvertTradesToCandles: () => void;
    isConverting: boolean;
    csvFileName: string;
    handleSyncData: () => void;
    isSyncing: boolean;
    syncProgress: number;
    syncStatusText: string;
    enableRiskManagement: boolean;
    setEnableRiskManagement: (v: boolean) => void;
    initialCash: number;
    setInitialCash: (v: number) => void;
    mode: 'backtest' | 'optimization' | 'walk_forward';
    setMode: (m: 'backtest' | 'optimization' | 'walk_forward') => void;
    wfaTrainWindow: number;
    setWfaTrainWindow: (n: number) => void;
    wfaTestWindow: number;
    setWfaTestWindow: (n: number) => void;
}

export const BacktestForm: React.FC<BacktestFormProps> = ({
    strategies,
    customStrategies,
    strategy,
    setStrategy,
    exchanges,
    selectedExchange,
    setSelectedExchange,
    markets,
    symbol,
    setSymbol,
    timeframe,
    setTimeframe,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    dataSource,
    setDataSource,
    handleDataFileUpload,
    isUploadingData,
    dataFileInputRef,
    tradeFiles,
    selectedTradeFile,
    setSelectedTradeFile,
    handleConvertTradesToCandles,
    isConverting,
    csvFileName,
    handleSyncData,
    isSyncing,
    syncProgress,
    syncStatusText,
    enableRiskManagement,
    setEnableRiskManagement,
    initialCash,
    setInitialCash,
    mode, setMode,
    wfaTrainWindow, setWfaTrainWindow,
    wfaTestWindow, setWfaTestWindow
}) => {
    const {
        commission, setCommission,
        slippage, setSlippage,
        leverage, setLeverage, // ✅ NEW
        secondaryTimeframe, setSecondaryTimeframe,
        stopLoss, setStopLoss,
        takeProfit, setTakeProfit,
        trailingStop, setTrailingStop
    } = useBacktest();

    // ✅ নতুন স্টেট: ডাইনামিক টাইমফ্রেম স্টোর করার জন্য
    const [availableTimeframes, setAvailableTimeframes] = useState<string[]>(DEFAULT_TIMEFRAMES);
    const [isLoadingTimeframes, setIsLoadingTimeframes] = useState(false);

    // Strategy Builder State
    const [isBuilderOpen, setIsBuilderOpen] = useState(false);

    // ✅ এফেক্ট: যখনই selectedExchange চেঞ্জ হবে, নতুন টাইমফ্রেম আনবে
    useEffect(() => {
        const fetchTimeframes = async () => {
            if (!selectedExchange) return;

            setIsLoadingTimeframes(true);
            try {
                const tfs = await marketDataService.getExchangeTimeframes(selectedExchange);
                setAvailableTimeframes(tfs);

                // যদি বর্তমান সিলেক্ট করা timeframe টি নতুন লিস্টে না থাকে, তবে প্রথমটি সেট করে দিন
                if (tfs.length > 0 && !tfs.includes(timeframe)) {
                    // setTimeframe(tfs[0]); // Optional: auto-select first available
                }
            } catch (error) {
                console.error("Failed to fetch timeframes:", error);
                setAvailableTimeframes(DEFAULT_TIMEFRAMES);
            } finally {
                setIsLoadingTimeframes(false);
            }
        };

        fetchTimeframes();
    }, [selectedExchange]);

    const inputBaseClasses = "w-full bg-white dark:bg-brand-dark/50 border border-brand-border-light dark:border-brand-border-dark rounded-md p-2 text-slate-900 dark:text-white focus:ring-brand-primary focus:border-brand-primary";

    // Quick Date Presets Handler
    const handlePresetChange = (days: number) => {
        const end = new Date();
        const start = new Date();
        start.setDate(end.getDate() - days);

        setEndDate(end.toISOString().split('T')[0]);
        setStartDate(start.toISOString().split('T')[0]);
    };

    const presetOptions = [
        { label: '1W', days: 7 },
        { label: '1M', days: 30 },
        { label: '3M', days: 90 },
        { label: '6M', days: 180 },
        { label: '1Y', days: 365 },
        { label: 'YTD', days: Math.floor((new Date().getTime() - new Date(new Date().getFullYear(), 0, 1).getTime()) / (1000 * 60 * 60 * 24)) },
    ];

    // Custom Header Component for DatePicker
    const CustomInputHeader = ({
        date,
        changeYear,
        changeMonth,
        decreaseMonth,
        increaseMonth,
        prevMonthButtonDisabled,
        nextMonthButtonDisabled,
    }: any) => {
        const years = range(1990, getYear(new Date()) + 1, 1); // 1990 থেকে বর্তমান বছর + ১
        const months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ];

        return (
            <div className="m-2 flex items-center justify-between px-2 py-2 bg-white dark:bg-slate-800 rounded-lg border-b border-gray-200 dark:border-gray-700">
                {/* Previous Month Button */}
                <button
                    onClick={decreaseMonth}
                    disabled={prevMonthButtonDisabled}
                    className="p-1 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-full text-slate-600 dark:text-slate-300 transition-colors disabled:opacity-50"
                    type="button"
                >
                    <ChevronLeft size={18} />
                </button>

                {/* Dropdowns Container */}
                <div className="flex gap-2">
                    {/* Month Select */}
                    <select
                        value={months[getMonth(date)]}
                        onChange={({ target: { value } }) => changeMonth(months.indexOf(value))}
                        className="bg-transparent text-sm font-bold text-slate-800 dark:text-white cursor-pointer focus:outline-none hover:text-brand-primary dark:hover:text-brand-primary transition-colors appearance-none text-center"
                    >
                        {months.map((option) => (
                            <option key={option} value={option} className="bg-white dark:bg-slate-800 text-slate-900 dark:text-white">
                                {option}
                            </option>
                        ))}
                    </select>

                    {/* Year Select */}
                    <select
                        value={getYear(date)}
                        onChange={({ target: { value } }) => changeYear(Number(value))}
                        className="bg-transparent text-sm font-bold text-slate-800 dark:text-white cursor-pointer focus:outline-none hover:text-brand-primary dark:hover:text-brand-primary transition-colors appearance-none text-center"
                    >
                        {years.map((option) => (
                            <option key={option} value={option} className="bg-white dark:bg-slate-800 text-slate-900 dark:text-white">
                                {option}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Next Month Button */}
                <button
                    onClick={increaseMonth}
                    disabled={nextMonthButtonDisabled}
                    className="p-1 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-full text-slate-600 dark:text-slate-300 transition-colors disabled:opacity-50"
                    type="button"
                >
                    <ChevronRight size={18} />
                </button>
            </div>
        );
    };

    return (
        <div className="space-y-6">
            {/* Control Panel Header */}
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white">Settings</h2>
                <Button
                    variant="secondary"
                    onClick={handleSyncData}
                    disabled={isSyncing}
                    className={`transition-all duration-300 ${isSyncing ? 'bg-blue-50 text-blue-600 border-blue-200' : ''}`}
                >
                    {isSyncing ? (
                        <span className="flex items-center gap-2">
                            <RefreshCw className="animate-spin" size={16} /> Syncing...
                        </span>
                    ) : (
                        <span className="flex items-center gap-2">
                            <UploadCloud size={16} /> Sync Data
                        </span>
                    )}
                </Button>
            </div>

            {/* ✅ NEW: Mode Selection Tab */}
            <div className="bg-gray-100 dark:bg-slate-800 p-1 rounded-lg flex text-sm font-medium mb-4">
                <button
                    onClick={() => setMode('backtest')}
                    className={`flex-1 py-2 rounded-md flex items-center justify-center gap-2 transition-all ${mode === 'backtest' ? 'bg-white dark:bg-slate-700 shadow text-brand-primary' : 'text-gray-500 hover:text-gray-700'}`}
                >
                    <Play size={16} /> Standard Backtest
                </button>
                <button
                    onClick={() => setMode('optimization')}
                    className={`flex-1 py-2 rounded-md flex items-center justify-center gap-2 transition-all ${mode === 'optimization' ? 'bg-white dark:bg-slate-700 shadow text-brand-primary' : 'text-gray-500 hover:text-gray-700'}`}
                >
                    <Layers size={16} /> Optimization
                </button>
                <button
                    onClick={() => setMode('walk_forward')}
                    className={`flex-1 py-2 rounded-md flex items-center justify-center gap-2 transition-all ${mode === 'walk_forward' ? 'bg-white dark:bg-slate-700 shadow text-brand-primary' : 'text-gray-500 hover:text-gray-700'}`}
                >
                    <GitMerge size={16} /> Walk-Forward
                </button>
            </div>

            {/* Sync Progress */}
            {isSyncing && (
                <div className="mb-4 p-4 rounded-xl border border-blue-100 dark:border-blue-900/30 bg-blue-50/50 dark:bg-blue-900/10 backdrop-blur-sm shadow-sm animate-fade-in">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">{syncStatusText}</span>
                        <span className="text-sm font-bold text-blue-600 dark:text-blue-400">{syncProgress}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-blue-500 rounded-full transition-all duration-500 ease-out"
                            style={{ width: `${syncProgress}%` }}
                        />
                    </div>
                </div>
            )}


            {/* Data Source Selection */}
            <div className="mb-6 border-b border-gray-200 dark:border-gray-700 pb-4">
                <label className="text-sm font-semibold text-gray-500 mb-2 block">Data Source</label>
                <div className="flex gap-4">
                    <button
                        onClick={() => setDataSource('database')}
                        className={`flex-1 flex items-center gap-2 px-4 py-3 border rounded-lg transition-all ${dataSource === 'database' ? 'border-brand-primary bg-brand-primary/5 ring-2 ring-brand-primary/20' : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'}`}
                    >
                        <span className="text-lg">🗄️</span>
                        <div className="text-left">
                            <div className="font-semibold text-sm text-slate-900 dark:text-white">Exchange Database</div>
                            <div className="text-xs text-gray-500">Sync from Binance/Bybit</div>
                        </div>
                    </button>

                    <button
                        onClick={() => setDataSource('csv')}
                        className={`flex-1 flex items-center gap-2 px-4 py-3 border rounded-lg transition-all ${dataSource === 'csv' ? 'border-brand-primary bg-brand-primary/5 ring-2 ring-brand-primary/20' : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'}`}
                    >
                        <span className="text-lg">📂</span>
                        <div className="text-left">
                            <div className="font-semibold text-sm text-slate-900 dark:text-white">Upload CSV</div>
                            <div className="text-xs text-gray-500">Use local OHLCV data</div>
                        </div>
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Database Mode Inputs */}
                {dataSource === 'database' && (
                    <>
                        <div>
                            <label className="block text-sm font-medium text-gray-500 mb-1">Exchange</label>
                            <select className={inputBaseClasses} value={selectedExchange} onChange={(e) => setSelectedExchange(e.target.value)}>
                                {exchanges.map(ex => <option key={ex} value={ex}>{ex.toUpperCase()}</option>)}
                            </select>
                        </div>
                        <div>
                            <SearchableSelect label="Market Pair" options={markets} value={symbol} onChange={setSymbol} />
                        </div>
                    </>
                )}

                {/* CSV Mode Inputs */}
                {dataSource === 'csv' && (
                    <div className="col-span-2">
                        <label className="block text-sm font-medium text-gray-500 mb-1">Upload Data (CSV)</label>
                        <div className="flex gap-2">
                            <input type="file" ref={dataFileInputRef} onChange={handleDataFileUpload} className="hidden" accept=".csv" />
                            <Button variant="outline" onClick={() => dataFileInputRef.current?.click()} className="w-full h-10 border-dashed border-2 flex items-center justify-center gap-2">
                                <UploadCloud size={16} /> {isUploadingData ? 'Uploading...' : 'Choose CSV'}
                            </Button>
                            <select
                                className="bg-gray-800 border border-gray-600 text-white text-sm rounded px-2 py-1 outline-none"
                                value={selectedTradeFile}
                                onChange={(e) => setSelectedTradeFile(e.target.value)}
                            >
                                <option value="" disabled>Select File</option>
                                {tradeFiles.map((file, index) => <option key={index} value={file}>{file}</option>)}
                                <option value="all">Convert All</option>
                            </select>
                            <Button
                                variant="secondary"
                                onClick={handleConvertTradesToCandles}
                                disabled={isConverting}
                            >
                                {isConverting ? "..." : "Convert"}
                            </Button>
                        </div>
                        {csvFileName && <p className="text-xs text-green-600 mt-1">✅ {csvFileName}</p>}
                    </div>
                )}

                {/* Strategies */}
                <div>
                    <div className="flex justify-between items-center mb-1">
                        <label className="block text-sm font-medium text-gray-500">Strategy</label>
                        <button
                            onClick={() => setIsBuilderOpen(true)}
                            className="text-xs flex items-center gap-1 text-brand-primary hover:text-brand-primary/80 font-semibold transition-colors"
                        >
                            <PlusCircle size={12} /> New
                        </button>
                    </div>
                    <select className={inputBaseClasses} value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                        <optgroup label="Strategy Library">
                            {strategies.map(s => <option key={s} value={s}>{s}</option>)}
                        </optgroup>

                        {customStrategies.length > 0 && (
                            <optgroup label="My Custom Strategies">
                                {customStrategies.map(s => <option key={s} value={s}>{s}</option>)}
                            </optgroup>
                        )}
                    </select>
                </div>

                {/* ✅ NEW: Walk-Forward Settings Panel */}
                {mode === 'walk_forward' && (
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4 mb-4 animate-fade-in col-span-1 md:col-span-2 lg:col-span-3">
                        <h3 className="text-sm font-bold text-blue-800 dark:text-blue-300 mb-3 flex items-center gap-2">
                            <GitMerge size={16} /> Walk-Forward Analysis Config
                        </h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs text-gray-500 font-semibold mb-1 block">Training Window (Days)</label>
                                <input
                                    type="number"
                                    value={wfaTrainWindow}
                                    onChange={(e) => setWfaTrainWindow(Number(e.target.value))}
                                    className="w-full bg-white dark:bg-slate-900 border border-blue-200 dark:border-blue-800 rounded p-2 text-sm"
                                    placeholder="e.g. 90"
                                />
                                <p className="text-[10px] text-gray-400 mt-1">In-sample period for optimization</p>
                            </div>
                            <div>
                                <label className="text-xs text-gray-500 font-semibold mb-1 block">Testing Window (Days)</label>
                                <input
                                    type="number"
                                    value={wfaTestWindow}
                                    onChange={(e) => setWfaTestWindow(Number(e.target.value))}
                                    className="w-full bg-white dark:bg-slate-900 border border-blue-200 dark:border-blue-800 rounded p-2 text-sm"
                                    placeholder="e.g. 30"
                                />
                                <p className="text-[10px] text-gray-400 mt-1">Out-of-sample period for validation</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Timeframe */}
                <div>
                    <label className="block text-sm font-medium text-gray-500 mb-1">
                        Timeframe
                        {isLoadingTimeframes && <span className="text-xs text-brand-primary ml-2 animate-pulse">Loading...</span>}
                    </label>
                    <select
                        className={inputBaseClasses}
                        value={timeframe}
                        onChange={(e) => setTimeframe(e.target.value)}
                        disabled={isLoadingTimeframes}
                    >
                        {availableTimeframes.map(t => (
                            <option key={t} value={t}>{t}</option>
                        ))}
                    </select>
                </div>

                {/* Secondary Timeframe */}
                <div>
                    <label className="block text-sm font-medium text-gray-500 mb-1">
                        Secondary TF <span className="text-[10px] text-brand-primary">(Optional)</span>
                    </label>
                    <select className={inputBaseClasses} value={secondaryTimeframe} onChange={(e) => setSecondaryTimeframe(e.target.value)}>
                        <option value="">None</option>
                        {availableTimeframes.map(t => (
                            <option key={t} value={t}>{t}</option>
                        ))}
                    </select>
                </div>

                {/* Modern Time Horizon & Date Selection */}
                <div className="col-span-1 md:col-span-2 lg:col-span-3 bg-gray-50 dark:bg-slate-800/50 p-4 rounded-xl border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-2 mb-3">
                        <History size={16} className="text-brand-primary" />
                        <label className="text-sm font-bold text-slate-700 dark:text-slate-300">Time Horizon</label>
                    </div>

                    <div className="flex flex-col lg:flex-row gap-4 items-end">
                        {/* Date Inputs Group */}
                        <div className="flex-1 grid grid-cols-2 gap-4 w-full">
                            <div className="relative group">
                                <label className="text-xs font-semibold text-gray-500 mb-1.5 block ml-1">Start Date</label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                        <Calendar size={14} className="text-gray-400 group-focus-within:text-brand-primary transition-colors" />
                                    </div>
                                    <DatePicker
                                        selected={startDate ? new Date(startDate) : null}
                                        onChange={(date: Date) => setStartDate(date?.toISOString().split('T')[0] || '')}
                                        className={`${inputBaseClasses} pl-9 font-medium transition-all hover:border-brand-primary/50 cursor-pointer`}
                                        dateFormat="yyyy-MM-dd"
                                        placeholderText="Select start"

                                        // ✨ নতুন সিস্টেম: কাস্টম হেডার
                                        renderCustomHeader={CustomInputHeader}

                                        // বডি ডার্ক মোড ফিক্স (সরাসরি ক্লাস অ্যাপ্লাই করা)
                                        calendarClassName="!bg-white dark:!bg-slate-900 !border-gray-200 dark:!border-gray-700 !font-sans !text-slate-900 dark:!text-slate-100 shadow-xl rounded-xl overflow-hidden"
                                        dayClassName={() => "dark:text-slate-200 hover:!bg-brand-primary hover:!text-white rounded-full"}
                                        popperClassName="!z-50" // নিশ্চিত করে যে এটি সবকিছুর উপরে দেখাবে
                                    />
                                </div>
                            </div>

                            <div className="relative group">
                                <label className="text-xs font-semibold text-gray-500 mb-1.5 block ml-1">End Date</label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                        <Clock size={14} className="text-gray-400 group-focus-within:text-brand-primary transition-colors" />
                                    </div>
                                    <DatePicker
                                        selected={endDate ? new Date(endDate) : null}
                                        onChange={(date: Date) => setEndDate(date?.toISOString().split('T')[0] || '')}
                                        className={`${inputBaseClasses} pl-9 font-medium transition-all hover:border-brand-primary/50 cursor-pointer`}
                                        dateFormat="yyyy-MM-dd"
                                        placeholderText="Select end"

                                        // ✨ নতুন সিস্টেম: কাস্টম হেডার
                                        renderCustomHeader={CustomInputHeader}

                                        // বডি ডার্ক মোড ফিক্স
                                        calendarClassName="!bg-white dark:!bg-slate-900 !border-gray-200 dark:!border-gray-700 !font-sans !text-slate-900 dark:!text-slate-100 shadow-xl rounded-xl overflow-hidden"
                                        dayClassName={() => "dark:text-slate-200 hover:!bg-brand-primary hover:!text-white rounded-full"}
                                        popperClassName="!z-50"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Quick Select Buttons */}
                        <div className="w-full lg:w-auto">
                            <label className="text-xs font-semibold text-gray-500 mb-1.5 block ml-1 lg:text-right px-1">Quick Select</label>
                            <div className="flex bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-gray-700 p-1">
                                {presetOptions.map((option) => (
                                    <button
                                        key={option.label}
                                        onClick={() => handlePresetChange(option.days)}
                                        className="flex-1 px-3 py-1.5 text-xs font-medium rounded-md text-slate-600 dark:text-slate-400 hover:bg-brand-primary/10 hover:text-brand-primary transition-all focus:outline-none focus:ring-2 focus:ring-brand-primary/20 active:scale-95"
                                    >
                                        {option.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Execution & Risk Settings (Modified) */}
            <div className="mt-4 pt-4 border-t border-brand-border-light dark:border-brand-border-dark">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        {enableRiskManagement ? <ShieldCheck size={16} className="text-green-500" /> : <ShieldAlert size={16} className="text-gray-400" />}
                        Risk Management & Execution
                    </h3>
                    <div className="flex items-center gap-2">
                        <label className="text-xs text-gray-500 cursor-pointer" htmlFor="risk-toggle">Enable Risk Params</label>
                        <input
                            id="risk-toggle"
                            type="checkbox"
                            checked={enableRiskManagement}
                            onChange={(e) => setEnableRiskManagement(e.target.checked)}
                            className="w-4 h-4 text-brand-primary rounded focus:ring-brand-primary border-gray-300"
                        />
                    </div>
                </div>

                <div className={`grid grid-cols-2 md:grid-cols-5 gap-4 transition-opacity duration-300 ${enableRiskManagement ? 'opacity-100' : 'opacity-50'}`}>
                    <div>
                        <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1">
                            <Wallet size={12} /> Initial Cash ($)
                        </label>
                        <input
                            type="number"
                            value={initialCash}
                            onChange={(e) => setInitialCash(Number(e.target.value))}
                            className={`${inputBaseClasses} font-bold text-green-600 dark:text-green-400`}
                        />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-500 mb-1">Commission (%)</label>
                        <input type="number" step="0.01" value={commission} onChange={(e) => setCommission(parseFloat(e.target.value))} className={inputBaseClasses} />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-500 mb-1">Slippage (%)</label>
                        <input type="number" step="0.01" value={slippage} onChange={(e) => setSlippage(parseFloat(e.target.value))} className={inputBaseClasses} />
                    </div>
                    {/* ✅ Leverage Input Section */}
                    <div className="col-span-2 md:col-span-3"> {/* Full width or partial */}
                        <div className="space-y-2 border border-gray-700 p-2 rounded-lg">
                            <label className="text-xs font-medium text-gray-300 flex justify-between">
                                <span>Leverage (x{leverage})</span>
                                <span className="text-[10px] text-gray-500">{leverage > 1 ? "Futures Mode" : "Spot Mode"}</span>
                            </label>
                            <div className="flex items-center gap-4">
                                <input
                                    type="range"
                                    min="1"
                                    max="20"
                                    step="1"
                                    value={leverage}
                                    onChange={(e) => setLeverage(Number(e.target.value))}
                                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                                />
                                <input
                                    type="number"
                                    min="1"
                                    max="125"
                                    value={leverage}
                                    onChange={(e) => setLeverage(Number(e.target.value))}
                                    className="w-16 px-2 py-1 bg-gray-800 border border-gray-700 rounded-md text-white text-xs focus:outline-none focus:border-blue-500"
                                />
                            </div>
                        </div>
                    </div>
                    {/* Only disable these if risk is off, commission/slippage usually apply always but user might want full off */}
                    <div>
                        <label className="block text-xs text-gray-500 mb-1">Stop Loss (%)</label>
                        <input type="number" step="0.1" value={stopLoss} disabled={!enableRiskManagement} onChange={(e) => setStopLoss(parseFloat(e.target.value))} className={inputBaseClasses} />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-500 mb-1">Take Profit (%)</label>
                        <input type="number" step="0.1" value={takeProfit} disabled={!enableRiskManagement} onChange={(e) => setTakeProfit(parseFloat(e.target.value))} className={inputBaseClasses} />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-500 mb-1">Trailing Stop (%)</label>
                        <input type="number" step="0.1" value={trailingStop} disabled={!enableRiskManagement} onChange={(e) => setTrailingStop(parseFloat(e.target.value))} className={inputBaseClasses} />
                    </div>
                </div>
            </div>

            {/* Strategy Builder Modal */}
            <StrategyBuilderModal
                isOpen={isBuilderOpen}
                onClose={() => setIsBuilderOpen(false)}
                onSuccess={() => {
                    // Reload page to refresh strategy list
                    window.location.reload();
                }}
            />
        </div>
    );
}
