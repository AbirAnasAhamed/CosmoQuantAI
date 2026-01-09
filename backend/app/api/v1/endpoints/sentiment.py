from fastapi import APIRouter, HTTPException
from app.services.news_service import news_service
import ccxt.async_support as ccxt  # Async CCXT
import pandas as pd
import pandas_ta as ta  # Technical Analysis Library
import numpy as np
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/news")
async def get_sentiment_news():
    return await news_service.fetch_news()

@router.get("/fear-greed")
async def get_fear_greed():
    return await news_service.fetch_fear_greed_index()

@router.get("/correlation")
async def get_sentiment_correlation(symbol: str = "BTC/USDT", days: int = 7):
    """
    Full library-based logic:
    1. CCXT for live Price and Volume.
    2. GNews for News Sentiment (Retail Score).
    3. Pandas-TA for Volume Flow (Smart Money Score).
    """
    try:
        # 1. Fetch Live Market Data (Binance)
        exchange = ccxt.binance()
        timeframe = '1h'
        limit = 24 * days
        
        # OHLCV Data Fetch
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        await exchange.close()

        if not ohlcv:
            return []

        # Create DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # 2. Fetch Sentiment Data (from GNews)
        sentiment_df = await news_service.fetch_historical_sentiment(days=days)

        # 3. Merge Market and Sentiment Data
        merged_df = df.join(sentiment_df, how='left')
        
        # Missing Sentiment Fill (ffill instead of method='ffill')
        merged_df['score'] = merged_df['score'].ffill().fillna(0)

        # ---------------------------------------------------------
        # 4. Smart Money vs Retail Calculation (Logic)
        # ---------------------------------------------------------
        
        # Retail Score = News Sentiment + Price Momentum mix
        # Retail usually follows price (FOMO)
        merged_df['retail_score'] = merged_df['score'] * 0.7 + merged_df['close'].pct_change().rolling(5).mean() * 10
        merged_df['retail_score'] = merged_df['retail_score'].fillna(0)

        # Smart Money Score = Money Flow Index (MFI) or On-Balance Volume (OBV)
        # Smart money moves on volume, not just price.
        # We will use CMF (Chaikin Money Flow) for smart money detection.
        merged_df.ta.cmf(append=True)  # Adds CMF_20 column
        # Normalize CMF to -1 to 1 range
        cmf_col = merged_df.columns[-1] # Last column is CMF
        merged_df['smart_money_score'] = merged_df[cmf_col].rolling(3).mean() * 5 # Scaling
        merged_df['smart_money_score'] = merged_df['smart_money_score'].clip(-1, 1).fillna(0)

        # Momentum & Social Volume Simulation
        merged_df['momentum'] = merged_df['close'].diff().fillna(0)
        # Social Volume = Volume * Volatility (Proxy)
        merged_df['social_volume'] = (merged_df['volume'] * merged_df['high'].diff().abs() / 1000).fillna(100).astype(int)

        # Fill any remaining NaNs to avoid JSON error
        merged_df = merged_df.fillna(0)
        merged_df = merged_df.replace({np.nan: 0})

        # 5. Final Response Construction
        chart_data = []
        for ts, row in merged_df.iterrows():
            # Check for NaN specifically just in case
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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/heatmap")
async def get_sentiment_heatmap():
    # Heatmap kept static/random for now as live fetching 50 coins might be slow
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
