from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import json

from app.api import deps
from app.schemas.analytics import PerformanceMetrics, CorrelationRequest, CorrelationResponse, RollingCorrelationPoint
from app.services.analytics import analytics_service
from app.services.market_analysis_service import market_analysis_service
from app.services.websocket_manager import manager

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

@router.post("/correlation-matrix", response_model=CorrelationResponse)
def get_correlation_matrix(
    request: CorrelationRequest,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Calculate correlation matrix and cointegration for a list of assets.
    """
    try:
        if not request.symbols or len(request.symbols) < 2:
            raise HTTPException(status_code=400, detail="At least two symbols are required.")
            
        result = market_analysis_service.get_correlation_data(
            symbols=request.symbols,
            timeframe=request.timeframe
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/correlation/rolling", response_model=List[RollingCorrelationPoint])
def get_rolling_correlation(
    symbol_a: str,
    symbol_b: str,
    timeframe: str = "1h",
    window: int = 30,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Get rolling correlation history between two assets.
    """
    try:
        return market_analysis_service.get_rolling_correlation(
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            timeframe=timeframe,
            window=window
        )
    except Exception as e:
        print(f"Error calculating rolling correlation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# IMPORTANT: Using router.websocket, not app.websocket
# The path here is RELATIVE to the router's prefix.
# If api_router includes this with prefix="/analytics", then url is /api/v1/analytics/ws/correlation
@router.websocket("/ws/correlation")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket, "correlation_feed")
    try:
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'XRP/USDT', 'BNB/USDT']
        
        while True:
            try:
                data = market_analysis_service.get_correlation_data(symbols, "1h")
                
                await websocket.send_json({
                    "type": "update",
                    "data": data
                })
                
                await asyncio.sleep(2) 
            except Exception as e:
                print(f"Error in correlation loop: {e}")
                await asyncio.sleep(5) 
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, "correlation_feed")
