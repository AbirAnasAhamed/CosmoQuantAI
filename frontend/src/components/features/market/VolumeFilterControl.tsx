import React, { useState, useEffect } from 'react';

interface VolumeFilterControlProps {
    threshold: number;
    onThresholdChange: (value: number) => void;
}

const formatSize = (s: number) => {
    if (isNaN(s)) return '0';
    if (s >= 1_000_000_000) return parseFloat((s / 1_000_000_000).toFixed(2)) + 'B';
    if (s >= 1_000_000) return parseFloat((s / 1_000_000).toFixed(2)) + 'M';
    if (s >= 1_000) return parseFloat((s / 1_000).toFixed(2)) + 'k';
    return parseFloat(s.toFixed(2)).toString();
};

const parseSize = (val: string): number => {
    if (!val) return 0;
    const str = val.toString().trim().toLowerCase();
    const numMatch = str.match(/[\d.]+/);
    if (!numMatch) return 0;
    let num = parseFloat(numMatch[0]);
    
    if (str.endsWith('b')) num *= 1_000_000_000;
    else if (str.endsWith('m')) num *= 1_000_000;
    else if (str.endsWith('k')) num *= 1_000;
    
    return isNaN(num) ? 0 : num;
};

export const VolumeFilterControl: React.FC<VolumeFilterControlProps> = ({ threshold, onThresholdChange }) => {
    const min = 1000;
    const max = 100000000;
    const [inputValue, setInputValue] = useState<string>(formatSize(threshold));

    // Sync external threshold changes (like from slider interactions) into the input box
    useEffect(() => {
        setInputValue(formatSize(threshold));
    }, [threshold]);

    // Logarithmic slider mapping for better UX across huge range
    const valueToSlider = (val: number) => {
        if (val <= min) return 0;
        if (val >= max) return 100;
        return 100 * Math.log(val / min) / Math.log(max / min);
    };

    const sliderToValue = (slider: number) => {
        if (slider <= 0) return min;
        if (slider >= 100) return max;
        const raw = min * Math.pow(max / min, slider / 100);
        if (raw >= 1000000) return Math.round(raw / 100000) * 100000;
        if (raw >= 1000) return Math.round(raw / 1000) * 1000;
        return raw;
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setInputValue(e.target.value);
    };

    const handleInputBlur = () => {
        const parsed = parseSize(inputValue);
        if (parsed >= 0) {
            onThresholdChange(parsed);
            setInputValue(formatSize(parsed));
        } else {
            // Revert on invalid input
            setInputValue(formatSize(threshold));
        }
    };

    const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            handleInputBlur();
        }
    };

    return (
        <div className="flex items-center gap-3 bg-gray-100 dark:bg-white/5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-white/10">
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 whitespace-nowrap">
                Min Vol:
            </span>
            <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={valueToSlider(threshold)}
                onChange={(e) => onThresholdChange(sliderToValue(parseFloat(e.target.value)))}
                className="w-24 h-1.5 bg-gray-300 dark:bg-gray-600 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <input
                type="text"
                value={inputValue}
                onChange={handleInputChange}
                onBlur={handleInputBlur}
                onKeyDown={handleInputKeyDown}
                className="w-20 bg-transparent text-sm font-mono font-bold text-gray-800 dark:text-blue-400 outline-none border-b border-transparent focus:border-brand-primary transition-colors text-right"
                placeholder="1000"
            />
        </div>
    );
};
