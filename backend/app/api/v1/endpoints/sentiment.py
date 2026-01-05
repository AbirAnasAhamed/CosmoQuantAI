from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api import deps
from app.services.market_service import MarketService
from app.models.sentiment import SentimentHistory
from app.services.news_service import news_service
from datetime import datetime, timedelta
import pandas as pd

router = APIRouter()
market_service = MarketService()

@router.get("/news")
async def get_sentiment_news():
    """Live News Fetching"""
    return await news_service.fetch_news()

@router.get("/fear-greed")
async def get_fear_greed():
    return {"value": "55", "value_classification": "Greed"}

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
    # Price DataFrame
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
        
        # 4. Resample & Merge
        # Ffill sentiment to match price timeframe
        sent_resampled = sent_df.resample('1H').mean().interpolate(method='linear') 
        
        # Join tables
        merged_df = price_df.join(sent_resampled, how='left')
        
        # Handle NaN (default 0)
        merged_df['score'] = merged_df['score'].fillna(0)
    else:
        # If no sentiment history, fill with 0
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
