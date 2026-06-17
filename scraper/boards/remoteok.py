import httpx
from datetime import datetime, timezone
from scraper.boards.base import BaseScraper, Listing
import logging

log = logging.getLogger(__name__)

class RemoteOKScraper(BaseScraper):
    board_name = "remoteok"
    _URL = "https://remoteok.com/api"
    _HEADERS = {"User-Agent": "job-radar/1.0 (personal aggregator)"}

    async def fetch(self, db) -> list[Listing]:
        run_id = self._start_run(db)
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(self._URL, headers=self._HEADERS)
                response.raise_for_status()
                data = response.json()

            jobs = [item for item in data if item.get("slug")]

            listings = []
            for job in jobs:
                salary = None
                lo, hi = job.get("salary_min"), job.get("salary_max")
                if lo and hi:
                    salary = f"${lo:,} – ${hi:,}"

                listings.append(Listing(
                    board=self.board_name,
                    title=job.get("position", "").strip(),
                    company=job.get("company"),
                    location=job.get("location") or "Remote",
                    description=job.get("description"),
                    url=job.get("url") or f"https://remoteok.com/l/{job['slug']}",
                    salary_text=salary,
                    posted_at=datetime.fromtimestamp(job["epoch"], tz=timezone.utc) if job.get("epoch") else None,
                ))

            self._end_run(db, run_id, found=len(listings), new=0)
            return listings

        except Exception as e:
            self._end_run(db, run_id, found=0, new=0, error=str(e))
            log.error(f"[remoteok] {e}")
            return []
