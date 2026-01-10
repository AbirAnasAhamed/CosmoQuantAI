from typing import Optional, Any, Dict, List
from pydantic import BaseModel
from datetime import datetime

# Shared properties
class BotBase(BaseModel):
    name: Optional[str] = None
    exchange: Optional[str] = "binance"
    market: Optional[str] = "BTC/USDT"
    strategy: Optional[str] = None
    timeframe: Optional[str] = "1h"
    status: Optional[str] = "inactive"
    config: Optional[Dict[str, Any]] = {}
    
    # ✅ এই লাইনগুলো নিশ্চিত করুন (নতুন যোগ করা হয়েছে)
    trade_value: Optional[float] = 100.0
    trade_unit: Optional[str] = "QUOTE"
    api_key_id: Optional[str] = None  # <--- এটি খুব গুরুত্বপূর্ণ

# Properties to receive on Bot creation
class BotCreate(BotBase):
    name: str
    exchange: str
    market: str

# Properties to receive on Bot update
class BotUpdate(BotBase):
    pass

# Properties shared by models stored in DB
class BotInDBBase(BotBase):
    id: int
    owner_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True # Pydantic v2 হলে, v1 হলে orm_mode = True

# Properties to return to client
class Bot(BotInDBBase):
    pass
