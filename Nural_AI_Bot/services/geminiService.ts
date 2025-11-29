import { GoogleGenAI, Type } from "@google/genai";
import { AiAnalysisResult, IndicatorData } from "../types";

// Initialize Gemini Client
const apiKey = process.env.API_KEY || '';
const ai = new GoogleGenAI({ apiKey });

export const analyzeMarketData = async (
  symbol: string,
  currentPrice: number,
  indicators: IndicatorData
): Promise<AiAnalysisResult> => {
  if (!apiKey) {
    return {
      decision: 'HOLD',
      confidence: 0,
      reasoning: "API Key missing. Cannot perform AI analysis.",
      riskAssessment: "N/A"
    };
  }

  const prompt = `
    You are OmniTrade AI Agent C (Decision Maker). 
    
    Context:
    Symbol: ${symbol}
    Current Price: ${currentPrice}
    Technical Indicators:
    - RSI (14): ${indicators.rsi.toFixed(2)}
    - MACD: ${indicators.macd.toFixed(4)}
    - Signal Line: ${indicators.signal.toFixed(4)}
    - MA7: ${indicators.ma7.toFixed(2)}
    - MA25: ${indicators.ma25.toFixed(2)}

    Task:
    1. Analyze the technical data and simulate a sentiment analysis (Agent B) for this asset. 
    2. Determine whether to BUY, SELL, or HOLD.
    3. Calculate a Confidence score (0-100).
    4. Provide a Detailed Risk Assessment:
       - Evaluate Volatility (e.g., "High volatility expected due to MACD divergence").
       - Identify potential "Fakeouts" or "Liquidity Traps".
       - Recommend Stop-Loss tightness (e.g., "Use wide stops due to chop" or "Tight stops required").
    5. Generate SHAP (Explainable AI) Values:
       - Identify the top 3 factors driving your decision.
       - Assign an impact score (-1.0 to +1.0) for each (Negative = Bearish, Positive = Bullish).
    
    Response Format: JSON
  `;

  try {
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            decision: { type: Type.STRING, enum: ["BUY", "SELL", "HOLD"] },
            confidence: { type: Type.NUMBER },
            reasoning: { type: Type.STRING },
            riskAssessment: { type: Type.STRING },
            shapValues: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  feature: { type: Type.STRING },
                  impact: { type: Type.NUMBER }
                }
              }
            }
          },
          required: ["decision", "confidence", "reasoning", "riskAssessment", "shapValues"]
        }
      }
    });

    const text = response.text;
    if (!text) throw new Error("Empty response from AI");

    const result = JSON.parse(text) as AiAnalysisResult;
    return result;

  } catch (error) {
    console.error("Gemini Analysis Error:", error);
    return {
      decision: 'HOLD',
      confidence: 0,
      reasoning: "AI Analysis failed due to network or API error.",
      riskAssessment: "High Uncertainty - System Offline"
    };
  }
};