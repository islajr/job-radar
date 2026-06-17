from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AdminUserView(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    alerts_paused: bool
    telegram_connected: bool

class ScraperRunView(BaseModel):
    id: str
    board: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    listings_found: int
    new_listings: int
    errors: Optional[str] = None
    status: str

    class Config:
        from_attributes = True
