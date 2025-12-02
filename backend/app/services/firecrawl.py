import httpx
from typing import Optional

from ..config import get_settings


class FirecrawlService:
    """Service for fetching HTML content via Firecrawl API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_url = self.settings.firecrawl_api_url
        self.api_key = self.settings.firecrawl_api_key
        print(f"[Firecrawl] Initialized with API URL: {self.api_url}")
        print(f"[Firecrawl] API Key set: {'Yes' if self.api_key else 'No'}")
    
    async def fetch_html(self, url: str, max_age: int = 172800000) -> Optional[str]:
        """
        Fetch HTML content from a URL using Firecrawl API.
        
        Args:
            url: The URL to scrape
            max_age: Cache max age in milliseconds (default 48 hours)
            
        Returns:
            HTML content string or None if failed
        """
        payload = {
            "url": url,
            "onlyMainContent": False,
            "maxAge": max_age,
            "formats": ["rawHtml"],  # Use rawHtml to preserve script tags with coordinates
            "waitFor": 2000,  # Wait 2 seconds for JS to execute
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Extract HTML from response (try rawHtml first, fallback to html)
                if data.get("success") and data.get("data"):
                    return data["data"].get("rawHtml") or data["data"].get("html")
                
                return None
                
            except httpx.HTTPStatusError as e:
                print(f"HTTP error fetching {url}: {e.response.status_code}")
                return None
            except httpx.RequestError as e:
                print(f"Request error fetching {url}: {e}")
                return None
            except Exception as e:
                print(f"Unexpected error fetching {url}: {e}")
                return None
    
    async def fetch_listing_page(self, base_url: str, page: int = 1) -> Optional[str]:
        """
        Fetch a listing page (for getting listing URLs).
        
        Args:
            base_url: Base URL for listings (e.g., https://www.njuskalo.hr/prodaja-stanova/varazdin)
            page: Page number
            
        Returns:
            HTML content string or None if failed
        """
        url = f"{base_url}?page={page}" if page > 1 else base_url
        return await self.fetch_html(url)

