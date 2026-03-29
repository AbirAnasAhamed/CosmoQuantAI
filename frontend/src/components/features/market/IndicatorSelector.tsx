import React, { useState, useRef, useEffect } from 'react';

export interface IndicatorSettings {
    showEMA: boolean;
    showBB: boolean;
    showRSI: boolean;
    showVolume: boolean;
    showAutoFibo: boolean;
    showIchimoku: boolean;
    showTrendFinder: boolean;
    emaPeriod: number;
    bbPeriod: number;
    bbStdDev: number;
    rsiPeriod: number;
    autoFiboLookback: number;
    tenkanPeriod: number;
    kijunPeriod: number;
    senkouBPeriod: number;
    displacement: number;
    trendFinderLookback: number;
    trendFinderDev: number;
    trendFinderThreshold: string;
    enableTrendFinderVolumeFilter: boolean;
    trendFinderVolumeMultiplier: number;
}

interface IndicatorSelectorProps {
    settings: IndicatorSettings;
    onSettingsChange: (settings: IndicatorSettings) => void;
}

export const IndicatorSelector: React.FC<IndicatorSelectorProps> = ({ settings, onSettingsChange }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [multiplierLocal, setMultiplierLocal] = useState(settings.trendFinderVolumeMultiplier?.toString() || '1.5');
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        setMultiplierLocal(settings.trendFinderVolumeMultiplier?.toString() || '1.5');
    }, [settings.trendFinderVolumeMultiplier]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const toggleIndicator = (key: keyof IndicatorSettings) => {
        onSettingsChange({
            ...settings,
            [key]: !settings[key]
        });
    };

    const updateSetting = (key: keyof IndicatorSettings, value: number) => {
        if (!isNaN(value)) {
            onSettingsChange({
                ...settings,
                [key]: value
            });
        }
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium transition-all ${isOpen
                    ? 'bg-brand-primary/10 border-brand-primary text-brand-primary dark:text-brand-primary'
                    : 'bg-white dark:bg-black/20 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-white/10 hover:bg-gray-50 dark:hover:bg-white/5'
                    }`}
            >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                </svg>
                Indicators
                <svg className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {isOpen && (
                <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-[#0B1120] border border-gray-200 dark:border-white/10 rounded-xl shadow-xl z-50 overflow-hidden">
                    <div className="p-3 border-b border-gray-200 dark:border-white/10">
                        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Technical Indicators</h3>
                    </div>
                    <div className="p-2 flex flex-col gap-1">
                        <div className="flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-white/5 rounded-lg transition-colors group">
                            <label className="flex items-center cursor-pointer flex-1">
                                <input
                                    type="checkbox"
                                    checked={settings.showEMA}
                                    onChange={() => toggleIndicator('showEMA')}
                                    className="w-4 h-4 text-brand-primary bg-gray-100 border-gray-300 rounded focus:ring-brand-primary dark:focus:ring-brand-primary dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                                />
                                <span className="ml-3 text-sm font-medium text-gray-900 dark:text-gray-200 group-hover:text-brand-primary transition-colors">EMA</span>
                            </label>
                            <div className="flex items-center gap-1 bg-gray-100 dark:bg-white/10 px-1.5 py-0.5 rounded">
                                <span className="text-xs text-gray-500">P:</span>
                                <input
                                    type="number"
                                    value={settings.emaPeriod}
                                    onChange={(e) => updateSetting('emaPeriod', Number(e.target.value))}
                                    className="w-10 text-xs bg-transparent text-gray-700 dark:text-gray-300 focus:outline-none focus:text-brand-primary"
                                    min={1} max={500}
                                />
                            </div>
                        </div>

                        <div className="flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-white/5 rounded-lg transition-colors group">
                            <label className="flex items-center cursor-pointer flex-1">
                                <input
                                    type="checkbox"
                                    checked={settings.showBB}
                                    onChange={() => toggleIndicator('showBB')}
                                    className="w-4 h-4 text-brand-primary bg-gray-100 border-gray-300 rounded focus:ring-brand-primary dark:focus:ring-brand-primary dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                                />
                                <span className="ml-3 text-sm font-medium text-gray-900 dark:text-gray-200 group-hover:text-brand-primary transition-colors">Bollinger</span>
                            </label>
                            <div className="flex items-center gap-2 bg-gray-100 dark:bg-white/10 px-1.5 py-0.5 rounded">
                                <div className="flex items-center">
                                    <span className="text-xs text-gray-500">P:</span>
                                    <input
                                        type="number"
                                        value={settings.bbPeriod}
                                        onChange={(e) => updateSetting('bbPeriod', Number(e.target.value))}
                                        className="w-8 text-xs bg-transparent text-gray-700 dark:text-gray-300 focus:outline-none focus:text-brand-primary"
                                        min={1} max={500}
                                    />
                                </div>
                                <div className="flex items-center border-l dark:border-white/10 pl-2">
                                    <span className="text-xs text-gray-500">D:</span>
                                    <input
                                        type="number"
                                        value={settings.bbStdDev}
                                        onChange={(e) => updateSetting('bbStdDev', parseFloat(e.target.value))}
                                        className="w-8 text-xs bg-transparent text-gray-700 dark:text-gray-300 focus:outline-none focus:text-brand-primary"
                                        min={0.1} max={10} step={0.1}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-white/5 rounded-lg transition-colors group">
                            <label className="flex items-center cursor-pointer flex-1">
                                <input
                                    type="checkbox"
                                    checked={settings.showRSI}
                                    onChange={() => toggleIndicator('showRSI')}
                                    className="w-4 h-4 text-brand-primary bg-gray-100 border-gray-300 rounded focus:ring-brand-primary dark:focus:ring-brand-primary dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                                />
                                <span className="ml-3 text-sm font-medium text-gray-900 dark:text-gray-200 group-hover:text-brand-primary transition-colors">RSI</span>
                            </label>
                            <div className="flex items-center gap-1 bg-gray-100 dark:bg-white/10 px-1.5 py-0.5 rounded">
                                <span className="text-xs text-gray-500">P:</span>
                                <input
                                    type="number"
                                    value={settings.rsiPeriod}
                                    onChange={(e) => updateSetting('rsiPeriod', Number(e.target.value))}
                                    className="w-10 text-xs bg-transparent text-gray-700 dark:text-gray-300 focus:outline-none focus:text-brand-primary"
                                    min={1} max={500}
                                />
                            </div>
                        </div>

                        <div className="flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-white/5 rounded-lg transition-colors group">
                            <label className="flex items-center cursor-pointer flex-1">
                                <input
                                    type="checkbox"
                                    checked={settings.showVolume}
                                    onChange={() => toggleIndicator('showVolume')}
                                    className="w-4 h-4 text-brand-primary bg-gray-100 border-gray-300 rounded focus:ring-brand-primary dark:focus:ring-brand-primary dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                                />
                                <span className="ml-3 text-sm font-medium text-gray-900 dark:text-gray-200 group-hover:text-brand-primary transition-colors">Volume</span>
                            </label>
                        </div>

                        <div className="flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-white/5 rounded-lg transition-colors group">
                            <label className="flex items-center cursor-pointer flex-1">
                                <input
                                    type="checkbox"
                                    checked={settings.showAutoFibo}
                                    onChange={() => toggleIndicator('showAutoFibo')}
                                    className="w-4 h-4 text-brand-primary bg-gray-100 border-gray-300 rounded focus:ring-brand-primary dark:focus:ring-brand-primary dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                                />
                                <span className="ml-3 text-sm font-medium text-gray-900 dark:text-gray-200 group-hover:text-brand-primary transition-colors">Auto Fibo</span>
                            </label>
                            <div className="flex items-center gap-1 bg-gray-100 dark:bg-white/10 px-1.5 py-0.5 rounded">
                                <span className="text-xs text-gray-500">LB:</span>
                                <input
                                    type="number"
                                    value={settings.autoFiboLookback}
                                    onChange={(e) => updateSetting('autoFiboLookback', Number(e.target.value))}
                                    className="w-10 text-xs bg-transparent text-gray-700 dark:text-gray-300 focus:outline-none focus:text-brand-primary"
                                    min={10} max={1000} step={10}
                                />
                            </div>
                        </div>

                        <div className="flex flex-col gap-2 p-2 hover:bg-gray-50 dark:hover:bg-white/5 rounded-lg transition-colors group">
                           <div className="flex items-center justify-between">
                            <label className="flex items-center cursor-pointer flex-1">
                                <input
                                    type="checkbox"
                                    checked={settings.showIchimoku}
                                    onChange={() => toggleIndicator('showIchimoku')}
                                    className="w-4 h-4 text-brand-primary bg-gray-100 border-gray-300 rounded focus:ring-brand-primary dark:focus:ring-brand-primary dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                                />
                                <span className="ml-3 text-sm font-medium text-gray-900 dark:text-gray-200 group-hover:text-brand-primary transition-colors">Ichimoku Cloud</span>
                            </label>
                           </div>
                           <div className="grid grid-cols-2 gap-2 text-[10px]">
                                <div className="flex items-center gap-1 bg-gray-100 dark:bg-white/10 px-1.5 py-0.5 rounded">
                                    <span className="text-gray-500">T:</span>
                                    <input
                                        type="number"
                                        value={settings.tenkanPeriod}
                                        onChange={(e) => updateSetting('tenkanPeriod', Number(e.target.value))}
                                        className="w-full bg-transparent text-gray-700 dark:text-gray-300 focus:outline-none focus:text-brand-primary text-center"
                                        min={1} max={100}
                                    />
                                </div>
                                <div className="flex items-center gap-1 bg-gray-100 dark:bg-white/10 px-1.5 py-0.5 rounded">
                                    <span className="text-gray-500">K:</span>
                                    <input
                                        type="number"
                                        value={settings.kijunPeriod}
                                        onChange={(e) => updateSetting('kijunPeriod', Number(e.target.value))}
                                        className="w-full bg-transparent text-gray-700 dark:text-gray-300 focus:outline-none focus:text-brand-primary text-center"
                                        min={1} max={200}
                                    />
                                </div>
                                <div className="flex items-center gap-1 bg-gray-100 dark:bg-white/10 px-1.5 py-0.5 rounded">
                                    <span className="text-gray-500">B:</span>
                                    <input
                                        type="number"
                                        value={settings.senkouBPeriod}
                                        onChange={(e) => updateSetting('senkouBPeriod', Number(e.target.value))}
                                        className="w-full bg-transparent text-gray-700 dark:text-gray-300 focus:outline-none focus:text-brand-primary text-center"
                                        min={1} max={400}
                                    />
                                </div>
                                <div className="flex items-center gap-1 bg-gray-100 dark:bg-white/10 px-1.5 py-0.5 rounded">
                                    <span className="text-gray-500">D:</span>
                                    <input
                                        type="number"
                                        value={settings.displacement}
                                        onChange={(e) => updateSetting('displacement', Number(e.target.value))}
                                        className="w-full bg-transparent text-gray-700 dark:text-gray-300 focus:outline-none focus:text-brand-primary text-center"
                                        min={1} max={100}
                                    />
                                </div>
                           </div>
                        </div>

                        <div className="flex flex-col gap-2 p-2 hover:bg-gray-50 dark:hover:bg-white/5 rounded-lg transition-colors group">
                           <div className="flex items-center justify-between">
                            <label className="flex items-center cursor-pointer flex-1">
                                <input
                                    type="checkbox"
                                    checked={settings.showTrendFinder}
                                    onChange={() => toggleIndicator('showTrendFinder')}
                                    className="w-4 h-4 text-brand-primary bg-gray-100 border-gray-300 rounded focus:ring-brand-primary dark:focus:ring-brand-primary dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                                />
                                <span className="ml-3 text-sm font-medium text-gray-900 dark:text-gray-200 group-hover:text-brand-primary transition-colors">Adaptive Trend Finder</span>
                            </label>
                           </div>
                            <div className="flex items-center gap-2 mt-1">
                                <div className="flex items-center gap-1 bg-gray-100 dark:bg-white/10 px-1.5 py-1 rounded">
                                    <span className="text-gray-500 text-[10px]">Lookback:</span>
                                    <input
                                        type="number"
                                        value={settings.trendFinderLookback}
                                        onChange={(e) => updateSetting('trendFinderLookback', Number(e.target.value))}
                                        className="w-12 bg-transparent text-gray-700 dark:text-gray-300 focus:outline-none focus:text-brand-primary text-[10px]"
                                        min={20} max={2000} step={10}
                                    />
                                </div>
                                <div className="flex items-center gap-1 bg-gray-100 dark:bg-white/10 px-1.5 py-1 rounded">
                                    <span className="text-gray-500 text-[10px]">Dev:</span>
                                    <input
                                        type="number"
                                        value={settings.trendFinderDev}
                                        onChange={(e) => updateSetting('trendFinderDev', Number(e.target.value))}
                                        className="w-10 bg-transparent text-gray-700 dark:text-gray-300 focus:outline-none focus:text-brand-primary text-[10px]"
                                        min={0.1} max={5.0} step={0.1}
                                    />
                                </div>
                           </div>
                           <div className="flex flex-col gap-1 mt-1">
                                <label className="text-gray-500 text-[10px] font-bold uppercase">Min. Confidence:</label>
                                <select 
                                    className="w-full bg-gray-100 dark:bg-white/10 border border-transparent dark:border-white/5 rounded p-1 text-gray-700 dark:text-gray-200 text-[10px] focus:outline-none focus:border-brand-primary"
                                    value={settings.trendFinderThreshold || 'Strong'}
                                    onChange={(e) => onSettingsChange({ ...settings, trendFinderThreshold: e.target.value })}
                                >
                                    <option className="bg-white dark:bg-[#0B1120]" value="Moderate">Moderate (0.7+)</option>
                                    <option className="bg-white dark:bg-[#0B1120]" value="Moderately Strong">Moderately Strong (0.8+)</option>
                                    <option className="bg-white dark:bg-[#0B1120]" value="Mostly Strong">Mostly Strong (0.9+)</option>
                                    <option className="bg-white dark:bg-[#0B1120]" value="Strong">Strong (0.92+)</option>
                                    <option className="bg-white dark:bg-[#0B1120]" value="Very Strong">Very Strong (0.94+)</option>
                                    <option className="bg-white dark:bg-[#0B1120]" value="Exceptionally Strong">Exceptionally Strong (0.96+)</option>
                                    <option className="bg-white dark:bg-[#0B1120]" value="Ultra Strong">Ultra Strong (0.98+)</option>
                                </select>
                           </div>
                           <div className="flex flex-col gap-2 mt-2 pt-2 border-t dark:border-white/5">
                                <label className="flex items-center cursor-pointer group">
                                    <input
                                        type="checkbox"
                                        checked={settings.enableTrendFinderVolumeFilter}
                                        onChange={() => onSettingsChange({ ...settings, enableTrendFinderVolumeFilter: !settings.enableTrendFinderVolumeFilter })}
                                        className="w-3.5 h-3.5 text-brand-primary bg-gray-100 border-gray-300 rounded focus:ring-brand-primary dark:focus:ring-brand-primary dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                                    />
                                    <span className="ml-2 text-[10px] font-bold text-gray-500 uppercase group-hover:text-brand-primary transition-colors italic">Volume Filter (Confirmation)</span>
                                </label>
                                {settings.enableTrendFinderVolumeFilter && (
                                    <div className="flex items-center justify-between bg-gray-100 dark:bg-white/5 p-1.5 rounded animate-fadeIn">
                                        <span className="text-[10px] text-gray-500">Multiplier:</span>
                                        <input
                                            type="text"
                                            value={multiplierLocal}
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                if (val === '' || /^\d*\.?\d*$/.test(val)) {
                                                    setMultiplierLocal(val);
                                                    const num = parseFloat(val);
                                                    if (!isNaN(num)) {
                                                        onSettingsChange({ ...settings, trendFinderVolumeMultiplier: num });
                                                    }
                                                }
                                            }}
                                            className="w-12 bg-transparent text-gray-700 dark:text-gray-200 focus:outline-none text-[10px] text-right font-mono"
                                            placeholder="1.5"
                                        />
                                    </div>
                                )}
                           </div>
                         </div>
                    </div>
                </div>
            )}
        </div>
    );
};
