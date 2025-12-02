from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import scrape_router, listings_router, locations_router, ml_router
from .services.scheduler import start_scheduler, stop_scheduler, get_scheduler_status, run_scrape_now

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start/stop scheduler."""
    # Startup
    print("[App] Starting application...")
    start_scheduler()
    yield
    # Shutdown
    print("[App] Shutting down application...")
    stop_scheduler()


app = FastAPI(
    title="Real Estate Scraper API",
    description="API for scraping and managing real estate listings from njuskalo.hr",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(scrape_router, prefix="/api/scrape", tags=["Scraping"])
app.include_router(listings_router, prefix="/api/listings", tags=["Listings"])
app.include_router(locations_router, tags=["Locations"])
app.include_router(ml_router, prefix="/api/ml", tags=["Machine Learning"])


@app.get("/")
async def root():
    return {"message": "Real Estate Scraper API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/scheduler/status", tags=["Scheduler"])
async def scheduler_status():
    """Get the current scheduler status and upcoming job times."""
    return get_scheduler_status()


@app.post("/api/scheduler/trigger", tags=["Scheduler"])
async def trigger_scheduled_scrape(background_tasks: BackgroundTasks):
    """Manually trigger the scheduled Varaždin scrape."""
    background_tasks.add_task(run_scrape_now)
    return {
        "message": "Scheduled scrape triggered",
        "status": "running in background"
    }

