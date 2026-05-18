import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, Layers, GitMerge, CheckSquare, Square, Check, Settings2, Sliders, Dna } from 'lucide-react';

interface EnsembleBuilderProps {
    isEnsemble: boolean;
    setIsEnsemble: (val: boolean) => void;
    ensembleMethod: 'voting' | 'stacking';
    setEnsembleMethod: (val: 'voting' | 'stacking') => void;
    baseModels: string[];
    setBaseModels: React.Dispatch<React.SetStateAction<string[]>>;
    metaModel: string;
    setMetaModel: (val: string) => void;
    votingStrategy?: 'hard' | 'soft';
    setVotingStrategy?: (val: 'hard' | 'soft') => void;
    autoOptimizeWeights?: boolean;
    setAutoOptimizeWeights?: (val: boolean) => void;
    featureSubspacing?: boolean;
    setFeatureSubspacing?: (val: boolean) => void;
    disabled: boolean;
}

const AVAILABLE_BASE_MODELS = [
    { id: 'Random Forest', type: 'Tree' },
    { id: 'XGBoost', type: 'Boosting' },
    { id: 'LightGBM', type: 'Boosting' },
    { id: 'CatBoost', type: 'Boosting' },
    { id: 'LSTM', type: 'Deep Learning' },
    { id: 'Transformer', type: 'Attention' },
];

const AVAILABLE_META_MODELS = [
    { id: 'Logistic Regression', desc: 'Simple linear combination' },
    { id: 'Random Forest', desc: 'Tree-based meta learner' },
    { id: 'XGBoost', desc: 'Gradient boosting meta learner' },
    { id: 'Neural Network (MLP)', desc: 'Multi-layer perceptron meta learner' },
];

const EnsembleBuilder: React.FC<EnsembleBuilderProps> = ({
    isEnsemble,
    setIsEnsemble,
    ensembleMethod,
    setEnsembleMethod,
    baseModels,
    setBaseModels,
    metaModel,
    setMetaModel,
    votingStrategy = 'soft',
    setVotingStrategy = () => {},
    autoOptimizeWeights = false,
    setAutoOptimizeWeights = () => {},
    featureSubspacing = false,
    setFeatureSubspacing = () => {},
    disabled
}) => {

    const toggleBaseModel = (modelId: string) => {
        if (disabled) return;
        setBaseModels(prev => 
            prev.includes(modelId) ? prev.filter(m => m !== modelId) : [...prev, modelId]
        );
    };

    return (
        <div className="space-y-4">
            {/* Ensemble Mode Toggle */}
            <div className="flex items-center justify-between p-4 bg-purple-500/10 border border-purple-500/30 rounded-2xl shadow-[0_0_15px_rgba(168,85,247,0.1)]">
                <div>
                    <h4 className="text-sm font-black text-purple-400 flex items-center gap-2">
                        <Layers className="w-4 h-4" /> Advanced Ensemble Mode
                    </h4>
                    <p className="text-[10px] text-slate-400 mt-1">Combine multiple weak learners into a powerful super-model.</p>
                </div>
                <button
                    onClick={() => setIsEnsemble(!isEnsemble)}
                    disabled={disabled}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isEnsemble ? 'bg-purple-500 shadow-[0_0_10px_#a855f7]' : 'bg-slate-600'} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isEnsemble ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
            </div>

            <AnimatePresence>
                {isEnsemble && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="space-y-6 overflow-hidden"
                    >
                        {/* 1. Select Ensemble Method */}
                        <div className="space-y-3">
                            <h5 className="text-[10px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                                <span className="flex items-center justify-center w-4 h-4 rounded-full bg-purple-500/20 text-purple-400 text-[9px]">1</span>
                                Assembly Method
                            </h5>
                            <div className="grid grid-cols-2 gap-3">
                                <div 
                                    onClick={() => !disabled && setEnsembleMethod('voting')}
                                    className={`p-3 rounded-xl border cursor-pointer transition-all ${ensembleMethod === 'voting' ? 'bg-purple-500/20 border-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.2)]' : 'bg-white/5 border-white/10 hover:bg-white/10'} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                    <div className="flex items-center gap-2 mb-1">
                                        <CheckSquare className={`w-4 h-4 ${ensembleMethod === 'voting' ? 'text-purple-400' : 'text-slate-500'}`} />
                                        <span className={`text-xs font-bold ${ensembleMethod === 'voting' ? 'text-white' : 'text-slate-300'}`}>Voting (Soft/Hard)</span>
                                    </div>
                                    <p className="text-[9px] text-slate-400">Averages the predictions of all base models.</p>
                                </div>
                                <div 
                                    onClick={() => !disabled && setEnsembleMethod('stacking')}
                                    className={`p-3 rounded-xl border cursor-pointer transition-all ${ensembleMethod === 'stacking' ? 'bg-purple-500/20 border-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.2)]' : 'bg-white/5 border-white/10 hover:bg-white/10'} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                    <div className="flex items-center gap-2 mb-1">
                                        <GitMerge className={`w-4 h-4 ${ensembleMethod === 'stacking' ? 'text-purple-400' : 'text-slate-500'}`} />
                                        <span className={`text-xs font-bold ${ensembleMethod === 'stacking' ? 'text-white' : 'text-slate-300'}`}>Stacking</span>
                                    </div>
                                    <p className="text-[9px] text-slate-400">Trains a Meta-Model on the outputs of base models.</p>
                                </div>
                            </div>
                        </div>

                        {/* 1.5 Voting Options (Only if Voting) */}
                        <AnimatePresence>
                            {ensembleMethod === 'voting' && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className="space-y-3 pt-2 border-t border-white/10"
                                >
                                    <h5 className="text-[10px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                                        <Sliders className="w-3.5 h-3.5 text-purple-400" /> Voting Configuration
                                    </h5>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div 
                                            onClick={() => !disabled && setVotingStrategy('soft')}
                                            className={`p-2 rounded-lg border cursor-pointer transition-all ${votingStrategy === 'soft' ? 'bg-indigo-500/20 border-indigo-500/50' : 'bg-white/5 border-white/10'} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                                        >
                                            <div className="text-[10px] font-bold text-white mb-0.5">Soft Voting</div>
                                            <div className="text-[8px] text-slate-400">Averages probabilities</div>
                                        </div>
                                        <div 
                                            onClick={() => !disabled && setVotingStrategy('hard')}
                                            className={`p-2 rounded-lg border cursor-pointer transition-all ${votingStrategy === 'hard' ? 'bg-indigo-500/20 border-indigo-500/50' : 'bg-white/5 border-white/10'} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                                        >
                                            <div className="text-[10px] font-bold text-white mb-0.5">Hard Voting</div>
                                            <div className="text-[8px] text-slate-400">Majority rule class vote</div>
                                        </div>
                                    </div>
                                    
                                    {votingStrategy === 'soft' && (
                                        <div className="flex items-center justify-between p-2.5 bg-white/5 rounded-lg border border-white/5 mt-2">
                                            <div className="flex items-center gap-2">
                                                <Settings2 className="w-3.5 h-3.5 text-indigo-400" />
                                                <span className="text-xs text-slate-300">Auto-Optimize Weights</span>
                                            </div>
                                            <button
                                                onClick={() => setAutoOptimizeWeights(!autoOptimizeWeights)}
                                                disabled={disabled}
                                                className={`relative inline-flex h-4 w-8 items-center rounded-full transition-colors ${autoOptimizeWeights ? 'bg-indigo-500' : 'bg-slate-600'} ${disabled ? 'opacity-50' : ''}`}
                                            >
                                                <span className={`inline-block h-2.5 w-2.5 transform rounded-full bg-white transition-transform ${autoOptimizeWeights ? 'translate-x-4' : 'translate-x-1'}`} />
                                            </button>
                                        </div>
                                    )}
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* 2. Select Base Models */}
                        <div className="space-y-3">
                            <div className="flex justify-between items-center">
                                <h5 className="text-[10px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                                    <span className="flex items-center justify-center w-4 h-4 rounded-full bg-purple-500/20 text-purple-400 text-[9px]">2</span>
                                    Select Base Models
                                </h5>
                                <span className="text-[10px] text-purple-400 font-bold bg-purple-500/20 px-2 py-0.5 rounded-full">
                                    {baseModels.length} Selected
                                </span>
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                {AVAILABLE_BASE_MODELS.map(model => (
                                    <div 
                                        key={model.id}
                                        onClick={() => toggleBaseModel(model.id)}
                                        className={`flex items-center gap-3 p-2 rounded-lg border cursor-pointer transition-all ${baseModels.includes(model.id) ? 'bg-cyan-500/10 border-cyan-500/30' : 'bg-white/5 border-white/5 hover:bg-white/10'} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                                    >
                                        <div className={`w-4 h-4 rounded flex items-center justify-center border ${baseModels.includes(model.id) ? 'bg-cyan-500 border-cyan-400' : 'border-slate-500'}`}>
                                            {baseModels.includes(model.id) && <Check className="w-3 h-3 text-black" />}
                                        </div>
                                        <div>
                                            <div className={`text-xs font-bold ${baseModels.includes(model.id) ? 'text-cyan-300' : 'text-slate-300'}`}>{model.id}</div>
                                            <div className="text-[8px] text-slate-500 uppercase">{model.type}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            
                            {/* Feature Subspacing Toggle */}
                            <div className="flex items-center justify-between p-3 mt-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                                <div className="flex items-center gap-2">
                                    <Dna className="w-4 h-4 text-emerald-400" />
                                    <div>
                                        <div className="text-xs font-bold text-emerald-300">Feature Subspacing</div>
                                        <div className="text-[8px] text-emerald-500/70 uppercase">Reduces model correlation</div>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setFeatureSubspacing(!featureSubspacing)}
                                    disabled={disabled}
                                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${featureSubspacing ? 'bg-emerald-500' : 'bg-slate-600'} ${disabled ? 'opacity-50' : ''}`}
                                >
                                    <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${featureSubspacing ? 'translate-x-5' : 'translate-x-1'}`} />
                                </button>
                            </div>
                        </div>

                        {/* 3. Select Meta Model (Only if Stacking) */}
                        <AnimatePresence>
                            {ensembleMethod === 'stacking' && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className="space-y-3 pt-2 border-t border-white/10"
                                >
                                    <h5 className="text-[10px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                                        <span className="flex items-center justify-center w-4 h-4 rounded-full bg-purple-500/20 text-purple-400 text-[9px]">3</span>
                                        Select Meta-Model
                                    </h5>
                                    <div className="space-y-2">
                                        {AVAILABLE_META_MODELS.map(model => (
                                            <div 
                                                key={model.id}
                                                onClick={() => !disabled && setMetaModel(model.id)}
                                                className={`flex items-center gap-3 p-2.5 rounded-xl border cursor-pointer transition-all ${metaModel === model.id ? 'bg-amber-500/10 border-amber-500/30 shadow-[0_0_10px_rgba(245,158,11,0.1)]' : 'bg-white/5 border-white/5 hover:bg-white/10'} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                                            >
                                                <div className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center flex-shrink-0 ${metaModel === model.id ? 'border-amber-400' : 'border-slate-500'}`}>
                                                    {metaModel === model.id && <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shadow-[0_0_5px_#f59e0b]"></div>}
                                                </div>
                                                <div>
                                                    <div className={`text-xs font-bold ${metaModel === model.id ? 'text-amber-300' : 'text-slate-300'}`}>{model.id}</div>
                                                    <div className="text-[9px] text-slate-500">{model.desc}</div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default EnsembleBuilder;
