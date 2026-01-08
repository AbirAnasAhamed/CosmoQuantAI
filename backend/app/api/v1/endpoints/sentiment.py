from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.services.market_service import MarketService
from app.models.sentiment import SentimentHistory
from app.services.news_service import news_service
from app.services.ai_service import ai_service
from datetime import datetime, timedelta
import pandas as pd
from pydantic import BaseModel

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

    # 3. Merge Data with Pandas
    price_df = pd.DataFrame([{
        "timestamp": c.timestamp,
        "price": c.close,
        "volume": c.volume
    } for c in candles])
    
    if price_df.empty: return []
    price_df.set_index('timestamp', inplace=True)

    if sentiment_history:
        # ✅ Include new metrics here
        sent_df = pd.DataFrame([{
            "timestamp": s.timestamp,
            "score": s.score,
            "sentiment_momentum": s.sentiment_momentum or 0, # Handle Null
            "social_volume": s.social_volume or 0            # Handle Null
        } for s in sentiment_history])
        
        sent_df.set_index('timestamp', inplace=True)
        if sent_df.index.tz is not None:
            sent_df.index = sent_df.index.tz_convert('UTC').tz_localize(None)

        # 4. Resample Logic
        # Score & Momentum = Mean (Average state over the hour)
        # Social Volume = Sum (Total mentions in that hour)
        sent_resampled = sent_df.resample('1h').agg({
            'score': 'mean',
            'sentiment_momentum': 'mean',
            'social_volume': 'sum'
        }).interpolate(method='linear')
        
        merged_df = price_df.join(sent_resampled, how='left')
        merged_df['score'] = merged_df['score'].fillna(0)
        merged_df['sentiment_momentum'] = merged_df['sentiment_momentum'].fillna(0)
        merged_df['social_volume'] = merged_df['social_volume'].fillna(0)
    else:
        merged_df = price_df
        merged_df['score'] = 0
        merged_df['sentiment_momentum'] = 0
        merged_df['social_volume'] = 0

    # 5. Build JSON Response
    chart_data = []
    for ts, row in merged_df.iterrows():
        chart_data.append({
            "time": ts.isoformat(),
            "price": row['price'],
            "score": round(row['score'], 2),
            "momentum": round(row['sentiment_momentum'], 2), # ✅ New Field
            "social_volume": int(row['social_volume']),      # ✅ New Field
            "volume": row['volume']
        })

    return chart_data

@router.get("/narratives")
async def get_market_narratives():
    """
    Analyzes cached news to generate Word Cloud and Trending Narratives using AI.
    """
    try:
        # ১. নিউজ ফেচ করা (news_service থেকে)
        news_items = await news_service.fetch_news()
        
        if not news_items:
            return {"word_cloud": [], "narratives": ["No sufficient data to generate narratives."]}

        # ২. হেডলাইনগুলো একত্রিত করা
        headlines_text = ". ".join([item['content'] for item in news_items[:20]]) # টপ ২০টি নিউজ নিচ্ছি

        # ৩. AI দিয়ে ন্যারেটিভ জেনারেট করা
        narrative_data = ai_service.generate_market_narratives(headlines_text)
        
        return narrative_data
    except Exception as e:
        print(f"Narrative Generation Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate market narratives")
