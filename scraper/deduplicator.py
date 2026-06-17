import hashlib
import uuid
from scraper.boards.base import Listing

def make_fingerprint(listing: Listing) -> str:
    """
    Deterministic fingerprint for deduplication.
    Combines board + company + title, all lowercased, to handle
    the same job appearing across multiple runs.
    """
    raw = "|".join([
        listing.board,
        (listing.company or "").lower().strip(),
        listing.title.lower().strip(),
    ])
    return hashlib.sha256(raw.encode()).hexdigest()

def deduplicate_and_store(db, listings: list[Listing]) -> list[dict]:
    """
    For each listing, attempt an INSERT. If the fingerprint already exists,
    skip (ON CONFLICT DO NOTHING). Return only newly inserted listings as dicts
    with their DB-assigned UUIDs, for the matcher to consume.
    """
    new_listings = []

    with db.cursor() as cur:
        for listing in listings:
            fp = make_fingerprint(listing)
            listing_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO listings
                    (id, board, title, company, location, description, url, salary_text, posted_at, fingerprint)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fingerprint) DO NOTHING
                RETURNING id
            """, (
                listing_id, listing.board, listing.title, listing.company, listing.location,
                listing.description, listing.url, listing.salary_text,
                listing.posted_at, fp
            ))
            db.commit()
            result = cur.fetchone()

            if result:  # None means the ON CONFLICT path was taken
                new_listings.append({
                    "id": listing_id,
                    "board": listing.board,
                    "title": listing.title,
                    "company": listing.company,
                    "location": listing.location,
                    "description": listing.description,
                    "url": listing.url,
                    "salary_text": listing.salary_text,
                })

    return new_listings
