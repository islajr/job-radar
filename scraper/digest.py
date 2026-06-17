import asyncio
import logging
from collections import defaultdict
from scraper.database import get_connection
from scraper.notifier.resend_notifier import send_email_message

log = logging.getLogger(__name__)

def format_digest_email(listings: list[dict]) -> str:
    items_html = ""
    for i, l in enumerate(listings, 1):
        salary = f" &bull; 💰 {l['salary_text']}" if l.get("salary_text") else ""
        company = l.get("company") or "Unknown company"
        location = l.get("location") or "Remote"
        board = l.get("board", "").capitalize()
        
        items_html += f"""
        <div style="border-bottom: 1px solid #e5e5ea; padding: 16px 0; margin-bottom: 8px;">
            <div style="font-size: 16px; font-weight: 600; color: #1d1d1f; margin-bottom: 4px;">
                {i}. {l['title']}
            </div>
            <div style="font-size: 14px; color: #6e6e73; margin-bottom: 8px;">
                🏢 <b>{company}</b> &bull; 📍 {location} &bull; via {board}{salary}
            </div>
            <a href="{l['url']}" target="_blank" style="font-size: 14px; color: #0071e3; text-decoration: none; font-weight: 500;">
                View Job Listing &rarr;
            </a>
        </div>
        """
        
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #f5f5f7;
                margin: 0;
                padding: 24px;
            }}
            .container {{
                max-width: 560px;
                margin: 0 auto;
                background-color: #ffffff;
                border: 1px solid #e5e5ea;
                border-radius: 12px;
                padding: 28px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
            }}
            .header {{
                font-size: 14px;
                font-weight: 700;
                color: #0071e3;
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .digest-title {{
                font-size: 22px;
                font-weight: 700;
                color: #1d1d1f;
                margin: 0 0 8px 0;
                line-height: 1.25;
            }}
            .digest-subtitle {{
                font-size: 14px;
                color: #6e6e73;
                margin-bottom: 24px;
                border-bottom: 2px solid #e5e5ea;
                padding-bottom: 12px;
            }}
            .footer {{
                margin-top: 24px;
                font-size: 12px;
                color: #86868b;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">🔎 Job Radar Digest</div>
            <h1 class="digest-title">Your Daily Remote Job Digest</h1>
            <div class="digest-subtitle">We found {len(listings)} new match(es) for your profile today.</div>
            <div>
                {items_html}
            </div>
            <div class="footer">
                You are receiving this because email alerts are enabled for your Job Radar account.
            </div>
        </div>
    </body>
    </html>
    """

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
            user_email = first["email"]

            match_ids_to_mark.extend([l["match_id"] for l in listings])

            if "email" in channels and user_email:
                subject = f"Job Radar: Daily Digest ({len(listings)} new matches)"
                html = format_digest_email(listings)
                tasks.append(send_email_message(user_email, subject, html))

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

