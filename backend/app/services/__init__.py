from .supabase import get_supabase_client, SupabaseService
from .firecrawl import FirecrawlService
from .parser import ListingParser, SearchPageParser
from .crozilla_parser import CrozillaListingParser, CrozillaSearchParser
from .classifier import ListingClassifier, ClassifiedListing
from .ml_service import get_ml_service, ModelType, ModelResult, CorrelationResult
from .ml_router_helpers import (
    get_filtered_listings,
    calculate_deal_score,
    build_hidden_layers,
    analyze_listings_for_deals,
    build_features_from_request,
    build_confidence_note,
    fallback_price_prediction,
    calculate_similarity_scores,
    format_similar_listing,
    get_available_models,
)
from .deduplication import (
    DeduplicationService,
    get_deduplication_service,
    calculate_similarity_score,
    DuplicateStatus,
)

__all__ = [
    # Supabase
    "get_supabase_client",
    "SupabaseService",
    # Firecrawl
    "FirecrawlService",
    # Parser
    "ListingParser",
    "SearchPageParser",
    # Crozilla Parser
    "CrozillaListingParser",
    "CrozillaSearchParser",
    # Classifier
    "ListingClassifier",
    "ClassifiedListing",
    # ML Service
    "get_ml_service",
    "ModelType",
    "ModelResult",
    "CorrelationResult",
    # ML Router Helpers
    "get_filtered_listings",
    "calculate_deal_score",
    "build_hidden_layers",
    "analyze_listings_for_deals",
    "build_features_from_request",
    "build_confidence_note",
    "fallback_price_prediction",
    "calculate_similarity_scores",
    "format_similar_listing",
    "get_available_models",
    # Deduplication
    "DeduplicationService",
    "get_deduplication_service",
    "calculate_similarity_score",
    "DuplicateStatus",
]

