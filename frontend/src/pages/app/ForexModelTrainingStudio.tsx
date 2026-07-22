import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, Play, Settings, Activity, Layers, Target, Cpu, CheckCircle2, XCircle, Loader2, Globe, Terminal, Database } from 'lucide-react';
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
    const [dateRangeMode, setDateRangeMode] = useState<'ticks' | 'date'>('ticks');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
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
    const [showTerminal, setShowTerminal] = useState(false);
    const logsEndRef = useRef<HTMLDivElement>(null);

    // Scraper States
    const [forexScrapeJob, setForexScrapeJob] = useState<ForexTrainingJob | null>(null);
    const [forexSnapshotFiles, setForexSnapshotFiles] = useState<string[]>([]);
    const [selectedForexFile, setSelectedForexFile] = useState('');

    const ALGORITHM_CATEGORIES = [
        { 
            name: "Econometric & Statistical (Forex Core)", 
            desc: "Classic Quant models for Macro & Volatility", 
            algos: [
                { id: 'ARIMA', type: 'Statistical', desc: 'AutoRegressive Integrated Moving Average' },
                { id: 'VAR', type: 'Statistical', desc: 'Vector AutoRegression for multi-pair correlation' },
                { id: 'GARCH', type: 'Volatility', desc: 'Predicts volatility clustering' },
                { id: 'EGARCH', type: 'Volatility', desc: 'Exponential GARCH for asymmetric shocks' },
                { id: 'NeuralProphet', type: 'Time-Series', desc: 'Captures daily/weekly session seasonality' }
            ] 
        },
        { 
            name: "Market Regime & Macro", 
            desc: "Detects hidden states and handles uncertainty", 
            algos: [
                { id: 'HMM', type: 'Regime Detection', desc: 'Hidden Markov Model for market states' },
                { id: 'Markov-Switching', type: 'Regime Detection', desc: 'Dynamic weight shifting based on regime' },
                { id: 'Bayesian NN', type: 'Probabilistic', desc: 'Handles uncertainty of macro-economic events' }
            ] 
        },
        { 
            name: "Indicator & Tabular Engines", 
            desc: "Fastest. Best for Technical Indicators & L2 Snapshots", 
            algos: [
                { id: 'Random Forest', type: 'Supervised', desc: 'Ensemble of decision trees' },
                { id: 'XGBoost', type: 'Supervised', desc: 'Optimized gradient boosting' },
                { id: 'LightGBM', type: 'Supervised', desc: 'Fast, distributed gradient boosting' },
                { id: 'CatBoost', type: 'Supervised', desc: 'Great for categorical and tabular data' },
                { id: 'TabNet', type: 'Supervised', desc: 'Deep learning for tabular data with attention' }
            ] 
        },
        { 
            name: "Trend & Sequence Memory", 
            desc: "Best for tracking long-term trends & historical patterns", 
            algos: [
                { id: 'LSTM', type: 'Supervised', desc: 'Long Short-Term Memory networks' },
                { id: 'GRU', type: 'Supervised', desc: 'Gated Recurrent Units, faster than LSTM' },
                { id: 'TCN', type: 'Supervised', desc: 'Temporal Convolutional Network' }
            ] 
        },
        { 
            name: "Micro-Pattern & Scalping", 
            desc: "Best for raw Orderbook flow & spatial feature extraction", 
            algos: [
                { id: '1D-CNN', type: 'Supervised', desc: '1D Convolutional Neural Network' },
                { id: 'DeepLOB', type: 'Supervised', desc: 'Deep learning model for Limit Order Books' },
                { id: 'Transformer', type: 'Supervised', desc: 'Attention-based sequence modeling' }
            ] 
        },
        { 
            name: "RL: Active Trading Agents", 
            desc: "Standard self-learning environments (Live/Simulated Trading)", 
            algos: [
                { id: 'PPO-RL', type: 'Reinforcement Learning', desc: 'Proximal Policy Optimization' },
                { id: 'SAC-RL', type: 'Reinforcement Learning', desc: 'Soft Actor-Critic for continuous action' },
                { id: 'A2C-RL', type: 'Reinforcement Learning', desc: 'Advantage Actor-Critic (Fast Baseline)' },
                { id: 'DDPG-RL', type: 'Reinforcement Learning', desc: 'Deep Deterministic Policy Gradient' },
                { id: 'TD3-RL', type: 'Reinforcement Learning', desc: 'Twin Delayed DDPG (Stable Continuous)' },
                { id: 'DQN-RL', type: 'Reinforcement Learning', desc: 'Dueling Double DQN (Discrete actions)' }
            ] 
        },
        { 
            name: "RL: Risk-Aware (Distributional)", 
            desc: "Models that learn the distribution of returns to minimize risk", 
            algos: [
                { id: 'QR-DQN', type: 'Distributional RL', desc: 'Quantile Regression DQN (Risk-Aware)' }
            ] 
        },
        { 
            name: "RL: Offline & Imitation", 
            desc: "Learn from historical or expert trader demonstrations", 
            algos: [
                { id: 'CQL', type: 'Offline RL', desc: 'Conservative Q-Learning (Learn from history)' },
                { id: 'GAIL', type: 'Imitation Learning', desc: 'Generative Adversarial Imitation Learning' }
            ] 
        },
        { 
            name: "Next-Gen Architectures", 
            desc: "Cutting-edge dynamic neural models", 
            algos: [
                { id: 'Decision-Transformer', type: 'Offline RL', desc: 'Action generation based on target ROI' },
                { id: 'Liquid-NN', type: 'Continuous RNN', desc: 'Dynamically adapts weights during live trading' }
            ] 
        },
        { 
            name: "Anomaly Detection", 
            desc: "Unsupervised learning for crash/pump detection", 
            algos: [
                { id: 'Auto-Encoder', type: 'Unsupervised', desc: 'Finds anomalies via reconstruction loss' }
            ] 
        }
    ];

    React.useEffect(() => {
        const loadInstruments = async () => {
            try {
                const data = await forexMlTrainingService.getInstruments();
                setInstruments(data);
                if (data.length > 0) {
                    const hasEurUsd = data.some((i: any) => i.name === 'EUR_USD');
                    if (hasEurUsd) {
                        setSymbol('EUR_USD');
                    } else {
                        setSymbol(data[0].name);
                    }
                }
            } catch (err) {
                console.error("Failed to load instruments", err);
            }
        };
        loadInstruments();
    }, []);

    // Auto-scroll logs
    useEffect(() => {
        if (logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [activeJob?.logs, forexScrapeJob?.logs]);

    // Load Forex Snapshots
    useEffect(() => {
        forexMlTrainingService.getForexSnapshots().then((files) => {
            setForexSnapshotFiles(files);
            if (files.length > 0 && !selectedForexFile) {
                setSelectedForexFile(files[0]);
            }
        }).catch(err => console.error("Failed to load forex snapshots", err));
    }, []);

    // Polling logic for Training Job
    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (isTraining && activeJob && ['PENDING', 'RUNNING'].includes(activeJob.status)) {
            interval = setInterval(async () => {
                try {
                    const latestJob = await forexMlTrainingService.getJobStatus(activeJob.id);
                    setActiveJob(latestJob);
                    if (['COMPLETED', 'FAILED'].includes(latestJob.status)) {
                        setIsTraining(false);
                        clearInterval(interval);
                    }
                } catch (error) {
                    console.error("Error fetching job status:", error);
                }
            }, 1000);
        }
        return () => clearInterval(interval);
    }, [isTraining, activeJob?.id, activeJob?.status]);

    // Polling logic for Scraper Job
    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (forexScrapeJob && ['PENDING', 'RUNNING'].includes(forexScrapeJob.status)) {
            interval = setInterval(async () => {
                try {
                    const latestJob = await forexMlTrainingService.getJobStatus(forexScrapeJob.id);
                    setForexScrapeJob(latestJob);
                    if (['COMPLETED', 'FAILED'].includes(latestJob.status)) {
                        clearInterval(interval);
                        if (latestJob.status === 'COMPLETED') {
                            forexMlTrainingService.getForexSnapshots().then((files) => {
                                setForexSnapshotFiles(files);
                                if (files.length > 0) {
                                    setSelectedForexFile(files[0]);
                                }
                            });
                        }
                    }
                } catch (error) {
                    console.error("Error fetching scrape job status:", error);
                }
            }, 1000);
        }
        return () => clearInterval(interval);
    }, [forexScrapeJob?.id, forexScrapeJob?.status]);

    const handleStartForexCollector = async (config: {target_rows: number, mode?: string, start_date?: string, end_date?: string, timeframe?: string, data_source?: string}) => {
        try {
            const job = await forexMlTrainingService.startForexCollector({
                symbol: symbol,
                ...config
            });
            setForexScrapeJob(job);
        } catch (error: any) {
            alert(`Failed to start collector: ${error.message}`);
        }
    };

    const handleCancelForexCollector = async () => {
        if (!forexScrapeJob) return;
        if (!window.confirm("Are you sure you want to stop data collection?")) return;
        try {
            await forexMlTrainingService.cancelTraining(forexScrapeJob.id);
            setForexScrapeJob(prev => prev ? { ...prev, status: 'FAILED', error_message: 'Collection cancelled by user.' } : null);
        } catch (error: any) {
            alert(`Failed to cancel collection: ${error.message}`);
        }
    };

    const handleDeleteSnapshot = async (e: React.MouseEvent) => {
        e.preventDefault();
        if (!selectedForexFile) return;
        if (!window.confirm(`Are you sure you want to delete ${selectedForexFile}?`)) return;
        try {
            await forexMlTrainingService.deleteForexSnapshot(selectedForexFile);
            setForexSnapshotFiles(prev => prev.filter(f => f !== selectedForexFile));
            setSelectedForexFile('');
            alert(`Deleted ${selectedForexFile}`);
        } catch (error: any) {
            alert(`Failed to delete snapshot: ${error.message}`);
        }
    };

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
                    date_range_mode: dateRangeMode,
                    start_date: startDate,
                    end_date: endDate,
                    use_triple_barrier: useTripleBarrier,
                    pt_sl_ratio: ptSlRatio,
                    barrier_timeout: barrierTimeout,
                    use_automl: useAutoMl,
                    automl_trials: autoMlTrials,
                    enable_meta_labeling: enableMetaLabeling,
                    feature_selection_method: featureSelectionMethod,
                    wfo_windows: wfoWindows,
                    selected_forex_features: selectedForexFeatures,
                    snapshot_file: selectedForexFile
                }
            });
            setActiveJob(job);
            setShowTerminal(true);
            alert("Training job started successfully!");
        } catch (error) {
            console.error("Failed to start training", error);
            alert("Failed to start Forex training job.");
        }
    };

    const handleCancelTraining = async () => {
        if (!activeJob) return;
        if (!window.confirm("Are you sure you want to stop this training job?")) return;
        try {
            await forexMlTrainingService.cancelTraining(activeJob.id);
            setIsTraining(false);
            setActiveJob(prev => prev ? { ...prev, status: 'FAILED', error_message: 'Training cancelled by user.' } : null);
        } catch (error) {
            console.error("Failed to cancel training", error);
            alert("Failed to cancel training job.");
        }
    };

    return (
        <>
            <div className="h-full flex flex-col space-y-3 relative overflow-hidden bg-black/20 rounded-3xl">
            {/* Background Orbs adapted for Forex (Teal/Blue vibe) */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-teal-600/20 blur-[120px] rounded-full pointer-events-none"></div>
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/20 blur-[120px] rounded-full pointer-events-none"></div>

            <header className="flex items-center gap-4 z-10 px-2 mt-2">
                <h2 className="text-xl font-black text-white flex items-center gap-2">
                    <Globe className="w-5 h-5 text-teal-400" />
                    Forex ML Intelligence Studio
                </h2>
                <div className="w-px h-4 bg-white/20"></div>
                <div className="text-slate-400 text-xs font-medium tracking-wide flex items-center gap-2">
                    Decentralized Market Modeling with Macro-Economic Pipelines
                </div>
            </header>

            <div className="flex-1 flex flex-col min-h-0 relative z-10">
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
                            dateRangeMode={dateRangeMode}
                            setDateRangeMode={setDateRangeMode}
                            startDate={startDate}
                            setStartDate={setStartDate}
                            endDate={endDate}
                            setEndDate={setEndDate}
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
                                        <div className="space-y-4">
                                            {ALGORITHM_CATEGORIES.map(category => (
                                                <div key={category.name} className="space-y-2">
                                                    <div>
                                                        <h4 className="text-[10px] font-black text-teal-400 uppercase tracking-widest">{category.name}</h4>
                                                        <p className="text-[10px] text-slate-500 font-medium">{category.desc}</p>
                                                    </div>
                                                    <div className="grid grid-cols-1 gap-2">
                                                        {category.algos.map(algo => (
                                                            <div 
                                                                key={algo.id} 
                                                                onClick={() => !isTraining && setAlgorithm(algo.id)}
                                                                className={`flex items-start p-3 rounded-xl border cursor-pointer transition-all duration-300 relative overflow-hidden ${algorithm === algo.id ? 'border-teal-400 bg-teal-500/20 shadow-[0_0_15px_rgba(20,184,166,0.2)]' : 'border-white/10 bg-white/5 hover:bg-white/10'} ${isTraining ? 'opacity-50 cursor-not-allowed' : ''}`}
                                                            >
                                                                <div className={`mt-1 w-3.5 h-3.5 rounded-full border flex items-center justify-center flex-shrink-0 ${algorithm === algo.id ? 'border-teal-400' : 'border-white/30'}`}>
                                                                    {algorithm === algo.id && <div className="w-1.5 h-1.5 bg-teal-400 rounded-full" />}
                                                                </div>
                                                                <div className="ml-3 flex-1 min-w-0">
                                                                    <div className="flex justify-between items-start mb-1">
                                                                        <span className={`text-xs font-bold ${algorithm === algo.id ? 'text-teal-300' : 'text-slate-300'}`}>{algo.id}</span>
                                                                        <span className="text-[9px] font-bold tracking-wider uppercase text-slate-500 bg-black/40 px-1.5 py-0.5 rounded border border-white/5">{algo.type}</span>
                                                                    </div>
                                                                    <p className="text-[10px] text-slate-400 leading-snug">{algo.desc}</p>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
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
                            symbol={symbol}
                            isTraining={isTraining}
                            timeframe={timeframe}
                            forexSnapshotFiles={forexSnapshotFiles}
                            selectedForexFile={selectedForexFile}
                            setSelectedForexFile={setSelectedForexFile}
                            handleDeleteSnapshot={handleDeleteSnapshot}
                            forexScrapeJob={forexScrapeJob}
                            setForexScrapeJob={setForexScrapeJob}
                            onStartCollector={handleStartForexCollector}
                            onCancelCollector={handleCancelForexCollector}
                        />

                        </div>

                    </div>
                    
                    <div className="pt-6 mt-2 relative z-10 flex flex-col gap-3 border-t border-white/10">
                        {isTraining && activeJob ? (
                            <div className="flex gap-3">
                                <button 
                                    onClick={() => setShowTerminal(true)}
                                    className="flex-1 py-4 rounded-2xl font-black text-[15px] flex items-center justify-center gap-3 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 transition-all duration-300 shadow-xl"
                                >
                                    <Activity className="w-5 h-5" /> SHOW LIVE TERMINAL
                                </button>
                                <button 
                                    onClick={handleCancelTraining}
                                    className="flex-1 py-4 rounded-2xl font-black text-[15px] flex items-center justify-center gap-2 bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20 transition-all"
                                >
                                    <XCircle className="w-5 h-5" /> CANCEL
                                </button>
                            </div>
                        ) : (
                            <button
                                onClick={handleStartTraining}
                                disabled={isTraining}
                                className={`w-full py-4 rounded-2xl font-black text-[15px] flex items-center justify-center gap-3 transition-all duration-300 shadow-xl bg-gradient-to-r from-teal-500 via-blue-500 to-indigo-600 text-white hover:shadow-[0_0_30px_rgba(20,184,166,0.5)] border border-white/20 hover:scale-[1.02] ${isTraining ? 'opacity-50 cursor-wait' : ''}`}
                            >
                                <Play className="w-5 h-5 fill-current" /> START DEEP TRAINING
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Live Execution Terminal Modal */}
            <AnimatePresence>
                {showTerminal && (
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/80 backdrop-blur-sm"
                    >
                        <div className="w-full max-w-6xl h-[85vh] relative flex flex-col min-h-0">
                            <button 
                                onClick={() => setShowTerminal(false)}
                                className="absolute -top-12 right-0 p-2 text-slate-400 hover:text-white transition-colors"
                            >
                                <XCircle className="w-8 h-8" />
                            </button>

                            <div className="flex flex-col bg-black/60 backdrop-blur-2xl border border-cyan-500/20 rounded-3xl shadow-[0_0_50px_rgba(56,189,248,0.1)] overflow-hidden h-full relative z-10 w-full">
                                {/* Header */}
                                <div className="px-6 py-4 bg-gradient-to-r from-cyan-900/40 to-blue-900/20 border-b border-cyan-500/20 flex items-center justify-between flex-shrink-0">
                                    <div className="flex items-center gap-3">
                                        <Terminal className="w-5 h-5 text-cyan-400" />
                                        <span className="text-sm font-mono text-cyan-100 tracking-widest font-bold">LIVE_CONSOLE_OUTPUT</span>
                                    </div>
                                    <div className="flex gap-2">
                                        <div className="w-3.5 h-3.5 rounded-full bg-red-500/50 border border-red-400 shadow-[0_0_10px_#ef4444]"></div>
                                        <div className="w-3.5 h-3.5 rounded-full bg-yellow-500/50 border border-yellow-400 shadow-[0_0_10px_#eab308]"></div>
                                        <div className="w-3.5 h-3.5 rounded-full bg-green-500/50 border border-green-400 shadow-[0_0_10px_#22c55e]"></div>
                                    </div>
                                </div>

                                {/* Progress Bar */}
                                {activeJob && (
                                    <div className="h-1.5 bg-gray-900 w-full relative overflow-hidden shadow-inner flex-shrink-0 border-b border-cyan-900/50">
                                        <motion.div 
                                            className={`absolute top-0 left-0 h-full ${activeJob.status === 'FAILED' ? 'bg-red-500 shadow-[0_0_10px_#ef4444]' : activeJob.status === 'COMPLETED' ? 'bg-emerald-500 shadow-[0_0_10px_#10b981]' : 'bg-gradient-to-r from-cyan-400 to-purple-500 shadow-[0_0_15px_#22d3ee]'}`}
                                            initial={{ width: 0 }}
                                            animate={{ width: `${activeJob.progress}%` }}
                                            transition={{ duration: 0.5 }}
                                        />
                                    </div>
                                )}

                                {/* Terminal Logs Area */}
                                <div className="flex-1 p-5 overflow-y-auto custom-scrollbar font-mono text-sm leading-relaxed">
                                    {!activeJob ? (
                                        <div className="h-full flex flex-col items-center justify-center text-gray-600 space-y-4">
                                            <Database className="w-12 h-12 opacity-20" />
                                            <p>Awaiting training instructions...</p>
                                        </div>
                                    ) : (
                                        <div className="space-y-1.5 pb-8">
                                            {activeJob.logs?.map((log, i) => {
                                                const isError = log.includes("ERROR") || log.includes("CRITICAL");
                                                const isWarning = log.includes("WARNING");
                                                const isSuccess = log.includes("SUCCESS") || log.includes("Model saved");
                                                return (
                                                    <div key={i} className={`flex ${isError ? 'text-red-400 font-semibold bg-red-500/10 p-1 rounded' : isWarning ? 'text-yellow-300' : isSuccess ? 'text-green-400 font-semibold' : 'text-cyan-300 hover:text-cyan-100'}`}>
                                                        <span className="opacity-50 mr-3 select-none">[{i.toString().padStart(4, '0')}]</span>
                                                        <span className="break-all">{log}</span>
                                                    </div>
                                                );
                                            })}
                                            {activeJob.status === 'RUNNING' && (
                                                <div className="flex items-center gap-2 text-cyan-500/50 mt-4 animate-pulse">
                                                    <span className="w-2 h-4 bg-cyan-400 block" />
                                                    <span>PROCESSING...</span>
                                                </div>
                                            )}
                                            {activeJob.status === 'FAILED' && (
                                                <div className="mt-4 p-4 border border-red-500/30 bg-red-500/10 rounded-xl text-red-400">
                                                    <div className="font-bold mb-1">PROCESS TERMINATED</div>
                                                    <div>{activeJob.error_message}</div>
                                                </div>
                                            )}
                                            {activeJob.status === 'COMPLETED' && (
                                                <div className="mt-4 text-green-400 font-bold">
                                                    PROCESS COMPLETED SUCCESSFULLY
                                                </div>
                                            )}
                                            <div ref={logsEndRef} />
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
};

export default ForexModelTrainingStudio;
