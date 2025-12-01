"""
API endpoints for location data (županije and districts).
"""

from fastapi import APIRouter
from typing import List, Dict, Optional

from ..locations_config.locations import (
    ZUPANIJE,
    get_all_zupanije,
    get_districts,
    build_search_url,
)

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("/zupanije", response_model=List[str])
async def list_zupanije():
    """Get list of all županije (counties)."""
    return get_all_zupanije()


@router.get("/zupanije/{zupanija}/districts", response_model=List[str])
async def list_districts(zupanija: str):
    """Get list of districts for a specific županija."""
    return get_districts(zupanija)


@router.get("/all", response_model=Dict[str, List[str]])
async def get_all_locations():
    """Get all županije with their districts."""
    return ZUPANIJE


@router.get("/search-url")
async def get_search_url(
    zupanija: str,
    district: Optional[str] = None,
    property_type: str = "prodaja-stanova"
):
    """
    Generate a njuskalo.hr search URL for a location.
    
    Args:
        zupanija: The županija name
        district: Optional district name
        property_type: Type of listing (prodaja-stanova, iznajmljivanje-stanova, etc.)
    """
    url = build_search_url(zupanija, district, property_type)
    return {"url": url, "zupanija": zupanija, "district": district}

