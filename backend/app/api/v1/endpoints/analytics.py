from typing import Any, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.api import deps
from app.schemas.analytics import PerformanceMetrics
from app.services.analytics import analytics_service

router = APIRouter()

@router.get("/performance", response_model=PerformanceMetrics)
def get_performance_metrics(
    db: Session = Depends(deps.get_db),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Any:
    """
    Get performance analytics (Sharpe Ratio, Max Drawdown, Win Rate)
    """
    return analytics_service.calculate_performance_metrics(
        db=db,
        start_date=start_date,
        end_date=end_date
    )
