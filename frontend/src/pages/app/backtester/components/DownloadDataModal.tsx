import React from 'react';
import { X, Download, AlertCircle } from 'lucide-react';
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

                        <div className="col-span-2 md:col-span-1">
                            <label className="block text-xs font-medium text-gray-500 mb-1">Start Date</label>
                            <DatePicker
                                selected={dlStartDate ? new Date(dlStartDate) : null}
                                onChange={(date: Date) => setDlStartDate(date?.toISOString().split('T')[0] || '')}
                                className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500 text-slate-900 dark:text-white"
                                dateFormat="yyyy-MM-dd"
                            />
                        </div>
                        <div className="col-span-2 md:col-span-1">
                            <label className="block text-xs font-medium text-gray-500 mb-1">End Date (Optional)</label>
                            <DatePicker
                                selected={dlEndDate ? new Date(dlEndDate) : null}
                                onChange={(date: Date) => setDlEndDate(date?.toISOString().split('T')[0] || '')}
                                className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500 text-slate-900 dark:text-white"
                                dateFormat="yyyy-MM-dd"
                                placeholderText="Till Now"
                            />
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
