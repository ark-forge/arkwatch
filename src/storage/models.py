"""Database models for ArkWatch"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class WatchStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class Watch(BaseModel):
    """Watch model"""

    id: UUID
    user_id: str | None = None
    name: str
    url: str
    check_interval: int = 3600  # seconds
    min_change_ratio: float | None = None  # per-watch threshold (0.0-1.0), None = use global default
    notify_email: str | None = None
    status: WatchStatus = WatchStatus.ACTIVE
    last_check: datetime | None = None
    last_content_hash: str | None = None
    last_content: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Report(BaseModel):
    """Report model"""

    id: UUID
    watch_id: UUID
    changes_detected: bool
    previous_hash: str | None = None
    current_hash: str
    diff: str | None = None
    ai_summary: str | None = None
    ai_importance: str | None = None
    notified: bool = False
    created_at: datetime

    class Config:
        from_attributes = True
