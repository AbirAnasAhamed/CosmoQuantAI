from fastapi import APIRouter, HTTPException, BackgroundTasks, Body, Depends
from typing import Optional
import ccxt.async_support as ccxt
import logging
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app import models, crud
from app.api import deps
from app.core.security import decrypt_key

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
        raise HTTPException(status_code=400, detail=f"Connection Failed: {str(e)}")

@router.post("/order")
async def place_order(
    order: OrderRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Place a REAL order on the exchange"""
    
    # ১. ব্যবহারকারীর API Key খুঁজে বের করা
    api_key_record = db.query(models.ApiKey).filter(
        models.ApiKey.user_id == current_user.id,
        models.ApiKey.exchange == order.exchange_id,
        models.ApiKey.is_enabled == True
    ).first()

    if not api_key_record:
        raise HTTPException(status_code=404, detail=f"No active API key found for {order.exchange_id}")

    exchange = None
    try:
        # ২. সিক্রেট কি ডিক্রিপ্ট করা এবং এক্সচেঞ্জ সেটআপ
        decrypted_secret = decrypt_key(api_key_record.secret_key)
        exchange_class = getattr(ccxt, order.exchange_id, None)
        
        if not exchange_class:
             raise HTTPException(status_code=400, detail="Unsupported exchange")

        exchange = exchange_class({
            'apiKey': api_key_record.api_key,
            'secret': decrypted_secret,
            'enableRateLimit': True,
        })

        # ৩. অর্ডার প্লেস করা
        response = None
        if order.type.lower() == 'market':
            response = await exchange.create_market_order(order.symbol, order.side, order.amount)
        elif order.type.lower() == 'limit':
            if not order.price:
                raise HTTPException(status_code=400, detail="Price is required for limit orders")
            response = await exchange.create_limit_order(order.symbol, order.side, order.amount, order.price)
        else:
             raise HTTPException(status_code=400, detail="Invalid order type")

        return {
            "id": response['id'],
            "symbol": response['symbol'],
            "status": response.get('status', 'open'),
            "side": response['side'],
            "amount": response['amount'],
            "price": response.get('price') or response.get('average'),
            "message": "Order placed successfully"
        }

    except Exception as e:
        logger.error(f"Order placement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Exchange Error: {str(e)}")
    
    finally:
        if exchange:
            await exchange.close()
