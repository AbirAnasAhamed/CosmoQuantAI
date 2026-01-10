from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.news_service import news_service
from app.services.ai_service import ai_service
import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
import random

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
    # Top 30 Crypto Mock Data for Heatmap
    heatmap_data = [
        {"name": "Bitcoin", "symbol": "BTC", "marketCap": 850000000000, "sentimentScore": 0.65},
        {"name": "Ethereum", "symbol": "ETH", "marketCap": 400000000000, "sentimentScore": 0.45},
        {"name": "Binance Coin", "symbol": "BNB", "marketCap": 95000000000, "sentimentScore": 0.15},
        {"name": "Solana", "symbol": "SOL", "marketCap": 78000000000, "sentimentScore": 0.88},
        {"name": "Ripple", "symbol": "XRP", "marketCap": 35000000000, "sentimentScore": -0.35},
        {"name": "Cardano", "symbol": "ADA", "marketCap": 22000000000, "sentimentScore": 0.05},
        {"name": "Avalanche", "symbol": "AVAX", "marketCap": 14000000000, "sentimentScore": 0.32},
        {"name": "Dogecoin", "symbol": "DOGE", "marketCap": 12000000000, "sentimentScore": 0.75},
        {"name": "Polkadot", "symbol": "DOT", "marketCap": 11000000000, "sentimentScore": -0.12},
        {"name": "Chainlink", "symbol": "LINK", "marketCap": 10500000000, "sentimentScore": 0.55},
        {"name": "Tron", "symbol": "TRX", "marketCap": 9800000000, "sentimentScore": 0.20},
        {"name": "Polygon", "symbol": "MATIC", "marketCap": 8500000000, "sentimentScore": -0.05},
        {"name": "Shiba Inu", "symbol": "SHIB", "marketCap": 6500000000, "sentimentScore": 0.60},
        {"name": "Litecoin", "symbol": "LTC", "marketCap": 5500000000, "sentimentScore": 0.10},
        {"name": "Uniswap", "symbol": "UNI", "marketCap": 4800000000, "sentimentScore": 0.25},
        {"name": "Cosmos", "symbol": "ATOM", "marketCap": 4200000000, "sentimentScore": 0.18},
        {"name": "Stellar", "symbol": "XLM", "marketCap": 3800000000, "sentimentScore": -0.22},
        {"name": "Monero", "symbol": "XMR", "marketCap": 3200000000, "sentimentScore": 0.08},
        {"name": "Ethereum Classic", "symbol": "ETC", "marketCap": 3000000000, "sentimentScore": -0.45},
        {"name": "Filecoin", "symbol": "FIL", "marketCap": 2800000000, "sentimentScore": -0.65},
        {"name": "Hedera", "symbol": "HBAR", "marketCap": 2600000000, "sentimentScore": 0.12},
        {"name": "Aptos", "symbol": "APT", "marketCap": 2500000000, "sentimentScore": 0.92},
        {"name": "Cronos", "symbol": "CRO", "marketCap": 2400000000, "sentimentScore": -0.15},
        {"name": "Lido DAO", "symbol": "LDO", "marketCap": 2300000000, "sentimentScore": 0.40},
        {"name": "Arbitrum", "symbol": "ARB", "marketCap": 2100000000, "sentimentScore": -0.55},
        {"name": "Near Protocol", "symbol": "NEAR", "marketCap": 2000000000, "sentimentScore": 0.35},
        {"name": "VeChain", "symbol": "VET", "marketCap": 1900000000, "sentimentScore": 0.02},
        {"name": "Optimism", "symbol": "OP", "marketCap": 1800000000, "sentimentScore": -0.25},
        {"name": "Aave", "symbol": "AAVE", "marketCap": 1600000000, "sentimentScore": 0.28},
        {"name": "Injective", "symbol": "INJ", "marketCap": 1500000000, "sentimentScore": 0.85},
    ]
    
    # Optional: ডাটাগুলো একটু র‍্যান্ডমাইজ করা যাতে প্রতিবার রিফ্রেশে কিছুটা পরিবর্তন মনে হয় (Production এ এটা রিয়েল ডাটা হবে)
    for coin in heatmap_data:
        fluctuation = random.uniform(-0.05, 0.05)
        coin["sentimentScore"] = max(-1, min(1, coin["sentimentScore"] + fluctuation))

    return heatmap_data
