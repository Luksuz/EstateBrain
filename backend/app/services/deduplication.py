"""
Cross-marketplace deduplication service for real estate listings.
Uses fuzzy matching to identify potential duplicate properties across different sources.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .supabase import SupabaseService


class DuplicateStatus(str, Enum):
    """Status of a duplicate relationship."""
    PENDING = "pending"        # Needs review
    CONFIRMED = "confirmed"    # Confirmed as duplicate
    REJECTED = "rejected"      # Not a duplicate (false positive)


@dataclass
class SimilarityResult:
    """Result of comparing two listings."""
    listing_a_id: str
    listing_b_id: str
    listing_a_url: str
    listing_b_url: str
    listing_a_source: str
    listing_b_source: str
    overall_score: float
    score_breakdown: Dict[str, float]
    
    
@dataclass
class DuplicateCandidate:
    """A potential duplicate listing pair."""
    primary_listing: Dict[str, Any]
    duplicate_listing: Dict[str, Any]
    similarity_score: float
    score_breakdown: Dict[str, float]
    status: DuplicateStatus = DuplicateStatus.PENDING


# Feature weights for similarity scoring (must sum to 100)
SIMILARITY_WEIGHTS = {
    "price": 30,           # Price is a strong indicator
    "area": 30,            # Area is very important
    "rooms": 20,           # Room count matters
    "renovation": 10,      # Renovation level can vary between listings
    "location": 10,        # Same district is important
}

# Tolerances for similarity calculations
PRICE_TOLERANCE_PCT = 0.05      # 15% price difference allowed
AREA_TOLERANCE_PCT = 0.05       # 10% area difference allowed
RENOVATION_TOLERANCE = 1        # 3 level difference max


def calculate_price_similarity(price_a: Optional[float], price_b: Optional[float]) -> float:
    """
    Calculate similarity score for prices.
    
    Returns:
        Score from 0-100 based on price similarity
    """
    if price_a is None or price_b is None:
        return 0  # Can't compare without prices
    
    if price_a <= 0 or price_b <= 0:
        return 0
    
    diff_pct = abs(price_a - price_b) / max(price_a, price_b)
    
    if diff_pct <= PRICE_TOLERANCE_PCT:
        # Linear decay within tolerance
        return 100 * (1 - diff_pct / PRICE_TOLERANCE_PCT)
    else:
        return 0


def calculate_area_similarity(area_a: Optional[float], area_b: Optional[float]) -> float:
    """
    Calculate similarity score for living area.
    
    Returns:
        Score from 0-100 based on area similarity
    """
    if area_a is None or area_b is None:
        return 0  # Can't compare without areas
    
    if area_a <= 0 or area_b <= 0:
        return 0
    
    diff_pct = abs(area_a - area_b) / max(area_a, area_b)
    
    if diff_pct <= AREA_TOLERANCE_PCT:
        # Linear decay within tolerance
        return 100 * (1 - diff_pct / AREA_TOLERANCE_PCT)
    else:
        return 0


def calculate_rooms_similarity(rooms_a: Optional[int], rooms_b: Optional[int]) -> float:
    """
    Calculate similarity score for room count.
    
    Returns:
        Score from 0-100 based on room count similarity
    """
    if rooms_a is None or rooms_b is None:
        return 0  # Can't compare without room count
    
    diff = abs(rooms_a - rooms_b)
    
    if diff == 0:
        return 100
    elif diff == 1:
        return 50  # One room difference is plausible (counting differences)
    else:
        return 0


def calculate_renovation_similarity(
    reno_a: Optional[int], 
    reno_b: Optional[int]
) -> float:
    """
    Calculate similarity score for renovation level.
    
    Returns:
        Score from 0-100 based on renovation level similarity
    """
    if reno_a is None or reno_b is None:
        return 0  # Can't compare without renovation level
    
    diff = abs(reno_a - reno_b)
    
    if diff <= RENOVATION_TOLERANCE:
        # Linear decay within tolerance
        return 100 * (1 - diff / RENOVATION_TOLERANCE)
    else:
        return 0


def calculate_location_similarity(
    district_a: Optional[str], 
    district_b: Optional[str]
) -> float:
    """
    Calculate similarity score for location.
    
    Returns:
        100 if same district, 0 otherwise
    """
    if district_a is None or district_b is None:
        return 0
    
    # Normalize and compare
    district_a_norm = district_a.lower().strip()
    district_b_norm = district_b.lower().strip()
    
    if district_a_norm == district_b_norm:
        return 100
    
    # Check for partial matches (e.g., "Varaždin" vs "Centar, Varaždin")
    if district_a_norm in district_b_norm or district_b_norm in district_a_norm:
        return 50
    
    return 0


def calculate_similarity_score(
    listing_a: Dict[str, Any], 
    listing_b: Dict[str, Any]
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate overall similarity score between two listings.
    
    Args:
        listing_a: First listing dict
        listing_b: Second listing dict
        
    Returns:
        Tuple of (overall_score, breakdown_dict)
        Overall score is 0-100, breakdown shows individual component scores
    """
    breakdown = {}
    weighted_score = 0
    total_weight = 0
    
    # Price similarity
    price_score = calculate_price_similarity(
        listing_a.get("price_eur"),
        listing_b.get("price_eur")
    )
    if listing_a.get("price_eur") and listing_b.get("price_eur"):
        breakdown["price"] = price_score
        weighted_score += price_score * SIMILARITY_WEIGHTS["price"]
        total_weight += SIMILARITY_WEIGHTS["price"]
    
    # Area similarity
    area_score = calculate_area_similarity(
        listing_a.get("living_area_m2"),
        listing_b.get("living_area_m2")
    )
    if listing_a.get("living_area_m2") and listing_b.get("living_area_m2"):
        breakdown["area"] = area_score
        weighted_score += area_score * SIMILARITY_WEIGHTS["area"]
        total_weight += SIMILARITY_WEIGHTS["area"]
    
    # Room count similarity
    rooms_score = calculate_rooms_similarity(
        listing_a.get("bedroom_count"),
        listing_b.get("bedroom_count")
    )
    if listing_a.get("bedroom_count") is not None and listing_b.get("bedroom_count") is not None:
        breakdown["rooms"] = rooms_score
        weighted_score += rooms_score * SIMILARITY_WEIGHTS["rooms"]
        total_weight += SIMILARITY_WEIGHTS["rooms"]
    
    # Renovation level similarity
    reno_score = calculate_renovation_similarity(
        listing_a.get("renovation_level"),
        listing_b.get("renovation_level")
    )
    if listing_a.get("renovation_level") is not None and listing_b.get("renovation_level") is not None:
        breakdown["renovation"] = reno_score
        weighted_score += reno_score * SIMILARITY_WEIGHTS["renovation"]
        total_weight += SIMILARITY_WEIGHTS["renovation"]
    
    # Location similarity
    location_score = calculate_location_similarity(
        listing_a.get("location_district"),
        listing_b.get("location_district")
    )
    if listing_a.get("location_district") and listing_b.get("location_district"):
        breakdown["location"] = location_score
        weighted_score += location_score * SIMILARITY_WEIGHTS["location"]
        total_weight += SIMILARITY_WEIGHTS["location"]
    
    # Calculate overall score (normalize by weights actually used)
    if total_weight > 0:
        overall_score = weighted_score / total_weight
    else:
        overall_score = 0
    
    return overall_score, breakdown


class DeduplicationService:
    """Service for finding and managing duplicate listings."""
    
    # Minimum score to consider listings as potential duplicates
    DUPLICATE_THRESHOLD = 75
    
    def __init__(self):
        self.supabase = SupabaseService()
    
    async def find_duplicates_for_listing(
        self, 
        listing_id: str,
        min_score: float = None
    ) -> List[DuplicateCandidate]:
        """
        Find potential duplicates for a specific listing.
        
        Args:
            listing_id: ID of the listing to check
            min_score: Minimum similarity score (default: DUPLICATE_THRESHOLD)
            
        Returns:
            List of DuplicateCandidate objects
        """
        if min_score is None:
            min_score = self.DUPLICATE_THRESHOLD
        
        # Get the target listing
        target = await self.supabase.get_listing(listing_id)
        if not target:
            return []
        
        # Get all other listings (different source preferred for cross-marketplace dedup)
        query = self.supabase.client.table("listings_v3").select("*")
        query = query.neq("id", listing_id)
        query = query.is_("duplicate_of", "null")  # Don't check already-marked duplicates
        
        # Prefer checking against other sources
        if target.get("source"):
            query = query.neq("source", target["source"])
        
        result = query.execute()
        candidates = result.data
        
        duplicates = []
        for candidate in candidates:
            score, breakdown = calculate_similarity_score(target, candidate)
            
            if score >= min_score:
                duplicates.append(DuplicateCandidate(
                    primary_listing=target,
                    duplicate_listing=candidate,
                    similarity_score=score,
                    score_breakdown=breakdown,
                ))
        
        # Sort by similarity score descending
        duplicates.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return duplicates
    
    async def find_all_cross_source_duplicates(
        self,
        min_score: float = None,
        limit: int = 100
    ) -> List[DuplicateCandidate]:
        """
        Find all potential duplicates between different sources.
        
        Compares njuskalo listings against crozilla listings.
        
        Args:
            min_score: Minimum similarity score (default: DUPLICATE_THRESHOLD)
            limit: Maximum number of candidates to return
            
        Returns:
            List of DuplicateCandidate objects
        """
        if min_score is None:
            min_score = self.DUPLICATE_THRESHOLD
        
        # Get all listings grouped by source
        njuskalo_query = self.supabase.client.table("listings_v3").select("*")
        njuskalo_query = njuskalo_query.eq("source", "njuskalo")
        njuskalo_query = njuskalo_query.is_("duplicate_of", "null")
        njuskalo_result = njuskalo_query.execute()
        njuskalo_listings = njuskalo_result.data
        
        crozilla_query = self.supabase.client.table("listings_v3").select("*")
        crozilla_query = crozilla_query.eq("source", "crozilla")
        crozilla_query = crozilla_query.is_("duplicate_of", "null")
        crozilla_result = crozilla_query.execute()
        crozilla_listings = crozilla_result.data
        
        print(f"[Dedup] Comparing {len(njuskalo_listings)} njuskalo vs {len(crozilla_listings)} crozilla listings")
        
        duplicates = []
        checked_pairs = set()  # Avoid duplicate pairs
        
        for njuskalo in njuskalo_listings:
            for crozilla in crozilla_listings:
                # Create sorted pair key to avoid checking both directions
                pair_key = tuple(sorted([njuskalo["id"], crozilla["id"]]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                score, breakdown = calculate_similarity_score(njuskalo, crozilla)
                
                if score >= min_score:
                    duplicates.append(DuplicateCandidate(
                        primary_listing=njuskalo,  # Njuskalo is primary
                        duplicate_listing=crozilla,
                        similarity_score=score,
                        score_breakdown=breakdown,
                    ))
        
        # Sort by similarity score descending
        duplicates.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return duplicates[:limit]
    
    async def mark_as_duplicate(
        self, 
        duplicate_id: str, 
        primary_id: str
    ) -> bool:
        """
        Mark a listing as a duplicate of another.
        
        Args:
            duplicate_id: ID of the duplicate listing
            primary_id: ID of the primary listing
            
        Returns:
            True if successful
        """
        try:
            self.supabase.client.table("listings_v3").update({
                "duplicate_of": primary_id
            }).eq("id", duplicate_id).execute()
            return True
        except Exception as e:
            print(f"[Dedup] Error marking duplicate: {e}")
            return False
    
    async def unmark_duplicate(self, listing_id: str) -> bool:
        """
        Remove duplicate marking from a listing.
        
        Args:
            listing_id: ID of the listing to unmark
            
        Returns:
            True if successful
        """
        try:
            self.supabase.client.table("listings_v3").update({
                "duplicate_of": None
            }).eq("id", listing_id).execute()
            return True
        except Exception as e:
            print(f"[Dedup] Error unmarking duplicate: {e}")
            return False
    
    async def get_duplicate_groups(self) -> List[Dict[str, Any]]:
        """
        Get all listings grouped by their duplicate relationships.
        
        Returns:
            List of groups, each containing primary listing and its duplicates
        """
        # Get all listings that are marked as duplicates
        query = self.supabase.client.table("listings_v3").select("*")
        query = query.not_.is_("duplicate_of", "null")
        result = query.execute()
        
        # Group by primary listing
        groups = {}
        for listing in result.data:
            primary_id = listing["duplicate_of"]
            if primary_id not in groups:
                groups[primary_id] = {
                    "primary_id": primary_id,
                    "duplicates": []
                }
            groups[primary_id]["duplicates"].append(listing)
        
        # Fetch primary listing details
        for primary_id, group in groups.items():
            primary = await self.supabase.get_listing(primary_id)
            if primary:
                group["primary_listing"] = primary
        
        return list(groups.values())


# Singleton instance
_dedup_service: Optional[DeduplicationService] = None


def get_deduplication_service() -> DeduplicationService:
    """Get or create deduplication service singleton."""
    global _dedup_service
    if _dedup_service is None:
        _dedup_service = DeduplicationService()
    return _dedup_service


