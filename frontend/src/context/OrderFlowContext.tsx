import React, { createContext, useContext, useState, ReactNode } from 'react';
import { IndicatorSettings } from '@/components/features/market/IndicatorSelector';

interface OrderFlowContextProps {
    activeTab: 'heatmap' | 'bot_settings' | 'bot_logs';
    setActiveTab: (tab: 'heatmap' | 'bot_settings' | 'bot_logs') => void;
    activeWallHunterId: number | null;
    setActiveWallHunterId: (id: number | null) => void;
    exchange: string;
    setExchange: (ex: string) => void;
    symbol: string;
    setSymbol: (sym: string) => void;
    interval: string;
    setInterval: (intv: string) => void;
    showFootprint: boolean;
    setShowFootprint: (show: boolean) => void;
    indicatorSettings: IndicatorSettings;
    setIndicatorSettings: (settings: IndicatorSettings) => void;
}

const OrderFlowContext = createContext<OrderFlowContextProps | undefined>(undefined);

export const OrderFlowProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [activeTab, setActiveTab] = useState<'heatmap' | 'bot_settings' | 'bot_logs'>('heatmap');
    const [activeWallHunterId, setActiveWallHunterId] = useState<number | null>(null);
    const [exchange, setExchange] = useState('binance');
    const [symbol, setSymbol] = useState('DOGE/USDT');
    const [interval, setInterval] = useState('1m');
    const [showFootprint, setShowFootprint] = useState(false);
    const [indicatorSettings, setIndicatorSettings] = useState<IndicatorSettings>({
        showEMA: false,
        showBB: true,
        showRSI: false,
        showVolume: true,
        showAutoFibo: false,
        showIchimoku: false,
        emaPeriod: 20,
        bbPeriod: 20,
        bbStdDev: 2,
        rsiPeriod: 14,
        autoFiboLookback: 200,
        tenkanPeriod: 9,
        kijunPeriod: 26,
        senkouBPeriod: 52,
        displacement: 26,
    });

    return (
        <OrderFlowContext.Provider
            value={{
                activeTab, setActiveTab,
                activeWallHunterId, setActiveWallHunterId,
                exchange, setExchange,
                symbol, setSymbol,
                interval, setInterval,
                showFootprint, setShowFootprint,
                indicatorSettings, setIndicatorSettings
            }}
        >
            {children}
        </OrderFlowContext.Provider>
    );
};

export const useOrderFlowContext = () => {
    const context = useContext(OrderFlowContext);
    if (!context) {
        throw new Error("useOrderFlowContext must be used within an OrderFlowProvider");
    }
    return context;
};
