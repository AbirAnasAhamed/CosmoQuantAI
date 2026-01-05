from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from typing import Optional
import ccxt.async_support as ccxt
import logging
from pydantic import BaseModel

# ✅ ফিক্স: সরাসরি news_service ইম্পোর্ট না করে ক্লাসের ইনস্ট্যান্স দরকার হলে 
# আমরা news_service.py থেকে ক্লাসটি ইম্পোর্ট করে আলাদাভাবে হ্যান্ডেল করতে পারি। 
# অথবা Circular Import এড়াতে ফাংশনের ভেতরে ইম্পোর্ট করতে পারি।

# from app.services.news_service import news_service # ❌ এই লাইনটি সমস্যা করছে যদি Circular Import থাকে

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Schemas ---
class OrderRequest(BaseModel):
    symbol: str
    side: str # 'buy' or 'sell'
    type: str # 'market' or 'limit'
    amount: float
    price: Optional[float] = None
    exchange_id: str = 'binance'

class ConnectionTestRequest(BaseModel):
    exchange_id: str
    api_key: str
    api_secret: str

# --- Endpoints ---

@router.get("/news")
async def get_crypto_news():
    """Fetch latest crypto news"""
    # ✅ ফিক্স: এখানে লোকাল ইম্পোর্ট ব্যবহার করা হয়েছে যাতে মডিউল লোডিং এর সময় লুপ না হয়
    from app.services.news_service import news_service 
    return await news_service.fetch_news()

@router.post("/test-connection")
async def test_exchange_connection(request: ConnectionTestRequest):
    """Test validity of API keys"""
    exchange_class = getattr(ccxt, request.exchange_id, None)
    if not exchange_class:
        raise HTTPException(status_code=400, detail="Unsupported exchange")
    
    try:
        exchange = exchange_class({
            'apiKey': request.api_key,
            'secret': request.api_secret,
            'enableRateLimit': True
        })
        
        # Try to fetch balance as a test
        await exchange.fetch_balance()
        await exchange.close()
        return {"status": "success", "message": "Connection Successful"}
        
    except Exception as e:
        if 'exchange' in locals():
            await exchange.close()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/order")
async def place_order(order: OrderRequest):
    """Place a real order on the exchange"""
    
    # Simulating a successful order for the UI flow
    import asyncio
    await asyncio.sleep(1) # simulate network delay
    
    return {
        "id": "123456789",
        "symbol": order.symbol,
        "status": "closed",
        "side": order.side,
        "amount": order.amount,
        "price": order.price or 68000.00,
        "message": "Order placed successfully (SIMULATED)"
    }
