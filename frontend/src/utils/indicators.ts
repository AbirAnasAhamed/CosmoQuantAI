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
