from typing import Optional, Any, Dict, List
from pydantic import BaseModel, validator
from datetime import datetime

# Shared properties
class StrategyConfig(BaseModel):
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
    target_spread: Optional[float] = None
    leverage: Optional[int] = 1
    timeframe: str = "1h"
    amount_per_trade: float
    vol_threshold: Optional[float] = None
    risk_pct: Optional[float] = None
    sell_order_type: Optional[str] = "market"
    min_wall_lifetime: Optional[float] = 3.0
    partial_tp_pct: Optional[float] = 50.0
    vpvr_enabled: Optional[bool] = False
    vpvr_tolerance: Optional[float] = 0.2

    # --- NEW: Liquidation & Micro-Scalp Config ---
    enable_wall_trigger: Optional[bool] = True
    max_wall_distance_pct: Optional[float] = 1.0
    enable_liq_trigger: Optional[bool] = False
    liq_threshold: Optional[float] = 50000.0
    enable_micro_scalp: Optional[bool] = False
    micro_scalp_profit_ticks: Optional[int] = 2
    micro_scalp_min_wall: Optional[float] = 100000.0
    
    # --- Advanced Liquidation (Smart HFT) ---
    enable_liq_cascade: Optional[bool] = False
    liq_cascade_window: Optional[int] = 5
    enable_dynamic_liq: Optional[bool] = False
    dynamic_liq_multiplier: Optional[float] = 1.0
    enable_ob_imbalance: Optional[bool] = False
    ob_imbalance_ratio: Optional[float] = 1.5
    
    # --- BTC Liquidation Follower ---
    follow_btc_liq: Optional[bool] = False
    btc_liq_threshold: Optional[float] = 500000.0

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
    description: Optional[str] = None
    exchange: Optional[str] = "binance"
    market: Optional[str] = "BTC/USDT"
    strategy: Optional[str] = None
    timeframe: Optional[str] = "1h"
    status: Optional[str] = "inactive"
    config: Optional[StrategyConfig] = None
    
    trade_value: Optional[float] = 100.0
    trade_unit: Optional[str] = "QUOTE"
    api_key_id: Optional[str] = None
    is_paper_trading: Optional[bool] = True 

class BotCreate(BotBase):
    name: str
    exchange: str
    market: str
    config: StrategyConfig 

class BotUpdate(BotBase):
    pass

class BotInDBBase(BotBase):
    id: int
    owner_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    config: Optional[Dict[str, Any]] = None 
    
    class Config:
        from_attributes = True

class Bot(BotInDBBase):
    pnl: Optional[float] = 0.0
    pnl_percent: Optional[float] = 0.0
    win_rate: Optional[float] = 0.0
    equity_history: List[float] = []
