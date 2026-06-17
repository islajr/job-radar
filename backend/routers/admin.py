from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.database import get_db
from backend.models.user import User
from backend.models.profile import UserProfile, NotificationSettings
from backend.models.match import ScraperRun
from backend.schemas.admin import AdminUserView, ScraperRunView
from backend.services.dispatch_service import trigger_scraper_workflow
from backend.dependencies import require_admin

router = APIRouter()

@router.get("/users", response_model=list[AdminUserView])
async def get_users(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    stmt = (
        select(
            User.id,
            User.email,
            User.full_name,
            User.is_active,
            User.is_admin,
            User.created_at,
            UserProfile.alerts_paused,
            NotificationSettings.telegram_connected
        )
        .join(UserProfile, UserProfile.user_id == User.id)
        .join(NotificationSettings, NotificationSettings.user_id == User.id)
    )
    result = await db.execute(stmt)
    users = []
    for r in result.all():
        users.append(AdminUserView(
            id=str(r.id),
            email=r.email,
            full_name=r.full_name,
            is_active=r.is_active,
            is_admin=r.is_admin,
            created_at=r.created_at,
            alerts_paused=r.alerts_paused,
            telegram_connected=r.telegram_connected
        ))
    return users

@router.get("/scraper-runs", response_model=list[ScraperRunView])
async def get_scraper_runs(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    stmt = select(ScraperRun).order_by(desc(ScraperRun.started_at)).limit(50)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/trigger-scrape")
async def trigger_scrape(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    success = await trigger_scraper_workflow()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to trigger scraper workflow via GitHub Actions API")
    return {"ok": True}
