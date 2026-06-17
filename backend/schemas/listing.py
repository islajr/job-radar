from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MatchOut(BaseModel):
    id:           str
    listing_id:   str
    title:        str
    company:      Optional[str] = None
    location:     Optional[str] = None
    url:          str
    salary_text:  Optional[str] = None
    board:        str
    created_at:   datetime

    class Config:
        from_attributes = True

class BoardStatusOut(BaseModel):
    board: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str

    class Config:
        from_attributes = True
