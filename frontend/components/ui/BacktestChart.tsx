import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries } from 'lightweight-charts';

interface TradeMarker {
    time: string; // ISO String from backend
    type: 'buy' | 'sell';
    price: number;
}

interface CandleData {
    time: number; // UNIX timestamp
    open: number;
    high: number;
    low: number;
    close: number;
}

interface BacktestChartProps {
    data: CandleData[];
    trades: TradeMarker[];
}

const BacktestChart: React.FC<BacktestChartProps> = ({ data, trades }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        // ১. চার্ট তৈরি
        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: '#1E293B' }, // Dark theme bg
                textColor: '#D9D9D9',
            },
            grid: {
                vertLines: { color: '#334155' },
                horzLines: { color: '#334155' },
            },
            width: chartContainerRef.current.clientWidth,
            height: 400,
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
            }
        });
        chartRef.current = chart;

        // ২. ক্যান্ডেলস্টিক সিরিজ যোগ
        const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#10B981',
            downColor: '#F43F5E',
            borderVisible: false,
            wickUpColor: '#10B981',
            wickDownColor: '#F43F5E',
        });

        // ৩. ডেটা সেট করা (অবশ্যই সর্টেড হতে হবে)
        const sortedData = [...data].sort((a, b) => a.time - b.time);
        candlestickSeries.setData(sortedData as any);

        // ৪. ট্রেড মার্কার বসানো
        const markers = trades.map(trade => {
            const tradeTime = new Date(trade.time).getTime() / 1000;
            return {
                time: tradeTime, // ক্যান্ডেল টাইমের সাথে মিলতে হবে
                position: trade.type === 'buy' ? 'belowBar' : 'aboveBar',
                color: trade.type === 'buy' ? '#10B981' : '#F43F5E',
                shape: trade.type === 'buy' ? 'arrowUp' : 'arrowDown',
                text: trade.type.toUpperCase() + ` @ ${trade.price.toFixed(2)}`,
            };
        });

        // লাইটওয়েট চার্ট টাইম ম্যাচিং নিয়ে একটু সেনসিটিভ। 
        // আমরা ট্রেড টাইমকে নিকটতম ক্যান্ডেলের টাইমে রাউন্ড করছি না, আশা করি ব্যাকটেস্ট একই ক্যান্ডেল টাইম দিবে।
        // সর্ট করে বসানো নিরাপদ।
        const sortedMarkers = markers.sort((a, b) => (a.time as number) - (b.time as number));

        console.log('Candlestick Series:', candlestickSeries);
        console.log('Available methods:', Object.keys(candlestickSeries));
        console.log('Prototype methods:', Object.getOwnPropertyNames(Object.getPrototypeOf(candlestickSeries)));

        if (typeof (candlestickSeries as any).setMarkers === 'function') {
            (candlestickSeries as any).setMarkers(sortedMarkers as any);
        } else {
            console.warn('setMarkers method is missing on candlestickSeries');
        }

        chart.timeScale().fitContent();

        // রেসপন্সিভ করা
        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [data, trades]);

    return (
        <div ref={chartContainerRef} className="w-full h-[400px] rounded-xl overflow-hidden border border-brand-border-dark" />
    );
};

export default BacktestChart;
