"""
Parser for Crozilla.com real estate listings.
Extracts raw data from HTML and uses the shared LLM classifier.
"""

import re
import json
import math
from bs4 import BeautifulSoup
from typing import Optional, List, Tuple
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
from .parser import (
    get_district_center,
    haversine_distance,
    DEFAULT_CENTER_LAT,
    DEFAULT_CENTER_LNG,
)


class CrozillaSearchParser:
    """Parser for extracting listing URLs from Crozilla.com search results pages."""
    
    BASE_URL = "https://www.crozilla.com"
    
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
        
        # Primary method: Get URLs from tile links
        # Selector: .search-results__tile-row a.tile__link
        tile_links = soup.select(".search-results__tile-row a.tile__link")
        for link in tile_links:
            href = link.get("href")
            if href and cls._is_listing_url(href):
                full_url = urljoin(cls.BASE_URL, href)
                urls.add(full_url)
        
        # Fallback: Any link with /nekretnina/ in path
        if not urls:
            all_links = soup.select("a[href*='/nekretnina/']")
            for link in all_links:
                href = link.get("href")
                if href and cls._is_listing_url(href):
                    full_url = urljoin(cls.BASE_URL, href)
                    urls.add(full_url)
        
        print(f"[CrozillaSearchParser] Found {len(urls)} listing URLs")
        return list(urls)
    
    @classmethod
    def _is_listing_url(cls, href: str) -> bool:
        """Check if a URL is a listing detail page."""
        if not href:
            return False
        
        # Listing URLs contain /nekretnina/ followed by digits
        if "/nekretnina/" in href:
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
        
        # Look for pagination elements
        pagination = soup.select(".pagination a, .paging a, [class*='page']")
        
        max_page = 1
        for item in pagination:
            text = item.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))
        
        return max_page
    
    @classmethod
    def extract_source_id(cls, url: str) -> Optional[str]:
        """Extract the Crozilla listing ID from URL.
        
        Example: https://www.crozilla.com/nekretnina/17302483 -> 17302483
        """
        match = re.search(r'/nekretnina/(\d+)', url)
        return match.group(1) if match else None


class CrozillaListingParser:
    """Parser for extracting listing data from Crozilla.com HTML."""

    @classmethod
    def _extract_coordinates(cls, soup: BeautifulSoup) -> Tuple[Optional[float], Optional[float]]:
        """
        Extract latitude and longitude from the __NUXT__ JavaScript variable.
        
        Crozilla stores property data in a Nuxt.js hydration script that contains
        the property object with latitude and longitude fields.
        
        Returns:
            Tuple of (latitude, longitude), or (None, None) if not found
        """
        try:
            # Find all script tags
            script_tags = soup.find_all("script")
            
            for script in script_tags:
                script_content = script.string
                if not script_content:
                    continue
                
                # Look for __NUXT__ variable assignment
                if "window.__NUXT__" in script_content or "__NUXT__" in script_content:
                    # Try to extract the JSON data
                    # Pattern: window.__NUXT__= or __NUXT__=
                    match = re.search(r'(?:window\.)?__NUXT__\s*=\s*(\{.+\})\s*;?\s*$', script_content, re.DOTALL)
                    if match:
                        try:
                            nuxt_json = match.group(1)
                            # Clean up the JSON - remove function calls that might break parsing
                            # Sometimes Nuxt uses functions like `function(a,b,c){...}` which aren't valid JSON
                            # Try parsing as-is first
                            nuxt_data = json.loads(nuxt_json)
                            
                            # Navigate to property data - structure: data[0].property
                            data = nuxt_data.get("data", [])
                            if data and len(data) > 0:
                                first_data = data[0]
                                if isinstance(first_data, dict):
                                    property_data = first_data.get("property", {})
                                    lat = property_data.get("latitude")
                                    lng = property_data.get("longitude")
                                    
                                    if lat is not None and lng is not None:
                                        print(f"[CrozillaParser] Found coordinates: lat={lat}, lng={lng}")
                                        return (float(lat), float(lng))
                        except json.JSONDecodeError:
                            # NUXT uses unquoted keys - try regex without quotes
                            pass
                    
                    # Property-level coordinates appear as: longitude:X,latitude:Y (lng before lat)
                    # Geography fallback appears as: latitude:X,longitude:Y (lat before lng)
                    # Try to find property-level first (more specific)
                    
                    # Find all coordinate pairs
                    all_coords = []
                    
                    # Pattern 1: longitude,latitude (property level - more specific)
                    prop_match = re.search(r'longitude["\']?\s*:\s*([\d.-]+)[,\s]+latitude["\']?\s*:\s*([\d.-]+)', script_content)
                    if prop_match:
                        lng = float(prop_match.group(1))
                        lat = float(prop_match.group(2))
                        # Skip if it's the county fallback (46.25)
                        if abs(lat - 46.25) > 0.001:
                            print(f"[CrozillaParser] Found property coordinates: lat={lat}, lng={lng}")
                            return (lat, lng)
                        all_coords.append((lat, lng, "property"))
                    
                    # Pattern 2: latitude,longitude (geography level)
                    geo_matches = re.findall(r'latitude["\']?\s*:\s*([\d.-]+)[,\s\}]+[^}]*?longitude["\']?\s*:\s*([\d.-]+)', script_content)
                    for lat_str, lng_str in geo_matches:
                        lat = float(lat_str)
                        lng = float(lng_str)
                        # Skip if it's the county fallback (46.25)
                        if abs(lat - 46.25) > 0.001:
                            all_coords.append((lat, lng, "geography"))
                    
                    # Return the most specific coordinates found (non-fallback)
                    for lat, lng, source in all_coords:
                        if abs(lat - 46.25) > 0.001:
                            print(f"[CrozillaParser] Found coordinates ({source}): lat={lat}, lng={lng}")
                            return (lat, lng)
                    
                    # Fallback to first match if all are county-level
                    lat_match = re.search(r'latitude["\']?\s*:\s*([\d.-]+)', script_content)
                    lng_match = re.search(r'longitude["\']?\s*:\s*([\d.-]+)', script_content)
                    if lat_match and lng_match:
                        lat = float(lat_match.group(1))
                        lng = float(lng_match.group(1))
                        print(f"[CrozillaParser] Found coordinates (fallback): lat={lat}, lng={lng}")
                        return (lat, lng)
            
            print("[CrozillaParser] No coordinates found in __NUXT__ data")
            return (None, None)
            
        except Exception as e:
            print(f"[CrozillaParser] Failed to extract coordinates: {e}")
            return (None, None)

    @classmethod
    def extract_raw_data(cls, html_content: str, url: str) -> dict:
        """Extract raw data from HTML without any classification."""
        soup = BeautifulSoup(html_content, "html.parser")
        listing_data = {}
        
        # --- Extract coordinates from __NUXT__ ---
        latitude, longitude = cls._extract_coordinates(soup)
        listing_data["latitude"] = latitude
        listing_data["longitude"] = longitude
        
        # Helper functions matching the JS snippet
        def get_text(selector: str) -> Optional[str]:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(separator=" ", strip=True)
                return " ".join(text.split())  # Normalize whitespace
            return None
        
        def get_detail_value(detail_name: str) -> Optional[str]:
            """Get value from property details dt/dd pairs."""
            dts = soup.select(".property__details dt")
            for dt in dts:
                if dt.get_text(strip=True) == detail_name:
                    dd = dt.find_next_sibling("dd")
                    if dd:
                        return " ".join(dd.get_text(separator=" ", strip=True).split())
            return None
        
        def extract_features(data_test_id: str) -> Optional[List[str]]:
            """Extract available features from a feature list."""
            ul = soup.select_one(f'ul[data-test-id="{data_test_id}"]')
            if not ul:
                return None
            
            features = []
            for li in ul.select("li"):
                # Check for SVG with 'on' class (available feature)
                if li.select_one("svg.on"):
                    name = li.get_text(strip=True)
                    features.append(name)
            
            return features if features else None
        
        # --- Main Data ---
        listing_data["title"] = get_text("h1.property__title")
        listing_data["location"] = get_text("span.property__address")
        
        # Price - try multiple selectors
        price_text = get_text(".property__price__text")
        if not price_text:
            price_text = get_text(".property__price-top span")
        if price_text:
            listing_data["price"] = price_text.replace("€", "").strip()
        
        # --- Property Details ---
        listing_data["price_per_sqm"] = get_detail_value("Cijena po m²")
        listing_data["area_sqm"] = get_detail_value("Površina")
        listing_data["levels"] = get_detail_value("Nivoi")
        
        # Floor - clean up extra info
        floor = get_detail_value("Kat")
        if floor:
            floor = re.sub(r"\s*\(Broj katova:\s*\d+\)", "", floor).strip()
        listing_data["floor"] = floor
        
        listing_data["kitchens"] = get_detail_value("Kuhinje")
        listing_data["bathrooms_count"] = get_detail_value("Kupaonice")
        listing_data["living_rooms"] = get_detail_value("Dnevne sobe")
        listing_data["heating"] = get_detail_value("Grijanje")
        listing_data["year_built"] = get_detail_value("Godina izgradnje")
        
        # Energy class - try container first, then detail value
        energy_elem = soup.select_one(".property__details dd .energy-container")
        if energy_elem:
            listing_data["energy_class"] = energy_elem.get_text(strip=True)
        else:
            listing_data["energy_class"] = get_detail_value("Energetski razred")
        
        listing_data["documents"] = get_detail_value("Dokumenti")
        listing_data["property_id"] = get_detail_value("Šifra u sustavu")
        listing_data["advertiser_id"] = get_detail_value("Šifra oglasa")
        listing_data["first_published"] = get_detail_value("Prvi put objavljeno")
        listing_data["last_updated"] = get_detail_value("Poslijednje ažuriranje")
        
        # --- Description ---
        desc_elem = soup.select_one(".property__description p")
        if desc_elem:
            # Convert <br> to newlines
            html = str(desc_elem)
            html = re.sub(r"<br\s*/?>", "\n", html)
            desc_soup = BeautifulSoup(html, "html.parser")
            listing_data["description"] = desc_soup.get_text(strip=True)
        
        # --- Summary Info from Icon List ---
        info_items = soup.select("ul.property__info li")
        for item in info_items:
            text = item.get_text(strip=True)
            item_id = item.get("id", "")
            if item_id == "roomsIcon":
                listing_data["rooms_total"] = text
            elif item_id == "no_of_bathroomsIcon":
                listing_data["bathrooms_icon"] = text
        
        # --- Features ---
        listing_data["features"] = {
            "indoor": extract_features("indoor"),
            "outdoor": extract_features("outdoor"),
            "construction": extract_features("construction"),
            "good_for": extract_features("goodfor"),
        }
        
        # Extract parking count from outdoor features
        outdoor_features = listing_data["features"].get("outdoor") or []
        for feature in outdoor_features:
            if "Parkirna mjesta" in feature:
                match = re.search(r"\((\d+)\)", feature)
                if match:
                    listing_data["parking_spaces_count"] = int(match.group(1))
                else:
                    listing_data["parking_spaces_count"] = 1
        
        # --- Images ---
        images = []
        gallery_items = soup.select(".property__gallery__item img")
        for img in gallery_items:
            src = img.get("src") or img.get("data-src")
            if src:
                images.append({"src": src})
        listing_data["images"] = images
        
        # Total image count
        total_images_text = get_text(".property__gallery__mediainfo span")
        if total_images_text and total_images_text.isdigit():
            listing_data["total_images"] = int(total_images_text)
        else:
            listing_data["total_images"] = len(images)
        
        # --- Agency Info ---
        agency_elem = soup.select_one(".property__agency__info")
        if agency_elem:
            listing_data["agency"] = {
                "name": get_text(".property__agency__info h3 a"),
                "address": get_text(".property__agency__info p"),
                "website": soup.select_one(".property__agency__website").get("href") 
                           if soup.select_one(".property__agency__website") else None,
                "agent": get_text(".property__agency__contact"),
            }
        
        # --- Source ID from URL ---
        listing_data["source_id"] = CrozillaSearchParser.extract_source_id(url)
        listing_data["ad_id"] = listing_data.get("property_id") or listing_data.get("source_id")
        
        return listing_data

    @classmethod
    def _convert_images(cls, raw_images: list) -> list[ImageData]:
        """Convert raw image dicts to ImageData objects."""
        return [
            ImageData(
                src=img.get("src"),
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
    def _convert_to_classifier_format(cls, raw_data: dict) -> dict:
        """
        Convert Crozilla raw data format to the format expected by the LLM classifier.
        This maps Crozilla field names to the classifier's expected structure.
        """
        # Build highlighted_attributes (similar to njuskalo's format)
        highlighted_attributes = {}
        if raw_data.get("area_sqm"):
            highlighted_attributes["Stambena površina"] = raw_data["area_sqm"]
        if raw_data.get("rooms_total"):
            highlighted_attributes["Broj soba"] = raw_data["rooms_total"]
        if raw_data.get("floor"):
            highlighted_attributes["Kat"] = raw_data["floor"]
        
        # Build basic_details
        basic_details = {}
        if raw_data.get("location"):
            basic_details["Lokacija"] = raw_data["location"]
        if raw_data.get("year_built"):
            basic_details["Godina izgradnje"] = raw_data["year_built"]
        if raw_data.get("heating"):
            basic_details["Grijanje"] = raw_data["heating"]
        if raw_data.get("energy_class"):
            basic_details["Energetski razred"] = raw_data["energy_class"]
        if raw_data.get("bathrooms_count"):
            basic_details["Kupaonice"] = raw_data["bathrooms_count"]
        
        # Build additional_info from features
        additional_info = {}
        features = raw_data.get("features", {})
        if features.get("indoor"):
            additional_info["Unutarnje karakteristike"] = features["indoor"]
        if features.get("outdoor"):
            additional_info["Vanjske karakteristike"] = features["outdoor"]
        if features.get("construction"):
            additional_info["Izgradnja"] = features["construction"]
        
        return {
            "title": raw_data.get("title"),
            "price": raw_data.get("price"),
            "ad_id": raw_data.get("ad_id"),
            "highlighted_attributes": highlighted_attributes,
            "basic_details": basic_details,
            "description": raw_data.get("description"),
            "additional_info": additional_info,
            "images": raw_data.get("images", []),
            "category_path": ["Nekretnine", "Stanovi", "Prodaja"],  # Default for apartments
        }

    @classmethod
    async def parse(cls, html_content: str, url: str, location_context: dict = None) -> ListingCreate:
        """
        Parse HTML content using LLM for classification.
        
        Args:
            html_content: Raw HTML content of the listing page
            url: The source URL
            location_context: Optional dict with location info for LLM
        """
        settings = get_settings()
        
        # Extract raw data from HTML
        raw_data = cls.extract_raw_data(html_content, url)
        print(f"[CrozillaParser] Extracted: title={raw_data.get('title')}, price={raw_data.get('price')}")
        
        # Convert images
        images = cls._convert_images(raw_data.get("images", []))
        
        # Get source ID from URL
        source_id = CrozillaSearchParser.extract_source_id(url)
        
        # Check if OpenRouter API key is configured
        if not settings.openrouter_api_key:
            print("[CrozillaParser] No OpenRouter key, returning without classification")
            return cls._create_listing_without_llm(raw_data, url, images, source_id)
        
        try:
            from .classifier import ListingClassifier
            
            # Convert to classifier format
            classifier_data = cls._convert_to_classifier_format(raw_data)
            
            classifier = ListingClassifier()
            c = await classifier.classify(classifier_data, location_context=location_context)
            
            print(f"[CrozillaParser] Classification complete: renovation_level={c.condition.renovation_level}")
            
            # Get coordinates from raw_data (extracted from __NUXT__)
            listing_lat = raw_data.get("latitude")
            listing_lng = raw_data.get("longitude")
            district = c.location.district
            
            # Calculate distance from listing to its district center
            distance_from_center = None
            if listing_lat is not None and listing_lng is not None:
                center_lat, center_lng = get_district_center(district)
                distance_from_center = haversine_distance(listing_lat, listing_lng, center_lat, center_lng)
                print(f"[CrozillaParser] Distance from {district or 'Varaždin'} center: {distance_from_center} km")
            
            return ListingCreate(
                external_id=c.basic_info.listing_id or raw_data.get("ad_id"),
                url=url,
                source=ListingSource.CROZILLA,
                source_id=source_id,
                title=c.basic_info.title or raw_data.get("title"),
                price_eur=c.basic_info.price_euros,
                # Location
                location_city=c.location.city,
                location_district=c.location.district,
                floor_level=c.location.floor_level,
                latitude=listing_lat,
                longitude=listing_lng,
                location_approximate=False,  # Crozilla coordinates are typically exact
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
                seller_name=raw_data.get("agency", {}).get("name"),
                seller_contact=raw_data.get("agency", {}).get("website"),
                raw_data=raw_data,
            )
        except Exception as e:
            print(f"[CrozillaParser] LLM failed: {e}")
            import traceback
            traceback.print_exc()
            return cls._create_listing_without_llm(raw_data, url, images, source_id)

    @classmethod
    def _create_listing_without_llm(
        cls, raw_data: dict, url: str, images: list[ImageData], source_id: str
    ) -> ListingCreate:
        """Create a listing without LLM classification (fallback)."""
        # Try to extract price
        price_eur = None
        if raw_data.get("price"):
            try:
                # Remove non-numeric chars except decimal
                price_str = re.sub(r"[^\d,.]", "", raw_data["price"])
                price_str = price_str.replace(",", ".")
                price_eur = float(price_str)
            except (ValueError, TypeError):
                pass
        
        # Try to extract area
        area_m2 = None
        if raw_data.get("area_sqm"):
            try:
                area_str = re.sub(r"[^\d,.]", "", raw_data["area_sqm"])
                area_str = area_str.replace(",", ".")
                area_m2 = float(area_str)
            except (ValueError, TypeError):
                pass
        
        # Get coordinates from raw_data
        listing_lat = raw_data.get("latitude")
        listing_lng = raw_data.get("longitude")
        
        # Calculate distance from default Varaždin center
        distance_from_center = None
        if listing_lat is not None and listing_lng is not None:
            distance_from_center = haversine_distance(
                listing_lat, listing_lng,
                DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG
            )
        
        return ListingCreate(
            external_id=raw_data.get("ad_id"),
            url=url,
            source=ListingSource.CROZILLA,
            source_id=source_id,
            title=raw_data.get("title"),
            price_eur=price_eur,
            location_city=None,
            location_district=None,
            floor_level=raw_data.get("floor"),
            latitude=listing_lat,
            longitude=listing_lng,
            location_approximate=False if listing_lat else None,
            distance_from_center=distance_from_center,
            metadata_area_m2=area_m2,
            living_area_m2=area_m2,
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
            energy_class=raw_data.get("energy_class"),
            description=raw_data.get("description"),
            images=images,
            additional_info=raw_data.get("features", {}),
            seller_name=raw_data.get("agency", {}).get("name"),
            seller_contact=raw_data.get("agency", {}).get("website"),
            raw_data=raw_data,
        )


