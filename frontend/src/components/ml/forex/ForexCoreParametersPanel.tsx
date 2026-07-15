import React from 'react';
import { Settings, Activity, Loader2, XCircle } from 'lucide-react';
import TargetSelection from '@/components/ml/TargetSelection';
import ForecastConfigurator from '@/components/ml/ForecastConfigurator';
import EvaluationMetricSelector from '@/components/ml/EvaluationMetricSelector';
import FractionalDiffConfig from '@/components/ml/FractionalDiffConfig';
import DataAugmentationConfig from '@/components/ml/DataAugmentationConfig';
import ClusterImportanceToggle from '@/components/ml/ClusterImportanceToggle';
import AdversarialTrainingConfig from '@/components/ml/AdversarialTrainingConfig';
import DatasetSplitConfig from '@/components/ml/DatasetSplitConfig';
import { TripleBarrierToggle } from './TripleBarrierToggle';
import { MetaLabelingToggle } from './MetaLabelingToggle';
import { FeatureSelectionDropdown } from './FeatureSelectionDropdown';
import LiveMarketPulse from '@/components/ml/LiveMarketPulse';
import { ForexScraperPanel } from './ForexScraperPanel';
import { Trash2 } from 'lucide-react';

export interface ForexCoreParametersProps {
    symbol: string;
    setSymbol: (v: string) => void;
    broker: string;
    setBroker: (v: string) => void;
    instruments: any[];
    isTraining: boolean;
    isDeleting: boolean;
    handleDeleteDataset: () => void;
    
    // Timeframe & Rows & Dates
    timeframe: string;
    setTimeframe: (v: string) => void;
    targetRows: number;
    setTargetRows: (v: number) => void;
    dateRangeMode: 'ticks' | 'date';
    setDateRangeMode: (v: 'ticks' | 'date') => void;
    startDate: string;
    setStartDate: (v: string) => void;
    endDate: string;
    setEndDate: (v: string) => void;
    
    // Core Parameters
    modelName: string;
    setModelName: (v: string) => void;
    predictionTarget: string;
    setPredictionTarget: (v: string) => void;
    forecastHorizon: number;
    setForecastHorizon: (v: number) => void;
    lookbackWindow: number;
    setLookbackWindow: (v: number) => void;
    evalMetric: string;
    setEvalMetric: (v: string) => void;

    // Preprocessing
    outlierRemoval: string;
    setOutlierRemoval: (v: string) => void;
    scalingMethod: string;
    setScalingMethod: (v: string) => void;

    // Advanced Preprocessing
    fractionalDiff: boolean;
    setFractionalDiff: (v: boolean) => void;
    fractionalDValue: number;
    setFractionalDValue: (v: number) => void;
    augmentationStrategy: string;
    setAugmentationStrategy: (v: string) => void;
    augmentationFactor: number;
    setAugmentationFactor: (v: number) => void;
    useClusteredImportance: boolean;
    setUseClusteredImportance: (v: boolean) => void;
    enableAdversarial: boolean;
    setEnableAdversarial: (v: boolean) => void;
    adversarialEpsilon: number;
    setAdversarialEpsilon: (v: number) => void;
    enableMetaLabeling: boolean;
    setEnableMetaLabeling: (v: boolean) => void;
    featureSelectionMethod: string;
    setFeatureSelectionMethod: (v: string) => void;

    // Dataset Split
    splitMethod: string;
    setSplitMethod: (v: string) => void;
    trainRatio: number;
    setTrainRatio: (v: number) => void;
    valRatio: number;
    setValRatio: (v: number) => void;
    testRatio: number;
    setTestRatio: (v: number) => void;
    imbalanceStrategy: string;
    setImbalanceStrategy: (v: string) => void;
    purgeLength: number;
    setPurgeLength: (v: number) => void;
    wfoWindows: number;
    setWfoWindows: (v: number) => void;
    
    // Triple Barrier
    useTripleBarrier: boolean;
    setUseTripleBarrier: (v: boolean) => void;
    ptSlRatio: number;
    setPtSlRatio: (v: number) => void;
    barrierTimeout: number;
    setBarrierTimeout: (v: number) => void;
    
    // Scraper Props
    forexSnapshotFiles: string[];
    selectedForexFile: string;
    setSelectedForexFile: (v: string) => void;
    handleDeleteSnapshot: (e: React.MouseEvent) => void;
    forexScrapeJob: any;
    onStartCollector: (config: any) => void;
    onCancelCollector: () => void;
}

const TIMEFRAMES = ['5s', '10s', '30s', '1m', '5m', '15m', '30m', '1h', '4h', '1d'];

const ForexSymbolSelector = ({ symbol, setSymbol, broker, setBroker, instruments }: any) => {
    const [isOpen, setIsOpen] = React.useState(false);
    const [searchQuery, setSearchQuery] = React.useState('');

    const filteredInstruments = instruments.filter((inst: any) => 
        inst.display_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
        inst.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const selectedInst = instruments.find((i: any) => i.name === symbol);
    
    return (
        <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
                <select value={broker} onChange={(e) => setBroker(e.target.value)} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-teal-500/50 outline-none w-[140px]">
                    <option value="oanda" className="bg-gray-900 text-white">OANDA</option>
                    <option value="fxcm" className="bg-gray-900 text-white">FXCM</option>
                    <option value="mt5" className="bg-gray-900 text-white">MetaTrader 5</option>
                </select>
                
                <div className="relative flex-1">
                    <div 
                        onClick={() => setIsOpen(!isOpen)}
                        className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white cursor-pointer hover:bg-white/10 transition-colors flex items-center justify-between"
                    >
                        <span>{instruments.length === 0 ? "Loading..." : (selectedInst?.display_name || symbol)}</span>
                        <svg className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                    </div>
                    
                    {isOpen && (
                        <>
                            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)}></div>
                            <div className="absolute top-full left-0 right-0 mt-2 bg-[#0a0f16] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col max-h-[300px]">
                                <div className="p-2 border-b border-white/10">
                                    <input 
                                        type="text"
                                        placeholder="Search pair..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-teal-500/50"
                                        autoFocus
                                    />
                                </div>
                                <div className="overflow-y-auto custom-scrollbar p-1">
                                    {filteredInstruments.length === 0 ? (
                                        <div className="p-3 text-xs text-slate-400 text-center">No pairs found</div>
                                    ) : (
                                        filteredInstruments.map((inst: any) => (
                                            <div 
                                                key={inst.name}
                                                onClick={() => {
                                                    setSymbol(inst.name);
                                                    setIsOpen(false);
                                                    setSearchQuery('');
                                                }}
                                                className={`px-3 py-2 text-sm rounded-lg cursor-pointer transition-colors ${symbol === inst.name ? 'bg-teal-500/20 text-teal-400' : 'text-slate-300 hover:bg-white/10 hover:text-white'}`}
                                            >
                                                {inst.display_name}
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export const ForexCoreParametersPanel: React.FC<ForexCoreParametersProps> = (props) => {
    return (
        <div className="flex flex-col h-full bg-white/5 border border-teal-500/30 rounded-2xl shadow-[0_0_12px_rgba(20,184,166,0.1)] overflow-hidden">
            <div className="p-5 bg-black/40 border-b border-white/10 flex-shrink-0 relative z-20">
                <h3 className="text-sm font-bold text-teal-400 flex items-center gap-2 uppercase tracking-widest">
                    <Settings className="w-4 h-4" /> Core Parameters
                </h3>
            </div>
            <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar h-full">
                
                {/* Upper Half: Asset, Model Name, Targets */}
                <div className="flex flex-col gap-4">
                    <LiveMarketPulse symbol={props.symbol} exchange={props.broker} />
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Broker & Currency Pair</label>
                        <ForexSymbolSelector 
                            symbol={props.symbol} 
                            setSymbol={props.setSymbol} 
                            broker={props.broker} 
                            setBroker={props.setBroker} 
                            instruments={props.instruments} 
                        />
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Custom Model Name (Optional)</label>
                    <input 
                        type="text" 
                        value={props.modelName} 
                        onChange={e => props.setModelName(e.target.value)}
                        disabled={props.isTraining}
                        className="w-full bg-white/5 backdrop-blur-md border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-teal-500/50 outline-none transition-all disabled:opacity-50 placeholder-white/30 shadow-inner"
                        placeholder="e.g., EURUSD_Scalper_V1"
                    />
                </div>

                <TargetSelection 
                    predictionTarget={props.predictionTarget}
                    setPredictionTarget={props.setPredictionTarget}
                    isTraining={props.isTraining}
                />

                <TripleBarrierToggle 
                    useTripleBarrier={props.useTripleBarrier}
                    setUseTripleBarrier={props.setUseTripleBarrier}
                    ptSlRatio={props.ptSlRatio}
                    setPtSlRatio={props.setPtSlRatio}
                    barrierTimeout={props.barrierTimeout}
                    setBarrierTimeout={props.setBarrierTimeout}
                    isTraining={props.isTraining}
                />

                <ForecastConfigurator
                    forecastHorizon={props.forecastHorizon}
                    setForecastHorizon={props.setForecastHorizon}
                    lookbackWindow={props.lookbackWindow}
                    setLookbackWindow={props.setLookbackWindow}
                />

                <EvaluationMetricSelector
                    predictionTarget={props.predictionTarget}
                    evalMetric={props.evalMetric}
                    setEvalMetric={props.setEvalMetric}
                />

                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Timeframe (Resolution)</label>
                    <div className="grid grid-cols-3 gap-2">
                        {TIMEFRAMES.map(tf => (
                            <button
                                key={tf}
                                disabled={props.isTraining}
                                onClick={() => props.setTimeframe(tf)}
                                className={`py-2 rounded-xl text-sm font-bold transition-all duration-300 ${props.timeframe === tf ? 'bg-teal-500/20 text-teal-400 border border-teal-400/50 shadow-[0_0_15px_rgba(20,184,166,0.3)]' : 'bg-white/5 text-slate-400 hover:bg-white/10 border border-white/5 hover:text-white'}`}
                            >
                                {tf}
                            </button>
                        ))}
                    </div>
                </div>
                
                <div className="pt-2 border-t border-white/10 mt-4">
                    <div className="mb-4">
                        <label className="block text-sm font-bold text-slate-300 mb-2">Select Dataset Snapshot (Parquet)</label>
                        <div className="flex items-center gap-2">
                            <select 
                                value={props.selectedForexFile} 
                                onChange={e => props.setSelectedForexFile(e.target.value)}
                                disabled={props.isTraining}
                                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-teal-500/50 outline-none"
                            >
                                {props.forexSnapshotFiles.length === 0 && <option value="" className="text-slate-500">No snapshots available. Please collect data first.</option>}
                                {props.forexSnapshotFiles.map(f => (
                                    <option key={f} value={f} className="bg-gray-900 text-white">{f}</option>
                                ))}
                            </select>
                            {props.selectedForexFile && (
                                <button
                                    onClick={props.handleDeleteSnapshot}
                                    disabled={props.isTraining}
                                    className="p-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-xl border border-red-500/20 transition-all flex items-center justify-center"
                                    title="Delete selected snapshot"
                                >
                                    <Trash2 className="w-5 h-5" />
                                </button>
                            )}
                        </div>
                    </div>

                    <ForexScraperPanel 
                        symbol={props.symbol}
                        isTraining={props.isTraining}
                        forexScrapeJob={props.forexScrapeJob}
                        onStartCollector={props.onStartCollector}
                        onCancelCollector={props.onCancelCollector}
                        timeframe={props.timeframe}
                    />
                </div>

                {/* Lower Half: Advanced Preprocessing UI */}
                <div className="mt-6 pt-6 border-t border-white/10">
                    <h4 className="text-xs font-bold text-teal-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <Activity className="w-4 h-4" /> Data Preprocessing
                    </h4>
                    
                    <div className="space-y-4">
                        {/* Note: Missing Data Handling is excluded intentionally for Forex */}

                        <div>
                            <label className="block text-[11px] font-bold text-slate-400 mb-1.5 uppercase">Outlier Filtering</label>
                            <div className="grid grid-cols-3 gap-2">
                                {[
                                    { id: 'none', label: 'None' },
                                    { id: 'zscore', label: 'Z-Score (>3σ)' },
                                    { id: 'iqr', label: 'IQR Clipping' }
                                ].map(opt => (
                                    <button
                                        key={opt.id}
                                        disabled={props.isTraining}
                                        onClick={() => props.setOutlierRemoval(opt.id)}
                                        className={`py-1.5 rounded-lg text-xs font-bold transition-all ${props.outlierRemoval === opt.id ? 'bg-teal-500/20 text-teal-300 border border-teal-500/50 shadow-[0_0_10px_rgba(20,184,166,0.2)]' : 'bg-white/5 text-slate-400 border border-white/5 hover:bg-white/10'}`}
                                    >
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <label className="block text-[11px] font-bold text-slate-400 mb-1.5 uppercase">Feature Scaling</label>
                            <div className="grid grid-cols-4 gap-2">
                                {[
                                    { id: 'none', label: 'None' },
                                    { id: 'standard', label: 'Standard' },
                                    { id: 'minmax', label: 'MinMax' },
                                    { id: 'robust', label: 'Robust' }
                                ].map(opt => (
                                    <button
                                        key={opt.id}
                                        disabled={props.isTraining}
                                        onClick={() => props.setScalingMethod(opt.id)}
                                        className={`py-1.5 rounded-lg text-xs font-bold transition-all ${props.scalingMethod === opt.id ? 'bg-teal-500/20 text-teal-300 border border-teal-500/50 shadow-[0_0_10px_rgba(20,184,166,0.2)]' : 'bg-white/5 text-slate-400 border border-white/5 hover:bg-white/10'}`}
                                    >
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                        
                        <FeatureSelectionDropdown 
                            featureSelectionMethod={props.featureSelectionMethod}
                            setFeatureSelectionMethod={props.setFeatureSelectionMethod}
                            isTraining={props.isTraining}
                        />
                        
                        <FractionalDiffConfig 
                            fractionalDiff={props.fractionalDiff}
                            setFractionalDiff={props.setFractionalDiff}
                            fractionalDValue={props.fractionalDValue}
                            setFractionalDValue={props.setFractionalDValue}
                        />
                        
                        <DataAugmentationConfig
                            augmentationStrategy={props.augmentationStrategy}
                            setAugmentationStrategy={props.setAugmentationStrategy}
                            augmentationFactor={props.augmentationFactor}
                            setAugmentationFactor={props.setAugmentationFactor}
                        />
                        
                        <ClusterImportanceToggle 
                            useClusteredImportance={props.useClusteredImportance}
                            setUseClusteredImportance={props.setUseClusteredImportance}
                        />
                        
                        <AdversarialTrainingConfig 
                            enableAdversarial={props.enableAdversarial}
                            setEnableAdversarial={props.setEnableAdversarial}
                            adversarialEpsilon={props.adversarialEpsilon}
                            setAdversarialEpsilon={props.setAdversarialEpsilon}
                        />

                        <MetaLabelingToggle 
                            enableMetaLabeling={props.enableMetaLabeling}
                            setEnableMetaLabeling={props.setEnableMetaLabeling}
                            isTraining={props.isTraining}
                        />
                    </div>
                </div>

                {/* Dataset Split Configuration */}
                <div className="mt-6 pt-6 border-t border-white/10">
                    <DatasetSplitConfig
                        splitMethod={props.splitMethod}
                        setSplitMethod={props.setSplitMethod}
                        trainRatio={props.trainRatio}
                        setTrainRatio={props.setTrainRatio}
                        valRatio={props.valRatio}
                        setValRatio={props.setValRatio}
                        testRatio={props.testRatio}
                        setTestRatio={props.setTestRatio}
                        imbalanceStrategy={props.imbalanceStrategy}
                        setImbalanceStrategy={props.setImbalanceStrategy}
                        purgeLength={props.purgeLength}
                        setPurgeLength={props.setPurgeLength}
                        wfoWindows={props.wfoWindows}
                        setWfoWindows={props.setWfoWindows}
                    />
                </div>

            </div>
        </div>
    );
};
