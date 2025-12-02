import asyncio
import threading
from typing import Optional, Tuple, Type
from dataclasses import dataclass

from ..models.scrape_job import JobStatus, ScrapeJobUpdate
from ..services.firecrawl import FirecrawlService
from ..services.parser import ListingParser
from ..services.crozilla_parser import CrozillaListingParser
from ..services.supabase import SupabaseService


def get_parser_for_url(url: str) -> Type:
    """
    Get the appropriate parser class based on the URL domain.
    
    Args:
        url: The listing URL
        
    Returns:
        Parser class (ListingParser or CrozillaListingParser)
    """
    if "crozilla.com" in url:
        return CrozillaListingParser
    else:
        # Default to njuskalo parser
        return ListingParser

# Maximum concurrent Firecrawl requests
MAX_CONCURRENT_SCRAPES = 5


@dataclass
class ScrapeResult:
    """Result of a single URL scrape operation."""
    url: str
    success: bool
    error_message: Optional[str] = None


async def scrape_single_url(
    url: str,
    job_id: str,
    firecrawl: FirecrawlService,
    supabase: SupabaseService,
    semaphore: asyncio.Semaphore,
    location_context: dict = None,
) -> ScrapeResult:
    """
    Scrape a single URL with semaphore-controlled concurrency.
    Automatically detects the source (njuskalo/crozilla) and uses the appropriate parser.
    
    Args:
        url: The listing URL to scrape
        job_id: The scrape job ID
        firecrawl: Firecrawl service instance
        supabase: Supabase service instance
        semaphore: Semaphore for controlling concurrent requests
        location_context: Optional location context for LLM
        
    Returns:
        ScrapeResult with success status and any error message
    """
    async with semaphore:
        # Determine which parser to use based on URL
        parser_class = get_parser_for_url(url)
        source_name = "crozilla" if parser_class == CrozillaListingParser else "njuskalo"
        print(f"[Scraper] Processing URL ({source_name}): {url}")
        
        try:
            # Fetch HTML content (async)
            html_content = await firecrawl.fetch_html(url)
            # Save HTML to disk for debugging/auditing
            if html_content:
                print(f"[Scraper] Got HTML for {url} (length: {len(html_content)})")
                # Try to derive a safe filename from the URL
                import hashlib, os
                html_dir = "scraped_html"
                os.makedirs(html_dir, exist_ok=True)
                url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
                filename = os.path.join(html_dir, f"{url_hash}.html")
                try:
                    with open(filename, "w", encoding="utf-8") as html_file:
                        html_file.write(html_content)
                    print(f"[Scraper] Saved HTML to {filename}")
                except Exception as e:
                    print(f"[Scraper] Failed to save HTML for {url}: {e}")
            else:
                print(f"[Scraper] No HTML fetched for {url} (empty response)")
            if html_content:
                print(f"[Scraper] Got HTML for {url}, parsing with {source_name} parser...")
                # Parse the HTML using appropriate parser with location context
                listing_data = await parser_class.parse(html_content, url, location_context=location_context)
                listing_data.scrape_job_id = job_id
                # Save to database (upsert to handle duplicates)
                await supabase.upsert_listing(listing_data)
                print(f"[Scraper] Saved listing for {url}")
                return ScrapeResult(url=url, success=True)
            else:
                error_msg = f"Failed to fetch HTML"
                print(f"[Scraper] {error_msg} for {url}")
                return ScrapeResult(url=url, success=False, error_message=error_msg)
            
        except Exception as e:
            error_msg = str(e)
            print(f"[Scraper] Error processing {url}: {error_msg}")
            return ScrapeResult(url=url, success=False, error_message=error_msg)


async def scrape_listings_task(job_id: str, urls: list[str], skip_existing: bool = True, zupanija: str = None) -> None:
    """
    Background task to scrape listings from provided URLs with async concurrency.
    
    Uses asyncio.Semaphore to limit concurrent Firecrawl requests to MAX_CONCURRENT_SCRAPES.
    LLM classification is also done asynchronously.
    
    Args:
        job_id: The scrape job ID to track progress
        urls: List of listing URLs to scrape
        skip_existing: If True, skip URLs that already exist in DB
        zupanija: Optional županija name for location context
    """
    supabase = SupabaseService()
    firecrawl = FirecrawlService()
    
    # Get location context for LLM if županija is provided
    location_context = None
    if zupanija:
        from ..locations_config.locations import get_location_context
        location_context = get_location_context(zupanija)
        print(f"[Scraper] Using location context: city={location_context.get('city')}, {len(location_context.get('districts', []))} districts, {len(location_context.get('neighborhoods', []))} neighborhoods")
    
    print(f"[Scraper] Starting job {job_id} with {len(urls)} URLs (max {MAX_CONCURRENT_SCRAPES} concurrent)")
    
    # Update job status to running
    await supabase.update_scrape_job(
        job_id,
        ScrapeJobUpdate(status=JobStatus.RUNNING)
    )
    
    # Check which URLs already exist in database
    urls_to_process = urls
    skipped_count = 0
    
    if skip_existing:
        existing_urls = await supabase.get_existing_urls(urls)
        urls_to_process = [url for url in urls if url not in existing_urls]
        skipped_count = len(urls) - len(urls_to_process)
        
        if skipped_count > 0:
            print(f"[Scraper] Skipping {skipped_count} existing listings, processing {len(urls_to_process)} new ones")
            
            # Update progress immediately to show skipped count
            await supabase.update_scrape_job(
                job_id,
                ScrapeJobUpdate(processed_urls=skipped_count)
            )
    
    # Create semaphore for concurrent request limiting
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)
    
    # Track progress
    processed = 0
    errors = []
    new_listings = 0
    
    # Progress tracking lock
    progress_lock = asyncio.Lock()
    
    async def process_with_progress(url: str) -> ScrapeResult:
        """Process a URL and update progress."""
        nonlocal processed, new_listings
        
        result = await scrape_single_url(url, job_id, firecrawl, supabase, semaphore, location_context)
        
        # Update progress atomically
        async with progress_lock:
            processed += 1
            if result.success:
                new_listings += 1
            
            # Update job progress
            await supabase.update_scrape_job(
                job_id,
                ScrapeJobUpdate(processed_urls=skipped_count + processed)
            )
        
        return result
    
    # Process all URLs concurrently with semaphore limiting
    if urls_to_process:
        print(f"[Scraper] Starting async processing of {len(urls_to_process)} URLs...")
        tasks = [process_with_progress(url) for url in urls_to_process]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect errors
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            elif isinstance(result, ScrapeResult) and not result.success:
                errors.append(f"{result.url}: {result.error_message}")
    
    # Update final status
    final_status = JobStatus.COMPLETED
    
    # Build summary message
    summary_parts = []
    if skipped_count > 0:
        summary_parts.append(f"Skipped {skipped_count} existing")
    summary_parts.append(f"Processed {new_listings} new")
    if errors:
        summary_parts.append(f"Errors: {len(errors)}")
        # Only include first 10 errors to avoid huge messages
        summary_parts.append("\n".join(errors[:10]))
        if len(errors) > 10:
            summary_parts.append(f"... and {len(errors) - 10} more errors")
    
    error_message = " | ".join(summary_parts) if summary_parts else None
    
    await supabase.update_scrape_job(
        job_id,
        ScrapeJobUpdate(
            status=final_status,
            error_message=error_message,
        )
    )
    
    print(f"[Scraper] Job {job_id} completed. Skipped: {skipped_count}, New: {new_listings}, Errors: {len(errors)}")


def run_scrape_task(job_id: str, urls: list[str], skip_existing: bool = True, zupanija: str = None) -> None:
    """
    Synchronous wrapper to run the async scrape task in a new thread with its own event loop.
    Used by FastAPI's BackgroundTasks.
    
    Args:
        job_id: The scrape job ID
        urls: List of URLs to scrape
        skip_existing: Whether to skip existing URLs
        zupanija: Optional županija name for location context
    """
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(scrape_listings_task(job_id, urls, skip_existing, zupanija))
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
