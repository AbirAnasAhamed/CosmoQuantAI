import React from 'react';

export interface TimeframeSelectorProps {
    interval: string;
    onIntervalChange: (newInterval: string) => void;
}

const INTERVAL_LIST = [
    '1m',
    '5m',
    '15m',
    '1h',
    '4h'
];

export const TimeframeSelector: React.FC<TimeframeSelectorProps> = ({ interval, onIntervalChange }) => {
    return (
        <div className="flex bg-gray-100 dark:bg-white/5 rounded p-1 shadow-sm border border-gray-200 dark:border-white/10">
            {INTERVAL_LIST.map((int) => (
                <button
                    key={int}
                    onClick={() => onIntervalChange(int)}
                    className={`
                        px-3 py-1 text-xs font-mono font-medium rounded transition-all duration-200
                        ${interval === int
                            ? 'bg-white dark:bg-[#0B1120] text-brand-primary shadow-sm ring-1 ring-gray-200 dark:ring-white/10'
                            : 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-300 hover:bg-black/5 dark:hover:bg-white/5'
                        }
                    `}
                >
                    {int}
                </button>
            ))}
        </div>
    );
};
