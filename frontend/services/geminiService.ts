import { AiAnalysisResult, IndicatorData } from '../types';

export const analyzeMarketData = async (
    symbol: string,
    currentPrice: number,
    indicators: IndicatorData
): Promise<AiAnalysisResult> => {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // Mock logic for demonstration
    const randomDecision = Math.random();
    let decision: 'BUY' | 'SELL' | 'HOLD' = 'HOLD';
    let confidence = 50;

    if (randomDecision > 0.6) {
        decision = 'BUY';
        confidence = Math.floor(Math.random() * 30) + 70;
    } else if (randomDecision < 0.4) {
        decision = 'SELL';
        confidence = Math.floor(Math.random() * 30) + 70;
    } else {
        confidence = Math.floor(Math.random() * 40) + 30;
    }

    return {
        decision,
        confidence,
        reasoning: `Analysis of ${symbol} suggests a ${decision} signal based on current market conditions. RSI and MACD indicators show mixed signals, but overall trend alignment supports this decision.`,
        riskAssessment: 'Moderate risk detected due to recent volatility. Recommended to use tight stop-losses.',
        shapValues: [
            { feature: 'RSI', impact: Math.random() * 0.5 },
            { feature: 'MACD', impact: Math.random() * 0.5 - 0.2 },
            { feature: 'Volume', impact: Math.random() * 0.3 },
            { feature: 'Sentiment', impact: Math.random() * 0.4 },
        ],
    };
};
