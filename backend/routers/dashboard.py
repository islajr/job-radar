from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.database import get_db
from backend.models.user import User
from backend.models.profile import UserProfile
from backend.models.match import UserMatch, ScraperRun
from backend.models.listing import Listing
from backend.schemas.listing import MatchOut, BoardStatusOut
from backend.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter()

class AlertPauseUpdate(BaseModel):
    paused: bool

@router.get("/matches", response_model=list[MatchOut])
async def get_matches(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = (
        select(
            UserMatch.id,
            UserMatch.listing_id,
            Listing.title,
            Listing.company,
            Listing.location,
            Listing.url,
            Listing.salary_text,
            Listing.board,
            UserMatch.created_at
        )
        .join(Listing, UserMatch.listing_id == Listing.id)
        .where(UserMatch.user_id == user.id)
        .order_by(UserMatch.created_at.desc())
        .limit(20)
    )
    result = await db.execute(stmt)
    
    matches = []
    for r in result.all():
        matches.append(MatchOut(
            id=str(r.id),
            listing_id=str(r.listing_id),
            title=r.title,
            company=r.company,
            location=r.location,
            url=r.url,
            salary_text=r.salary_text,
            board=r.board,
            created_at=r.created_at
        ))
    return matches

@router.patch("/alerts/pause")
async def pause_alerts(body: AlertPauseUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = (
        update(UserProfile)
        .where(UserProfile.user_id == user.id)
        .values(alerts_paused=body.paused)
    )
    await db.execute(stmt)
    await db.commit()
    return {"ok": True, "paused": body.paused}

@router.get("/scraper-status", response_model=list[BoardStatusOut])
async def get_scraper_status(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ScraperRun)
        .distinct(ScraperRun.board)
        .order_by(ScraperRun.board, ScraperRun.started_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()
