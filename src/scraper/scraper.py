"""Web scraping module using httpx and BeautifulSoup"""
import hashlib
import httpx
from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import difflib


@dataclass
class ScrapeResult:
    """Result of a web scrape"""
    url: str
    status_code: int
    content_hash: str
    text_content: str
    title: Optional[str]
    scraped_at: datetime
    error: Optional[str] = None


class WebScraper:
    """Simple web scraper for monitoring changes"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "ArkWatch/1.0 (Web Monitoring Service)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr,en;q=0.5",
        }
    
    async def scrape(self, url: str) -> ScrapeResult:
        """Scrape a URL and return the result"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Remove script and style elements
                for element in soup(["script", "style", "nav", "footer", "header"]):
                    element.decompose()
                
                # Get text content
                text = soup.get_text(separator="\n", strip=True)
                
                # Get title
                title = soup.title.string if soup.title else None
                
                # Compute hash
                content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
                
                return ScrapeResult(
                    url=url,
                    status_code=response.status_code,
                    content_hash=content_hash,
                    text_content=text,
                    title=title,
                    scraped_at=datetime.utcnow(),
                )
        except Exception as e:
            return ScrapeResult(
                url=url,
                status_code=0,
                content_hash="",
                text_content="",
                title=None,
                scraped_at=datetime.utcnow(),
                error=str(e),
            )
    
    @staticmethod
    def compute_diff(old_content: str, new_content: str) -> tuple[bool, str]:
        """Compare two contents and return diff"""
        if old_content == new_content:
            return False, ""
        
        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile="previous",
            tofile="current",
            lineterm="",
        )
        diff_text = "".join(diff)
        
        return True, diff_text


# Test function
async def test_scraper():
    scraper = WebScraper()
    result = await scraper.scrape("https://example.com")
    print(f"URL: {result.url}")
    print(f"Status: {result.status_code}")
    print(f"Title: {result.title}")
    print(f"Hash: {result.content_hash}")
    print(f"Content length: {len(result.text_content)} chars")
    if result.error:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_scraper())
