from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.db.session import SessionLocal 
from app.tasks import run_live_bot_task
from app import utils

router = APIRouter()

@router.get("/", response_model=List[schemas.Bot])
def read_bots(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve bots belonging to the current user.
    """
    bots = db.query(models.Bot).filter(models.Bot.owner_id == current_user.id).offset(skip).limit(limit).all()
    return bots

@router.post("/", response_model=schemas.Bot)
def create_bot(
    *,
    db: Session = Depends(deps.get_db),
    bot_in: schemas.BotCreate,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new bot.
    """
    # ✅ ফিক্স: model_dump থেকে 'status' বাদ দেওয়া হয়েছে যাতে কনফ্লিক্ট না হয়
    bot_data = bot_in.model_dump(exclude={"status"}) 
    
    bot = models.Bot(
        **bot_data,
        owner_id=current_user.id,
        status="inactive" # ডিফল্ট স্ট্যাটাস সেট করা হচ্ছে
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot

@router.put("/{bot_id}", response_model=schemas.Bot)
def update_bot(
    *,
    db: Session = Depends(deps.get_db),
    bot_id: int,
    bot_in: schemas.BotUpdate,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Update a bot configuration.
    """
    bot = db.query(models.Bot).filter(models.Bot.id == bot_id, models.Bot.owner_id == current_user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    update_data = bot_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bot, field, value)
        
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot

@router.delete("/{bot_id}", response_model=schemas.Bot)
def delete_bot(
    *,
    db: Session = Depends(deps.get_db),
    bot_id: int,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete a bot. If the bot is running, it force-stops the background task first.
    """
    bot = db.query(models.Bot).filter(models.Bot.id == bot_id, models.Bot.owner_id == current_user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
        
    if bot.status == "active":
        try:
            r = utils.get_redis_client()
            task_key = f"bot_task:{bot_id}"
            r.delete(task_key)
            print(f"Force stopped worker for bot {bot_id} before deletion.")
        except Exception as e:
            print(f"Error stopping worker for bot {bot_id}: {e}")
            
    db.delete(bot)
    db.commit()
    return bot

@router.post("/{bot_id}/action", response_model=schemas.Bot)
def control_bot(
    *,
    db: Session = Depends(deps.get_db),
    bot_id: int,
    action: str, # "start", "stop"
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Start or Stop a bot instance using Celery & Redis.
    """
    bot = db.query(models.Bot).filter(models.Bot.id == bot_id, models.Bot.owner_id == current_user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    r = utils.get_redis_client()
    task_key = f"bot_task:{bot_id}"

    if action == "start":
        if bot.status == "active":
            raise HTTPException(status_code=400, detail="Bot is already running")
            
        bot.status = "active"
        db.commit()
        run_live_bot_task.delay(bot_id=bot.id)
        
    elif action == "stop":
        bot.status = "inactive"
        db.commit()
        r.delete(task_key)
        
    db.refresh(bot)
    return bot
