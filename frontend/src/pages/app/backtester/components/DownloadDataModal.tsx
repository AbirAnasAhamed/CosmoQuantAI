import React from 'react';
import { X, Download, AlertCircle, ChevronLeft, ChevronRight, Calendar, Clock } from 'lucide-react';
import { getYear, getMonth } from 'date-fns';
import Button from '@/components/common/Button';
import SearchableSelect from '@/components/common/SearchableSelect';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

interface DownloadDataModalProps {
    isOpen: boolean;
    onClose: () => void;
    downloadType: 'candles' | 'trades';
    setDownloadType: (t: 'candles' | 'trades') => void;
    exchanges: string[];
    dlExchange: string;
    setDlExchange: (e: string) => void;
    dlMarkets: string[];
    dlSymbol: string;
    setDlSymbol: (s: string) => void;
    dlTimeframe: string;
    setDlTimeframe: (t: string) => void;
    dlStartDate: string;
    setDlStartDate: (d: string) => void;
    dlEndDate: string;
    setDlEndDate: (d: string) => void;
    isDownloading: boolean;
    downloadProgress: number;
    isLoadingDlMarkets: boolean;
    handleStartDownload: () => void;
    handleStopDownload: () => void;
}

const TIMEFRAME_OPTIONS = [
    "1m", "3m", "5m", "15m", "30m", "45m",
    "1h", "2h", "3h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M"
];

export const DownloadDataModal: React.FC<DownloadDataModalProps> = ({
    isOpen,
    onClose,
    downloadType,
    setDownloadType,
    exchanges,
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
}) => {

    // --- Helper Function ---
    const range = (start: number, end: number, step = 1) => {
        const result = [];
        for (let i = start; i <= end; i += step) {
            result.push(i);
        }
        return result;
    };

    const inputBaseClasses = "w-full bg-white dark:bg-slate-900 border border-gray-300 dark:border-gray-700 rounded-md p-2 text-slate-900 dark:text-white focus:ring-brand-primary focus:border-brand-primary";

    // --- Custom Header Component ---
    const CustomInputHeader = ({
        date,
        changeYear,
        changeMonth,
        decreaseMonth,
        increaseMonth,
        prevMonthButtonDisabled,
        nextMonthButtonDisabled,
    }: any) => {
        const years = range(2010, getYear(new Date()) + 1, 1); // 2010 থেকে বর্তমান সাল পর্যন্ত
        const months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ];

        return (
            <div className="m-2 flex items-center justify-between px-2 py-2 bg-white dark:bg-slate-800 rounded-lg border-b border-gray-200 dark:border-gray-700">
                <button
                    onClick={decreaseMonth}
                    disabled={prevMonthButtonDisabled}
                    className="p-1 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-full text-slate-600 dark:text-slate-300 transition-colors disabled:opacity-50"
                    type="button"
                >
                    <ChevronLeft size={18} />
                </button>

                <div className="flex gap-2">
                    <select
                        value={months[getMonth(date)]}
                        onChange={({ target: { value } }) => changeMonth(months.indexOf(value))}
                        className="bg-transparent text-sm font-bold text-slate-800 dark:text-white cursor-pointer focus:outline-none hover:text-brand-primary transition-colors appearance-none text-center"
                    >
                        {months.map((option) => (
                            <option key={option} value={option} className="bg-white dark:bg-slate-800 text-slate-900 dark:text-white">
                                {option}
                            </option>
                        ))}
                    </select>

                    <select
                        value={getYear(date)}
                        onChange={({ target: { value } }) => changeYear(Number(value))}
                        className="bg-transparent text-sm font-bold text-slate-800 dark:text-white cursor-pointer focus:outline-none hover:text-brand-primary transition-colors appearance-none text-center"
                    >
                        {years.map((option) => (
                            <option key={option} value={option} className="bg-white dark:bg-slate-800 text-slate-900 dark:text-white">
                                {option}
                            </option>
                        ))}
                    </select>
                </div>

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

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
            <div className="bg-white dark:bg-[#1e222d] rounded-2xl shadow-2xl w-full max-w-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                {/* Header */}
                <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-6 relative">
                    <button onClick={onClose} className="absolute top-4 right-4 text-white/80 hover:text-white transition-colors">
                        <X size={24} />
                    </button>
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        <Download className="text-blue-200" /> Download Market Data
                    </h3>
                    <p className="text-blue-100 text-sm mt-1">Fetch historical data from exchanges to local storage.</p>
                </div>

                {/* Body */}
                <div className="p-6 space-y-6">
                    {/* Tabs */}
                    <div className="flex bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
                        <button
                            onClick={() => setDownloadType('candles')}
                            className={`flex-1 py-2 rounded-md text-sm font-semibold transition-all ${downloadType === 'candles' ? 'bg-white dark:bg-blue-600 text-blue-600 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700'}`}
                        >
                            Candles (OHLCV)
                        </button>
                        <button
                            onClick={() => setDownloadType('trades')}
                            className={`flex-1 py-2 rounded-md text-sm font-semibold transition-all ${downloadType === 'trades' ? 'bg-white dark:bg-blue-600 text-blue-600 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700'}`}
                        >
                            Trades (Tick Data)
                        </button>
                    </div>

                    {/* Form Grid */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2 md:col-span-1">
                            <label className="block text-xs font-medium text-gray-500 mb-1">Exchange</label>
                            <select
                                className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                                value={dlExchange}
                                onChange={(e) => setDlExchange(e.target.value)}
                            >
                                {exchanges.map(ex => <option key={ex} value={ex}>{ex.toUpperCase()}</option>)}
                            </select>
                        </div>
                        <div className="col-span-2 md:col-span-1">
                            <label className="block text-xs font-medium text-gray-500 mb-1">
                                {isLoadingDlMarkets ? "Loading Markets..." : "Market Pair"}
                            </label>
                            <SearchableSelect options={dlMarkets} value={dlSymbol} onChange={setDlSymbol} />
                        </div>

                        {downloadType === 'candles' && (
                            <div className="col-span-2">
                                <label className="block text-xs font-medium text-gray-500 mb-1">Timeframe</label>
                                <div className="flex flex-wrap gap-2">
                                    {['1m', '5m', '15m', '1h', '4h', '1d'].map(tf => (
                                        <button
                                            key={tf}
                                            onClick={() => setDlTimeframe(tf)}
                                            className={`px-3 py-1.5 rounded text-xs font-medium border ${dlTimeframe === tf ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700 text-blue-700 dark:text-blue-300' : 'border-gray-200 dark:border-gray-700 text-gray-500 hover:bg-gray-50'}`}
                                        >
                                            {tf}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Date Selection Grid */}
                        <div className="col-span-2 grid grid-cols-2 gap-4 mb-4">
                            {/* Start Date */}
                            <div className="relative group">
                                <label className="text-xs font-semibold text-gray-500 mb-1.5 block ml-1">Start Date</label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none z-10">
                                        <Calendar size={14} className="text-gray-400 group-focus-within:text-brand-primary transition-colors" />
                                    </div>
                                    <DatePicker
                                        selected={dlStartDate ? new Date(dlStartDate) : null}
                                        onChange={(date: Date) => setDlStartDate(date?.toISOString().split('T')[0] || '')}
                                        className={`${inputBaseClasses} pl-9 font-medium transition-all hover:border-brand-primary/50 cursor-pointer`}
                                        dateFormat="yyyy-MM-dd"
                                        placeholderText="Select start"
                                        renderCustomHeader={CustomInputHeader} // আমাদের কাস্টম হেডার
                                        calendarClassName="!bg-white dark:!bg-slate-900 !border-gray-200 dark:!border-gray-700 !font-sans !text-slate-900 dark:!text-slate-100 shadow-xl rounded-xl overflow-hidden"
                                        dayClassName={() => "dark:text-slate-200 hover:!bg-brand-primary hover:!text-white rounded-full"}
                                        popperClassName="!z-50"
                                    />
                                </div>
                            </div>

                            {/* End Date */}
                            <div className="relative group">
                                <label className="text-xs font-semibold text-gray-500 mb-1.5 block ml-1">End Date</label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none z-10">
                                        <Clock size={14} className="text-gray-400 group-focus-within:text-brand-primary transition-colors" />
                                    </div>
                                    <DatePicker
                                        selected={dlEndDate ? new Date(dlEndDate) : null}
                                        onChange={(date: Date) => setDlEndDate(date?.toISOString().split('T')[0] || '')}
                                        className={`${inputBaseClasses} pl-9 font-medium transition-all hover:border-brand-primary/50 cursor-pointer`}
                                        dateFormat="yyyy-MM-dd"
                                        placeholderText="Select end"
                                        renderCustomHeader={CustomInputHeader} // আমাদের কাস্টম হেডার
                                        calendarClassName="!bg-white dark:!bg-slate-900 !border-gray-200 dark:!border-gray-700 !font-sans !text-slate-900 dark:!text-slate-100 shadow-xl rounded-xl overflow-hidden"
                                        dayClassName={() => "dark:text-slate-200 hover:!bg-brand-primary hover:!text-white rounded-full"}
                                        popperClassName="!z-50"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    {isDownloading && (
                        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 animate-pulse">
                            <div className="flex justify-between text-xs font-bold text-blue-600 mb-2">
                                <span>Downloading...</span>
                                <span>{downloadProgress}%</span>
                            </div>
                            <div className="h-2 bg-blue-200 dark:bg-blue-800 rounded-full overflow-hidden">
                                <div className="h-full bg-blue-600 transition-all duration-300" style={{ width: `${downloadProgress}%` }}></div>
                            </div>
                        </div>
                    )}

                    {downloadType === 'trades' && (
                        <div className="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-200 rounded-lg text-xs">
                            <AlertCircle size={16} className="mt-0.5 shrink-0" />
                            <p>Trade data is massive. Downloading large ranges may take a while and consume significant validation time.</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
                    <Button variant="outline" onClick={onClose} disabled={isDownloading}>Cancel</Button>
                    {isDownloading ? (
                        <Button variant="secondary" onClick={handleStopDownload} className="text-red-500 border-red-500 hover:bg-red-50">Stop Download</Button>
                    ) : (
                        <Button onClick={handleStartDownload} className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/30">
                            Start Download
                        </Button>
                    )}
                </div>
            </div>
        </div>
    );
};
