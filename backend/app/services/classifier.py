"""
LLM-based listing classifier using LangChain and OpenRouter.
Classifies raw listing data into standardized categories with image analysis.
"""

import os
from typing import Optional, List
from pydantic import BaseModel, Field, SecretStr
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.utils.utils import secret_from_env

from ..config import get_settings


# ============== OpenRouter Client ==============

class ChatOpenRouter(ChatOpenAI):
    """ChatOpenAI configured for OpenRouter API."""
    
    openai_api_key: Optional[SecretStr] = Field(
        alias="api_key",
        default_factory=secret_from_env("OPENROUTER_API_KEY", default=None),
    )

    @property
    def lc_secrets(self) -> dict[str, str]:
        return {"openai_api_key": "OPENROUTER_API_KEY"}

    def __init__(self, openai_api_key: Optional[str] = None, **kwargs):
        openai_api_key = openai_api_key or os.environ.get("OPENROUTER_API_KEY")
        super().__init__(
            base_url="https://openrouter.ai/api/v1",
            openai_api_key=openai_api_key,
            **kwargs
        )


# ============== Structured Output Schema ==============

class BasicInfo(BaseModel):
    """Basic listing information."""
    title: Optional[str] = Field(None, description="The full title of the listing")
    price_euros: Optional[float] = Field(None, description="The total listed price in Euros")
    listing_id: Optional[str] = Field(None, description="The unique ID from the platform (Šifra oglasa)")


class Location(BaseModel):
    """Location information - extracted from 'Lokacija' field."""
    city: Optional[str] = Field(None, description="The main city - always use the županija capital (e.g., 'Varaždin' for Varaždinska županija)")
    district: Optional[str] = Field(None, description="The district (e.g., Novi Marof, Ivanec, Ludbreg, or Varaždin for center)")
    floor_level: Optional[str] = Field(None, description="Floor number (e.g., '2. kat', 'Prizemlje', 'Multi' for multi-level)")


class Dimensions(BaseModel):
    """Area measurements - critical for resolving discrepancies."""
    metadata_area_m2: Optional[float] = Field(None, description="Area in metadata box (often incorrect)")
    description_living_area_m2: Optional[float] = Field(None, description="Living area from description text - TRUST THIS")
    outdoor_area_m2: Optional[float] = Field(None, description="Terraces, balconies, yards area")
    area_conflict_detected: Optional[bool] = Field(None, description="True if metadata differs >10% from description")


class ParkingType(str):
    GARAGE = "GARAGE"
    OUTDOOR_OWNED = "OUTDOOR_OWNED"
    PUBLIC_PAID = "PUBLIC_PAID"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class BuildingSpecs(BaseModel):
    """Building specifications."""
    year_built: Optional[int] = Field(None, description="Year of construction")
    is_new_construction: Optional[bool] = Field(None, description="True if 'Novogradnja' or current year")
    bedroom_count: Optional[int] = Field(None, description="Number of bedrooms (not total rooms)")
    bathroom_count: Optional[int] = Field(None, description="Number of bathrooms")
    parking_type: Optional[str] = Field(None, description="GARAGE, OUTDOOR_OWNED, PUBLIC_PAID, NONE, UNKNOWN")


class ConstructionPhase(str):
    ROH_BAU = "ROH_BAU"
    HIGH_ROH_BAU = "HIGH_ROH_BAU"
    FINISHED_NEW = "FINISHED_NEW"
    OLD_MAINTAINED = "OLD_MAINTAINED"
    NEEDS_RENOVATION = "NEEDS_RENOVATION"


class HeatingSystem(str):
    GAS_FLOOR = "GAS_FLOOR"
    HEAT_PUMP = "HEAT_PUMP"
    ELECTRIC = "ELECTRIC"
    DISTRICT_HEATING = "DISTRICT_HEATING"
    WOOD_PELLET = "WOOD_PELLET"
    UNKNOWN = "UNKNOWN"


class Condition(BaseModel):
    """Property condition details."""
    construction_phase: Optional[str] = Field(
        None, 
        description="ROH_BAU (unfinished shell), HIGH_ROH_BAU, FINISHED_NEW, OLD_MAINTAINED, NEEDS_RENOVATION"
    )
    heating_system: Optional[str] = Field(
        None,
        description="GAS_FLOOR (podno grijanje na plin), HEAT_PUMP, ELECTRIC, DISTRICT_HEATING, WOOD_PELLET, UNKNOWN"
    )
    energy_class: Optional[str] = Field(None, description="Energy rating: A+, A, B, C, D, E, F, G")


class RoomAnalysis(BaseModel):
    """Individual room detected from images or description."""
    room_type: str = Field(
        ..., 
        description="LIVING_ROOM, BEDROOM, KITCHEN, BATHROOM, TOILET, HALLWAY, BALCONY, TERRACE, STORAGE, GARAGE, LAUNDRY, DINING_ROOM, OFFICE, WALK_IN_CLOSET, EXTERIOR, FLOOR_PLAN, OTHER"
    )
    image_url: Optional[str] = Field(
        None, 
        description="The EXACT URL of the image showing this room. Null if room is only mentioned in description."
    )
    condition: str = Field(
        default="UNKNOWN",
        description="NEW, EXCELLENT, GOOD, FAIR, NEEDS_WORK, ROH_BAU, UNKNOWN (use UNKNOWN if no image)"
    )
    condition_reasoning: Optional[str] = Field(
        None,
        description="Explain WHY you assigned this condition. For rooms without images: 'Mentioned in description but no image available'"
    )
    features: List[str] = Field(
        default_factory=list,
        description="Features visible or mentioned: FLOOR_HEATING, AIR_CONDITIONING, FIREPLACE, BUILT_IN_CLOSET, BATHTUB, SHOWER, DOUBLE_SINK, KITCHEN_ISLAND, MODERN_APPLIANCES, LARGE_WINDOWS, HIGH_CEILING, PARQUET_FLOOR, TILE_FLOOR, LAMINATE_FLOOR"
    )
    notes: Optional[str] = Field(None, description="Brief observation. For description-only rooms, quote the relevant text.")
    estimated_area_m2: Optional[float] = Field(None, description="Room size if mentioned in description or visible")
    from_description: Optional[bool] = Field(None, description="True if this room was extracted from description text (no image)")


class ClassifiedListing(BaseModel):
    """Complete structured output for classified listing."""
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    location: Location = Field(default_factory=Location)
    dimensions: Dimensions = Field(default_factory=Dimensions)
    building_specs: BuildingSpecs = Field(default_factory=BuildingSpecs)
    condition: Condition = Field(default_factory=Condition)
    rooms: List[RoomAnalysis] = Field(default_factory=list, description="Rooms detected from images")


CLASSIFICATION_PROMPT = """You are a Croatian real estate listing analyzer. Extract structured data from the listing below AND identify ALL rooms from BOTH images AND description text.

## CRITICAL RULES:
1. **AREA CONFLICT**: The metadata area (in header) is often WRONG. The description text has the TRUE living area. Flag conflicts >10%.
2. **ROH-BAU**: "Roh-bau" or "gruba gradnja" means unfinished shell - set construction_phase to ROH_BAU
3. **HEATING**: "Podno grijanje na plin" = GAS_FLOOR, "Toplinska pumpa" = HEAT_PUMP
4. **BEDROOMS**: Count actual bedrooms, not total rooms. "4-sobni" often means 3 bedrooms + living room.

## LOCATION GUIDE (CRITICAL):

The "Lokacija" field contains the REAL location. It follows this structure:
`Županija > District > Specific Area`

{location_context}

**Rules for location extraction:**
1. **city** should ALWAYS be the županija capital (e.g., "Varaždin" for Varaždinska županija)
2. **district** should be the district/town from the DISTRICTS list (e.g., Novi Marof, Ivanec, Ludbreg, Varaždin)
3. If the location is in the main city center, use the city name as district (e.g., "Varaždin")
4. If the location says "Varaždin - Okolica > Kućan Marof", then city="Varaždin", district="Kućan Marof"
5. If the location says "Varaždin > Centar" or just mentions Varaždin center, then city="Varaždin", district="Varaždin"

## CROATIAN TERMS:
- Novogradnja = new construction (is_new_construction: true)
- Roh-bau / gruba gradnja = ROH_BAU
- Podno grijanje = floor heating
- Peć na plin = GAS_FLOOR
- Toplinska pumpa / dizalica topline = HEAT_PUMP
- Daljinsko grijanje / toplana = DISTRICT_HEATING
- Stambena površina = living area
- Prizemlje = ground floor
- Garaža / garažno mjesto = GARAGE parking
- Soba = room
- Spavaća soba = bedroom
- Dnevni boravak / dnevna soba = living room
- Kuhinja = kitchen
- Kupaonica = bathroom
- WC / toalet = toilet
- Hodnik = hallway
- Balkon = balcony
- Terasa = terrace
- Ostava = storage
- Garaža = garage
- Blagovaonica = dining room
- Radna soba = office

## ROOM DETECTION - TWO SOURCES:

### SOURCE 1: DESCRIPTION TEXT
First, extract rooms mentioned in the description. Look for:
- "X-sobni stan" (X-room apartment) - e.g., "3-sobni" = typically 2 bedrooms + 1 living room
- "2 spavaće sobe" (2 bedrooms)
- "dnevni boravak" (living room)
- "kuhinja s blagovaonicom" (kitchen with dining area)
- "2 kupaonice" (2 bathrooms)
- "WC" or "toalet" (separate toilet)
- "balkon" (balcony), "terasa" (terrace)
- "ostava" (storage), "garaža" (garage)

For rooms mentioned in description but NOT shown in images:
- Set image_url to null
- Set condition to "UNKNOWN" 
- Set condition_reasoning to "Mentioned in description but no image available"
- In notes, quote the text that mentions this room

### SOURCE 2: IMAGES
Then, analyze images to:
- Confirm rooms mentioned in description
- Add any additional rooms visible in images
- Assign condition based on what you SEE

**CRITICAL IMAGE RULES:**
1. Multiple images may show the SAME ROOM from different angles - create only ONE entry per unique room
2. For rooms with images, copy the EXACT image URL into image_url field
3. Merge description info with image info for the same room

**Room Types:**
- LIVING_ROOM: Main living area, often with sofa, TV (dnevni boravak)
- BEDROOM: Room with bed (spavaća soba) - create separate entries for each
- KITCHEN: Cooking area (kuhinja)
- BATHROOM: Full bath with shower/tub AND toilet (kupaonica)
- TOILET: Separate WC (WC, toalet)
- HALLWAY: Corridor, entrance (hodnik)
- BALCONY: Enclosed or open balcony (balkon)
- TERRACE: Outdoor terrace/patio (terasa)
- STORAGE: Pantry, utility room (ostava)
- GARAGE: Car parking space (garaža)
- LAUNDRY: Laundry/utility room
- DINING_ROOM: Dedicated dining area (blagovaonica)
- OFFICE: Home office/study (radna soba)
- WALK_IN_CLOSET: Large closet/dressing room (garderoba)
- EXTERIOR: Building facade, garden, exterior view
- FLOOR_PLAN: Architectural drawing (tlocrt)
- OTHER: Anything else

**Condition Assessment (for rooms with images):**
- NEW: Never used, pristine
- EXCELLENT: Like new, minimal wear
- GOOD: Normal wear, well maintained
- FAIR: Some wear visible, aging
- NEEDS_WORK: Requires renovation
- ROH_BAU: Unfinished, bare walls/concrete
- UNKNOWN: No image available (for description-only rooms)

**IMPORTANT - Condition Reasoning:**
For rooms WITH images, explain WHY you assigned that condition based on:
- Wall/paint condition (fresh paint, scuffs, cracks, stains)
- Flooring state (new tiles, worn parquet, scratches)
- Fixtures age (modern faucets, dated handles, rusty elements)
- Appliances (new stainless steel, old white goods)
- Overall design (contemporary minimalist, 90s style, dated)

For rooms WITHOUT images: "Mentioned in description but no image available"

**Features to Detect:**
FLOOR_HEATING, AIR_CONDITIONING, FIREPLACE, BUILT_IN_CLOSET, BATHTUB, SHOWER, DOUBLE_SINK, KITCHEN_ISLAND, MODERN_APPLIANCES, LARGE_WINDOWS, HIGH_CEILING, PARQUET_FLOOR, TILE_FLOOR, LAMINATE_FLOOR

## LISTING DATA:
{listing_json}

{image_instruction}

Extract all listing information AND create ONE room entry per UNIQUE room/space. Use the EXACT image_index from the list. Set null if not found."""


class ListingClassifier:
    """Service for classifying listings using LLM via OpenRouter."""
    
    def __init__(self):
        settings = get_settings()
        self.model_name = settings.openrouter_model_name
        self.api_key = settings.openrouter_api_key
        
        self.llm = ChatOpenRouter(
            model_name=self.model_name,
            openai_api_key=self.api_key,
            temperature=0,
        )
        self.structured_llm = self.llm.with_structured_output(ClassifiedListing)
    
    async def classify(self, raw_data: dict, location_context: dict = None) -> ClassifiedListing:
        """
        Classify raw listing data using LLM with optional image analysis.
        
        Args:
            raw_data: The raw listing data from scraping
            location_context: Optional dict with:
                - zupanija: The county name (e.g., "Varaždinska županija")
                - city: The main city (e.g., "Varaždin") 
                - districts: List of district names (e.g., ["Ivanec", "Novi Marof", "Ludbreg"])
                - neighborhoods: List of neighborhood names (e.g., ["Banfica", "Texas", "Bronx"])
        """
        import json
        
        # Build location context string for the prompt
        location_context_str = ""
        if location_context:
            zupanija = location_context.get("zupanija", "")
            city = location_context.get("city", "")
            districts = location_context.get("districts", [])
            
            location_context_str = f"""
**For this listing, the županija is: {zupanija}**
**The main city (use for 'city' field): {city}**

DISTRICTS (use for 'district' field):
{', '.join(districts) if districts else 'None specified'}

If the location mentions "Centar" or is in the main city, set district to "{city}".
If you see "- Okolica" it means suburbs, it is usually the same as district if mentioned.
"""
        else:
            location_context_str = """
No specific location context provided. Extract city and neighborhood from the "Lokacija" field.
If you see a county name (županija), use its capital as the city.
"""
        
        # Prepare text data
        description = raw_data.get("description") or ""
        data_for_llm = {
            "title": raw_data.get("title"),
            "price": raw_data.get("price"),
            "ad_id": raw_data.get("ad_id"),
            "highlighted_attributes": raw_data.get("highlighted_attributes") or {},
            "basic_details": raw_data.get("basic_details") or {},
            "description": description[:3000],
            "additional_info": raw_data.get("additional_info") or {},
            "category_path": raw_data.get("category_path") or [],
        }
        
        listing_json = json.dumps(data_for_llm, ensure_ascii=False, indent=2)
        
        # Get ALL image URLs
        images = raw_data.get("images", [])
        image_urls = []
        for img in images:
            url = img.get("large") or img.get("thumbnail") or img.get("src")
            if url:
                image_urls.append(url)
        
        # Build multimodal message content with actual images
        content_blocks = []
        
        # Build the prompt with location context
        base_prompt = CLASSIFICATION_PROMPT.replace('{listing_json}', listing_json).replace('{location_context}', location_context_str)
        
        # Add text instruction first
        if image_urls:
            text_instruction = f"""{base_prompt.replace('{image_instruction}', '')}

## IMAGES TO ANALYZE ({len(image_urls)} images):

**IMPORTANT RULES:**
1. Look at EACH image below carefully
2. Some images may show the SAME ROOM from DIFFERENT ANGLES - create only ONE entry per unique room
3. For each unique room, set `image_url` to the URL of the BEST image showing that room
4. The images are numbered - reference them by their URL

For each UNIQUE room, output a room object with:
- room_type: The type of room shown
- image_url: The FULL URL of the best image for this room
- condition: The room's condition  
- condition_reasoning: WHY you assigned this condition (what you SEE in the image)
- features: List of visible features
- notes: Brief observation

**Here are the {len(image_urls)} images to analyze:**
"""
            content_blocks.append({"type": "text", "text": text_instruction})
            
            # Add each image as an image_url block with its URL label
            for i, url in enumerate(image_urls):
                # Add URL label before image
                content_blocks.append({"type": "text", "text": f"\n[Image {i}] URL: {url}"})
                content_blocks.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
        else:
            text_instruction = base_prompt.replace('{image_instruction}', '## NO IMAGES AVAILABLE - Skip rooms analysis')
            content_blocks.append({"type": "text", "text": text_instruction})
        
        # Create message with multimodal content
        messages = [HumanMessage(content=content_blocks)]
        
        try:
            print(f"[Classifier] Using model: {self.model_name}")
            print(f"[Classifier] Analyzing with {len(image_urls)} images")
            
            # Try structured output first
            try:
                result = await self.structured_llm.ainvoke(messages)
            except Exception as struct_error:
                # If structured output fails (e.g., model returns markdown), parse manually
                print(f"[Classifier] Structured output failed, trying manual parse: {struct_error}")
                
                # Get raw response
                raw_response = await self.llm.ainvoke(messages)
                response_text = raw_response.content
                
                # Strip markdown code blocks if present
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]
                
                response_text = response_text.strip()
                
                # Parse JSON manually
                import json as json_module
                parsed = json_module.loads(response_text)
                result = ClassifiedListing(**parsed)
            
            # Log room detection results
            for room in result.rooms:
                has_url = bool(room.image_url)
                print(f"[Classifier] Room '{room.room_type}' -> has_url={has_url}, condition={room.condition}")
            
            print(f"[Classifier] Result: price={result.basic_info.price_euros}, "
                  f"area={result.dimensions.description_living_area_m2}m², "
                  f"phase={result.condition.construction_phase}, "
                  f"rooms={len(result.rooms)}")
            
            return result
            
        except Exception as e:
            print(f"[Classifier] Error: {e}")
            import traceback
            traceback.print_exc()
            return ClassifiedListing()
