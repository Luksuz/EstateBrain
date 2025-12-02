"""
APScheduler service for scheduled scraping tasks.
Runs automatic scraping of njuskalo.hr Varaždin listings every 12 hours.
"""

import asyncio
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from .firecrawl import FirecrawlService
from .parser import SearchPageParser
from .supabase import SupabaseService
from ..models.scrape_job import ScrapeJobCreate
from ..tasks.scraper import run_scrape_task


# Default search URL for Varaždin county real estate
VARAZDIN_SEARCH_URL = "https://www.njuskalo.hr/prodaja-stanova/varazdinska"
VARAZDIN_ZUPANIJA = "Varaždinska"

# Scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


async def scheduled_scrape_varazdin():
    """
    Scheduled task to scrape all Varaždin listings.
    This runs every 12 hours automatically.
    """
    print(f"\n{'='*60}")
    print(f"[Scheduler] Starting scheduled scrape at {datetime.now().isoformat()}")
    print(f"{'='*60}\n")
    
    try:
        firecrawl = FirecrawlService()
        supabase = SupabaseService()
        all_listing_urls = []
        pages_scraped = 0
        
        # Scrape only first 2 pages (new listings appear here)
        max_pages = 2
        
        for page in range(1, max_pages + 1):
            # Build URL with page parameter
            if page == 1:
                url = VARAZDIN_SEARCH_URL
            else:
                separator = "&" if "?" in VARAZDIN_SEARCH_URL else "?"
                url = f"{VARAZDIN_SEARCH_URL}{separator}page={page}"
            
            print(f"[Scheduler] Fetching page {page}: {url}")
            html = await firecrawl.fetch_html(url)
            
            if not html:
                print(f"[Scheduler] Failed to fetch page {page}, stopping")
                break
            
            # Extract listing URLs
            urls = SearchPageParser.extract_listing_urls(html)
            
            if not urls:
                print(f"[Scheduler] No listings found on page {page}, stopping")
                break
            
            all_listing_urls.extend(urls)
            pages_scraped += 1
            
            # Log total pages available (only on first page)
            if page == 1:
                available_pages = SearchPageParser.get_total_pages(html)
                print(f"[Scheduler] Total pages available: {available_pages} (scraping first {max_pages} only)")
            
            # Small delay to be nice to the server
            await asyncio.sleep(1)
        
        # Deduplicate URLs
        unique_urls = list(dict.fromkeys(all_listing_urls))
        
        print(f"\n[Scheduler] Found {len(unique_urls)} unique listings across {pages_scraped} pages")
        
        if not unique_urls:
            print("[Scheduler] No listings found, skipping job creation")
            return
        
        # Check how many already exist in DB
        existing_urls = await supabase.get_existing_urls(unique_urls)
        new_count = len(unique_urls) - len(existing_urls)
        existing_count = len(existing_urls)
        
        print(f"[Scheduler] {new_count} new listings, {existing_count} already exist")
        
        if new_count == 0:
            print("[Scheduler] No new listings to scrape, job completed")
            return
        
        # Create scrape job
        job = ScrapeJobCreate(urls=unique_urls)
        created_job = await supabase.create_scrape_job(job)
        
        print(f"[Scheduler] Created job {created_job.id}, starting scrape...")
        
        # Run the scrape task (skip existing listings)
        # Note: run_scrape_task is synchronous (runs async internally in a thread)
        run_scrape_task(
            job_id=created_job.id,
            urls=unique_urls,
            skip_existing=True,
            zupanija=VARAZDIN_ZUPANIJA
        )
        
        print(f"\n[Scheduler] Scheduled scrape completed at {datetime.now().isoformat()}")
        print(f"[Scheduler] Processed {new_count} new listings")
        
    except Exception as e:
        print(f"[Scheduler] ERROR during scheduled scrape: {e}")
        import traceback
        traceback.print_exc()


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def start_scheduler():
    """Start the scheduler with the scraping job."""
    scheduler = get_scheduler()
    
    if scheduler.running:
        print("[Scheduler] Scheduler already running")
        return
    
    # Add job to run every 12 hours
    scheduler.add_job(
        scheduled_scrape_varazdin,
        trigger=IntervalTrigger(hours=12),
        id="scrape_varazdin_12h",
        name="Scrape Varaždin listings every 12 hours",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )
    
    # Also add a job that runs at specific times (6 AM and 6 PM)
    # This provides more predictable timing
    scheduler.add_job(
        scheduled_scrape_varazdin,
        trigger=CronTrigger(hour="6,18", minute=0),
        id="scrape_varazdin_cron",
        name="Scrape Varaždin at 6 AM and 6 PM",
        replace_existing=True,
        max_instances=1,
    )
    
    # Run first scrape immediately on startup
    scheduler.add_job(
        scheduled_scrape_varazdin,
        id="scrape_varazdin_startup",
        name="Initial scrape on startup",
        replace_existing=True,
    )
    
    scheduler.start()
    
    print("\n" + "="*60)
    print("[Scheduler] Started APScheduler")
    print("[Scheduler] Jobs scheduled:")
    print("  - IMMEDIATE: Running first scrape now")
    print("  - Every 12 hours (interval)")
    print("  - At 6:00 AM and 6:00 PM daily (cron)")
    print(f"  - Scraping: {VARAZDIN_SEARCH_URL}")
    print("  - Pages: First 2 pages only")
    print("="*60 + "\n")


def stop_scheduler():
    """Stop the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[Scheduler] Stopped APScheduler")
    _scheduler = None


async def run_scrape_now():
    """Manually trigger a scrape (for testing or API calls)."""
    print("[Scheduler] Manual scrape triggered")
    await scheduled_scrape_varazdin()


def get_scheduler_status() -> dict:
    """Get current scheduler status and next run times."""
    scheduler = get_scheduler()
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs,
    }

