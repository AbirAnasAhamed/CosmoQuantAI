from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PerformanceMetrics(BaseModel):
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    total_pnl: float
    start_date: Optional[datetime]
    end_date: Optional[datetime]
