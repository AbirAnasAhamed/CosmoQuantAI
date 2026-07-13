import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, Play, Settings, Activity, Layers, Target, Cpu, CheckCircle2, XCircle, Loader2, Globe } from 'lucide-react';
import { forexMlTrainingService, ForexTrainingJob } from '@/services/forexMlTrainingService';
import { ForexAdvancedPipeline } from '@/components/features/market/ForexAdvancedPipeline';
import { ForexCoreParametersPanel } from '@/components/ml/forex/ForexCoreParametersPanel';
import { AutoMlToggle } from '@/components/ml/forex/AutoMlToggle';

const ForexModelTrainingStudio: React.FC = () => {
    // Core Parameters
    const [symbol, setSymbol] = useState('EUR_USD');
    const [broker, setBroker] = useState('oanda');
    const [timeframe, setTimeframe] = useState('1h');
    const [targetRows, setTargetRows] = useState(100000);
    const [modelName, setModelName] = useState('');
    const [predictionTarget, setPredictionTarget] = useState('classification');
    const [forecastHorizon, setForecastHorizon] = useState(2);
    const [lookbackWindow, setLookbackWindow] = useState(60);
    const [evalMetric, setEvalMetric] = useState('f1');
    const [outlierRemoval, setOutlierRemoval] = useState('none');
    const [scalingMethod, setScalingMethod] = useState('standard');
    const [fractionalDiff, setFractionalDiff] = useState(false);
    const [fractionalDValue, setFractionalDValue] = useState(0.5);
    const [augmentationStrategy, setAugmentationStrategy] = useState('none');
    const [augmentationFactor, setAugmentationFactor] = useState(1);
    const [useClusteredImportance, setUseClusteredImportance] = useState(false);
    const [enableAdversarial, setEnableAdversarial] = useState(false);
    const [adversarialEpsilon, setAdversarialEpsilon] = useState(0.01);
    const [splitMethod, setSplitMethod] = useState('chronological');
    const [trainRatio, setTrainRatio] = useState(70);
    const [valRatio, setValRatio] = useState(15);
    const [testRatio, setTestRatio] = useState(15);
    const [imbalanceStrategy, setImbalanceStrategy] = useState('none');
    const [purgeLength, setPurgeLength] = useState(0);
    
    // Advanced Quant States
    const [useTripleBarrier, setUseTripleBarrier] = useState(false);
    const [ptSlRatio, setPtSlRatio] = useState(1.5);
    const [barrierTimeout, setBarrierTimeout] = useState(24);
    const [useAutoMl, setUseAutoMl] = useState(false);
    const [autoMlTrials, setAutoMlTrials] = useState(50);
    const [enableMetaLabeling, setEnableMetaLabeling] = useState(false);
    const [featureSelectionMethod, setFeatureSelectionMethod] = useState('none');
    const [wfoWindows, setWfoWindows] = useState(5);

    // Forex Specific Engine Features
    // Advanced UI Features (PLP Style)
    const [selectedForexFeatures, setSelectedForexFeatures] = useState<string[]>(['session_features', 'macro_calendar']);
    
    // Neural Architecture
    const [algorithm, setAlgorithm] = useState('Random Forest');
    const [epochs, setEpochs] = useState(50);
    
    const [instruments, setInstruments] = useState<{name: string, display_name: string}[]>([]);
    
    // Status
    const [isTraining, setIsTraining] = useState(false);
    const [activeJob, setActiveJob] = useState<ForexTrainingJob | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);

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
                    model_name: modelName,
                    prediction_target: predictionTarget,
                    forecast_horizon: forecastHorizon,
                    lookback_window: lookbackWindow,
                    eval_metric: evalMetric,
                    outlier_removal: outlierRemoval,
                    scaling_method: scalingMethod,
                    fractional_diff: fractionalDiff,
                    fractional_d_value: fractionalDValue,
                    augmentation_strategy: augmentationStrategy,
                    augmentation_factor: augmentationFactor,
                    use_clustered_importance: useClusteredImportance,
                    enable_adversarial: enableAdversarial,
                    adversarial_epsilon: adversarialEpsilon,
                    split_method: splitMethod,
                    train_ratio: trainRatio,
                    val_ratio: valRatio,
                    test_ratio: testRatio,
                    imbalance_strategy: imbalanceStrategy,
                    purge_length: purgeLength,
                    
                    market_session_features: selectedForexFeatures.includes('session_features'),
                    ignore_weekend_gaps: selectedForexFeatures.includes('weekend_gap'),
                    macroeconomic_calendar: selectedForexFeatures.includes('macro_calendar'),
                    tick_volume_profiler: selectedForexFeatures.includes('tick_volume_profiler'),
                    cot_data: selectedForexFeatures.includes('cot_sentiment'),
                    currency_correlation: selectedForexFeatures.includes('currency_correlation'),
                    yield_differentials: selectedForexFeatures.includes('yield_differentials'),
                    target_rows: targetRows,
                    use_triple_barrier: useTripleBarrier,
                    pt_sl_ratio: ptSlRatio,
                    barrier_timeout: barrierTimeout,
                    use_automl: useAutoMl,
                    automl_trials: autoMlTrials,
                    enable_meta_labeling: enableMetaLabeling,
                    feature_selection_method: featureSelectionMethod,
                    wfo_windows: wfoWindows,
                    selected_forex_features: selectedForexFeatures
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
                        
                        {/* COLUMN 1: Core Parameters (Modularized) */}
                        <ForexCoreParametersPanel
                            symbol={symbol}
                            setSymbol={setSymbol}
                            broker={broker}
                            setBroker={setBroker}
                            instruments={instruments}
                            isTraining={isTraining}
                            isDeleting={isDeleting}
                            handleDeleteDataset={handleDeleteDataset}
                            timeframe={timeframe}
                            setTimeframe={setTimeframe}
                            targetRows={targetRows}
                            setTargetRows={setTargetRows}
                            modelName={modelName}
                            setModelName={setModelName}
                            predictionTarget={predictionTarget}
                            setPredictionTarget={setPredictionTarget}
                            forecastHorizon={forecastHorizon}
                            setForecastHorizon={setForecastHorizon}
                            lookbackWindow={lookbackWindow}
                            setLookbackWindow={setLookbackWindow}
                            evalMetric={evalMetric}
                            setEvalMetric={setEvalMetric}
                            outlierRemoval={outlierRemoval}
                            setOutlierRemoval={setOutlierRemoval}
                            scalingMethod={scalingMethod}
                            setScalingMethod={setScalingMethod}
                            fractionalDiff={fractionalDiff}
                            setFractionalDiff={setFractionalDiff}
                            fractionalDValue={fractionalDValue}
                            setFractionalDValue={setFractionalDValue}
                            augmentationStrategy={augmentationStrategy}
                            setAugmentationStrategy={setAugmentationStrategy}
                            augmentationFactor={augmentationFactor}
                            setAugmentationFactor={setAugmentationFactor}
                            useClusteredImportance={useClusteredImportance}
                            setUseClusteredImportance={setUseClusteredImportance}
                            enableAdversarial={enableAdversarial}
                            setEnableAdversarial={setEnableAdversarial}
                            adversarialEpsilon={adversarialEpsilon}
                            setAdversarialEpsilon={setAdversarialEpsilon}
                            splitMethod={splitMethod}
                            setSplitMethod={setSplitMethod}
                            trainRatio={trainRatio}
                            setTrainRatio={setTrainRatio}
                            valRatio={valRatio}
                            setValRatio={setValRatio}
                            testRatio={testRatio}
                            setTestRatio={setTestRatio}
                            imbalanceStrategy={imbalanceStrategy}
                            setImbalanceStrategy={setImbalanceStrategy}
                            purgeLength={purgeLength}
                            setPurgeLength={setPurgeLength}
                            useTripleBarrier={useTripleBarrier}
                            setUseTripleBarrier={setUseTripleBarrier}
                            ptSlRatio={ptSlRatio}
                            setPtSlRatio={setPtSlRatio}
                            barrierTimeout={barrierTimeout}
                            setBarrierTimeout={setBarrierTimeout}
                            enableMetaLabeling={enableMetaLabeling}
                            setEnableMetaLabeling={setEnableMetaLabeling}
                            featureSelectionMethod={featureSelectionMethod}
                            setFeatureSelectionMethod={setFeatureSelectionMethod}
                            wfoWindows={wfoWindows}
                            setWfoWindows={setWfoWindows}
                        />

                        {/* COLUMN 2: Neural Architecture */}
                        <div className="flex flex-col h-full bg-white/5 border border-teal-500/30 rounded-2xl shadow-[0_0_12px_rgba(20,184,166,0.1)] overflow-hidden">
                            <div className="p-5 bg-black/40 border-b border-white/10 flex-shrink-0 relative z-20">
                                <h3 className="text-sm font-bold text-blue-400 flex items-center gap-2 uppercase tracking-widest"><Cpu className="w-4 h-4" /> Neural Architecture</h3>
                            </div>
                            <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar h-full flex flex-col">
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
                                    <AutoMlToggle 
                                        useAutoMl={useAutoMl}
                                        setUseAutoMl={setUseAutoMl}
                                        autoMlTrials={autoMlTrials}
                                        setAutoMlTrials={setAutoMlTrials}
                                        epochs={epochs}
                                        setEpochs={setEpochs}
                                        isTraining={isTraining}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* COLUMN 3: Forex Data Engine (TradFi Data Pipeline) */}
                        <ForexAdvancedPipeline 
                            selectedFeatures={selectedForexFeatures}
                            onToggleFeature={(id) => {
                                setSelectedForexFeatures(prev => 
                                    prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id]
                                );
                            }}
                            onSetMultipleFeatures={setSelectedForexFeatures}
                            disabled={isTraining}
                        />

                        </div>

                    </div>
                    
                    <div className="pt-6 mt-2 relative z-10 flex flex-col gap-3 border-t border-white/10">
                        <button
                            onClick={handleStartTraining}
                            disabled={isTraining}
                            className={`w-full py-4 rounded-2xl font-black text-[15px] flex items-center justify-center gap-3 transition-all duration-300 shadow-xl bg-gradient-to-r from-teal-500 via-blue-500 to-indigo-600 text-white hover:shadow-[0_0_30px_rgba(20,184,166,0.5)] border border-white/20 hover:scale-[1.02] ${isTraining ? 'opacity-50 cursor-wait' : ''}`}
                        >
                            {isTraining ? (
                                <><Loader2 className="w-5 h-5 animate-spin" /> INITIALIZING...</>
                            ) : (
                                <><Play className="w-5 h-5 fill-current" /> START DEEP TRAINING</>
                            )}
                        </button>
                    </div>
                </div>
            </div>
    );
};

export default ForexModelTrainingStudio;
