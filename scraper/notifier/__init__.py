import asyncio
import logging
from scraper.notifier.resend_notifier import send_email_message, format_listing_email

log = logging.getLogger(__name__)

async def _send_one(match: dict) -> None:
    tasks = []
    listing = match["listing"]

    if "email" in match["channels"] and match.get("email"):
        tasks.append(send_email_message(
            to_email=match["email"],
            subject=f"Job Match: {listing.get('title', 'New Remote Role')}",
            html_content=format_listing_email(listing)
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

