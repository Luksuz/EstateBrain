from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class RoomType(str, Enum):
    """Room types detected from images."""
    LIVING_ROOM = "LIVING_ROOM"
    BEDROOM = "BEDROOM"
    KITCHEN = "KITCHEN"
    BATHROOM = "BATHROOM"
    TOILET = "TOILET"  # Separate WC
    HALLWAY = "HALLWAY"
    BALCONY = "BALCONY"
    TERRACE = "TERRACE"
    STORAGE = "STORAGE"
    GARAGE = "GARAGE"
    LAUNDRY = "LAUNDRY"
    DINING_ROOM = "DINING_ROOM"
    OFFICE = "OFFICE"
    WALK_IN_CLOSET = "WALK_IN_CLOSET"
    EXTERIOR = "EXTERIOR"  # Building/garden exterior
    FLOOR_PLAN = "FLOOR_PLAN"
    OTHER = "OTHER"


class RoomCondition(str, Enum):
    """Condition of a specific room."""
    NEW = "NEW"  # Brand new, never used
    EXCELLENT = "EXCELLENT"  # Like new
    GOOD = "GOOD"  # Normal wear
    FAIR = "FAIR"  # Some wear visible
    NEEDS_WORK = "NEEDS_WORK"  # Requires renovation
    ROH_BAU = "ROH_BAU"  # Unfinished
    UNKNOWN = "UNKNOWN"


class RoomFeature(str, Enum):
    """Notable features detected in rooms."""
    FLOOR_HEATING = "FLOOR_HEATING"
    AIR_CONDITIONING = "AIR_CONDITIONING"
    FIREPLACE = "FIREPLACE"
    BUILT_IN_CLOSET = "BUILT_IN_CLOSET"
    BATHTUB = "BATHTUB"
    SHOWER = "SHOWER"
    DOUBLE_SINK = "DOUBLE_SINK"
    KITCHEN_ISLAND = "KITCHEN_ISLAND"
    MODERN_APPLIANCES = "MODERN_APPLIANCES"
    LARGE_WINDOWS = "LARGE_WINDOWS"
    HIGH_CEILING = "HIGH_CEILING"
    PARQUET_FLOOR = "PARQUET_FLOOR"
    TILE_FLOOR = "TILE_FLOOR"
    LAMINATE_FLOOR = "LAMINATE_FLOOR"


class Room(BaseModel):
    """Individual room detected from images or description."""
    room_type: RoomType = Field(..., description="Type of room")
    image_url: Optional[str] = Field(None, description="Source image URL (null if from description only)")
    condition: RoomCondition = Field(default=RoomCondition.UNKNOWN, description="Room condition")
    condition_reasoning: Optional[str] = Field(None, description="AI reasoning for the condition assessment")
    features: List[str] = Field(default_factory=list, description="Detected features")
    notes: Optional[str] = Field(None, description="Additional observations")
    estimated_area_m2: Optional[float] = Field(None, description="Room size if mentioned or visible")
    from_description: Optional[bool] = Field(None, description="True if extracted from description (no image)")


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


class ListingBase(BaseModel):
    """Base listing model with all fields."""
    # Identifiers
    external_id: Optional[str] = Field(None, description="External ID from njuskalo.hr (Šifra oglasa)")
    url: str = Field(..., description="URL of the listing")
    
    # Basic Info
    title: Optional[str] = Field(None, description="Listing title")
    price_eur: Optional[float] = Field(None, description="Price in EUR")
    
    # Location
    location_city: Optional[str] = Field(None, description="City name")
    location_district: Optional[str] = Field(None, description="Neighborhood/district")
    floor_level: Optional[str] = Field(None, description="Floor (e.g., '2. kat', 'Prizemlje', 'Multi')")
    
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
    
    # Condition
    construction_phase: ConstructionPhase = Field(default=ConstructionPhase.UNKNOWN, description="Construction phase")
    heating_system: HeatingSystem = Field(default=HeatingSystem.UNKNOWN, description="Heating system")
    energy_class: Optional[str] = Field(None, description="Energy class (A+, A, B, C, D, E, F, G)")
    
    # Content
    description: Optional[str] = Field(None, description="Listing description")
    images: list[ImageData] = Field(default_factory=list, description="List of images")
    rooms: List[Room] = Field(default_factory=list, description="Rooms detected from images")
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
    is_new_construction: Optional[bool] = None
    min_bedrooms: Optional[int] = None
    # ML feature completeness filter
    require_ml_features: Optional[bool] = None  # If True, only return listings with all ML features
