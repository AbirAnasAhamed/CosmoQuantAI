from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.news_service import news_service
from app.services.ai_service import ai_service
import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta

router = APIRouter()

# --- Request Models ---
class SummaryRequest(BaseModel):
    headlines: str
    asset: str
    provider: str = "gemini"

@router.get("/news")
async def get_sentiment_news():
    return await news_service.fetch_news()

@router.get("/fear-greed")
async def get_fear_greed():
    return await news_service.fetch_fear_greed_index()

# ✅ মিসিং /summary এন্ডপয়েন্ট যোগ করা হয়েছে
@router.post("/summary")
async def generate_sentiment_summary(request: SummaryRequest):
    try:
        summary = ai_service.generate_market_sentiment_summary(
            headlines=request.headlines,
            asset=request.asset,
            provider=request.provider
        )
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ মিসিং /narratives এন্ডপয়েন্ট যোগ করা হয়েছে
@router.get("/narratives")
async def get_market_narratives():
    try:
        # প্রথমে নিউজ ফেচ করা হবে
        news_items = await news_service.fetch_news()
        
        # নিউজ থেকে হেডলাইনগুলো আলাদা করে স্ট্রিং বানানো
        headlines = " ".join([item['content'] for item in news_items[:20]]) # টপ ২০টি নিউজ
        
        if not headlines:
            return {"word_cloud": [], "narratives": ["No sufficient data to generate narratives."]}

        # AI সার্ভিস কল করা
        result = ai_service.generate_market_narratives(headlines=headlines)
        return result
    except Exception as e:
        print(f"Narrative Error: {e}")
        return {"word_cloud": [], "narratives": ["Error generating narratives."]}

@router.get("/correlation")
async def get_sentiment_correlation(symbol: str = "BTC/USDT", days: int = 7):
    try:
        exchange = ccxt.binance()
        timeframe = '1h'
        limit = 24 * days
        
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        await exchange.close()

        if not ohlcv:
            return []

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        sentiment_df = await news_service.fetch_historical_sentiment(days=days)
        merged_df = df.join(sentiment_df, how='left')
        
        merged_df['score'] = merged_df['score'].ffill().fillna(0)
        merged_df['retail_score'] = merged_df['score'] * 0.7 + merged_df['close'].pct_change().rolling(5).mean() * 10
        merged_df['retail_score'] = merged_df['retail_score'].fillna(0)

        merged_df.ta.cmf(append=True)
        cmf_col = merged_df.columns[-1]
        merged_df['smart_money_score'] = merged_df[cmf_col].rolling(3).mean() * 5
        merged_df['smart_money_score'] = merged_df['smart_money_score'].clip(-1, 1).fillna(0)

        merged_df['momentum'] = merged_df['close'].diff().fillna(0)
        merged_df['social_volume'] = (merged_df['volume'] * merged_df['high'].diff().abs() / 1000).fillna(100).astype(int)

        merged_df = merged_df.fillna(0)
        merged_df = merged_df.replace({np.nan: 0})

        chart_data = []
        for ts, row in merged_df.iterrows():
            smart_val = row['smart_money_score'] if not pd.isna(row['smart_money_score']) else 0
            retail_val = row['retail_score'] if not pd.isna(row['retail_score']) else 0
            
            chart_data.append({
                "time": ts.isoformat(),
                "price": row['close'],
                "score": round(row['score'], 2),
                "retail_score": round(retail_val, 2),        
                "smart_money_score": round(smart_val, 2), 
                "momentum": round(row['momentum'], 2), 
                "social_volume": int(row['social_volume']),
                "volume": row['volume'],
                "divergence": round(smart_val - retail_val, 2)
            })

        return chart_data

    except Exception as e:
        print(f"Correlation API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/heatmap")
async def get_sentiment_heatmap():
    return [
        {"name": "BTC", "symbol": "BTC", "marketCap": 800000000000, "sentimentScore": 0.5},
        {"name": "ETH", "symbol": "ETH", "marketCap": 400000000000, "sentimentScore": 0.3},
        {"name": "BNB", "symbol": "BNB", "marketCap": 90000000000, "sentimentScore": 0.1},
        {"name": "SOL", "symbol": "SOL", "marketCap": 60000000000, "sentimentScore": 0.8},
        {"name": "XRP", "symbol": "XRP", "marketCap": 30000000000, "sentimentScore": -0.2},
        {"name": "ADA", "symbol": "ADA", "marketCap": 20000000000, "sentimentScore": 0.0},
        {"name": "DOGE", "symbol": "DOGE", "marketCap": 12000000000, "sentimentScore": 0.4},
        {"name": "AVAX", "symbol": "AVAX", "marketCap": 11000000000, "sentimentScore": 0.2},
    ]
