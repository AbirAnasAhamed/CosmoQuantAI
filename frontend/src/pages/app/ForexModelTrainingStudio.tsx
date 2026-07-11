import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, Play, Settings, Activity, Layers, Target, Cpu, CheckCircle2, XCircle, Loader2, Globe } from 'lucide-react';
import { forexMlTrainingService, ForexTrainingJob } from '@/services/forexMlTrainingService';
import { ForexDataEngine } from '@/components/features/market/ForexDataEngine';

const ForexSymbolSelector = ({ symbol, setSymbol, broker, setBroker, instruments }: any) => (
    <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
            <select value={broker} onChange={(e) => setBroker(e.target.value)} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-teal-500/50 outline-none">
                <option value="oanda">OANDA</option>
                <option value="fxcm">FXCM</option>
                <option value="mt5">MetaTrader 5</option>
            </select>
            <select value={symbol} onChange={(e) => setSymbol(e.target.value)} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-teal-500/50 outline-none flex-1">
                {instruments.length === 0 && <option value="EUR_USD">Loading...</option>}
                {instruments.map((inst: any) => (
                    <option key={inst.name} value={inst.name}>{inst.display_name}</option>
                ))}
            </select>
        </div>
    </div>
);

const ForexModelTrainingStudio: React.FC = () => {
    // Core Parameters
    const [symbol, setSymbol] = useState('EUR/USD');
    const [broker, setBroker] = useState('oanda');
    const [timeframe, setTimeframe] = useState('1h');
    const [algorithm, setAlgorithm] = useState('Random Forest');
    const [epochs, setEpochs] = useState(50);
    const [targetRows, setTargetRows] = useState(100000);

    // Forex Specific Engine Features
    const [macroCalendar, setMacroCalendar] = useState(true);
    const [sessionFeatures, setSessionFeatures] = useState(true);
    const [ignoreWeekend, setIgnoreWeekend] = useState(true);
    const [tickVolume, setTickVolume] = useState(false);
    const [cotData, setCotData] = useState(false);
    const [currencyCorrelation, setCurrencyCorrelation] = useState(false);
    const [yieldDifferentials, setYieldDifferentials] = useState(false);
    
    const [instruments, setInstruments] = useState<{name: string, display_name: string}[]>([]);
    
    // Status
    const [isTraining, setIsTraining] = useState(false);
    const [activeJob, setActiveJob] = useState<ForexTrainingJob | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);

    const TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d'];
    const ALGORITHMS = ['Random Forest', 'XGBoost', 'LightGBM', 'LSTM', 'Transformer'];

    React.useEffect(() => {
        const loadInstruments = async () => {
            try {
                const data = await forexMlTrainingService.getInstruments();
                setInstruments(data);
                if (data.length > 0) setSymbol(data[0].name);
            } catch (err) {
                console.error("Failed to load instruments", err);
            }
        };
        loadInstruments();
    }, []);

    const handleDeleteDataset = async () => {
        if (!confirm(`Are you sure you want to delete the local dataset for ${symbol}?`)) return;
        setIsDeleting(true);
        try {
            const res = await forexMlTrainingService.deleteDataset(symbol);
            alert(res.message || "Dataset deleted successfully.");
        } catch (error: any) {
            console.error("Failed to delete dataset", error);
            alert(error?.response?.data?.detail || "Failed to delete dataset.");
        } finally {
            setIsDeleting(false);
        }
    };

    const handleStartTraining = async () => {
        setIsTraining(true);
        try {
            const job = await forexMlTrainingService.startTraining({
                symbol,
                timeframe,
                algorithm,
                config: {
                    epochs,
                    broker,
                    market_session_features: sessionFeatures,
                    ignore_weekend_gaps: ignoreWeekend,
                    macroeconomic_calendar: macroCalendar,
                    tick_volume_profiler: tickVolume,
                    cot_data: cotData,
                    currency_correlation: currencyCorrelation,
                    yield_differentials: yieldDifferentials,
                    target_rows: targetRows
                }
            });
            setActiveJob(job);
            alert("Training job started successfully!");
        } catch (error) {
            console.error("Failed to start training", error);
            alert("Failed to start Forex training job.");
        } finally {
            setIsTraining(false); // Remove this if we want to stay in 'training' UI state polling
        }
    };

    return (
        <div className="h-full flex flex-col space-y-3 relative overflow-hidden bg-black/20 rounded-3xl">
            {/* Background Orbs adapted for Forex (Teal/Blue vibe) */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-teal-600/20 blur-[120px] rounded-full pointer-events-none"></div>
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/20 blur-[120px] rounded-full pointer-events-none"></div>

            <header className="flex items-center gap-4 z-10 px-6 pt-6">
                <h2 className="text-xl font-black text-white flex items-center gap-2">
                    <Globe className="w-5 h-5 text-teal-400" />
                    Forex ML Intelligence Studio
                </h2>
                <div className="w-px h-4 bg-white/20"></div>
                <div className="text-slate-400 text-xs font-medium tracking-wide flex items-center gap-2">
                    Decentralized Market Modeling with Macro-Economic Pipelines
                </div>
            </header>

            <div className="flex-1 flex flex-col min-h-0 relative z-10 px-6 pb-6">
                <div className="w-full flex flex-col bg-black/40 backdrop-blur-2xl border border-white/10 rounded-3xl p-6 shadow-[0_8px_32px_rgba(0,0,0,0.5)] relative overflow-hidden h-full">
                    <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 flex-1 min-h-0">
                        
                        {/* COLUMN 1: Core Parameters */}
                        <div className="flex flex-col h-full bg-white/5 border border-teal-500/30 rounded-2xl shadow-[0_0_12px_rgba(20,184,166,0.1)] overflow-hidden">
                            <div className="p-5 bg-black/40 border-b border-white/10 flex-shrink-0 relative z-20">
                                <h3 className="text-sm font-bold text-teal-400 flex items-center gap-2 uppercase tracking-widest"><Settings className="w-4 h-4" /> Asset & Horizon</h3>
                            </div>
                            <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar h-full">
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">Broker & Currency Pair</label>
                                    <ForexSymbolSelector symbol={symbol} setSymbol={setSymbol} broker={broker} setBroker={setBroker} instruments={instruments} />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-1">Timeframe (Resolution)</label>
                                    <div className="grid grid-cols-3 gap-2">
                                        {TIMEFRAMES.map(tf => (
                                            <button
                                                key={tf}
                                                disabled={isTraining}
                                                onClick={() => setTimeframe(tf)}
                                                className={`py-2 rounded-xl text-sm font-bold transition-all duration-300 ${timeframe === tf ? 'bg-teal-500/20 text-teal-400 border border-teal-400/50 shadow-[0_0_15px_rgba(20,184,166,0.3)]' : 'bg-white/5 text-slate-400 hover:bg-white/10 border border-white/5 hover:text-white'}`}
                                            >
                                                {tf}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-1">Target Historical Ticks</label>
                                    <input 
                                        type="number" 
                                        value={targetRows} 
                                        onChange={e => setTargetRows(parseInt(e.target.value))}
                                        className="w-full bg-white/5 backdrop-blur-md border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-teal-500/50 outline-none mb-4"
                                    />
                                    
                                    <button 
                                        onClick={handleDeleteDataset}
                                        disabled={isDeleting}
                                        className="w-full py-2 bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 text-red-400 rounded-xl text-xs font-bold uppercase transition-all flex items-center justify-center gap-2"
                                    >
                                        {isDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                                        Clear Local Dataset
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* COLUMN 2: Forex Data Engine */}
                        <div className="flex flex-col h-full bg-white/5 border border-teal-500/30 rounded-2xl shadow-[0_0_12px_rgba(20,184,166,0.1)] overflow-hidden">
                            <div className="p-5 bg-black/40 border-b border-white/10 flex-shrink-0 relative z-20">
                                <h3 className="text-sm font-bold text-teal-400 flex items-center gap-2 uppercase tracking-widest"><Activity className="w-4 h-4" /> TradFi Data Pipeline</h3>
                            </div>
                            <div className="p-6 overflow-y-auto custom-scrollbar h-full">
                                <ForexDataEngine 
                                    macroCalendar={macroCalendar} setMacroCalendar={setMacroCalendar}
                                    sessionFeatures={sessionFeatures} setSessionFeatures={setSessionFeatures}
                                    ignoreWeekend={ignoreWeekend} setIgnoreWeekend={setIgnoreWeekend}
                                    tickVolume={tickVolume} setTickVolume={setTickVolume}
                                    cotData={cotData} setCotData={setCotData}
                                    currencyCorrelation={currencyCorrelation} setCurrencyCorrelation={setCurrencyCorrelation}
                                    yieldDifferentials={yieldDifferentials} setYieldDifferentials={setYieldDifferentials}
                                    disabled={isTraining}
                                />
                            </div>
                        </div>

                        {/* COLUMN 3: Neural Architecture */}
                        <div className="flex flex-col h-full bg-white/5 border border-teal-500/30 rounded-2xl shadow-[0_0_12px_rgba(20,184,166,0.1)] overflow-hidden">
                            <div className="p-5 bg-black/40 border-b border-white/10 flex-shrink-0 relative z-20">
                                <h3 className="text-sm font-bold text-blue-400 flex items-center gap-2 uppercase tracking-widest"><Cpu className="w-4 h-4" /> Neural Architecture</h3>
                            </div>
                            <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar h-full flex flex-col justify-between">
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-300 mb-2">Algorithm Selection</label>
                                        <div className="space-y-2">
                                            {ALGORITHMS.map(algo => (
                                                <div 
                                                    key={algo} 
                                                    onClick={() => !isTraining && setAlgorithm(algo)}
                                                    className={`p-3 rounded-xl border cursor-pointer transition-all duration-300 ${algorithm === algo ? 'border-blue-400 bg-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.2)] text-white' : 'border-white/10 bg-white/5 text-slate-400 hover:bg-white/10'}`}
                                                >
                                                    <span className="text-sm font-semibold">{algo}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-300 mb-1">Epochs / Trees</label>
                                        <input 
                                            type="number" 
                                            value={epochs} 
                                            onChange={e => setEpochs(parseInt(e.target.value))}
                                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-blue-500/50 outline-none"
                                        />
                                    </div>
                                </div>
                                
                                <div className="pt-4 border-t border-white/10">
                                    <button
                                        onClick={handleStartTraining}
                                        disabled={isTraining}
                                        className="w-full py-4 rounded-xl font-black uppercase tracking-widest transition-all duration-300 flex items-center justify-center gap-2 bg-gradient-to-r from-teal-500 to-blue-600 hover:from-teal-400 hover:to-blue-500 text-white shadow-[0_0_30px_rgba(20,184,166,0.3)] disabled:opacity-50"
                                    >
                                        {isTraining ? (
                                            <><Loader2 className="w-5 h-5 animate-spin" /> Initializing...</>
                                        ) : (
                                            <><Play className="w-5 h-5 fill-current" /> Compile & Train Model</>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            </div>
        </div>
    );
};

export default ForexModelTrainingStudio;
