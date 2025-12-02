from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum

from ..models.scrape_job import ScrapeJobCreate, ScrapeJobResponse
from ..services.supabase import SupabaseService
from ..services.firecrawl import FirecrawlService
from ..services.parser import SearchPageParser
from ..services.crozilla_parser import CrozillaSearchParser
from ..tasks.scraper import run_scrape_task


class ScrapeSource(str, Enum):
    """Available scraping sources."""
    NJUSKALO = "njuskalo"
    CROZILLA = "crozilla"


# Source configurations with default search URLs
SOURCE_CONFIG = {
    ScrapeSource.NJUSKALO: {
        "name": "Njuškalo",
        "domain": "njuskalo.hr",
        "default_search_url": "https://www.njuskalo.hr/prodaja-stanova/varazdinska",
        "parser": SearchPageParser,
    },
    ScrapeSource.CROZILLA: {
        "name": "Crozilla",
        "domain": "crozilla.com",
        "default_search_url": "https://www.crozilla.com/na_prodaju-stanovi/varazdinska",
        "parser": CrozillaSearchParser,
    },
}


def get_search_parser_for_source(source: ScrapeSource):
    """Get the search parser for a specific source."""
    return SOURCE_CONFIG[source]["parser"]


def detect_source_from_url(url: str) -> ScrapeSource:
    """Auto-detect source from URL domain."""
    if "crozilla.com" in url:
        return ScrapeSource.CROZILLA
    else:
        return ScrapeSource.NJUSKALO


router = APIRouter()


class SearchPageRequest(BaseModel):
    """Request to scrape listings from a search results page."""
    source: Optional[ScrapeSource] = Field(
        None, 
        description="Source marketplace (njuskalo or crozilla). If not provided, auto-detected from URL."
    )
    search_url: Optional[str] = Field(
        None,
        description="Search URL to scrape. If not provided, uses default URL for selected source."
    )
    max_pages: int = 1  # How many pages to scrape (default 1) - DEPRECATED, use start_page/end_page
    start_page: int = 1  # Starting page number (1-100)
    end_page: Optional[int] = None  # Ending page number (1-100), if None uses max_pages from start_page
    force_rescrape: bool = False  # If True, re-scrape even existing listings
    zupanija: Optional[str] = Field("Varaždinska", description="The županija name for location context")


class ExtractedUrlsResponse(BaseModel):
    """Response with extracted listing URLs."""
    source: str
    search_url: str
    pages_scraped: int
    total_listings: int
    new_listings: int
    existing_listings: int
    listing_urls: List[str]
    job_id: Optional[str] = None


class SourceInfo(BaseModel):
    """Information about a scraping source."""
    id: str
    name: str
    domain: str
    default_search_url: str


class SourcesResponse(BaseModel):
    """Response with available sources."""
    sources: List[SourceInfo]


@router.get("/sources", response_model=SourcesResponse)
async def get_available_sources():
    """
    Get list of available scraping sources.
    
    Returns source info including default search URLs for easy frontend integration.
    """
    sources = [
        SourceInfo(
            id=source.value,
            name=config["name"],
            domain=config["domain"],
            default_search_url=config["default_search_url"],
        )
        for source, config in SOURCE_CONFIG.items()
    ]
    return SourcesResponse(sources=sources)


@router.post("/from-search", response_model=ExtractedUrlsResponse)
async def scrape_from_search_page(
    request: SearchPageRequest,
    background_tasks: BackgroundTasks,
):
    """
    Extract listing URLs from a search results page and start scraping them.
    
    Supports both njuskalo.hr and crozilla.com:
    - njuskalo: https://www.njuskalo.hr/prodaja-stanova/varazdinska
    - crozilla: https://www.crozilla.com/na_prodaju-stanovi/varazdinska
    
    You can either:
    1. Specify `source` to use the default search URL for that marketplace
    2. Specify `search_url` to use a custom URL (source auto-detected)
    3. Specify both to use your custom URL with explicit source
    
    This will:
    1. Determine the source (from request or auto-detect)
    2. Fetch the search results page(s)
    3. Extract all individual listing URLs
    4. Create a scrape job for those listings
    5. Return the extracted URLs and job ID
    """
    firecrawl = FirecrawlService()
    all_listing_urls = []
    pages_scraped = 0
    
    # Determine source and search URL
    if request.source and not request.search_url:
        # Source specified, use default URL
        source = request.source
        search_url = SOURCE_CONFIG[source]["default_search_url"]
    elif request.search_url and not request.source:
        # URL specified, auto-detect source
        source = detect_source_from_url(request.search_url)
        search_url = request.search_url
    elif request.source and request.search_url:
        # Both specified, use as-is
        source = request.source
        search_url = request.search_url
    else:
        # Neither specified, default to njuskalo
        source = ScrapeSource.NJUSKALO
        search_url = SOURCE_CONFIG[source]["default_search_url"]
    
    # Get the appropriate parser
    search_parser = get_search_parser_for_source(source)
    source_name = source.value
    
    # Determine page range
    start_page = max(1, min(request.start_page, 100))  # Clamp to 1-100
    
    if request.end_page is not None:
        # Use explicit page range
        end_page = max(start_page, min(request.end_page, 100))  # Clamp to start_page-100
    else:
        # Fallback to max_pages from start_page (backward compatibility)
        end_page = min(start_page + request.max_pages - 1, 100)
    
    total_pages_to_scrape = end_page - start_page + 1
    
    print(f"[Scrape] Extracting listings from {search_url} ({source_name}, pages {start_page}-{end_page}, {total_pages_to_scrape} pages)")
    
    for page in range(start_page, end_page + 1):
        # Build URL with page parameter
        if page == 1:
            url = search_url
        else:
            # Different pagination formats per source
            if source == ScrapeSource.CROZILLA:
                # Crozilla uses /page_X format
                # Remove trailing slash if present, then append /page_X
                base_url = search_url.rstrip("/")
                url = f"{base_url}/page_{page}"
            else:
                # Njuskalo uses ?page=X or &page=X format
                separator = "&" if "?" in search_url else "?"
                url = f"{search_url}{separator}page={page}"
        
        print(f"[Scrape] Fetching page {page}: {url}")
        html = await firecrawl.fetch_html(url)

        if not html:
            print(f"[Scrape] Failed to fetch page {page}")
            break
        
        # Extract listing URLs using appropriate parser
        urls = search_parser.extract_listing_urls(html)
        
        if not urls:
            print(f"[Scrape] No listings found on page {page}, stopping")
            break
        
        all_listing_urls.extend(urls)
        pages_scraped += 1
        
        # Check if we should continue to next page (only check once on first page we scrape)
        if page == start_page:
            available_pages = search_parser.get_total_pages(html)
            print(f"[Scrape] Total pages available: {available_pages}")
            if available_pages < end_page:
                end_page = available_pages
                print(f"[Scrape] Adjusted end_page to {end_page} (max available)")
    
    # Deduplicate URLs
    unique_urls = list(dict.fromkeys(all_listing_urls))
    
    print(f"[Scrape] Found {len(unique_urls)} unique listings across {pages_scraped} pages")
    
    if not unique_urls:
        return ExtractedUrlsResponse(
            source=source_name,
            search_url=search_url,
            pages_scraped=pages_scraped,
            total_listings=0,
            new_listings=0,
            existing_listings=0,
            listing_urls=[],
            job_id=None
        )
    
    # Check how many already exist in DB
    supabase = SupabaseService()
    existing_urls = await supabase.get_existing_urls(unique_urls)
    new_count = len(unique_urls) - len(existing_urls)
    existing_count = len(existing_urls)
    
    print(f"[Scrape] {new_count} new listings, {existing_count} already exist")
    
    # Create scrape job for the extracted URLs
    job = ScrapeJobCreate(urls=unique_urls)
    created_job = await supabase.create_scrape_job(job)
    
    # Start background scraping task (skip_existing=True unless force_rescrape)
    skip_existing = not request.force_rescrape
    background_tasks.add_task(run_scrape_task, created_job.id, unique_urls, skip_existing, request.zupanija)
    
    return ExtractedUrlsResponse(
        source=source_name,
        search_url=search_url,
        pages_scraped=pages_scraped,
        total_listings=len(unique_urls),
        new_listings=new_count,
        existing_listings=existing_count,
        listing_urls=unique_urls,
        job_id=created_job.id
    )


@router.post("/jobs", response_model=ScrapeJobResponse)
async def create_scrape_job(
    job: ScrapeJobCreate,
    background_tasks: BackgroundTasks,
):
    """
    Create a new scrape job with a list of individual listing URLs.
    
    The job will be processed in the background. Use GET /jobs/{id} to check progress.
    """
    # Deduplicate URLs
    unique_urls = list(dict.fromkeys(job.urls))
    job.urls = unique_urls
    
    if not job.urls:
        raise HTTPException(status_code=400, detail="At least one URL is required")
    
    if len(job.urls) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 URLs per job")
    
    # Create the job in the database
    supabase = SupabaseService()
    created_job = await supabase.create_scrape_job(job)
    
    # Start background task
    background_tasks.add_task(run_scrape_task, created_job.id, job.urls)
    
    return created_job


@router.get("/jobs", response_model=list[ScrapeJobResponse])
async def list_scrape_jobs(
    limit: int = 50,
    offset: int = 0,
):
    """List all scrape jobs with pagination."""
    supabase = SupabaseService()
    jobs = await supabase.list_scrape_jobs(limit=limit, offset=offset)
    return jobs


@router.get("/jobs/{job_id}", response_model=ScrapeJobResponse)
async def get_scrape_job(job_id: str):
    """Get a specific scrape job by ID."""
    supabase = SupabaseService()
    job = await supabase.get_scrape_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

