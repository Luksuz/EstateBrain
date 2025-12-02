"""
LLM-based listing classifier using LangChain and OpenRouter.
Classifies raw listing data into standardized categories with renovation assessment.
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


class BuildingSpecs(BaseModel):
    """Building specifications."""
    year_built: Optional[int] = Field(None, description="Year of construction")
    is_new_construction: Optional[bool] = Field(None, description="True if 'Novogradnja' or current year")
    bedroom_count: Optional[int] = Field(None, description="Number of bedrooms (not total rooms)")
    bathroom_count: Optional[int] = Field(None, description="Number of bathrooms")
    parking_type: Optional[str] = Field(None, description="GARAGE, OUTDOOR_OWNED, PUBLIC_PAID, NONE, UNKNOWN")
    building_type: Optional[str] = Field(
        None, 
        description="HOUSE (kuća, family house, ground floor of house) or BUILDING (zgrada, apartment building, multi-story residential)"
    )
    interior_arranged: Optional[bool] = Field(
        None,
        description="True if interior is arranged/furnished, False if unfurnished/empty"
    )
    has_cellar: Optional[bool] = Field(
        None,
        description="True if apartment includes cellar/storage room (podrum, spremište)"
    )


class Condition(BaseModel):
    """Property condition details."""
    construction_phase: Optional[str] = Field(
        None, 
        description="ROH_BAU (unfinished shell), HIGH_ROH_BAU, FINISHED_NEW, OLD_MAINTAINED, NEEDS_RENOVATION"
    )
    renovation_level: Optional[int] = Field(
        None,
        description="1-10 rating: 1=uninhabitable hole, 5=dated but livable, 10=modern luxury. Objective measure of effort needed to reach comfortable modern living."
    )
    renovation_reasoning: Optional[str] = Field(
        None,
        description="Brief explanation of why this renovation level was assigned based on visible condition."
    )
    heating_system: Optional[str] = Field(
        None,
        description="GAS_FLOOR (podno grijanje na plin), HEAT_PUMP, ELECTRIC, DISTRICT_HEATING, WOOD_PELLET, UNKNOWN"
    )
    energy_class: Optional[str] = Field(None, description="Energy rating: A+, A, B, C, D, E, F, G")


class ClassifiedListing(BaseModel):
    """Complete structured output for classified listing."""
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    location: Location = Field(default_factory=Location)
    dimensions: Dimensions = Field(default_factory=Dimensions)
    building_specs: BuildingSpecs = Field(default_factory=BuildingSpecs)
    condition: Condition = Field(default_factory=Condition)


CLASSIFICATION_PROMPT = """You are a Croatian real estate listing analyzer. Extract structured data from the listing and assess the overall renovation level.

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

## BUILDING TYPE DETECTION:

Determine if the property is in a HOUSE or BUILDING:

**HOUSE indicators:**
- "kuća", "obiteljska kuća" (family house)
- "prizemlje kuće" (ground floor of house)
- "dio kuće" (part of house)
- Ground floor with garden/yard ("dvorište")
- Single-family or two-family property
- "katnica" (multi-story house)

**BUILDING indicators:**
- "zgrada", "stambena zgrada" (residential building)
- Floor mentioned (1. kat, 2. kat, etc.) without house reference
- "lift" (elevator) mentioned
- Multiple apartments mentioned
- "novogradnja" in urban context usually = BUILDING
- High-rise or multi-unit residential

## INTERIOR ARRANGED DETECTION:

Determine if the property comes with REAL furniture (not renders/visualizations):

**ARRANGED (interior_arranged: true):**
- "namješten" (furnished) or "opremljen stan" (equipped apartment) in description
- "potpuno opremljen" (fully equipped) or "kompletno namješten"
- REAL photos (not 3D renders) showing: beds, sofas, dining tables, wardrobes, living room furniture
- Clearly lived-in appearance with real furniture
- "s namještajem" (with furniture)

**NOT ARRANGED (interior_arranged: false):**
- "nenamješten" (unfurnished) in description
- "prazan stan" (empty apartment) or "bez namještaja" (without furniture)
- REAL photos showing empty rooms - no beds, no sofas, no wardrobes
- Only built-in kitchen cabinets/appliances (this is STANDARD, not "furnished")
- New construction showing only built-in elements
- "stan za uređenje" (apartment for arranging)

**CRITICAL DISTINCTIONS:**
- Built-in kitchen with appliances = NOT furnished (this is standard)
- 3D renders/visualizations showing furniture = IGNORE these, they're just marketing
- Floor plans = NOT relevant to furnished status
- Only count REAL furniture in REAL photos

**Default to false** for new construction unless explicitly stated as furnished

## CELLAR/STORAGE DETECTION:

Determine if the property includes a cellar or storage room:

**HAS CELLAR (has_cellar: true):**
- "podrum" (cellar/basement storage)
- "spremište" (storage room)
- "drvarnica" (wood storage - counts as cellar)
- "ostava" (pantry/storage)
- "podrumska prostorija" (basement room)
- Listed in additional features/amenities
- Visible in images: basement corridor, storage units, cellar door

**NO CELLAR (has_cellar: false):**
- No mention of storage in description
- "bez podruma" (without cellar)
- Explicitly states no storage included

**If unclear:** Set to null

## RENOVATION LEVEL ASSESSMENT (1-10):

This is an OBJECTIVE measure of how much effort/investment would be needed to bring the property to comfortable modern living standards.

**Rating Scale:**
- **1-2**: Uninhabitable. Major structural issues, no utilities, dangerous conditions. Complete gut renovation needed.
- **3-4**: Needs significant work. Outdated everything (bathroom, kitchen, floors). Would need €20k+ investment.
- **5-6**: Dated but livable. 80s-90s aesthetics, functional but old. Cosmetic updates needed. €10-20k investment.
- **7-8**: Good condition. Minor updates needed. Modern enough for most people. €5-10k for personal touches.
- **9-10**: Move-in ready modern. Contemporary finishes, new appliances, no work needed. Modern luxury at 10.

**CRITICAL: NEW CONSTRUCTION / UNDER CONSTRUCTION:**
When images show ONLY:
- 3D renders/visualizations of the apartment
- Exterior shots of building under construction
- Floor plans
- Building site photos
- "Vizualizacija" or render images

**→ This is NEW CONSTRUCTION being built. Rate it 9-10!**
- These will be BRAND NEW when finished
- Do NOT rate them low just because you can't see real interior
- "Novogradnja" (new construction) = renovation_level 9-10
- "U izgradnji" (under construction) = renovation_level 9-10

**Assessment Factors (from REAL interior images only):**
- Kitchen: Old cabinets/appliances vs modern fitted kitchen
- Bathroom: Dated tiles/fixtures vs modern walk-in shower, floating vanity
- Flooring: Worn parquet/linoleum vs new hardwood/tile
- Walls: Peeling paint/wallpaper vs fresh modern finish
- Windows: Old wooden frames vs PVC double-glazing
- Overall aesthetic: 70s/80s/90s feel vs contemporary design
- Fixtures: Brass/gold dated fixtures vs modern chrome/matte

**IMPORTANT**: If only SOME rooms need renovation, average it out. A modern kitchen but dated bathroom might be 7.

**If no REAL interior images available, estimate based on:**
- "Novogradnja" or new construction = **9-10** (will be brand new)
- "U izgradnji" (under construction) = **9-10**
- Year built 2020+ = **8-10**
- Year built 2010-2019 = **7-8**
- Year built 2000-2009 = **6-7**
- Year built 1990-1999 = **5-6**
- Year built before 1990 = **4-5** (unless renovated)
- "Potrebna adaptacija" in description = **3-5**
- ROH_BAU = **3** (unfinished shell, needs finishing but structurally new)

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
- Potrebna adaptacija / renovacija = needs renovation
- Kuća = house
- Zgrada = building
- Stan = apartment

## LISTING DATA:
{listing_json}

{image_instruction}

Extract all listing information. Set null if not found. For renovation_level, provide a justified rating based on what you observe."""


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

**FIRST: Identify what type of images these are:**
1. **3D Renders/Visualizations** - Computer-generated images showing how apartment WILL look
2. **Construction site photos** - Building being built, concrete, scaffolding
3. **Floor plans** - Technical drawings of layout
4. **Exterior building shots** - Outside of the building
5. **Real interior photos** - Actual photos of existing rooms

**IF images are mostly renders/construction/exterior (new construction):**
- renovation_level = 9-10 (it will be brand new!)
- interior_arranged = false (unless explicitly stated furnished)
- Don't penalize for "can't see real interior" - these are NEW BUILDS

**IF images show REAL interior:**
Look at ALL images to assess the overall renovation level. Consider:
- Kitchen condition and style
- Bathroom fixtures and tiles  
- Flooring throughout
- Wall finishes
- Windows and doors
- Overall aesthetic and modernity

For interior_arranged: Only count REAL furniture (beds, sofas, wardrobes) in REAL photos.
- Furniture shown in 3D renders does NOT mean furnished
- Built-in kitchen = standard, NOT furnished

Also determine building_type from exterior shots if available (house vs apartment building).

**Here are the {len(image_urls)} images to analyze:**
"""
            content_blocks.append({"type": "text", "text": text_instruction})
            
            # Add each image as an image_url block
            for i, url in enumerate(image_urls):
                content_blocks.append({"type": "text", "text": f"\n[Image {i}]"})
                content_blocks.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
        else:
            text_instruction = base_prompt.replace('{image_instruction}', '## NO IMAGES AVAILABLE - Estimate renovation_level from description and property age')
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
            
            print(f"[Classifier] Result: price={result.basic_info.price_euros}, "
                  f"area={result.dimensions.description_living_area_m2}m², "
                  f"phase={result.condition.construction_phase}, "
                  f"renovation_level={result.condition.renovation_level}, "
                  f"building_type={result.building_specs.building_type}, "
                  f"interior_arranged={result.building_specs.interior_arranged}")
            
            return result
            
        except Exception as e:
            print(f"[Classifier] Error: {e}")
            import traceback
            traceback.print_exc()
            return ClassifiedListing()
