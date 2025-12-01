from typing import Optional
from supabase import create_client, Client

from ..config import get_settings
from ..models.listing import ListingCreate, ListingResponse, ListingFilter
from ..models.scrape_job import JobStatus, ScrapeJobCreate, ScrapeJobResponse, ScrapeJobUpdate


_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create Supabase client singleton."""
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        key = settings.supabase_key or settings.supabase_anon_key
        _supabase_client = create_client(settings.supabase_url, key)
    return _supabase_client


class SupabaseService:
    """Service for Supabase database operations."""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    # ==================== SCRAPE JOBS ====================
    
    async def create_scrape_job(self, job: ScrapeJobCreate) -> ScrapeJobResponse:
        """Create a new scrape job."""
        data = {
            "urls": job.urls,
            "total_urls": len(job.urls),
            "processed_urls": 0,
            "status": JobStatus.PENDING.value,
        }
        
        result = self.client.table("scrape_jobs").insert(data).execute()
        return ScrapeJobResponse(**result.data[0])
    
    async def get_scrape_job(self, job_id: str) -> Optional[ScrapeJobResponse]:
        """Get a scrape job by ID."""
        result = self.client.table("scrape_jobs").select("*").eq("id", job_id).execute()
        if result.data:
            return ScrapeJobResponse(**result.data[0])
        return None
    
    async def list_scrape_jobs(self, limit: int = 50, offset: int = 0) -> list[ScrapeJobResponse]:
        """List scrape jobs with pagination."""
        result = (
            self.client.table("scrape_jobs")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return [ScrapeJobResponse(**row) for row in result.data]
    
    async def update_scrape_job(self, job_id: str, update: ScrapeJobUpdate) -> Optional[ScrapeJobResponse]:
        """Update a scrape job."""
        data = {}
        if update.status is not None:
            data["status"] = update.status.value
        if update.processed_urls is not None:
            data["processed_urls"] = update.processed_urls
        if update.error_message is not None:
            data["error_message"] = update.error_message
        
        if not data:
            return await self.get_scrape_job(job_id)
        
        result = self.client.table("scrape_jobs").update(data).eq("id", job_id).execute()
        if result.data:
            return ScrapeJobResponse(**result.data[0])
        return None
    
    # ==================== LISTINGS ====================
    
    def _listing_to_dict(self, listing: ListingCreate) -> dict:
        """Convert ListingCreate to database dictionary."""
        return {
            "external_id": listing.external_id,
            "url": listing.url,
            "title": listing.title,
            "price_eur": listing.price_eur,
            # Location
            "location_city": listing.location_city,
            "location_district": listing.location_district,
            "floor_level": listing.floor_level,
            # Dimensions
            "metadata_area_m2": listing.metadata_area_m2,
            "living_area_m2": listing.living_area_m2,
            "outdoor_area_m2": listing.outdoor_area_m2,
            "area_conflict": listing.area_conflict,
            # Building specs
            "year_built": listing.year_built,
            "is_new_construction": listing.is_new_construction,
            "bedroom_count": listing.bedroom_count,
            "bathroom_count": listing.bathroom_count,
            "parking_type": listing.parking_type.value,
            # Condition
            "construction_phase": listing.construction_phase.value,
            "heating_system": listing.heating_system.value,
            "energy_class": listing.energy_class,
            # Content
            "description": listing.description,
            "images": [img.model_dump() for img in listing.images],
            "rooms": [room.model_dump() for room in listing.rooms],
            "additional_info": listing.additional_info,
            # Seller
            "seller_name": listing.seller_name,
            "seller_contact": listing.seller_contact,
            # Metadata
            "scrape_job_id": listing.scrape_job_id,
            "raw_data": listing.raw_data,
        }
    
    async def create_listing(self, listing: ListingCreate) -> ListingResponse:
        """Create a new listing."""
        data = self._listing_to_dict(listing)
        result = self.client.table("listings").insert(data).execute()
        return ListingResponse(**result.data[0])
    
    async def upsert_listing(self, listing: ListingCreate) -> ListingResponse:
        """Create or update a listing based on URL."""
        data = self._listing_to_dict(listing)
        result = self.client.table("listings").upsert(data, on_conflict="url").execute()
        return ListingResponse(**result.data[0])
    
    async def get_listing(self, listing_id: str) -> Optional[ListingResponse]:
        """Get a listing by ID."""
        result = self.client.table("listings").select("*").eq("id", listing_id).execute()
        if result.data:
            return ListingResponse(**result.data[0])
        return None
    
    async def list_listings(
        self,
        filters: Optional[ListingFilter] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> tuple[list[ListingResponse], int]:
        """List listings with filters and pagination."""
        query = self.client.table("listings").select("*", count="exact")
        
        # Apply filters
        if filters:
            if filters.min_price is not None:
                query = query.gte("price_eur", filters.min_price)
            if filters.max_price is not None:
                query = query.lte("price_eur", filters.max_price)
            if filters.min_area is not None:
                query = query.gte("living_area_m2", filters.min_area)
            if filters.max_area is not None:
                query = query.lte("living_area_m2", filters.max_area)
            if filters.location_city:
                query = query.ilike("location_city", f"%{filters.location_city}%")
            if filters.construction_phase:
                query = query.eq("construction_phase", filters.construction_phase.value)
            if filters.heating_system:
                query = query.eq("heating_system", filters.heating_system.value)
            if filters.parking_type:
                query = query.eq("parking_type", filters.parking_type.value)
            if filters.is_new_construction is not None:
                query = query.eq("is_new_construction", filters.is_new_construction)
            if filters.min_bedrooms is not None:
                query = query.gte("bedroom_count", filters.min_bedrooms)
            
            # ML feature completeness filter - require essential features for ML predictions
            if filters.require_ml_features:
                # Required: price_eur, living_area_m2, bedroom_count, bathroom_count, location_district
                query = query.not_.is_("price_eur", "null")
                query = query.gte("price_eur", 1000)  # Filter out invalid/placeholder prices
                query = query.not_.is_("living_area_m2", "null")
                query = query.gte("living_area_m2", 10)  # Filter out invalid areas
                query = query.not_.is_("bedroom_count", "null")
                query = query.gte("bedroom_count", 0)
                query = query.not_.is_("bathroom_count", "null")
                query = query.gte("bathroom_count", 0)
                query = query.not_.is_("location_district", "null")
                query = query.neq("location_district", "")  # Filter out empty strings
        
        # Apply sorting and pagination
        query = query.order(sort_by, desc=sort_desc).range(offset, offset + limit - 1)
        
        result = query.execute()
        total = result.count or 0
        listings = [ListingResponse(**row) for row in result.data]
        
        return listings, total
    
    async def delete_listing(self, listing_id: str) -> bool:
        """Delete a listing by ID."""
        result = self.client.table("listings").delete().eq("id", listing_id).execute()
        return len(result.data) > 0
    
    async def get_existing_urls(self, urls: list[str]) -> set[str]:
        """
        Check which URLs already exist in the database.
        
        Args:
            urls: List of URLs to check
            
        Returns:
            Set of URLs that already exist in the database
        """
        if not urls:
            return set()
        
        existing = set()
        
        # Process in batches to avoid query string length limits
        # PostgREST/Supabase can fail with "Bad Request" if too many items in .in_()
        batch_size = 50
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            try:
                result = self.client.table("listings").select("url").in_("url", batch).execute()
                existing.update(row["url"] for row in result.data)
            except Exception as e:
                print(f"[Supabase] Error checking existing URLs batch {i//batch_size}: {e}")
                # Continue with other batches even if one fails
        
        return existing
    
    async def get_listing_by_url(self, url: str) -> Optional[ListingResponse]:
        """Get a listing by URL."""
        result = self.client.table("listings").select("*").eq("url", url).execute()
        if result.data:
            return ListingResponse(**result.data[0])
        return None
