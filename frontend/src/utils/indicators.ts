export interface IndicatorDataPoint {
    time: string | number;
    value: number;
}

export interface BollingerBandsDataPoint {
    time: string | number;
    upper: number;
    middle: number;
    lower: number;
}

// Simple Moving Average
export const calculateSMA = (data: { time: any; close: number }[], period: number): IndicatorDataPoint[] => {
    const result: IndicatorDataPoint[] = [];
    for (let i = period - 1; i < data.length; i++) {
        let sum = 0;
        for (let j = 0; j < period; j++) {
            sum += data[i - j].close;
        }
        result.push({ time: data[i].time, value: sum / period });
    }
    return result;
};

// Exponential Moving Average
export const calculateEMA = (data: { time: any; close: number }[], period: number): IndicatorDataPoint[] => {
    const result: IndicatorDataPoint[] = [];
    if (data.length < period) return result;

    const multiplier = 2 / (period + 1);

    // First EMA is SMA
    let sum = 0;
    for (let i = 0; i < period; i++) {
        sum += data[i].close;
    }
    let prevEMA = sum / period;

    result.push({ time: data[period - 1].time, value: prevEMA });

    for (let i = period; i < data.length; i++) {
        const ema = (data[i].close - prevEMA) * multiplier + prevEMA;
        result.push({ time: data[i].time, value: ema });
        prevEMA = ema;
    }

    return result;
};

// Bollinger Bands
// Returns { time, upper, middle, lower }
export const calculateBollingerBands = (data: { time: any; close: number }[], period: number, stdDev: number = 2): BollingerBandsDataPoint[] => {
    const result: BollingerBandsDataPoint[] = [];
    for (let i = period - 1; i < data.length; i++) {
        let sum = 0;
        for (let j = 0; j < period; j++) {
            sum += data[i - j].close;
        }
        const middle = sum / period;

        let varianceSum = 0;
        for (let j = 0; j < period; j++) {
            varianceSum += Math.pow(data[i - j].close - middle, 2);
        }
        const variance = varianceSum / period;
        const sd = Math.sqrt(variance);

        result.push({
            time: data[i].time,
            upper: middle + stdDev * sd,
            middle: middle,
            lower: middle - stdDev * sd
        });
    }
    return result;
};

// Relative Strength Index
export const calculateRSI = (data: { time: any; close: number }[], period: number = 14): IndicatorDataPoint[] => {
    const result: IndicatorDataPoint[] = [];
    if (data.length <= period) return result;

    let upSum = 0;
    let downSum = 0;

    // Calculate initial average gain/loss
    for (let i = 1; i <= period; i++) {
        const diff = data[i].close - data[i - 1].close;
        if (diff > 0) {
            upSum += diff;
        } else {
            downSum -= diff;
        }
    }

    let avgUp = upSum / period;
    let avgDown = downSum / period;

    result.push({
        time: data[period].time,
        value: avgDown === 0 ? 100 : 100 - (100 / (1 + avgUp / avgDown))
    });

    // Wilder's Smoothing
    for (let i = period + 1; i < data.length; i++) {
        const diff = data[i].close - data[i - 1].close;
        let up = 0;
        let down = 0;

        if (diff > 0) {
            up = diff;
        } else {
            down = -diff;
        }

        avgUp = (avgUp * (period - 1) + up) / period;
        avgDown = (avgDown * (period - 1) + down) / period;

        let rsi = 100;
        if (avgDown > 0) {
            rsi = 100 - (100 / (1 + avgUp / avgDown));
        }

        result.push({ time: data[i].time, value: rsi });
    }

    return result;
};

// --- Incremental Updates for Real-time Performance ---

/**
 * Updates EMA for the latest data point without recalculating history
 * @param data The candle data including the latest point
 * @param prevEMA The EMA value of the previous candle
 * @param period EMA period
 */
export const updateEMA = (data: { time: any; close: number }, prevEMA: number, period: number): IndicatorDataPoint => {
    const multiplier = 2 / (period + 1);
    const ema = (data.close - prevEMA) * multiplier + prevEMA;
    return { time: data.time, value: ema };
};

/**
 * Updates Bollinger Bands for the latest data point
 * Note: BB needs some history to calculate standard deviation accurately.
 * For efficiency, we only use the last 'period' candles.
 */
export const updateBollingerBands = (dataSlice: { time: any; close: number }[], period: number, stdDev: number = 2): BollingerBandsDataPoint => {
    const lastPoint = dataSlice[dataSlice.length - 1];
    let sum = 0;
    for (let i = 0; i < dataSlice.length; i++) {
        sum += dataSlice[i].close;
    }
    const middle = sum / dataSlice.length;

    let varianceSum = 0;
    for (let i = 0; i < dataSlice.length; i++) {
        varianceSum += Math.pow(dataSlice[i].close - middle, 2);
    }
    const variance = varianceSum / dataSlice.length;
    const sd = Math.sqrt(variance);

    return {
        time: lastPoint.time,
        upper: middle + stdDev * sd,
        middle: middle,
        lower: middle - stdDev * sd
    };
};

/**
 * Updates RSI for the latest data point using Wilder's Smoothing
 */
export const updateRSI = (data: { close: number; time: any }, prevClose: number, prevAvgUp: number, prevAvgDown: number, period: number): { rsi: IndicatorDataPoint, avgUp: number, avgDown: number } => {
    const diff = data.close - prevClose;
    let up = 0;
    let down = 0;

    if (diff > 0) {
        up = diff;
    } else {
        down = -diff;
    }

    const avgUp = (prevAvgUp * (period - 1) + up) / period;
    const avgDown = (prevAvgDown * (period - 1) + down) / period;

    let rsiValue = 100;
    if (avgDown > 0) {
        rsiValue = 100 - (100 / (1 + avgUp / avgDown));
    }

    return {
        rsi: { time: data.time, value: rsiValue },
        avgUp,
        avgDown
    };
};

/**
 * Calculates Average True Range (ATR)
 * @param data OHLCV data
 * @param period ATR period
 */
export const calculateATR = (data: { time: any; high: number; low: number; close: number }[], period: number = 14): IndicatorDataPoint[] => {
    const result: IndicatorDataPoint[] = [];
    if (data.length <= period) return result;

    const trs: number[] = [];
    for (let i = 1; i < data.length; i++) {
        const h = data[i].high;
        const l = data[i].low;
        const pc = data[i - 1].close;
        const tr = Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc));
        trs.push(tr);
    }

    // First ATR is SMA of TRs
    let trSum = 0;
    for (let i = 0; i < period; i++) {
        trSum += trs[i];
    }
    let prevATR = trSum / period;
    result.push({ time: data[period].time, value: prevATR });

    // Subsequent ATRs use smoothing
    for (let i = period; i < trs.length; i++) {
        const atr = (prevATR * (period - 1) + trs[i]) / period;
        result.push({ time: data[i + 1].time, value: atr });
        prevATR = atr;
    }

    return result;
};

// --- Ichimoku Cloud ---
export interface IchimokuDataPoint {
    time: string | number;
    tenkan: number | null;
    kijun: number | null;
    senkouA: number | null;
    senkouB: number | null;
    chikou: number | null;
}

export const calculateIchimoku = (
    data: { time: any; high: number; low: number; close: number }[],
    tenkanPeriod: number = 9,
    kijunPeriod: number = 26,
    senkouBPeriod: number = 52,
    displacement: number = 26
): IchimokuDataPoint[] => {
    const result: IchimokuDataPoint[] = [];
    if (data.length < Math.min(tenkanPeriod, kijunPeriod, senkouBPeriod)) return result;

    const getExtremes = (slice: { high: number; low: number }[]) => {
        let h = -Infinity;
        let l = Infinity;
        for (const p of slice) {
            if (p.high > h) h = p.high;
            if (p.low < l) l = p.low;
        }
        return (h + l) / 2;
    };

    for (let i = 0; i < data.length; i++) {
        const tenkan = i >= tenkanPeriod - 1 ? getExtremes(data.slice(i - tenkanPeriod + 1, i + 1)) : null;
        const kijun = i >= kijunPeriod - 1 ? getExtremes(data.slice(i - kijunPeriod + 1, i + 1)) : null;
        const senkouB = i >= senkouBPeriod - 1 ? getExtremes(data.slice(i - senkouBPeriod + 1, i + 1)) : null;
        
        let senkouA = null;
        if (tenkan !== null && kijun !== null) {
            senkouA = (tenkan + kijun) / 2;
        }

        let chikou = null;
        if (i + displacement < data.length) {
            chikou = data[i + displacement].close;
        }

        result.push({
            time: data[i].time,
            tenkan,
            kijun,
            senkouA, 
            senkouB,
            chikou
        });
    }

    return result;
};
