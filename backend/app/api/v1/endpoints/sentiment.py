from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.services.market_service import MarketService
from app.models.sentiment import SentimentHistory
from app.services.news_service import news_service
from app.services.ai_service import ai_service # ✅ Import updated ai_service
from datetime import datetime, timedelta
import pandas as pd
from pydantic import BaseModel

router = APIRouter()
market_service = MarketService()

class SummaryRequest(BaseModel):
    headlines: str
    asset: str
    provider: str = "gemini" # Default value

@router.get("/news")
async def get_sentiment_news():
    return await news_service.fetch_news()

@router.get("/fear-greed")
async def get_fear_greed():
    return {"value": "55", "value_classification": "Greed"}

# ✅ Real AI Summary Endpoint
@router.post("/summary")
async def generate_market_summary(request: SummaryRequest):
    """
    Generate a summary using the User Selected AI Provider.
    """
    try:
        # ✅ 2. Service এ provider পাঠিয়ে দেওয়া
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
    Returns combined Price vs Sentiment data for the chart.
    """
    # 1. Get Price Data (Market Data)
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    candles = market_service.get_candles_from_db(db, symbol, timeframe, start_date=start_date)
    
    if not candles:
        return []

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
    
    if price_df.empty:
        return []
    
    price_df.set_index('timestamp', inplace=True)

    # Sentiment DataFrame
    if sentiment_history:
        sent_df = pd.DataFrame([{
            "timestamp": s.timestamp,
            "score": s.score
        } for s in sentiment_history])
        sent_df.set_index('timestamp', inplace=True)
        
        # ✅ FIX: Timezone Mismatch Solved
        if sent_df.index.tz is not None:
            sent_df.index = sent_df.index.tz_convert('UTC').tz_localize(None)

        # 4. Resample & Merge
        # ✅ FIX: '1H' deprecated warning solved by changing to '1h'
        sent_resampled = sent_df.resample('1h').mean().interpolate(method='linear') 
        
        merged_df = price_df.join(sent_resampled, how='left')
        merged_df['score'] = merged_df['score'].fillna(0)
    else:
        merged_df = price_df
        merged_df['score'] = 0

    # 5. Build JSON Response
    chart_data = []
    for ts, row in merged_df.iterrows():
        chart_data.append({
            "time": ts.isoformat(),
            "price": row['price'],
            "score": round(row['score'], 2),
            "volume": row['volume']
        })

    return chart_data
