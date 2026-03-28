import { create } from 'zustand';
import { IndicatorSettings } from '@/components/features/market/IndicatorSelector';

interface BotState {
    activeWallHunterId: number | null;
    setActiveWallHunterId: (id: number | null) => void;
    indicatorSettings: IndicatorSettings;
    setIndicatorSettings: (settings: IndicatorSettings) => void;
}

export const useBotStore = create<BotState>((set) => ({
    activeWallHunterId: null,
    setActiveWallHunterId: (id) => set({ activeWallHunterId: id }),
    indicatorSettings: {
        showEMA: false,
        showBB: true,
        showRSI: false,
        showVolume: true,
        showAutoFibo: false,
        showIchimoku: false,
        showTrendFinder: false,
        emaPeriod: 20,
        bbPeriod: 20,
        bbStdDev: 2,
        rsiPeriod: 14,
        autoFiboLookback: 200,
        tenkanPeriod: 9,
        kijunPeriod: 26,
        senkouBPeriod: 52,
        displacement: 26,
        trendFinderLookback: 200,
        trendFinderDev: 2.0,
    },
    setIndicatorSettings: (settings) => set({ indicatorSettings: settings }),
}));
