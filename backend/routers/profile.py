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

import httpx
from backend.config import settings

async def send_test_email(to_email: str) -> None:
    if not settings.resend_api_key or settings.resend_api_key == "re_fake_api_key":
        return
    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": f"Job Radar <{settings.resend_from_email}>",
        "to": [to_email],
        "subject": "Job Radar - Resend Integration Test Email",
        "html": f"""
        <html>
            <body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 20px; color: #1d1d1f;">
                <h2 style="color: #0071e3;">🔎 Resend Integration Working!</h2>
                <p>Hello! This email confirms that your Job Radar account is successfully linked to receive remote job alerts via Resend.</p>
                <p>Enjoy your job hunt!</p>
            </body>
        </html>
        """
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post("https://api.resend.com/emails", headers=headers, json=payload)
        response.raise_for_status()

@router.post("/profile/test-email")
async def trigger_test_email(user: User = Depends(get_current_user)):
    try:
        await send_test_email(user.email)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

