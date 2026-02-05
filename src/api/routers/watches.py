"""Watch management endpoints with authentication"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Optional

from ...storage import get_db
from ..auth import get_current_user, get_optional_user, get_tier_limits

router = APIRouter()


class WatchCreate(BaseModel):
    url: HttpUrl
    name: str
    check_interval: int = 3600
    notify_email: Optional[str] = None


class WatchUpdate(BaseModel):
    name: Optional[str] = None
    check_interval: Optional[int] = None
    notify_email: Optional[str] = None
    status: Optional[str] = None


@router.post("/watches")
async def create_watch(watch: WatchCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Check tier limits
    limits = get_tier_limits(user["tier"])
    user_watches = [w for w in db.get_watches() if w.get("user_email") == user["email"]]
    
    if len(user_watches) >= limits["max_watches"]:
        raise HTTPException(
            status_code=403, 
            detail=f"Limite atteinte: {limits['max_watches']} surveillances max pour le plan {user['tier']}"
        )
    
    # Enforce minimum check interval
    check_interval = max(watch.check_interval, limits["check_interval_min"])
    
    new_watch = db.create_watch(
        name=watch.name,
        url=str(watch.url),
        check_interval=check_interval,
        notify_email=watch.notify_email or user["email"],
    )
    
    # Tag with user email
    db.update_watch(new_watch["id"], user_email=user["email"])
    
    return new_watch


@router.get("/watches")
async def list_watches(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    db = get_db()
    watches = db.get_watches(status=status)
    
    # Filter by user (unless admin)
    if user["tier"] != "business":
        watches = [w for w in watches if w.get("user_email") == user["email"]]
    
    return watches


@router.get("/watches/{watch_id}")
async def get_watch(watch_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    watch = db.get_watch(watch_id)
    
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")
    
    # Check ownership (unless admin)
    if user["tier"] != "business" and watch.get("user_email") != user["email"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return watch


@router.patch("/watches/{watch_id}")
async def update_watch(watch_id: str, update: WatchUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    watch = db.get_watch(watch_id)
    
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")
    
    if user["tier"] != "business" and watch.get("user_email") != user["email"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    updates = {k: v for k, v in update.dict().items() if v is not None}
    
    # Enforce minimum check interval
    if "check_interval" in updates:
        limits = get_tier_limits(user["tier"])
        updates["check_interval"] = max(updates["check_interval"], limits["check_interval_min"])
    
    watch = db.update_watch(watch_id, **updates)
    return watch


@router.delete("/watches/{watch_id}")
async def delete_watch(watch_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    watch = db.get_watch(watch_id)
    
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")
    
    if user["tier"] != "business" and watch.get("user_email") != user["email"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete_watch(watch_id)
    return {"status": "deleted"}
