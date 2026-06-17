import asyncio
import logging
from collections import defaultdict
from scraper.database import get_connection
from scraper.notifier.telegram import send_telegram_message

log = logging.getLogger(__name__)

async def send_digest():
    db = get_connection()
    pending = []

    with db.cursor() as cur:
        cur.execute("""
            SELECT
                u.id AS user_id, u.email,
                um.listing_id, um.id AS match_id,
                l.title, l.company, l.location, l.url, l.salary_text, l.board,
                ns.channels, ns.telegram_chat_id, ns.telegram_connected, ns.frequency
            FROM user_matches um
            JOIN users u ON u.id = um.user_id
            JOIN listings l ON l.id = um.listing_id
            JOIN notification_settings ns ON ns.user_id = u.id
            JOIN user_profiles up ON up.user_id = u.id
            WHERE um.notified_at IS NULL
              AND ns.frequency = 'digest'
              AND up.alerts_paused = FALSE
              AND u.is_active = TRUE
            ORDER BY u.id, um.created_at
        """)
        pending = cur.fetchall()

        # Group by user
        by_user = defaultdict(list)
        for row in pending:
            user_id = str(row[0])
            by_user[user_id].append({
                "email": row[1],
                "listing_id": row[2],
                "match_id": row[3],
                "title": row[4],
                "company": row[5],
                "location": row[6],
                "url": row[7],
                "salary_text": row[8],
                "board": row[9],
                "channels": row[10],
                "telegram_chat_id": row[11],
                "telegram_connected": row[12],
                "frequency": row[13]
            })

        tasks = []
        match_ids_to_mark = []

        for user_id, listings in by_user.items():
            first = listings[0]
            channels = first["channels"] or []
            telegram_chat_id = first["telegram_chat_id"] if first["telegram_connected"] else None

            match_ids_to_mark.extend([l["match_id"] for l in listings])

            if "telegram" in channels and telegram_chat_id:
                text = f"📋 <b>Your daily job digest — {len(listings)} new match(es)</b>\n\n"
                for i, l in enumerate(listings, 1):
                    salary = f" · {l['salary_text']}" if l.get("salary_text") else ""
                    text += f"{i}. <b>{l['title']}</b> at {l.get('company','?')}{salary}\n<a href=\"{l['url']}\">View →</a>\n\n"
                tasks.append(send_telegram_message(telegram_chat_id, text))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Mark all as notified
        for match_id in match_ids_to_mark:
            cur.execute("UPDATE user_matches SET notified_at = now() WHERE id = %s", (match_id,))
        db.commit()
        
    db.close()
    log.info(f"Digest sent to {len(by_user)} user(s), covering {len(match_ids_to_mark)} match(es)")

if __name__ == "__main__":
    asyncio.run(send_digest())
