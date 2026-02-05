"""Database models for ArkWatch"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from uuid import UUID, uuid4


class WatchStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class Watch(BaseModel):
    """Watch model"""
    id: UUID
    user_id: Optional[str] = None
    name: str
    url: str
    check_interval: int = 3600  # seconds
    notify_email: Optional[str] = None
    status: WatchStatus = WatchStatus.ACTIVE
    last_check: Optional[datetime] = None
    last_content_hash: Optional[str] = None
    last_content: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Report(BaseModel):
    """Report model"""
    id: UUID
    watch_id: UUID
    changes_detected: bool
    previous_hash: Optional[str] = None
    current_hash: str
    diff: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_importance: Optional[str] = None
    notified: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True
