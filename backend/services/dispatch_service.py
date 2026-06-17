import httpx
from backend.config import settings

async def trigger_scraper_workflow() -> bool:
    url = f"https://api.github.com/repos/{settings.github_repo}/actions/workflows/scraper.yml/dispatches"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.github_dispatch_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            },
            json={"ref": "main"},
        )
    return response.status_code == 204  # GitHub returns 204 on success
