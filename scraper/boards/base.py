from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import logging

log = logging.getLogger(__name__)

@dataclass
class Listing:
    board:        str
    title:        str
    url:          str
    company:      Optional[str] = None
    location:     Optional[str] = None
    description:  Optional[str] = None
    salary_text:  Optional[str] = None
    posted_at:    Optional[datetime] = None

class BaseScraper(ABC):
    board_name: str = ""

    @abstractmethod
    async def fetch(self, db) -> list[Listing]:
        """
        Fetch all current listings from the board.
        Must log a scraper_runs row on both success and failure.
        Must not raise — return an empty list on failure and log the error.
        """
        pass

    def _start_run(self, db) -> str:
        """Insert a scraper_runs row with status='running'. Returns the run ID."""
        import uuid
        run_id = str(uuid.uuid4())
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO scraper_runs (id, board, started_at, status, listings_found, new_listings)
                   VALUES (%s, %s, %s, 'running', 0, 0)""",
                (run_id, self.board_name, datetime.now(timezone.utc))
            )
            db.commit()
            return run_id

    def _end_run(self, db, run_id: str, found: int, new: int, error: str = None):
        status = "failed" if error and found == 0 else ("partial" if error else "success")
        with db.cursor() as cur:
            cur.execute(
                """UPDATE scraper_runs
                   SET completed_at=%s, listings_found=%s, new_listings=%s, errors=%s, status=%s
                   WHERE id=%s""",
                (datetime.now(timezone.utc), found, new, error, status, run_id)
            )
            db.commit()
