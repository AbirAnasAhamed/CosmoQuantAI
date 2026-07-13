import React, { useState } from 'react';
import { Activity, Clock, Globe, Terminal, ChevronDown, CheckSquare, Square } from 'lucide-react';

export const FOREX_MODULES = [
    {
        id: 'smc_order_flow',
        title: 'SMC & Order Flow',
        icon: Activity,
        description: 'Smart Money Concepts and Institutional footprints.',
        features: [
            { id: 'fvg_liquidity', name: 'FVG Liquidity Draw Probability' },
            { id: 'order_block_mitigation', name: 'Order Block Mitigation Speed' },
            { id: 'bms_choch', name: 'BMS & CHoCH Volatility Multiplier' },
            { id: 'retail_sentiment', name: 'Retail Sentiment & OBI Proxy' },
            { id: 'currency_correlation', name: 'Currency Correlation Matrix' },
        ]
    },
    {
        id: 'ict_macro',
        title: 'ICT Time & Macro Dynamics',
        icon: Clock,
        description: 'Time-based killzones and session volatilities.',
        features: [
            { id: 'london_ny_killzone', name: 'London & NY Killzone Momentum' },
            { id: 'judas_swing', name: 'Judas Swing & Turtle Soup Fakeouts' },
            { id: 'pdh_pdl_sweep', name: 'PDH/PDL Sweep Proxy' },
            { id: 'session_features', name: 'Market Session Pipeline' },
            { id: 'weekend_gap', name: 'Weekend Gap Handler' },
        ]
    },
    {
        id: 'alt_data',
        title: 'Alternative Data & Sentiment',
        icon: Globe,
        description: 'Macro events, Central Bank NLP and Yields.',
        features: [
            { id: 'central_bank_nlp', name: 'Central Bank NLP Sentiment' },
            { id: 'stop_hunt_sweeps', name: 'Stop-Hunt & Liquidity Sweeps' },
            { id: 'macro_calendar', name: 'Macroeconomic Calendar' },
            { id: 'cot_sentiment', name: 'COT Sentiment (Smart Money)' },
            { id: 'yield_differentials', name: 'Yield Differentials' },
        ]
    },
    {
        id: 'microstructure',
        title: 'Microstructure & High Frequency',
        icon: Terminal,
        description: 'Tick-level velocity and informed trading proxies.',
        features: [
            { id: 'vpin_proxy', name: 'VPIN Proxy (Probability of Informed Trading)' },
            { id: 'synthetic_cvd', name: 'Synthetic CVD (Cumulative Volume Delta)' },
            { id: 'tick_acceleration', name: 'Tick Acceleration & Velocity' },
            { id: 'tick_volume_profiler', name: 'Tick Volume Profiler' },
        ]
    }
];

interface ForexAdvancedPipelineProps {
    selectedFeatures: string[];
    onToggleFeature: (featureId: string) => void;
    onSetMultipleFeatures: (featureIds: string[]) => void;
    disabled?: boolean;
}

export const ForexAdvancedPipeline: React.FC<ForexAdvancedPipelineProps> = ({
    selectedFeatures,
    onToggleFeature,
    onSetMultipleFeatures,
    disabled
}) => {
    const [expandedModule, setExpandedModule] = useState<string | null>('smc_order_flow');

    const handleSelectAll = (moduleId: string, features: {id: string}[], isAllSelected: boolean) => {
        if (disabled) return;
        
        let newSelection = [...selectedFeatures];
        if (isAllSelected) {
            // Remove all features from this module
            const moduleFeatureIds = features.map(f => f.id);
            newSelection = newSelection.filter(id => !moduleFeatureIds.includes(id));
        } else {
            // Add all
            features.forEach(f => {
                if (!newSelection.includes(f.id)) newSelection.push(f.id);
            });
        }
        onSetMultipleFeatures(newSelection);
    };

    return (
        <div className="flex flex-col h-full bg-[#0A0A0A]/90 border border-teal-500/30 rounded-[22px] shadow-[0_0_20px_rgba(20,184,166,0.1)] overflow-hidden relative">
            {/* Ambient Background Effects */}
            <div className="absolute top-0 right-0 w-48 h-48 bg-teal-600/10 blur-[80px] rounded-full pointer-events-none"></div>
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-blue-600/10 blur-[80px] rounded-full pointer-events-none"></div>
            
            <div className="p-5 bg-black/40 border-b border-white/10 flex-shrink-0 relative z-20">
                <h3 className="text-sm font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-blue-500 flex items-center gap-3 uppercase">
                    <Activity className="w-5 h-5 text-teal-400" /> TradFi Data Pipeline
                </h3>
                <p className="text-xs text-slate-400 mt-1.5 font-medium max-w-xl">
                    Advanced institutional feature engineering mapped for Forex/TradFi markets.
                </p>
            </div>
            
            <div className="p-4 overflow-y-auto custom-scrollbar h-full relative z-10 space-y-3">
                {FOREX_MODULES.map((module) => {
                    const ModuleIcon = module.icon;
                    const isExpanded = expandedModule === module.id;
                    
                    const moduleFeatureIds = module.features.map(f => f.id);
                    const selectedInModule = selectedFeatures.filter(id => moduleFeatureIds.includes(id));
                    const isAllSelected = selectedInModule.length === module.features.length;
                    const isPartiallySelected = selectedInModule.length > 0 && !isAllSelected;

                    return (
                        <div 
                            key={module.id} 
                            className={`rounded-xl border transition-all duration-300 overflow-hidden ${isExpanded ? 'border-teal-500/40 bg-teal-500/5' : 'border-white/5 bg-white/[0.02] hover:bg-white/[0.04]'}`}
                        >
                            {/* Accordion Header */}
                            <div 
                                className="flex items-center justify-between p-3 cursor-pointer"
                                onClick={() => setExpandedModule(isExpanded ? null : module.id)}
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`p-2 rounded-lg transition-colors ${isExpanded ? 'bg-teal-500/20 text-teal-300' : 'bg-white/5 text-slate-400'}`}>
                                        <ModuleIcon className="w-4 h-4" />
                                    </div>
                                    <div>
                                        <h4 className={`text-sm font-bold tracking-wide transition-colors ${isExpanded ? 'text-teal-300' : 'text-slate-300'}`}>
                                            {module.title}
                                        </h4>
                                        {!isExpanded && (
                                            <p className="text-[10px] text-slate-500 mt-0.5">{module.description}</p>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="text-[10px] font-mono text-teal-400 bg-teal-400/10 px-2 py-0.5 rounded-md">
                                        {selectedInModule.length} / {module.features.length}
                                    </div>
                                    <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`} />
                                </div>
                            </div>

                            {/* Accordion Body */}
                            {isExpanded && (
                                <div className="p-3 pt-0 border-t border-white/5 mt-2 space-y-1">
                                    <div className="flex items-center justify-between mb-3 px-2 py-1 bg-white/5 rounded-md">
                                        <span className="text-xs text-slate-400 font-medium">{module.description}</span>
                                        <button 
                                            disabled={disabled}
                                            onClick={(e) => { e.stopPropagation(); handleSelectAll(module.id, module.features, isAllSelected); }}
                                            className="text-[10px] uppercase font-bold tracking-wider text-teal-400 hover:text-teal-300 px-2 py-1 rounded hover:bg-teal-400/10 transition-colors"
                                        >
                                            {isAllSelected ? 'Deselect All' : 'Select All'}
                                        </button>
                                    </div>

                                    <div className="grid grid-cols-1 gap-1">
                                        {module.features.map(feature => {
                                            const isSelected = selectedFeatures.includes(feature.id);
                                            return (
                                                <div 
                                                    key={feature.id}
                                                    onClick={() => !disabled && onToggleFeature(feature.id)}
                                                    className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors ${isSelected ? 'bg-teal-500/10 hover:bg-teal-500/20' : 'hover:bg-white/5'} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                                                >
                                                    <div className={`transition-colors ${isSelected ? 'text-teal-400' : 'text-slate-600'}`}>
                                                        {isSelected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                                                    </div>
                                                    <span className={`text-xs font-medium ${isSelected ? 'text-teal-200' : 'text-slate-400'}`}>
                                                        {feature.name}
                                                    </span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
