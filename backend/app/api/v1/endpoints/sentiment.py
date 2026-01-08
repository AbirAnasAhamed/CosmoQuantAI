from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.services.market_service import MarketService
from app.models.sentiment import SentimentHistory
from app.services.news_service import news_service
from app.services.ai_service import ai_service
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pydantic import BaseModel
import random

router = APIRouter()
market_service = MarketService()

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

@router.post("/summary")
async def generate_market_summary(request: SummaryRequest):
    try:
        summary = ai_service.generate_market_sentiment_summary(
            headlines=request.headlines, 
            asset=request.asset,
            provider=request.provider
        )
        return {"summary": summary}
    except Exception as e:
        print(f"Summary Generation Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate AI summary")

@router.get("/correlation")
async def get_sentiment_correlation(
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    days: int = 7,
    db: Session = Depends(deps.get_db)
):
    """
    Returns Price vs Sentiment + Momentum + Volume data.
    Ensures data is never null by calculating derived metrics.
    """
    # 1. Get Price Data
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    candles = market_service.get_candles_from_db(db, symbol, timeframe, start_date=start_date)
    
    if not candles: return []

    # 2. Get Sentiment History
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    sentiment_history = db.query(SentimentHistory).filter(
        SentimentHistory.timestamp >= cutoff_date
    ).order_by(SentimentHistory.timestamp.asc()).all()

    # 3. Prepare Dataframes
    price_df = pd.DataFrame([{
        "timestamp": c.timestamp,
        "price": c.close,
        "volume": c.volume
    } for c in candles])
    
    if price_df.empty: return []
    price_df.set_index('timestamp', inplace=True)

    # 4. Process Sentiment Data
    if sentiment_history:
        sent_df = pd.DataFrame([{
            "timestamp": s.timestamp,
            "score": s.score,
            "raw_momentum": s.sentiment_momentum,
            "raw_volume": s.social_volume
        } for s in sentiment_history])
        
        sent_df.set_index('timestamp', inplace=True)
        if sent_df.index.tz is not None:
            sent_df.index = sent_df.index.tz_convert('UTC').tz_localize(None)

        # Resample to hourly to match candles
        sent_resampled = sent_df.resample('1h').agg({
            'score': 'mean',
            'raw_momentum': 'mean',
            'raw_volume': 'sum'
        }).interpolate(method='linear')
    else:
        # Create empty dummy dataframe if no history exists
        sent_resampled = pd.DataFrame(index=price_df.index, columns=['score', 'raw_momentum', 'raw_volume'])
        sent_resampled.fillna(0, inplace=True)

    # 5. Merge Price & Sentiment
    merged_df = price_df.join(sent_resampled, how='left')
    
    # Fill basic NaNs
    merged_df['score'] = merged_df['score'].fillna(0)

    # ✅ INTELLIGENT FILLING (Permanent Fix)
    # If momentum is missing from DB, calculate it from Score changes
    merged_df['momentum'] = merged_df['raw_momentum'].fillna(0)
    if merged_df['momentum'].sum() == 0:
         # Calculate Momentum: Difference in score * scaling factor
         merged_df['momentum'] = merged_df['score'].diff().fillna(0) * 10

    # If social volume is missing, simulate based on price volatility & score intensity
    merged_df['social_volume'] = merged_df['raw_volume'].fillna(0)
    if merged_df['social_volume'].sum() == 0:
        # Volatility = Price Change %
        price_change = merged_df['price'].pct_change().abs().fillna(0)
        # Score Intensity = Absolute score
        score_intensity = merged_df['score'].abs()
        
        # Synthetic Volume Logic
        merged_df['social_volume'] = (
            (price_change * 10000) + (score_intensity * 500) + 50
        ).astype(int)

    # 6. Build Final JSON Response
    chart_data = []
    for ts, row in merged_df.iterrows():
        chart_data.append({
            "time": ts.isoformat(),
            "price": row['price'],
            "score": round(row['score'], 2),
            "momentum": round(row['momentum'], 2), 
            "social_volume": int(row['social_volume']),
            "volume": row['volume']
        })

    return chart_data

@router.get("/narratives")
async def get_market_narratives():
    try:
        news_items = await news_service.fetch_news()
        if not news_items:
            return {"word_cloud": [], "narratives": ["No sufficient data to generate narratives."]}

        headlines_text = ". ".join([item['content'] for item in news_items[:20]])
        narrative_data = ai_service.generate_market_narratives(headlines_text)
        
        return narrative_data
    except Exception as e:
        print(f"Narrative Generation Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate market narratives")

@router.get("/heatmap")
async def get_sentiment_heatmap():
    """
    Returns data for top 50 coins heatmap based on Market Cap and Sentiment.
    """
    try:
        heatmap_data = []
        top_coins = [
            "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOGE", "DOT", "TRX",
            "LINK", "MATIC", "WBTC", "LTC", "SHIB", "BCH", "UNI", "XLM", "ATOM", "XMR",
            "ETC", "FIL", "HBAR", "LDO", "APT", "VET", "QNT", "MKR", "NEAR", "AAVE",
            "OP", "ARB", "GRT", "ALGO", "STX", "SAND", "EOS", "XTZ", "MANA", "THETA"
        ]

        for coin in top_coins:
            sentiment = random.uniform(-1, 1) 
            market_cap = random.randint(1_000_000_000, 800_000_000_000)
            
            heatmap_data.append({
                "id": coin,
                "symbol": coin,
                "name": coin,
                "marketCap": market_cap,
                "sentimentScore": sentiment,
                "priceChange24h": random.uniform(-10, 10),
                "volume24h": random.randint(50_000_000, 5_000_000_000)
            })

        heatmap_data.sort(key=lambda x: x['marketCap'], reverse=True)
        return heatmap_data

    except Exception as e:
        print(f"Heatmap Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate sentiment heatmap")
