"""
Parser that extracts raw data from HTML and uses LLM for classification.
"""

import re
from bs4 import BeautifulSoup
from typing import Optional, List
from urllib.parse import urljoin

from ..models.listing import (
    ListingCreate,
    ImageData,
    Room,
    RoomType,
    RoomCondition,
    ConstructionPhase,
    HeatingSystem,
    ParkingType,
)
from ..config import get_settings


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
        
        # 4. IMAGES
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
        
        # 5. HIGHLIGHTED ATTRIBUTES
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
        
        # 6. BASIC DETAILS
        basic_details = {}
        detail_terms = soup.select(".ClassifiedDetailBasicDetails-listTerm")
        detail_defs = soup.select(".ClassifiedDetailBasicDetails-listDefinition")
        for term, definition in zip(detail_terms, detail_defs):
            key = term.get_text(strip=True)
            value = definition.get_text(strip=True)
            basic_details[key] = value
        listing_data["basic_details"] = basic_details
        
        # 7. DESCRIPTION
        desc_elem = soup.select_one(".ClassifiedDetailDescription-text")
        listing_data["description"] = desc_elem.get_text(separator="\n", strip=True) if desc_elem else None
        
        # 8. ADDITIONAL INFO
        additional_info = {}
        property_groups = soup.select(".ClassifiedDetailPropertyGroups-group")
        for group in property_groups:
            group_title = group.select_one(".ClassifiedDetailPropertyGroups-groupTitle")
            if group_title:
                title = group_title.get_text(strip=True)
                items = group.select(".ClassifiedDetailPropertyGroups-groupListItem")
                additional_info[title] = [item.get_text(strip=True) for item in items]
        listing_data["additional_info"] = additional_info
        
        # 9. SELLER/OWNER DETAILS
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
        
        # 10. CATEGORY PATH
        breadcrumbs = []
        breadcrumb_items = soup.select(".breadcrumb-item a.link")
        for item in breadcrumb_items:
            breadcrumbs.append(item.get_text(strip=True))
        listing_data["category_path"] = breadcrumbs
        
        return listing_data

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
    def _map_room_type(cls, room_type: Optional[str]) -> RoomType:
        """Map string to RoomType enum."""
        if not room_type:
            return RoomType.OTHER
        mapping = {
            "LIVING_ROOM": RoomType.LIVING_ROOM,
            "BEDROOM": RoomType.BEDROOM,
            "KITCHEN": RoomType.KITCHEN,
            "BATHROOM": RoomType.BATHROOM,
            "TOILET": RoomType.TOILET,
            "HALLWAY": RoomType.HALLWAY,
            "BALCONY": RoomType.BALCONY,
            "TERRACE": RoomType.TERRACE,
            "STORAGE": RoomType.STORAGE,
            "GARAGE": RoomType.GARAGE,
            "LAUNDRY": RoomType.LAUNDRY,
            "DINING_ROOM": RoomType.DINING_ROOM,
            "OFFICE": RoomType.OFFICE,
            "WALK_IN_CLOSET": RoomType.WALK_IN_CLOSET,
            "EXTERIOR": RoomType.EXTERIOR,
            "FLOOR_PLAN": RoomType.FLOOR_PLAN,
            "OTHER": RoomType.OTHER,
        }
        return mapping.get(room_type.upper(), RoomType.OTHER)

    @classmethod
    def _map_room_condition(cls, condition: Optional[str]) -> RoomCondition:
        """Map string to RoomCondition enum."""
        if not condition:
            return RoomCondition.UNKNOWN
        mapping = {
            "NEW": RoomCondition.NEW,
            "EXCELLENT": RoomCondition.EXCELLENT,
            "GOOD": RoomCondition.GOOD,
            "FAIR": RoomCondition.FAIR,
            "NEEDS_WORK": RoomCondition.NEEDS_WORK,
            "ROH_BAU": RoomCondition.ROH_BAU,
            "UNKNOWN": RoomCondition.UNKNOWN,
        }
        return mapping.get(condition.upper(), RoomCondition.UNKNOWN)

    @classmethod
    def _convert_rooms(cls, classifier_rooms: list) -> list[Room]:
        """Convert classifier room analysis to Room objects."""
        rooms = []
        for r in classifier_rooms:
            rooms.append(Room(
                room_type=cls._map_room_type(r.room_type),
                image_url=r.image_url,
                condition=cls._map_room_condition(r.condition),
                condition_reasoning=r.condition_reasoning,
                features=r.features or [],
                notes=r.notes,
                estimated_area_m2=r.estimated_area_m2,
                from_description=r.from_description,
            ))
        return rooms

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
            
            # Convert rooms from classifier
            rooms = cls._convert_rooms(c.rooms)
            print(f"[Parser] Detected {len(rooms)} rooms from images")
            
            return ListingCreate(
                external_id=c.basic_info.listing_id or raw_data.get("ad_id"),
                url=url,
                title=c.basic_info.title or raw_data.get("title"),
                price_eur=c.basic_info.price_euros,
                # Location
                location_city=c.location.city,
                location_district=c.location.district,
                floor_level=c.location.floor_level,
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
                # Condition
                construction_phase=cls._map_construction_phase(c.condition.construction_phase),
                heating_system=cls._map_heating_system(c.condition.heating_system),
                energy_class=c.condition.energy_class,
                # Content
                description=raw_data.get("description"),
                images=images,
                rooms=rooms,
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
        return ListingCreate(
            external_id=raw_data.get("ad_id"),
            url=url,
            title=raw_data.get("title"),
            price_eur=None,
            location_city=None,
            location_district=None,
            floor_level=None,
            metadata_area_m2=None,
            living_area_m2=None,
            outdoor_area_m2=None,
            area_conflict=None,
            year_built=None,
            is_new_construction=None,
            bedroom_count=None,
            bathroom_count=None,
            parking_type=ParkingType.UNKNOWN,
            construction_phase=ConstructionPhase.UNKNOWN,
            heating_system=HeatingSystem.UNKNOWN,
            energy_class=None,
            description=raw_data.get("description"),
            images=images,
            additional_info=raw_data.get("additional_info", {}),
            seller_name=raw_data.get("seller", {}).get("name"),
            seller_contact=raw_data.get("seller", {}).get("website"),
            raw_data=raw_data,
        )
