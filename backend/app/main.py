from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import scrape_router, listings_router, locations_router, ml_router

settings = get_settings()

app = FastAPI(
    title="Real Estate Scraper API",
    description="API for scraping and managing real estate listings from njuskalo.hr",
    version="1.0.0",
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

