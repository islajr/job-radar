import secrets
from datetime import datetime, timedelta
import httpx
from backend.config import settings

cached_bot_username = None

async def get_bot_username() -> str:
    global cached_bot_username
    if cached_bot_username:
        return cached_bot_username
    
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            if data.get("ok"):
                cached_bot_username = data["result"]["username"]
                return cached_bot_username
        except Exception:
            pass
    return "JobRadarBot"  # fallback

def generate_connect_token() -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(minutes=15)
    return token, expiry

async def build_deep_link(token: str) -> str:
    username = await get_bot_username()
    return f"https://t.me/{username}?start={token}"

async def send_telegram_message(chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        })
