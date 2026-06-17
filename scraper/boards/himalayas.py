import httpx
from scraper.boards.base import BaseScraper, Listing
import logging

log = logging.getLogger(__name__)

class HimalayasScraper(BaseScraper):
    board_name = "himalayas"
    _URL = "https://himalayas.app/jobs/api?limit=100"

    async def fetch(self, db) -> list[Listing]:
        run_id = self._start_run(db)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(self._URL)
                response.raise_for_status()
                data = response.json()

            jobs = data.get("jobs", [])
            listings = [
                Listing(
                    board=self.board_name,
                    title=job.get("title", "").strip(),
                    company=job.get("company", {}).get("name"),
                    location="Remote",
                    description=job.get("description"),
                    url=job.get("applicationLink") or job.get("url", ""),
                    salary_text=None,
                    posted_at=None,
                )
                for job in jobs
            ]

            self._end_run(db, run_id, found=len(listings), new=0)
            return listings

        except Exception as e:
            self._end_run(db, run_id, found=0, new=0, error=str(e))
            log.error(f"[himalayas] {e}")
            return []
