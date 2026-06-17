import httpx
import logging
from scraper.config import settings

log = logging.getLogger(__name__)

async def send_email_message(to_email: str, subject: str, html_content: str) -> None:
    if not settings.resend_api_key or settings.resend_api_key == "re_fake_api_key":
        log.warning(f"Resend API key not configured or mock. Skipping email to {to_email}")
        return

    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": f"Job Radar <{settings.resend_from_email}>",
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post("https://api.resend.com/emails", headers=headers, json=payload)
        response.raise_for_status()

def format_listing_email(listing: dict) -> str:
    salary = f"<div style='font-size: 14px; color: #1d1d1f; margin-bottom: 8px;'>💰 {listing['salary_text']}</div>" if listing.get("salary_text") else ""
    company = listing.get("company") or "Unknown company"
    location = listing.get("location") or "Remote"
    board = listing.get("board", "").capitalize()
    
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
                max-width: 520px;
                margin: 0 auto;
                background-color: #ffffff;
                border: 1px solid #e5e5ea;
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
            }}
            .header {{
                font-size: 14px;
                font-weight: 700;
                color: #0071e3;
                margin-bottom: 12px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .title {{
                font-size: 20px;
                font-weight: 600;
                color: #1d1d1f;
                margin: 0 0 16px 0;
                line-height: 1.25;
            }}
            .detail-row {{
                font-size: 14px;
                color: #6e6e73;
                margin-bottom: 8px;
            }}
            .badge {{
                display: inline-block;
                font-size: 11px;
                font-weight: 500;
                padding: 2px 8px;
                border-radius: 10px;
                background-color: #f5f5f7;
                color: #86868b;
                border: 1px solid #e5e5ea;
                margin-top: 12px;
                text-transform: capitalize;
            }}
            .btn-container {{
                margin-top: 24px;
                text-align: center;
            }}
            .btn {{
                display: inline-block;
                background-color: #0071e3;
                color: #ffffff !important;
                text-decoration: none;
                padding: 10px 20px;
                border-radius: 20px;
                font-weight: 500;
                font-size: 14px;
                transition: background-color 0.2s;
            }}
            .btn:hover {{
                background-color: #0077ed;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">🔎 Job Radar Match</div>
            <h1 class="title">{listing['title']}</h1>
            <div class="detail-row">🏢 <b>{company}</b></div>
            <div class="detail-row">📍 {location}</div>
            {salary}
            <span class="badge">via {board}</span>
            <div class="btn-container">
                <a href="{listing['url']}" target="_blank" class="btn">View Job Listing</a>
            </div>
        </div>
    </body>
    </html>
    """
