import logging
import uuid

log = logging.getLogger(__name__)

def listing_matches_profile(listing: dict, profile: dict) -> bool:
    """
    Returns True if the listing passes the user's keyword filters.
    Matching is against a concatenation of title, description, and company.
    Case-insensitive. Partial word match is intentional.
    """
    if profile.get("alerts_paused"):
        return False

    searchable = " ".join(filter(None, [
        listing.get("title", ""),
        listing.get("description") or "",
        listing.get("company") or "",
    ])).lower()

    inclusion = [kw.lower().strip() for kw in profile.get("inclusion_keywords", []) if kw.strip()]
    exclusion = [kw.lower().strip() for kw in profile.get("exclusion_keywords", []) if kw.strip()]

    if inclusion and not any(kw in searchable for kw in inclusion):
        return False

    if any(kw in searchable for kw in exclusion):
        return False

    return True

def match_all_users(db, new_listings: list[dict]) -> list[dict]:
    """
    Cross-product of new_listings × active users.
    Inserts matching rows into user_matches (ON CONFLICT DO NOTHING handles
    re-runs safely). Returns match records for users on 'immediate' frequency.
    """
    immediate_matches = []

    with db.cursor() as cur:
        # Fetch active users who completed onboarding
        cur.execute("""
            SELECT
                u.id, u.email,
                up.inclusion_keywords, up.exclusion_keywords, up.alerts_paused,
                ns.channels, ns.frequency, ns.telegram_chat_id, ns.telegram_connected
            FROM users u
            JOIN user_profiles up ON up.user_id = u.id
            JOIN notification_settings ns ON ns.user_id = u.id
            WHERE u.is_active = TRUE
              AND up.alerts_paused = FALSE
              AND up.onboarding_complete = TRUE
        """)
        users = cur.fetchall()

        for listing in new_listings:
            for user in users:
                user_id, email, inclusion, exclusion, alerts_paused, channels, frequency, telegram_chat_id, telegram_connected = user

                profile = {
                    "inclusion_keywords": inclusion,
                    "exclusion_keywords": exclusion,
                    "alerts_paused": alerts_paused,
                }

                if not listing_matches_profile(listing, profile):
                    continue

                match_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO user_matches (id, user_id, listing_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, listing_id) DO NOTHING
                """, (match_id, user_id, listing["id"]))
                db.commit()

                if frequency == "immediate":
                    immediate_matches.append({
                        "user_id": str(user_id),
                        "listing_id": listing["id"],
                        "listing": listing,
                        "channels": channels or [],
                        "telegram_chat_id": telegram_chat_id if telegram_connected else None,
                        "email": email,
                    })

    log.info(f"Total immediate matches to notify: {len(immediate_matches)}")
    return immediate_matches
