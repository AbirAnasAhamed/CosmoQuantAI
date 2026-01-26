from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.news_service import news_service
from app.services.ai_service import ai_service
from app.api import deps
from app.models.sentiment import SentimentPoll, InfluencerTrack, SocialDominance
from app.schemas.sentiment import SentimentPollCreate, InfluencerTrack as InfluencerTrackSchema, SocialDominance as SocialDominanceSchema
import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
import random
from sqlalchemy import func

router = APIRouter()

# --- Request Models ---
class SummaryRequest(BaseModel):
    headlines: str
    asset: str
    provider: str = "gemini"

class VerifyNewsRequest(BaseModel):
    content: str

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

@router.post("/verify-news")
async def verify_news_credibility(request: VerifyNewsRequest):
    try:
        result = ai_service.analyze_news_credibility(news_content=request.content)
        return result
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
        
        # --- NEW: On-Chain Whale Tracking Logic (Simulated) ---
        # 1. Simulate Exchange Netflow (Mock Data)
        # Logic: Random noise + inverse price movement (Whales buy dips)
        np.random.seed(42) # For reproducibility
        merged_df['exchange_netflow'] = np.random.normal(0, 1000, len(merged_df)) 
        
        # Create Divergence: Price drops but Netflow is Negative (Outflow) -> Whales Accumulating
        # We'll just force some negative netflow when price is dropping to simulate "Smart Money Buying the Dip"
        merged_df['price_change'] = merged_df['close'].diff()
        merged_df.loc[merged_df['price_change'] < 0, 'exchange_netflow'] -= 500  # More outflow on dips
        
        # 2. Normalize Netflow (-1 to 1)
        # Negative Netflow (Outflow) = Bullish (Positive Score)
        # Positive Netflow (Inflow) = Bearish (Negative Score)
        max_flow = merged_df['exchange_netflow'].abs().max()
        merged_df['netflow_signal'] = -1 * (merged_df['exchange_netflow'] / max_flow) # Invert sign
        
        # 3. Enhanced Smart Money Score formula
        # smart_money_score = (0.4 * CMF_Score) + (0.6 * Netflow_Signal)
        # Note: CMF is already -1 to 1 approx
        cmf_score = merged_df[cmf_col].rolling(3).mean() * 5 # Scale CMF slightly as before
        cmf_score = cmf_score.clip(-1, 1).fillna(0)
        
        merged_df['smart_money_score'] = (0.4 * cmf_score) + (0.6 * merged_df['netflow_signal'])
        merged_df['smart_money_score'] = merged_df['smart_money_score'].clip(-1, 1).fillna(0)

        merged_df['momentum'] = merged_df['close'].diff().fillna(0)
        merged_df['social_volume'] = (merged_df['volume'] * merged_df['high'].diff().abs() / 1000).fillna(100).astype(int)

        merged_df = merged_df.fillna(0)
        merged_df = merged_df.replace({np.nan: 0})

        chart_data = []
        for ts, row in merged_df.iterrows():
            smart_val = row['smart_money_score'] if not pd.isna(row['smart_money_score']) else 0
            retail_val = row['retail_score'] if not pd.isna(row['retail_score']) else 0
            
            # Determine Netflow Status for Frontend Tooltip
            netflow_val = row['netflow_signal']
            netflow_status = "Accumulating" if netflow_val > 0.2 else "Dumping" if netflow_val < -0.2 else "Neutral"
            
            chart_data.append({
                "time": ts.isoformat(),
                "price": row['close'],
                "score": round(row['score'], 2),
                "retail_score": round(retail_val, 2),        
                "smart_money_score": round(smart_val, 2),
                "netflow_status": netflow_status, # NEW field for Tooltip
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

# --- New Endpoints ---

@router.post("/poll", status_code=status.HTTP_201_CREATED)
async def submit_sentiment_poll(poll: SentimentPollCreate, db: Session = Depends(deps.get_db)):
    """
    Submit a user's sentiment vote.
    """
    try:
        new_vote = SentimentPoll(
            user_id=poll.user_id,
            vote_type=poll.vote_type
        )
        db.add(new_vote)
        db.commit()
        db.refresh(new_vote)
        return {"status": "success", "message": "Vote recorded", "data": new_vote}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/poll-stats")
async def get_sentiment_poll_stats(db: Session = Depends(deps.get_db)):
    """
    Get percentage of Bullish vs Bearish votes for the last 24h.
    """
    try:
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        # Count votes
        total_votes = db.query(SentimentPoll).filter(SentimentPoll.timestamp >= last_24h).count()
        bullish_votes = db.query(SentimentPoll).filter(
            SentimentPoll.timestamp >= last_24h, 
            SentimentPoll.vote_type == 'bullish'
        ).count()
        
        if total_votes == 0:
            return {
                "bullish_pct": 0,
                "bearish_pct": 0,
                "total_votes": 0
            }
        
        bullish_pct = (bullish_votes / total_votes) * 100
        bearish_pct = 100 - bullish_pct
        
        return {
            "bullish_pct": round(bullish_pct, 1),
            "bearish_pct": round(bearish_pct, 1),
            "total_votes": total_votes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/influencers", response_model=list[InfluencerTrackSchema])
async def get_top_influencers(db: Session = Depends(deps.get_db)):
    """
    Get list of influencers sorted by reliability score.
    """
    try:
        # Mock some data if table is empty, just for demo if needed, 
        # but technically we should return what's in DB.
        influencers = db.query(InfluencerTrack).order_by(InfluencerTrack.reliability_score.desc()).limit(10).all()
        return influencers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/social-dominance", response_model=list[SocialDominanceSchema])
async def get_social_dominance(db: Session = Depends(deps.get_db), days: int = 7):
    """
    Get social dominance data for the last N days.
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        data = db.query(SocialDominance).filter(SocialDominance.timestamp >= start_date).all()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

