from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.utils import get_redis_client
import redis
from app import models
from app.api import deps

router = APIRouter()

class KillSwitchSchema(BaseModel):
    active: bool

@router.get("/kill-switch", response_model=KillSwitchSchema)
def get_kill_switch_status():
    """
    Get the current status of the Global Admin Kill Switch.
    """
    r = get_redis_client()
    status = r.get("global_kill_switch")
    is_active = status == "true"
    return {"active": is_active}

@router.post("/kill-switch", response_model=KillSwitchSchema)
def toggle_kill_switch(payload: KillSwitchSchema):
    """
    Toggle the Global Admin Kill Switch.
    """
    r = get_redis_client()
    r.set("global_kill_switch", "true" if payload.active else "false")
    return {"active": payload.active}

@router.get("/panic", response_model=KillSwitchSchema)
def get_panic_status(
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Get the panic status for the current user.
    """
    r = get_redis_client()
    key = f"GLOBAL_KILL_SWITCH:{current_user.id}"
    status = r.get(key)
    is_active = status == "true"
    return {"active": is_active}

@router.post("/panic", response_model=KillSwitchSchema)
def toggle_panic_switch(
    payload: KillSwitchSchema,
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Toggle the User Panic Switch.
    When active (True), all bots for this user MUST stop immediately.
    """
    r = get_redis_client()
    key = f"GLOBAL_KILL_SWITCH:{current_user.id}"
    r.set(key, "true" if payload.active else "false")
    return {"active": payload.active}
