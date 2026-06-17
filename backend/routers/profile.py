from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.user import User
from backend.models.profile import UserProfile, NotificationSettings
from backend.schemas.profile import ProfileUpdate, NotificationSettingsUpdate, UserProfileOut, NotificationSettingsOut
from backend.dependencies import get_current_user

router = APIRouter()

@router.get("/profile", response_model=UserProfileOut)
async def get_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/profile", response_model=UserProfileOut)
async def update_profile(body: ProfileUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(profile, key, val)
        
    await db.commit()
    await db.refresh(profile)
    return profile

@router.get("/notifications", response_model=NotificationSettingsOut)
async def get_notifications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NotificationSettings).where(NotificationSettings.user_id == user.id))
    ns = result.scalar_one_or_none()
    if not ns:
        raise HTTPException(status_code=404, detail="Notification settings not found")
    return ns

@router.put("/notifications", response_model=NotificationSettingsOut)
async def update_notifications(body: NotificationSettingsUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NotificationSettings).where(NotificationSettings.user_id == user.id))
    ns = result.scalar_one_or_none()
    if not ns:
        raise HTTPException(status_code=404, detail="Notification settings not found")
    
    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(ns, key, val)
        
    await db.commit()
    await db.refresh(ns)
    return ns
