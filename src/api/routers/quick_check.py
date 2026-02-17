"""Quick check endpoint - monitor any URL without signup"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
import asyncio

from ...scraper.scraper import _is_safe_url, WebScraper

router = APIRouter()


class QuickCheckRequest(BaseModel):
    url: HttpUrl


class QuickCheckResponse(BaseModel):
    url: str
    status: str
    message: str
    baseline: dict | None = None


@router.post("/quick-check")
async def quick_check(request: QuickCheckRequest):
    """
    Quick check endpoint - no authentication required.
    Monitors a URL immediately and returns baseline snapshot.
    """
    url = str(request.url)

    # SSRF protection
    safe, reason, _ = _is_safe_url(url)
    if not safe:
        raise HTTPException(
            status_code=400,
            detail=f"URL not allowed: {reason}"
        )

    try:
        # Scrape the URL immediately
        scraper = WebScraper(timeout=15)
        result = await asyncio.wait_for(
            scraper.scrape(url),
            timeout=20.0
        )

        if result.error:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to check URL: {result.error}"
            )

        # Return baseline snapshot
        return QuickCheckResponse(
            url=url,
            status="monitoring_started",
            message="Baseline captured. We'll watch for changes and notify you when we detect them.",
            baseline={
                "timestamp": result.scraped_at.isoformat(),
                "title": result.title,
                "status_code": result.status_code,
                "content_hash": result.content_hash[:16],
            }
        )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="Check timed out. URL took too long to respond."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking URL: {str(e)}"
        )
