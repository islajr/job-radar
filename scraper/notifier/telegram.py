import httpx
from scraper.config import settings

_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

async def send_telegram_message(chat_id: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(f"{_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        })
        response.raise_for_status()

def format_listing_telegram(listing: dict) -> str:
    salary = f"\n💰 {listing['salary_text']}" if listing.get("salary_text") else ""
    company = listing.get("company") or "Unknown company"
    location = listing.get("location") or "Remote"
    board = listing.get("board", "").capitalize()
    return (
        f"<b>{listing['title']}</b>\n"
        f"🏢 {company}\n"
        f"📍 {location}"
        f"{salary}\n"
        f"📋 via {board}\n"
        f"🔗 <a href=\"{listing['url']}\">View listing →</a>"
    )
