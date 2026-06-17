import httpx
import json
import logging
from bs4 import BeautifulSoup
from scraper.boards.base import BaseScraper, Listing

log = logging.getLogger(__name__)

class YCScraper(BaseScraper):
    board_name = "ycombinator"
    _URL = "https://www.ycombinator.com/jobs"

    async def fetch(self, db) -> list[Listing]:
        run_id = self._start_run(db)
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(self._URL)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            listings = []

            # YC Jobs stores its initial react state in a data-page attribute on a div
            component_div = soup.select_one("div[data-page]")
            if not component_div:
                raise ValueError("Could not find div with data-page attribute on YC Jobs page")

            page_data = json.loads(component_div["data-page"])
            props = page_data.get("props", {})
            job_postings = props.get("jobPostings", [])

            for job in job_postings:
                # Resolve relative URL
                job_url = job.get("url") or ""
                if job_url.startswith("/"):
                    url = f"https://www.workatastartup.com{job_url}"
                else:
                    url = job_url

                listings.append(Listing(
                    board=self.board_name,
                    title=job.get("title", "").strip(),
                    company=job.get("companyName"),
                    location=job.get("location") or "Remote",
                    description=job.get("companyOneLiner"),  # Expose company one-liner since full description isn't in this list
                    url=url,
                    salary_text=job.get("salaryRange") or None,
                    posted_at=None,
                ))

            self._end_run(db, run_id, found=len(listings), new=0)
            return listings

        except Exception as e:
            self._end_run(db, run_id, found=0, new=0, error=str(e))
            log.error(f"[ycombinator] {e}")
            return []
