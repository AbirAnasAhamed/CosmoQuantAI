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

// --- Adaptive Trend Finder (Log) ---
export interface TrendFinderDataPoint {
    time: string | number;
    value: number; // Midline value
    upper: number;
    lower: number;
}

export interface TrendFinderResult {
    period: number;
    stdDev: number;
    pearsonR: number;
    slope: number;
    intercept: number;
    confidence: string;
    points: TrendFinderDataPoint[];
    trendDirection: 'bullish' | 'bearish' | 'neutral';
}

export const getTrendConfidence = (pearsonR: number): string => {
    const p = Math.abs(pearsonR);
    if (p < 0.2) return 'Extremely Weak';
    if (p < 0.3) return 'Very Weak';
    if (p < 0.4) return 'Weak';
    if (p < 0.5) return 'Mostly Weak';
    if (p < 0.6) return 'Somewhat Weak';
    if (p < 0.7) return 'Moderately Weak';
    if (p < 0.8) return 'Moderate';
    if (p < 0.9) return 'Moderately Strong';
    if (p < 0.92) return 'Mostly Strong';
    if (p < 0.94) return 'Strong';
    if (p < 0.96) return 'Very Strong';
    if (p < 0.98) return 'Exceptionally Strong';
    return 'Ultra Strong';
};

export const calculateAdaptiveTrendFinder = (
    data: { time: any; close: number }[],
    lookback: number = 200,
    devMultiplier: number = 2.0
): TrendFinderResult | null => {
    const periods = [lookback];
    
    if (data.length < 2) return null; // Need minimum data

    let bestPeriod = periods[0];
    let bestPearsonR = -1; // We compare absolute values, so start negative
    let bestStdDev = 0;
    let MathLogStr: { [key: number]: number } = {};
    
    // Cache logarithms to speed up calculation
    for (let i = 0; i < data.length; i++) {
        MathLogStr[i] = Math.log(data[i].close);
    }

    let detectedSlope = 0;
    let detectedIntercept = 0;
    let actualPearsonRSigned = 0;

    for (const length of periods) {
        if (data.length < length) continue;
        
        let sumX = 0;
        let sumXX = 0;
        let sumYX = 0;
        let sumY = 0;
        
        // PineScript backward loop logic: i=1 to length, logSource[i-1]
        // This means it takes the last `length` items from the array, in reverse order
        for (let i = 1; i <= length; i++) {
            const idx = data.length - i;
            const lSrc = MathLogStr[idx];
            sumX += i;
            sumXX += i * i;
            sumYX += i * lSrc;
            sumY += lSrc;
        }

        const denominator = (length * sumXX - sumX * sumX);
        const slope = denominator === 0 ? 0 : (length * sumYX - sumX * sumY) / denominator;
        const average = sumY / length;
        const intercept = average - slope * sumX / length + slope;
        
        const period_1 = length - 1;
        const regres = intercept + slope * period_1 * 0.5;
        let sumSlp = intercept;
        
        let sumDxx = 0;
        let sumDyy = 0;
        let sumDyx = 0;
        let sumDev = 0;
        
        for (let i = 0; i <= period_1; i++) {
            const idx = data.length - 1 - i;
            let lSrc = MathLogStr[idx];
            const dxt = lSrc - average;
            const dyt = sumSlp - regres;
            
            lSrc = lSrc - sumSlp;
            sumSlp += slope;
            
            sumDxx += dxt * dxt;
            sumDyy += dyt * dyt;
            sumDyx += dxt * dyt;
            sumDev += lSrc * lSrc;
        }
        
        const unStdDev = Math.sqrt(sumDev / period_1);
        const divisor = sumDxx * sumDyy;
        const pearsonR = divisor === 0 ? 0 : sumDyx / Math.sqrt(divisor);
        
        // Find the highest absolute pearsonR
        if (bestPearsonR === -1 || Math.abs(pearsonR) > Math.abs(bestPearsonR)) {
            bestPearsonR = Math.abs(pearsonR);
            actualPearsonRSigned = pearsonR;
            bestPeriod = length;
            bestStdDev = unStdDev;
            detectedSlope = slope;
            detectedIntercept = intercept;
        }
    }

    if (bestPearsonR === -1 || bestStdDev === 0) return null;

    // Generate the projection points
    const points: TrendFinderDataPoint[] = [];
    const pointsLength = Math.min(bestPeriod, data.length);
    
    // slope > 0 in PineScript means DOWN trend over time since index 0 is latest and i grows backwards
    // So if slope is positive, older bars had higher log prices, so trend is DOWN
    
    for (let i = 0; i < pointsLength; i++) {
        const idx = data.length - 1 - i;
        // Pine formula: line at idx i is `intercept + slope * i`
        const midLog = detectedIntercept + detectedSlope * i;
        const midVal = Math.exp(midLog);
        
        const upperVal = midVal * Math.exp(devMultiplier * bestStdDev);
        const lowerVal = midVal / Math.exp(devMultiplier * bestStdDev);
        
        points.push({
            time: data[idx].time,
            value: midVal,
            upper: upperVal,
            lower: lowerVal
        });
    }
    
    // We generated points from latest (index 0) to oldest. Reverse to match data order.
    points.reverse();

    return {
        period: bestPeriod,
        stdDev: bestStdDev,
        pearsonR: actualPearsonRSigned,
        slope: detectedSlope,
        intercept: detectedIntercept,
        confidence: getTrendConfidence(bestPearsonR),
        points,
        trendDirection: detectedSlope > 0 ? 'bearish' : detectedSlope < 0 ? 'bullish' : 'neutral'
    };
};
