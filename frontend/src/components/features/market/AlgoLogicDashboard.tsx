import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { GodModeState } from '../../../hooks/useGodModeData';

interface AlgoLogicDashboardProps {
    data: GodModeState | null;
    numZones?: number;
    onClose: () => void;
}

export const AlgoLogicDashboard: React.FC<AlgoLogicDashboardProps> = ({ data, numZones = 3, onClose }) => {
    const [position, setPosition] = useState({ x: 20, y: 100 });
    const [isDragging, setIsDragging] = useState(false);
    const dragRef = useRef<{ startX: number, startY: number }>({ startX: 0, startY: 0 });

    const handleMouseDown = (e: React.MouseEvent) => {
        setIsDragging(true);
        dragRef.current = {
            startX: e.clientX - position.x,
            startY: e.clientY - position.y
        };
    };

    const handleMouseMove = (e: MouseEvent) => {
        if (!isDragging) return;
        setPosition({
            x: e.clientX - dragRef.current.startX,
            y: e.clientY - dragRef.current.startY
        });
    };

    const handleMouseUp = () => {
        setIsDragging(false);
    };

    useEffect(() => {
        if (isDragging) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
        } else {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        }
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging]);

    if (!data) return null;

    const {
        ema_red_force = 0,
        ema_green_force = 0,
        red_ratio = 50,
        green_ratio = 50,
        total_short_vol = 0,
        total_long_vol = 0,
        funding_rate = 0,
        current_direction = 'Neutral'
    } = data;

    // Formatting helpers
    const formatVol = (v: number) => v > 1000000 ? (v / 1000000).toFixed(2) + 'M' : v > 1000 ? (v / 1000).toFixed(1) + 'k' : v.toFixed(1);
    
    // Status Logic
    const isUp = current_direction === 'UP';
    const isDown = current_direction === 'DOWN';
    const statusColor = isUp ? 'text-green-400' : isDown ? 'text-red-400' : 'text-gray-400';
    const statusBg = isUp ? 'bg-green-500/20 border-green-500/30' : isDown ? 'bg-red-500/20 border-red-500/30' : 'bg-gray-500/20 border-gray-500/30';

    // Volume progress bar logic
    const totalVol = total_short_vol + total_long_vol;
    const shortVolPct = totalVol > 0 ? (total_short_vol / totalVol) * 100 : 50;
    const longVolPct = totalVol > 0 ? (total_long_vol / totalVol) * 100 : 50;

    const dashboardElement = (
        <div 
            style={{ left: position.x, top: position.y }}
            className="absolute z-50 w-72 rounded-xl backdrop-blur-md bg-[#0F172A]/80 border border-white/10 shadow-2xl overflow-hidden font-sans text-sm select-none"
        >
            {/* Header / Drag Handle */}
            <div 
                onMouseDown={handleMouseDown}
                className="flex items-center justify-between px-3 py-2 bg-white/5 border-b border-white/10 cursor-grab active:cursor-grabbing"
            >
                <div className="flex items-center gap-2">
                    <span className="text-brand-primary">🤖</span>
                    <h3 className="font-bold text-gray-200 text-xs">ALGO TARGET DASHBOARD</h3>
                </div>
                <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                    ✕
                </button>
            </div>

            <div className="p-4 space-y-4">
                
                {/* 1. Status Panel */}
                <div className={`p-3 rounded-lg border ${statusBg} flex flex-col items-center justify-center text-center`}>
                    <span className="text-xs text-gray-300 mb-1 font-medium">Live Status</span>
                    <div className={`text-lg font-bold uppercase tracking-wider ${statusColor}`}>
                        {current_direction ? `HUNTING ${current_direction}` : 'NEUTRAL'}
                    </div>
                </div>

                {/* 2. Funding Rate Sentiment */}
                <div className="bg-white/5 rounded-lg p-3">
                    <div className="flex justify-between items-center mb-1">
                        <span className="text-xs text-gray-400">Retail Sentiment (Funding)</span>
                        <span className={`text-xs font-bold ${funding_rate > 0 ? 'text-green-400' : funding_rate < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                            {funding_rate > 0 ? 'Long Heavy' : funding_rate < 0 ? 'Short Heavy' : 'Neutral'}
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-xs font-mono text-gray-300">{(funding_rate * 100).toFixed(4)}%</span>
                        <span className="text-[10px] text-gray-500">
                            {funding_rate > 0 ? 'Bias: Boosting Downside' : funding_rate < 0 ? 'Bias: Boosting Upside' : ''}
                        </span>
                    </div>
                </div>

                {/* 3. Real-time Liquidity Volume Fight */}
                <div>
                    <div className="flex justify-between items-center mb-1">
                        <span className="text-xs text-red-400 font-bold">Short Liq (Above)</span>
                        <span className="text-xs text-green-400 font-bold">Long Liq (Below)</span>
                    </div>
                    
                    {/* Volume Bar */}
                    <div className="h-3 w-full bg-gray-800 rounded-full overflow-hidden flex shadow-inner">
                        <div style={{ width: `${shortVolPct}%` }} className="h-full bg-gradient-to-r from-red-600 to-red-400 transition-all duration-300 relative">
                            {shortVolPct > 50 && <div className="absolute inset-0 bg-white/20 animate-pulse"></div>}
                        </div>
                        <div style={{ width: `${longVolPct}%` }} className="h-full bg-gradient-to-l from-green-600 to-green-400 transition-all duration-300 relative">
                            {longVolPct > 50 && <div className="absolute inset-0 bg-white/20 animate-pulse"></div>}
                        </div>
                    </div>
                    
                    <div className="flex justify-between items-center mt-1">
                        <span className="text-xs text-gray-300 font-mono">{formatVol(total_short_vol)}</span>
                        <span className="text-xs text-gray-300 font-mono">{formatVol(total_long_vol)}</span>
                    </div>
                </div>

                {/* 4. Magnetic EMA Force */}
                <div className="bg-white/5 rounded-lg p-3 grid grid-cols-2 gap-2">
                    <div className="flex flex-col">
                        <span className="text-[10px] text-gray-500">EMA Upward Force</span>
                        <span className="text-sm text-red-400 font-bold font-mono">{ema_red_force.toFixed(1)} <span className="text-xs font-normal opacity-70">({red_ratio.toFixed(1)}%)</span></span>
                    </div>
                    <div className="flex flex-col text-right">
                        <span className="text-[10px] text-gray-500">EMA Downward Force</span>
                        <span className="text-sm text-green-400 font-bold font-mono">{ema_green_force.toFixed(1)} <span className="text-xs font-normal opacity-70">({green_ratio.toFixed(1)}%)</span></span>
                    </div>
                </div>
                
            </div>
        </div>
    );

    // Render into document.body using a React Portal so it escapes all parent container overflow:hidden restrictions
    return typeof window !== 'undefined' ? createPortal(dashboardElement, document.body) : null;
};
