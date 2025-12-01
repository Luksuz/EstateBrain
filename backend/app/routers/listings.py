from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..models.listing import (
    ListingResponse,
    ListingFilter,
    ConstructionPhase,
    HeatingSystem,
    ParkingType,
)
from ..services.supabase import SupabaseService

router = APIRouter()


@router.get("", response_model=dict)
async def list_listings(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    location_city: Optional[str] = None,
    construction_phase: Optional[ConstructionPhase] = None,
    heating_system: Optional[HeatingSystem] = None,
    parking_type: Optional[ParkingType] = None,
    is_new_construction: Optional[bool] = None,
    min_bedrooms: Optional[int] = None,
    require_ml_features: bool = Query(default=False, description="Only return listings with complete ML features (price, area, bedrooms, bathrooms, location)"),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at"),
    sort_desc: bool = Query(default=True),
):
    """List all listings with optional filters and pagination.
    
    Use require_ml_features=true to only get listings with complete data for ML predictions:
    - price_eur (>= 1000€)
    - living_area_m2 (>= 10m²)
    - bedroom_count
    - bathroom_count
    - location_district
    """
    filters = ListingFilter(
        min_price=min_price,
        max_price=max_price,
        min_area=min_area,
        max_area=max_area,
        location_city=location_city,
        construction_phase=construction_phase,
        heating_system=heating_system,
        parking_type=parking_type,
        is_new_construction=is_new_construction,
        min_bedrooms=min_bedrooms,
        require_ml_features=require_ml_features,
    )
    
    supabase = SupabaseService()
    listings, total = await supabase.list_listings(
        filters=filters,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )
    
    return {
        "listings": listings,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: str):
    """Get a specific listing by ID."""
    supabase = SupabaseService()
    listing = await supabase.get_listing(listing_id)
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    return listing


@router.delete("/{listing_id}")
async def delete_listing(listing_id: str):
    """Delete a listing by ID."""
    supabase = SupabaseService()
    deleted = await supabase.delete_listing(listing_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    return {"message": "Listing deleted successfully"}


@router.get("/enums/construction-phases", response_model=list[dict])
async def get_construction_phases():
    """Get all construction phases."""
    return [{"value": c.value, "label": c.name.replace("_", " ").title()} for c in ConstructionPhase]


@router.get("/enums/heating-systems", response_model=list[dict])
async def get_heating_systems():
    """Get all heating systems."""
    return [{"value": h.value, "label": h.name.replace("_", " ").title()} for h in HeatingSystem]


@router.get("/enums/parking-types", response_model=list[dict])
async def get_parking_types():
    """Get all parking types."""
    return [{"value": p.value, "label": p.name.replace("_", " ").title()} for p in ParkingType]
