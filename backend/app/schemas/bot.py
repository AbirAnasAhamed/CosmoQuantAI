from typing import Optional, Any, Dict, List
from pydantic import BaseModel, validator
from datetime import datetime

# Shared properties
class StrategyConfig(BaseModel):
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    leverage: Optional[int] = 1
    timeframe: str = "1h"
    amount_per_trade: float

    @validator('stop_loss')
    def validate_stop_loss(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('stop_loss must be between 0 and 100')
        return v

    @validator('take_profit')
    def validate_take_profit(cls, v):
        if v is not None and v <= 0:
            raise ValueError('take_profit must be greater than 0')
        return v
    
    @validator('leverage')
    def validate_leverage(cls, v):
        if v is not None and (v < 1 or v > 125):
             raise ValueError('leverage must be between 1 and 125')
        return v

    @validator('amount_per_trade')
    def validate_amount_per_trade(cls, v):
        if v <= 0:
            raise ValueError('amount_per_trade must be greater than 0')
        return v

class BotBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None # ✅ Strategy Description
    exchange: Optional[str] = "binance"
    market: Optional[str] = "BTC/USDT"
    strategy: Optional[str] = None
    timeframe: Optional[str] = "1h"
    status: Optional[str] = "inactive"
    config: Optional[StrategyConfig] = None
    
    # ✅ এই লাইনগুলো নিশ্চিত করুন (নতুন যোগ করা হয়েছে)
    trade_value: Optional[float] = 100.0
    trade_unit: Optional[str] = "QUOTE"
    api_key_id: Optional[str] = None
    is_paper_trading: Optional[bool] = True # ✅ Default to True (Handles NULLs)

# Properties to receive on Bot creation
class BotCreate(BotBase):
    name: str
    exchange: str
    market: str
    config: StrategyConfig # Make config required for creation if needed, or keep optional but validated if present

# Properties to receive on Bot update
class BotUpdate(BotBase):
    pass

# Properties shared by models stored in DB
class BotInDBBase(BotBase):
    id: int
    owner_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    config: Optional[Dict[str, Any]] = None # DB stores JSON, so we might need mapping or let Pydantic handle it. 
                                            # Actually, if SQLAlchemy model has JSON type, Pydantic can map StrategyConfig <-> Dict.
                                            # However, responding to client, we want StrategyConfig. 
                                            # Let's keep it consistent.
    
    class Config:
        from_attributes = True # Pydantic v2 হলে, v1 হলে orm_mode = True

# Properties to return to client
class Bot(BotInDBBase):
    pnl: Optional[float] = 0.0
    pnl_percent: Optional[float] = 0.0
    win_rate: Optional[float] = 0.0
    equity_history: List[float] = []
