import React, { useEffect, useState } from 'react';
import {
    ResponsiveContainer,
    ComposedChart,
    Scatter,
    Line,
    XAxis,
    YAxis,
    ZAxis,
    Tooltip,
    Cell,
    CartesianGrid
} from 'recharts';
import { useTheme } from '@/context/ThemeContext';
import { LiquidationEvent } from '@/hooks/useLiquidationWebSocket';

interface LiquidationBubbleChartProps {
    data: LiquidationEvent[];
    activePair: string;
}

interface CandleData {
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
}

const LiquidationBubbleChart: React.FC<LiquidationBubbleChartProps> = ({ data, activePair }) => {
    const { theme } = useTheme();
    const [candles, setCandles] = useState<CandleData[]>([]);

    useEffect(() => {
        const fetchCandles = async () => {
            try {
                // Fetch last 50 candles (15m interval) from Binance
                // Fetch last 50 candles (15m interval) from Backend Proxy
                const symbol = activePair.replace('/', '');
                const response = await fetch(`http://localhost:8000/api/v1/liquidation/candles?symbol=${symbol}&interval=15m&limit=50`);
                const formatted: CandleData[] = await response.json();
                setCandles(formatted);
            } catch (error) {
                console.error("Failed to fetch candles", error);
            }
        };

        if (activePair) {
            fetchCandles();
            // Poll for fresh candles every 15s? Or just once on mount/change. 
            // For now, once is fine as liquidations are the live part.
        }
    }, [activePair]);

    // Prepare chart data
    // We need to combine or layer data. 
    // Recharts ComposedChart can handle multiple data sources if we pass them to individual components?
    // Actually, it's better to use specific data props for each series.
    // XAxis domain will be properly calculated if we include both datasets?
    // We will supply `candles` to ComposedChart (to set the main axis) and `data` to Scatter.

    const bubbleData = data.map((event) => ({
        ...event,
        time: event.timestamp || Date.now(), // Map timestamp to 'time' to match XAxis dataKey
        x: event.timestamp || Date.now(),    // Keep 'x' just in case
        y: event.price,
        z: event.amount
    }));

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            // Determine if we are hovering a bubble or a candle/line point
            const dataPoint = payload[0].payload;

            // If it's a bubble (has 'type' and 'amount')
            if (dataPoint.type) {
                return (
                    <div className={`p-2 border rounded shadow-lg text-xs font-mono z-50 ${theme === 'dark' ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white border-gray-200 text-slate-900'}`}>
                        <p className="font-bold mb-1 border-b border-gray-600 pb-1">{dataPoint.type} Liquidation</p>
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            <span className="text-gray-400">Price:</span>
                            <span>${dataPoint.price.toLocaleString()}</span>
                            <span className="text-gray-400">Amount:</span>
                            <span>${(dataPoint.amount || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                            <span className="text-gray-400">Time:</span>
                            <span>{dataPoint.time}</span>
                        </div>
                    </div>
                );
            }
            // If it's a candle/line point
            return (
                <div className={`p-2 border rounded shadow-lg text-xs font-mono z-50 ${theme === 'dark' ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white border-gray-200 text-slate-900'}`}>
                    <p className="font-bold mb-1 border-b border-gray-600 pb-1">Price Action</p>
                    <div>Price: ${dataPoint.close?.toLocaleString()}</div>
                    <div className="text-[10px] text-gray-500">{new Date(dataPoint.time).toLocaleTimeString()}</div>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="w-full h-full min-h-[200px]" style={{ width: '100%', height: '100%' }}>
            <ResponsiveContainer width="100%" height="100%" debounce={50}>
                <ComposedChart data={candles} margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={theme === 'dark' ? '#334155' : '#e2e8f0'} opacity={0.2} />

                    <XAxis
                        type="number"
                        dataKey="time"
                        name="Time"
                        domain={['dataMin', 'dataMax']} // Should include both if Scatters are recognized
                        tickFormatter={(unixTime) => new Date(unixTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        tick={{ fontSize: 10, fill: theme === 'dark' ? '#94a3b8' : '#64748b' }}
                        stroke={theme === 'dark' ? '#334155' : '#cbd5e1'}
                        allowDataOverflow={false}
                    />
                    <YAxis
                        type="number"
                        dataKey="close"
                        name="Price"
                        domain={['auto', 'auto']}
                        tick={{ fontSize: 10, fill: theme === 'dark' ? '#94a3b8' : '#64748b' }}
                        tickFormatter={(value) => `$${value.toLocaleString()}`}
                        width={60}
                        orientation="right"
                        stroke={theme === 'dark' ? '#334155' : '#cbd5e1'}
                    />
                    <ZAxis type="number" dataKey="z" range={[50, 600]} name="Amount" />

                    <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />

                    {/* Price Line (Context) */}
                    <Line
                        type="monotone"
                        dataKey="close"
                        stroke="#64748b"
                        strokeWidth={1}
                        dot={false}
                        activeDot={false}
                        opacity={0.5}
                        isAnimationActive={false}
                    />

                    {/* Liquidation Bubbles */}
                    <Scatter
                        name="Liquidations"
                        data={bubbleData}
                        fill="#8884d8"
                        isAnimationActive={false}
                    >
                        {bubbleData.map((entry, index) => (
                            <Cell
                                key={`cell-${index}`}
                                fill={entry.type === 'Long' ? '#F43F5E' : '#10B981'}
                                fillOpacity={0.6}
                                stroke={entry.type === 'Long' ? '#F43F5E' : '#10B981'}
                                strokeWidth={1}
                            />
                        ))}
                    </Scatter>
                </ComposedChart>
            </ResponsiveContainer>
        </div>
    );
};

export default LiquidationBubbleChart;
