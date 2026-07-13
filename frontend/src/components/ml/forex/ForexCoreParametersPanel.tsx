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
export interface ForexCoreParametersProps {
    symbol: string;
    setSymbol: (v: string) => void;
    broker: string;
    setBroker: (v: string) => void;
    instruments: any[];
    isTraining: boolean;
    isDeleting: boolean;
    handleDeleteDataset: () => void;
    
    // Timeframe & Rows
    timeframe: string;
    setTimeframe: (v: string) => void;
    targetRows: number;
    setTargetRows: (v: number) => void;
    
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
}

const TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d'];

const ForexSymbolSelector = ({ symbol, setSymbol, broker, setBroker, instruments }: any) => (
    <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
            <select value={broker} onChange={(e) => setBroker(e.target.value)} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-teal-500/50 outline-none">
                <option value="oanda" className="bg-gray-900 text-white">OANDA</option>
                <option value="fxcm" className="bg-gray-900 text-white">FXCM</option>
                <option value="mt5" className="bg-gray-900 text-white">MetaTrader 5</option>
            </select>
            <select value={symbol} onChange={(e) => setSymbol(e.target.value)} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-teal-500/50 outline-none flex-1">
                {instruments.length === 0 && <option value="EUR_USD" className="bg-gray-900 text-white">Loading...</option>}
                {instruments.map((inst: any) => (
                    <option key={inst.name} value={inst.name} className="bg-gray-900 text-white">{inst.display_name}</option>
                ))}
            </select>
        </div>
    </div>
);

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
                
                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Target Historical Ticks</label>
                    <input 
                        type="number" 
                        value={props.targetRows} 
                        onChange={e => props.setTargetRows(parseInt(e.target.value))}
                        disabled={props.isTraining}
                        className="w-full bg-white/5 backdrop-blur-md border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-teal-500/50 outline-none mb-4 shadow-inner"
                    />
                    
                    <button 
                        onClick={props.handleDeleteDataset}
                        disabled={props.isDeleting || props.isTraining}
                        className="w-full py-2 bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 text-red-400 rounded-xl text-xs font-bold uppercase transition-all flex items-center justify-center gap-2"
                    >
                        {props.isDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                        Clear Local Dataset
                    </button>
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
