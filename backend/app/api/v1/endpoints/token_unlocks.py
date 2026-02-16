from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.api import deps
from app.models.token_unlock import TokenUnlockEvent
from app.schemas.token_unlock import TokenUnlockResponse, TokenUnlockCreate
from app.services.token_unlock_service import TokenUnlockService

router = APIRouter()

@router.get("/", response_model=List[TokenUnlockResponse])
def read_unlocks(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Retrieve token unlock events.
    """
    unlocks = db.query(TokenUnlockEvent).order_by(TokenUnlockEvent.unlock_date).offset(skip).limit(limit).all()
    return unlocks

@router.post("/sync/{symbol}", response_model=TokenUnlockResponse)
async def sync_token_unlock(
    symbol: str,
    db: Session = Depends(deps.get_db),
):
    """
    Trigger manual sync for a token's unlock data.
    """
    service = TokenUnlockService(db)
    try:
        event = await service.sync_token(symbol)
        return event
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{id}/analysis", response_model=TokenUnlockResponse)
async def get_unlock_analysis(
    id: int,
    db: Session = Depends(deps.get_db)
):
    """
    Get or generate analysis for a specific event.
    """
    event = db.query(TokenUnlockEvent).filter(TokenUnlockEvent.id == id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Unlock event not found")
    
    if not event.ai_summary or not event.impact_score:
        service = TokenUnlockService(db)
        await service.analyze_impact(event)
        db.add(event)
        db.commit()
        db.refresh(event)
        
    return event
