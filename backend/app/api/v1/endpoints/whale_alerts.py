from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.whale_alert import WhaleAlert
from app.api import deps
from typing import List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class WhaleAlertSchema(BaseModel):
    symbol: str
    volume: float
    price: float
    timestamp: datetime
    exchange: str

    class Config:
        from_attributes = True

@router.get("/recent", response_model=List[WhaleAlertSchema])
def get_recent_alerts(
    db: Session = Depends(deps.get_db),
    limit: int = 10
):
    """
    Get recent whale alerts.
    """
    alerts = db.query(WhaleAlert).order_by(WhaleAlert.timestamp.desc()).limit(limit).all()
    return alerts
