from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from backend.database import get_db
from backend.models.user import User
from backend.models.profile import NotificationSettings
from backend.services.telegram_service import generate_connect_token, build_deep_link, send_telegram_message
from backend.dependencies import get_current_user

router = APIRouter()

@router.get("/connect")
async def get_connect_link(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    token, expiry = generate_connect_token()

    result = await db.execute(select(NotificationSettings).where(NotificationSettings.user_id == user.id))
    ns = result.scalar_one_or_none()
    if not ns:
        raise HTTPException(status_code=404, detail="Notification settings not found")
        
    ns.telegram_token = token
    ns.telegram_token_exp = expiry
    await db.commit()

    deep_link = await build_deep_link(token)
    return {"deep_link": deep_link, "expires_at": expiry.isoformat()}

@router.get("/status")
async def telegram_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(NotificationSettings).where(NotificationSettings.user_id == user.id))
    ns = result.scalar_one_or_none()
    if not ns:
        raise HTTPException(status_code=404, detail="Notification settings not found")
    return {"connected": ns.telegram_connected}

@router.post("/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        data = await request.json()
    except Exception:
        return {"ok": True}
        
    message = data.get("message", {})
    text = message.get("text", "")
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not chat_id:
        return {"ok": True}

    if text.startswith("/start "):
        token = text.split(" ", 1)[1].strip()
        result = await db.execute(
            select(NotificationSettings).where(
                NotificationSettings.telegram_token == token,
                NotificationSettings.telegram_token_exp > datetime.utcnow()
            )
        )
        ns = result.scalar_one_or_none()

        if ns:
            ns.telegram_chat_id = chat_id
            ns.telegram_connected = True
            ns.telegram_token = None
            ns.telegram_token_exp = None
            await db.commit()
            await send_telegram_message(chat_id, "✅ Connected! You'll receive job alerts here.")
        else:
            await send_telegram_message(chat_id, "That link has expired or is invalid. Please reconnect from the app.")
    else:
        await send_telegram_message(chat_id, "Hi! Manage your job alerts at the Job Radar app.")

    return {"ok": True}
