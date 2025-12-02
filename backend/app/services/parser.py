"""
Parser that extracts raw data from HTML and uses LLM for classification.
"""

import re
import json
import math
from bs4 import BeautifulSoup
from typing import Optional, List
from urllib.parse import urljoin

from ..models.listing import (
    ListingCreate,
    ListingSource,
    ImageData,
    BuildingType,
    ConstructionPhase,
    HeatingSystem,
    ParkingType,
)
from ..config import get_settings


# District coordinates for Varaždin county (fallback if DB not available)
# Distance is calculated from listing to its district center
DISTRICT_COORDS = {
    "Varaždin": (46.307491, 16.335753),
    "Gornji Kneginec": (46.25051, 16.37555),
    "Ivanec": (46.23333, 16.13333),
    "Klenovnik": (46.27028, 16.07000),
    "Lepoglava": (46.21056, 16.03556),
    "Ludbreg": (46.25000, 16.63333),
    "Maruševec": (46.28262, 16.18539),
    "Novi Marof": (46.16667, 16.33333),
    "Petrijanec": (46.34917, 16.22500),
    "Sračinec": (46.32944, 16.27889),
    "Trnovec Bartolovečki": (46.29472, 16.39889),
    "Varaždinske Toplice": (46.2300, 16.4014),
    "Veliki Bukovec": (46.07800, 16.02225),
    "Visoko": (46.20, 16.15),
}

# Default center (Varaždin) for unknown districts
DEFAULT_CENTER_LAT = 46.307491
DEFAULT_CENTER_LNG = 16.335753


def get_district_center(district_name: Optional[str]) -> tuple[float, float]:
    """
    Get the center coordinates for a district.
    Falls back to Varaždin center if district not found.
    
    Args:
        district_name: Name of the district
        
    Returns:
        Tuple of (latitude, longitude)
    """
    if not district_name:
        return (DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG)
    
    # Try exact match first
    if district_name in DISTRICT_COORDS:
        return DISTRICT_COORDS[district_name]
    
    # Try case-insensitive match
    district_lower = district_name.lower()
    for name, coords in DISTRICT_COORDS.items():
        if name.lower() == district_lower:
            return coords
    
    # Try partial match (district name contains or is contained in)
    for name, coords in DISTRICT_COORDS.items():
        if name.lower() in district_lower or district_lower in name.lower():
            return coords
    
    # Default to Varaždin
    return (DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth using the Haversine formula.
    
    Args:
        lat1, lon1: Coordinates of the first point (in degrees)
        lat2, lon2: Coordinates of the second point (in degrees)
        
    Returns:
        Distance in kilometers
    """
    # Earth's radius in kilometers
    R = 6371.0
    
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return round(distance, 2)


class SearchPageParser:
    """Parser for extracting listing URLs from njuskalo.hr search results pages."""
    
    BASE_URL = "https://www.njuskalo.hr"
    
    @classmethod
    def extract_listing_urls(cls, html_content: str) -> List[str]:
        """
        Extract all listing URLs from a search results page.
        
        Args:
            html_content: HTML content of the search results page
            
        Returns:
            List of unique listing URLs
        """
        soup = BeautifulSoup(html_content, "html.parser")
        urls = set()
        
        # Primary method: Get URLs from data-href attribute on EntityList-item--Regular
        # This is the most reliable way to get listing URLs
        listing_items = soup.select("li.EntityList-item--Regular[data-href]")
        for item in listing_items:
            href = item.get("data-href")
            if href and cls._is_listing_url(href):
                full_url = urljoin(cls.BASE_URL, href)
                urls.add(full_url)
        
        # Fallback: Look for links in entity-title
        if not urls:
            title_links = soup.select(".entity-title a[href]")
            for link in title_links:
                href = link.get("href")
                if href and cls._is_listing_url(href):
                    full_url = urljoin(cls.BASE_URL, href)
                    urls.add(full_url)
        
        # Fallback 2: Any link with oglas- in the URL
        if not urls:
            all_links = soup.select("a[href*='oglas-']")
            for link in all_links:
                href = link.get("href")
                if href and cls._is_listing_url(href):
                    full_url = urljoin(cls.BASE_URL, href)
                    urls.add(full_url)
        
        print(f"[SearchPageParser] Found {len(urls)} listing URLs")
        return list(urls)
    
    @classmethod
    def _is_listing_url(cls, href: str) -> bool:
        """Check if a URL is a listing detail page, not a category or other page."""
        if not href:
            return False
        
        # Listing URLs contain "oglas-" followed by digits
        if "oglas-" in href:
            return True
            
        return False
    
    @classmethod
    def get_total_pages(cls, html_content: str) -> int:
        """
        Get the total number of pages from a search results page.
        
        Returns:
            Total number of pages, or 1 if pagination not found
        """
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Look for pagination
        pagination = soup.select(".Pagination-item, .pagination-item, .page-link")
        
        max_page = 1
        for item in pagination:
            text = item.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))
        
        return max_page


class ListingParser:
    """Parser for extracting listing data from njuskalo.hr HTML."""

    @classmethod
    def extract_raw_data(cls, html_content: str) -> dict:
        """Extract raw data from HTML without any classification."""
        soup = BeautifulSoup(html_content, "html.parser")
        listing_data = {}
        
        # 1. TITLE
        title_elem = soup.select_one("h1.ClassifiedDetailSummary-title")
        listing_data["title"] = title_elem.get_text(strip=True) if title_elem else None
        
        # 2. PRICE
        price_elem = soup.select_one("dd.ClassifiedDetailSummary-priceDomestic")
        listing_data["price"] = price_elem.get_text(strip=True) if price_elem else None
        
        # 3. AD ID/CODE
        ad_code_elem = soup.select_one(".ClassifiedDetailSummary-adCode")
        if ad_code_elem:
            ad_code_text = ad_code_elem.get_text(strip=True)
            match = re.search(r"(\d+)", ad_code_text)
            listing_data["ad_id"] = match.group(1) if match else ad_code_text
        else:
            listing_data["ad_id"] = None
        
        # 4. COORDINATES
        coordinates = cls._extract_coordinates(soup)
        if coordinates:
            listing_data["latitude"] = coordinates["lat"]
            listing_data["longitude"] = coordinates["lng"]
            listing_data["location_approximate"] = coordinates.get("approximate", False)
            print(f"[Parser] Found coordinates: lat={coordinates['lat']}, lng={coordinates['lng']}")
        
        # 5. IMAGES
        images = []
        gallery_items = soup.select(".ClassifiedDetailGallery-sliderListItem")
        for item in gallery_items:
            image_data = {
                "id": item.get("data-id"),
                "thumbnail": item.get("data-thumb-image-url"),
                "large": item.get("data-large-image-url"),
                "width": item.get("data-large-image-width"),
                "height": item.get("data-large-image-height"),
            }
            img_elem = item.select_one("img.ClassifiedDetailGallery-slideImage")
            if img_elem:
                image_data["src"] = img_elem.get("src") or img_elem.get("data-src")
            images.append(image_data)
        listing_data["images"] = images
        listing_data["image_count"] = len(images)
        
        # 6. HIGHLIGHTED ATTRIBUTES
        highlighted_attrs = {}
        highlighted_items = soup.select(".ClassifiedDetailHighlightedAttributes-listItem")
        for item in highlighted_items:
            label = item.select_one(".ClassifiedDetailHighlightedAttributes-label")
            value = item.select_one(".ClassifiedDetailHighlightedAttributes-text")
            if label:
                key = label.get_text(strip=True)
                val = value.get_text(strip=True) if value else "Da"
                highlighted_attrs[key] = val
        listing_data["highlighted_attributes"] = highlighted_attrs
        
        # 7. BASIC DETAILS
        basic_details = {}
        detail_terms = soup.select(".ClassifiedDetailBasicDetails-listTerm")
        detail_defs = soup.select(".ClassifiedDetailBasicDetails-listDefinition")
        for term, definition in zip(detail_terms, detail_defs):
            key = term.get_text(strip=True)
            value = definition.get_text(strip=True)
            basic_details[key] = value
        listing_data["basic_details"] = basic_details
        
        # 8. DESCRIPTION
        desc_elem = soup.select_one(".ClassifiedDetailDescription-text")
        listing_data["description"] = desc_elem.get_text(separator="\n", strip=True) if desc_elem else None
        
        # 9. ADDITIONAL INFO
        additional_info = {}
        property_groups = soup.select(".ClassifiedDetailPropertyGroups-group")
        for group in property_groups:
            group_title = group.select_one(".ClassifiedDetailPropertyGroups-groupTitle")
            if group_title:
                title = group_title.get_text(strip=True)
                items = group.select(".ClassifiedDetailPropertyGroups-groupListItem")
                additional_info[title] = [item.get_text(strip=True) for item in items]
        listing_data["additional_info"] = additional_info
        
        # 10. SELLER/OWNER DETAILS
        owner_data = {}
        owner_section = soup.select_one(".ClassifiedDetailOwnerDetails")
        if owner_section:
            owner_name = owner_section.select_one(".ClassifiedDetailOwnerDetails-title a")
            owner_data["name"] = owner_name.get_text(strip=True) if owner_name else None
            
            contact_entries = owner_section.select(".ClassifiedDetailOwnerDetails-contactEntry")
            for entry in contact_entries:
                if entry.select_one(".icon--classifiedDetailViewGlobe"):
                    link = entry.select_one("a")
                    owner_data["website"] = link.get("href") if link else None
        listing_data["seller"] = owner_data
        
        # 11. CATEGORY PATH
        breadcrumbs = []
        breadcrumb_items = soup.select(".breadcrumb-item a.link")
        for item in breadcrumb_items:
            breadcrumbs.append(item.get_text(strip=True))
        listing_data["category_path"] = breadcrumbs
        
        return listing_data

    @classmethod
    def _extract_coordinates(cls, soup: BeautifulSoup) -> Optional[dict]:
        """
        Extract latitude and longitude from the ClassifiedDetailMap script tag.
        
        Returns:
            Dict with 'lat', 'lng', and 'approximate' keys, or None if not found
        """
        # Find all script tags
        script_tags = soup.find_all("script")
        
        for script in script_tags:
            script_content = script.string
            if not script_content:
                continue
            
            # Look for the ClassifiedDetailMap boot data
            if "ClassifiedDetailMap" in script_content and "mapData" in script_content:
                try:
                    # Extract the JSON object from app.boot.push(...)
                    # Pattern: app.boot.push({...})
                    match = re.search(r'app\.boot\.push\((.*?)\);?\s*$', script_content, re.DOTALL)
                    if match:
                        json_str = match.group(1)
                        data = json.loads(json_str)
                        
                        # Navigate to the coordinates
                        map_data = data.get("values", {}).get("mapData", {})
                        default_marker = map_data.get("defaultMarker", {})
                        
                        lat = default_marker.get("lat")
                        lng = default_marker.get("lng")
                        approximate = default_marker.get("approximate", False)
                        
                        if lat is not None and lng is not None:
                            print(f"[Parser] Found coordinates: lat={lat}, lng={lng}, approximate={approximate}")
                            return {
                                "lat": lat,
                                "lng": lng,
                                "approximate": approximate
                            }
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[Parser] Failed to parse map coordinates: {e}")
                    continue
        
        print("[Parser] No coordinates found in page")
        return None

    @classmethod
    def _convert_images(cls, raw_images: list) -> list[ImageData]:
        """Convert raw image dicts to ImageData objects."""
        return [
            ImageData(
                id=img.get("id"),
                thumbnail=img.get("thumbnail"),
                large=img.get("large"),
                src=img.get("src"),
                width=img.get("width"),
                height=img.get("height"),
            )
            for img in raw_images
        ]

    @classmethod
    def _map_construction_phase(cls, phase: Optional[str]) -> ConstructionPhase:
        """Map string to ConstructionPhase enum."""
        if not phase:
            return ConstructionPhase.UNKNOWN
        mapping = {
            "ROH_BAU": ConstructionPhase.ROH_BAU,
            "HIGH_ROH_BAU": ConstructionPhase.HIGH_ROH_BAU,
            "FINISHED_NEW": ConstructionPhase.FINISHED_NEW,
            "OLD_MAINTAINED": ConstructionPhase.OLD_MAINTAINED,
            "NEEDS_RENOVATION": ConstructionPhase.NEEDS_RENOVATION,
        }
        return mapping.get(phase.upper(), ConstructionPhase.UNKNOWN)

    @classmethod
    def _map_heating_system(cls, heating: Optional[str]) -> HeatingSystem:
        """Map string to HeatingSystem enum."""
        if not heating:
            return HeatingSystem.UNKNOWN
        mapping = {
            "GAS_FLOOR": HeatingSystem.GAS_FLOOR,
            "HEAT_PUMP": HeatingSystem.HEAT_PUMP,
            "ELECTRIC": HeatingSystem.ELECTRIC,
            "DISTRICT_HEATING": HeatingSystem.DISTRICT_HEATING,
            "WOOD_PELLET": HeatingSystem.WOOD_PELLET,
            "WOOD/PELLET": HeatingSystem.WOOD_PELLET,
        }
        return mapping.get(heating.upper(), HeatingSystem.UNKNOWN)

    @classmethod
    def _map_parking_type(cls, parking: Optional[str]) -> ParkingType:
        """Map string to ParkingType enum."""
        if not parking:
            return ParkingType.UNKNOWN
        mapping = {
            "GARAGE": ParkingType.GARAGE,
            "OUTDOOR_OWNED": ParkingType.OUTDOOR_OWNED,
            "PUBLIC_PAID": ParkingType.PUBLIC_PAID,
            "NONE": ParkingType.NONE,
        }
        return mapping.get(parking.upper(), ParkingType.UNKNOWN)

    @classmethod
    def _map_building_type(cls, building_type: Optional[str]) -> Optional[BuildingType]:
        """Map string to BuildingType enum."""
        if not building_type:
            return None
        mapping = {
            "HOUSE": BuildingType.HOUSE,
            "BUILDING": BuildingType.BUILDING,
        }
        return mapping.get(building_type.upper())

    @classmethod
    async def parse(cls, html_content: str, url: str, location_context: dict = None) -> ListingCreate:
        """
        Parse HTML content using LLM for classification.
        
        Args:
            html_content: Raw HTML content of the listing page
            url: The source URL
            location_context: Optional dict with location info to help LLM:
                - zupanija: County name (e.g., "Varaždinska županija")
                - city: Main city (e.g., "Varaždin")
                - districts: List of district names
                - neighborhoods: List of neighborhood names
        """
        settings = get_settings()
        
        # Extract raw data from HTML
        raw_data = cls.extract_raw_data(html_content)
        print(f"[Parser] Extracted: title={raw_data.get('title')}, price={raw_data.get('price')}")
        
        # Convert images
        images = cls._convert_images(raw_data.get("images", []))
        
        # Check if OpenRouter API key is configured
        if not settings.openrouter_api_key:
            print("[Parser] No OpenRouter key, returning without classification")
            return cls._create_listing_without_llm(raw_data, url, images)
        
        try:
            from .classifier import ListingClassifier
            
            classifier = ListingClassifier()
            c = await classifier.classify(raw_data, location_context=location_context)
            
            print(f"[Parser] Classification complete: renovation_level={c.condition.renovation_level}, building_type={c.building_specs.building_type}")
            
            # Calculate distance from listing to its district center
            listing_lat = raw_data.get("latitude")
            listing_lng = raw_data.get("longitude")
            district = c.location.district
            
            distance_from_center = None
            if listing_lat is not None and listing_lng is not None:
                # Get district center coordinates
                center_lat, center_lng = get_district_center(district)
                distance_from_center = haversine_distance(listing_lat, listing_lng, center_lat, center_lng)
                print(f"[Parser] Distance from {district or 'Varaždin'} center: {distance_from_center} km")
            
            return ListingCreate(
                external_id=c.basic_info.listing_id or raw_data.get("ad_id"),
                url=url,
                source=ListingSource.NJUSKALO,
                source_id=raw_data.get("ad_id"),
                title=c.basic_info.title or raw_data.get("title"),
                price_eur=c.basic_info.price_euros,
                # Location
                location_city=c.location.city,
                location_district=c.location.district,
                floor_level=c.location.floor_level,
                latitude=listing_lat,
                longitude=listing_lng,
                location_approximate=raw_data.get("location_approximate"),
                distance_from_center=distance_from_center,
                # Dimensions
                metadata_area_m2=c.dimensions.metadata_area_m2,
                living_area_m2=c.dimensions.description_living_area_m2,
                outdoor_area_m2=c.dimensions.outdoor_area_m2,
                area_conflict=c.dimensions.area_conflict_detected,
                # Building specs
                year_built=c.building_specs.year_built,
                is_new_construction=c.building_specs.is_new_construction,
                bedroom_count=c.building_specs.bedroom_count,
                bathroom_count=c.building_specs.bathroom_count,
                parking_type=cls._map_parking_type(c.building_specs.parking_type),
                building_type=cls._map_building_type(c.building_specs.building_type),
                interior_arranged=c.building_specs.interior_arranged,
                has_cellar=c.building_specs.has_cellar,
                # Condition
                construction_phase=cls._map_construction_phase(c.condition.construction_phase),
                renovation_level=c.condition.renovation_level,
                heating_system=cls._map_heating_system(c.condition.heating_system),
                energy_class=c.condition.energy_class,
                # Content
                description=raw_data.get("description"),
                images=images,
                additional_info=raw_data.get("additional_info", {}),
                # Seller
                seller_name=raw_data.get("seller", {}).get("name"),
                seller_contact=raw_data.get("seller", {}).get("website"),
                raw_data=raw_data,
            )
        except Exception as e:
            print(f"[Parser] LLM failed: {e}")
            import traceback
            traceback.print_exc()
            return cls._create_listing_without_llm(raw_data, url, images)

    @classmethod
    def _create_listing_without_llm(cls, raw_data: dict, url: str, images: list[ImageData]) -> ListingCreate:
        """Create a listing without LLM classification (fallback)."""
        # Calculate distance from default Varaždin center
        listing_lat = raw_data.get("latitude")
        listing_lng = raw_data.get("longitude")
        distance_from_center = None
        if listing_lat is not None and listing_lng is not None:
            distance_from_center = haversine_distance(
                listing_lat, listing_lng,
                DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG
            )
        
        return ListingCreate(
            external_id=raw_data.get("ad_id"),
            url=url,
            source=ListingSource.NJUSKALO,
            source_id=raw_data.get("ad_id"),
            title=raw_data.get("title"),
            price_eur=None,
            location_city=None,
            location_district=None,
            floor_level=None,
            latitude=listing_lat,
            longitude=listing_lng,
            location_approximate=raw_data.get("location_approximate"),
            distance_from_center=distance_from_center,
            metadata_area_m2=None,
            living_area_m2=None,
            outdoor_area_m2=None,
            area_conflict=None,
            year_built=None,
            is_new_construction=None,
            bedroom_count=None,
            bathroom_count=None,
            parking_type=ParkingType.UNKNOWN,
            building_type=None,
            interior_arranged=None,
            has_cellar=None,
            construction_phase=ConstructionPhase.UNKNOWN,
            renovation_level=None,
            heating_system=HeatingSystem.UNKNOWN,
            energy_class=None,
            description=raw_data.get("description"),
            images=images,
            additional_info=raw_data.get("additional_info", {}),
            seller_name=raw_data.get("seller", {}).get("name"),
            seller_contact=raw_data.get("seller", {}).get("website"),
            raw_data=raw_data,
        )
