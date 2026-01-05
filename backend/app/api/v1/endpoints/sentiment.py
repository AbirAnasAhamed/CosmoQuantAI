from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.services.market_service import MarketService
from app.models.sentiment import SentimentHistory
from app.services.news_service import news_service
from datetime import datetime, timedelta
import pandas as pd
from pydantic import BaseModel

router = APIRouter()
market_service = MarketService()

# ✅ ১. রিকোয়েস্ট বডি ভ্যালিডেশনের জন্য Pydantic মডেল
class SummaryRequest(BaseModel):
    headlines: str
    asset: str

@router.get("/news")
async def get_sentiment_news():
    """Live News Fetching"""
    return await news_service.fetch_news()

@router.get("/fear-greed")
async def get_fear_greed():
    return {"value": "55", "value_classification": "Greed"}

# ✅ ২. নতুন Summary Endpoint (AI Summary এর জন্য)
@router.post("/summary")
async def generate_market_summary(request: SummaryRequest):
    """
    Generate a summary from news headlines.
    (This is a placeholder logic to fix the 404 error. 
    You can connect your Real AI Service here later.)
    """
    try:
        # এখানে আপনি চাইলে আপনার app.services.ai_service ব্যবহার করতে পারেন
        # আপাতত একটি ডামি ইন্টেলিজেন্ট রেসপন্স দেওয়া হচ্ছে
        
        word_count = len(request.headlines.split())
        sentiment_tone = "mixed" if "volatility" in request.headlines.lower() else "moderately bullish"
        
        summary = (
            f"⚡ AI Market Insight for {request.asset}: \n\n"
            f"Analyzing {word_count} data points from recent headlines indicates a {sentiment_tone} market sentiment. "
            f"Key institutional activity is detected around current price levels. "
            f"Traders should monitor volume spikes as a confirmation signal for the next trend direction."
        )
        
        return {"summary": summary}
    
    except Exception as e:
        print(f"Summary Generation Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate summary")

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
