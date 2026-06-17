import asyncio
import logging
from scraper.boards.remoteok import RemoteOKScraper
from scraper.boards.himalayas import HimalayasScraper
from scraper.boards.ycombinator import YCScraper
from scraper.deduplicator import deduplicate_and_store
from scraper.matcher import match_all_users
from scraper.notifier import dispatch_immediate_notifications
from scraper.database import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SCRAPERS = [RemoteOKScraper, HimalayasScraper, YCScraper]

async def run():
    db = get_connection()

    # Run all scrapers concurrently; failures are captured, not raised
    results = await asyncio.gather(
        *[cls().fetch(db) for cls in SCRAPERS],
        return_exceptions=True
    )

    all_listings = []
    for scraper_cls, result in zip(SCRAPERS, results):
        if isinstance(result, Exception):
            log.error(f"[{scraper_cls.board_name}] Failed: {result}")
        else:
            log.info(f"[{scraper_cls.board_name}] Fetched {len(result)} listings")
            all_listings.extend(result)

    new_listings = deduplicate_and_store(db, all_listings)
    log.info(f"New listings stored: {len(new_listings)}")

    # Update the new_listings metrics in scraper_runs
    if new_listings:
        new_by_board = {}
        for l in new_listings:
            b = l["board"]
            new_by_board[b] = new_by_board.get(b, 0) + 1

        with db.cursor() as cur:
            for board, count in new_by_board.items():
                cur.execute(
                    """UPDATE scraper_runs
                       SET new_listings = %s
                       WHERE board = %s AND id = (
                           SELECT id FROM scraper_runs
                           WHERE board = %s
                           ORDER BY started_at DESC
                           LIMIT 1
                       )""",
                    (count, board, board)
                )
            db.commit()

        matches = match_all_users(db, new_listings)
        log.info(f"Matches found: {len(matches)}")
        await dispatch_immediate_notifications(db, matches)

    db.close()

if __name__ == "__main__":
    asyncio.run(run())
