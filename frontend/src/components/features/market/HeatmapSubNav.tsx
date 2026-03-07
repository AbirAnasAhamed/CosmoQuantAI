import React from 'react';
import { Activity, Settings, AlignLeft } from 'lucide-react';

interface HeatmapSubNavProps {
    activeTab: 'heatmap' | 'bot_settings' | 'bot_logs';
    onChange: (tab: 'heatmap' | 'bot_settings' | 'bot_logs') => void;
}

export const HeatmapSubNav: React.FC<HeatmapSubNavProps> = ({ activeTab, onChange }) => {
    return (
        <div className="flex bg-white dark:bg-[#0B1120] border-b border-gray-200 dark:border-white/10 px-4 py-2">
            <div className="flex space-x-1 bg-gray-100 dark:bg-black/30 p-1 rounded-lg">
                <button
                    onClick={() => onChange('heatmap')}
                    className={`flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${activeTab === 'heatmap'
                            ? 'bg-blue-600/10 text-brand-primary border border-blue-500/20 shadow-sm'
                            : 'text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-black/10'
                        }`}
                >
                    <Activity size={16} />
                    <span>Heatmap View</span>
                </button>
                <button
                    onClick={() => onChange('bot_settings')}
                    className={`flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${activeTab === 'bot_settings'
                            ? 'bg-green-600/10 text-green-500 border border-green-500/20 shadow-sm'
                            : 'text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-black/10'
                        }`}
                >
                    <Settings size={16} />
                    <span>Bot Options</span>
                </button>
                <button
                    onClick={() => onChange('bot_logs')}
                    className={`flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${activeTab === 'bot_logs'
                            ? 'bg-purple-600/10 text-purple-400 border border-purple-500/20 shadow-sm'
                            : 'text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-black/10'
                        }`}
                >
                    <AlignLeft size={16} />
                    <span>Bot Logs</span>
                </button>
            </div>
        </div>
    );
};
