from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class BuildingType(str, Enum):
    """Type of building the apartment is in."""
    HOUSE = "HOUSE"  # Kuća - standalone house or part of a house
    BUILDING = "BUILDING"  # Zgrada - apartment building


class ConstructionPhase(str, Enum):
    """Construction/completion status."""
    ROH_BAU = "ROH_BAU"  # Unfinished shell, gruba gradnja
    HIGH_ROH_BAU = "HIGH_ROH_BAU"  # Advanced roh-bau
    FINISHED_NEW = "FINISHED_NEW"  # Novogradnja, finished
    OLD_MAINTAINED = "OLD_MAINTAINED"  # Older but maintained
    NEEDS_RENOVATION = "NEEDS_RENOVATION"  # Potrebna adaptacija
    UNKNOWN = "UNKNOWN"


class HeatingSystem(str, Enum):
    """Heating system type."""
    GAS_FLOOR = "GAS_FLOOR"  # Podno grijanje na plin
    HEAT_PUMP = "HEAT_PUMP"  # Toplinska pumpa, dizalica topline
    ELECTRIC = "ELECTRIC"  # Električno
    DISTRICT_HEATING = "DISTRICT_HEATING"  # Toplana, daljinsko grijanje
    WOOD_PELLET = "WOOD_PELLET"  # Drva, pelet
    UNKNOWN = "UNKNOWN"


class ParkingType(str, Enum):
    """Parking availability type."""
    GARAGE = "GARAGE"  # Garaža, garažno mjesto
    OUTDOOR_OWNED = "OUTDOOR_OWNED"  # Vanjsko parkirno mjesto
    PUBLIC_PAID = "PUBLIC_PAID"  # Javni parking
    NONE = "NONE"  # Bez parkinga
    UNKNOWN = "UNKNOWN"


class ImageData(BaseModel):
    """Image data for a listing."""
    id: Optional[str] = None
    thumbnail: Optional[str] = None
    large: Optional[str] = None
    src: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None


class ListingSource(str, Enum):
    """Source marketplace for the listing."""
    NJUSKALO = "njuskalo"
    CROZILLA = "crozilla"


class ListingBase(BaseModel):
    """Base listing model with all fields."""
    # Identifiers
    external_id: Optional[str] = Field(None, description="External ID from platform (Šifra oglasa)")
    url: str = Field(..., description="URL of the listing")
    source: ListingSource = Field(default=ListingSource.NJUSKALO, description="Source marketplace")
    source_id: Optional[str] = Field(None, description="Platform-specific listing ID")
    duplicate_of: Optional[str] = Field(None, description="ID of the primary listing if this is a duplicate")
    
    # Basic Info
    title: Optional[str] = Field(None, description="Listing title")
    price_eur: Optional[float] = Field(None, description="Price in EUR")
    
    # Location
    location_city: Optional[str] = Field(None, description="City name")
    location_district: Optional[str] = Field(None, description="Neighborhood/district")
    floor_level: Optional[str] = Field(None, description="Floor (e.g., '2. kat', 'Prizemlje', 'Multi')")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    location_approximate: Optional[bool] = Field(None, description="True if coordinates are approximate")
    distance_from_center: Optional[float] = Field(None, description="Distance from center in km (Haversine)")
    
    # Dimensions - CRITICAL: description_living_area is the trusted value
    metadata_area_m2: Optional[float] = Field(None, description="Area from metadata (often wrong)")
    living_area_m2: Optional[float] = Field(None, description="True living area from description")
    outdoor_area_m2: Optional[float] = Field(None, description="Terrace/balcony/yard area")
    area_conflict: Optional[bool] = Field(None, description="True if metadata differs >10% from living area")
    
    # Building Specs
    year_built: Optional[int] = Field(None, description="Year built")
    is_new_construction: Optional[bool] = Field(None, description="Is novogradnja")
    bedroom_count: Optional[int] = Field(None, description="Number of bedrooms")
    bathroom_count: Optional[int] = Field(None, description="Number of bathrooms")
    parking_type: ParkingType = Field(default=ParkingType.UNKNOWN, description="Parking type")
    building_type: Optional[BuildingType] = Field(None, description="House or apartment building")
    interior_arranged: Optional[bool] = Field(None, description="True if apartment has arranged/furnished interior")
    has_cellar: Optional[bool] = Field(None, description="True if includes cellar/storage room")
    
    # Condition
    construction_phase: ConstructionPhase = Field(default=ConstructionPhase.UNKNOWN, description="Construction phase")
    renovation_level: Optional[int] = Field(
        None, 
        ge=1, 
        le=10, 
        description="Renovation level 1-10 (1=needs full renovation, 10=modern luxury)"
    )
    heating_system: HeatingSystem = Field(default=HeatingSystem.UNKNOWN, description="Heating system")
    energy_class: Optional[str] = Field(None, description="Energy class (A+, A, B, C, D, E, F, G)")
    
    # Content
    description: Optional[str] = Field(None, description="Listing description")
    images: list[ImageData] = Field(default_factory=list, description="List of images")
    additional_info: dict = Field(default_factory=dict, description="Additional property info")
    
    # Seller
    seller_name: Optional[str] = Field(None, description="Seller/agent name")
    seller_contact: Optional[str] = Field(None, description="Seller contact info")


class ListingCreate(ListingBase):
    """Model for creating a new listing."""
    scrape_job_id: Optional[str] = Field(None, description="Associated scrape job ID")
    raw_data: Optional[dict] = Field(None, description="Raw parsed data")


class ListingResponse(ListingBase):
    """Model for listing response."""
    id: str
    scrape_job_id: Optional[str] = None
    source: ListingSource = ListingSource.NJUSKALO
    source_id: Optional[str] = None
    duplicate_of: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ListingFilter(BaseModel):
    """Filter options for listing queries."""
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    location_city: Optional[str] = None
    construction_phase: Optional[ConstructionPhase] = None
    heating_system: Optional[HeatingSystem] = None
    parking_type: Optional[ParkingType] = None
    building_type: Optional[BuildingType] = None
    interior_arranged: Optional[bool] = None
    is_new_construction: Optional[bool] = None
    min_bedrooms: Optional[int] = None
    min_renovation_level: Optional[int] = None
    max_renovation_level: Optional[int] = None
    max_distance_from_center: Optional[float] = None
    # ML feature completeness filter
    require_ml_features: Optional[bool] = None  # If True, only return listings with all ML features
    # Source filter
    source: Optional[ListingSource] = None  # Filter by marketplace source
    exclude_duplicates: Optional[bool] = None  # If True, exclude listings marked as duplicates
