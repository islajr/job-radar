import asyncio
import logging
from scraper.notifier.telegram import send_telegram_message, format_listing_telegram

log = logging.getLogger(__name__)

async def _send_one(match: dict) -> None:
    tasks = []
    listing = match["listing"]

    if "telegram" in match["channels"] and match.get("telegram_chat_id"):
        tasks.append(send_telegram_message(
            chat_id=match["telegram_chat_id"],
            text=format_listing_telegram(listing)
        ))

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                log.error(f"Notification failed for user {match['user_id']}: {r}")

async def dispatch_immediate_notifications(db, matches: list[dict]) -> None:
    await asyncio.gather(*[_send_one(m) for m in matches], return_exceptions=True)
    # Mark all as notified
    with db.cursor() as cur:
        for m in matches:
            cur.execute(
                "UPDATE user_matches SET notified_at = now() WHERE user_id = %s AND listing_id = %s",
                (m["user_id"], m["listing_id"])
            )
        db.commit()
