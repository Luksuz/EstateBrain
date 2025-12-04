"""
Pydantic models for ML API endpoints.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


# ==================== FEATURE SETS ====================

class FeatureSet(str, Enum):
    """Predefined feature combinations for model training."""
    OPTIMAL = "optimal"         # 5 best features: area, bedrooms, outdoor, renovation, distance (CV=89.2%)
    MINIMAL = "minimal"         # 2 features: area + bedrooms
    CORE = "core"               # 4 features: area, bedrooms, bathrooms, renovation
    STANDARD = "standard"       # 6 features: core + new_construction, garage
    NUMERIC = "numeric"         # All numeric features, no categoricals
    FULL = "full"               # All features including district
    CUSTOM = "custom"           # Custom feature list provided by user


# Feature definitions for each preset
FEATURE_SET_DEFINITIONS = {
    FeatureSet.OPTIMAL: {
        "numeric": ["living_area_m2", "bedroom_count", "distance_from_center"],
        "derived": [],
        "boolean": ["is_new_construction"],
        "categorical": [],
        "description": "Best 4 features after dedup & outlier removal (R²=91.77%, RMSE=€29,856)"
    },
    FeatureSet.MINIMAL: {
        "numeric": ["living_area_m2", "bedroom_count"],
        "derived": [],
        "boolean": [],
        "categorical": [],
        "description": "Most basic: area + bedrooms only"
    },
    FeatureSet.CORE: {
        "numeric": ["living_area_m2", "bedroom_count", "bathroom_count", "renovation_level"],
        "derived": [],
        "boolean": [],
        "categorical": [],
        "description": "Core property features without location"
    },
    FeatureSet.STANDARD: {
        "numeric": ["living_area_m2", "bedroom_count", "bathroom_count", "renovation_level"],
        "derived": ["has_garage"],
        "boolean": ["is_new_construction"],
        "categorical": [],
        "description": "Standard features without location encoding"
    },
    FeatureSet.NUMERIC: {
        "numeric": ["living_area_m2", "bedroom_count", "bathroom_count", "outdoor_area_m2", 
                   "renovation_level", "distance_from_center"],
        "derived": ["has_garage", "is_house", "is_furnished", "has_cellar"],
        "boolean": ["is_new_construction"],
        "categorical": [],
        "description": "All numeric/boolean features, no one-hot encoding"
    },
    FeatureSet.FULL: {
        "numeric": ["living_area_m2", "bedroom_count", "bathroom_count", "outdoor_area_m2",
                   "renovation_level", "distance_from_center"],
        "derived": ["has_garage", "is_house", "is_furnished", "has_cellar"],
        "boolean": ["is_new_construction"],
        "categorical": ["location_district"],
        "description": "All features including location (one-hot encoded)"
    },
}


# ==================== TRAINING ====================

class TrainRequest(BaseModel):
    """Request body for model training."""
    model_type: str = Field("auto", description="Model type - 'auto' selects best model automatically")
    test_size: float = Field(0.2, ge=0.1, le=0.5, description="Test set proportion")
    cv_folds: int = Field(5, ge=2, le=10, description="Cross-validation folds")
    
    # Feature selection
    feature_set: FeatureSet = Field(
        FeatureSet.OPTIMAL, 
        description="Feature set: optimal (4 best features), full, minimal, etc."
    )
    custom_features: Optional[List[str]] = Field(
        None,
        description="Custom feature list (only used when feature_set='custom')"
    )
    
    # Regularization params (Ridge, Lasso, ElasticNet, SVR)
    alpha: Optional[float] = Field(1.0, ge=0.001, le=100, description="Regularization strength")
    l1_ratio: Optional[float] = Field(0.5, ge=0, le=1, description="ElasticNet L1/L2 mix (0=Ridge, 1=Lasso)")
    
    # Tree-based params
    max_depth: Optional[int] = Field(10, ge=1, le=50, description="Tree max depth")
    n_estimators: Optional[int] = Field(100, ge=10, le=500, description="Number of trees/estimators")
    learning_rate: Optional[float] = Field(0.1, ge=0.01, le=1.0, description="Boosting learning rate")
    
    # KNN params
    n_neighbors: Optional[int] = Field(5, ge=1, le=50, description="KNN neighbors")
    
    # SVR params
    C: Optional[float] = Field(1.0, ge=0.01, le=100, description="SVR regularization")
    kernel: Optional[str] = Field("rbf", description="SVR kernel (rbf, linear, poly)")
    
    # MLP (Neural Network) params
    hidden_layer_1: Optional[int] = Field(100, ge=10, le=500, description="Neurons in first hidden layer")
    hidden_layer_2: Optional[int] = Field(50, ge=0, le=500, description="Neurons in second hidden layer (0 to disable)")
    activation: Optional[str] = Field("relu", description="Activation function (relu, tanh, logistic)")
    learning_rate_init: Optional[float] = Field(0.001, ge=0.0001, le=0.1, description="Initial learning rate")
    max_iter: Optional[int] = Field(500, ge=100, le=2000, description="Max iterations")
    
    # Data filters
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    location_district: Optional[str] = None
    
    # Exclusion filters
    exclude_new_construction: Optional[bool] = Field(False, description="Exclude new construction properties")
    only_new_construction: Optional[bool] = Field(False, description="Only include new construction properties")


class ModelResultResponse(BaseModel):
    """Response for model training."""
    model_type: str
    r2_score: float
    rmse: float
    mae: float
    cv_scores: List[float]
    cv_mean: float
    cv_std: float
    feature_importance: Optional[Dict[str, float]] = None
    coefficients: Optional[Dict[str, float]] = None
    predictions: Optional[List[float]] = None
    actual: Optional[List[float]] = None
    sample_count: int
    # Feature set info
    feature_set: Optional[str] = None
    features_used: Optional[List[str]] = None
    feature_count: Optional[int] = None


class FeatureSetInfo(BaseModel):
    """Information about a feature set."""
    name: str
    description: str
    feature_count: int
    features: List[str]


class FeatureSetComparisonResult(BaseModel):
    """Result of training with a specific feature set."""
    feature_set: str
    feature_count: int
    features: List[str]
    r2_score: float
    rmse: float
    mae: float
    cv_mean: float
    cv_std: float


class CompareFeatureSetsRequest(BaseModel):
    """Request to compare different feature sets."""
    model_type: str = Field("ridge", description="Model type to use for comparison")
    feature_sets: List[FeatureSet] = Field(
        default=[FeatureSet.MINIMAL, FeatureSet.CORE, FeatureSet.STANDARD, FeatureSet.NUMERIC, FeatureSet.FULL],
        description="Feature sets to compare"
    )
    test_size: float = Field(0.2, ge=0.1, le=0.5)
    cv_folds: int = Field(5, ge=2, le=10)
    # Data filters
    min_price: Optional[float] = None
    max_price: Optional[float] = None


class CompareFeatureSetsResponse(BaseModel):
    """Response comparing different feature sets."""
    model_type: str
    sample_count: int
    results: List[FeatureSetComparisonResult]
    best_feature_set: str
    best_r2_score: float
    recommendation: str


# ==================== PREDICTION ====================

class PredictRequest(BaseModel):
    """Request body for price prediction."""
    model_type: str = Field(..., description="Model type to use")
    living_area_m2: float = Field(..., ge=10, le=1000)
    bedroom_count: int = Field(1, ge=0, le=20)
    bathroom_count: int = Field(1, ge=0, le=10)
    year_built: Optional[int] = Field(None, ge=1900, le=2030)
    location_city: Optional[str] = None
    construction_phase: Optional[str] = None
    heating_system: Optional[str] = None
    parking_type: Optional[str] = None
    is_new_construction: Optional[bool] = False


class PredictResponse(BaseModel):
    """Response for prediction."""
    predicted_price: float
    model_type: str


class PredictFromUrlRequest(BaseModel):
    """Request to predict price from a listing URL."""
    url: str = Field(..., description="The njuskalo.hr listing URL")
    model_type: str = Field("auto", description="Model type - 'auto' selects best model automatically")


class PredictFromUrlResponse(BaseModel):
    """Response for URL-based price prediction."""
    url: str
    title: str
    actual_price: Optional[float]
    predicted_price: float
    difference: Optional[float]
    difference_pct: Optional[float]
    deal_score: Optional[str]
    features_used: Dict[str, Any]
    model_used: str
    confidence_note: str


class ManualPredictRequest(BaseModel):
    """Request body for manual price prediction with custom listing data.
    
    If description or images are provided, uses LLM to analyze them (same as scraping).
    Otherwise, uses the structured fields directly.
    """
    model_type: str = Field("auto", description="Model type - 'auto' selects best model automatically")
    
    # Basic info
    title: Optional[str] = Field(None, description="Listing title")
    actual_price: Optional[float] = Field(None, description="Listed price in EUR")
    
    # Location
    location_district: Optional[str] = Field(None, description="District/neighborhood")
    
    # Property details
    living_area_m2: float = Field(..., ge=10, le=1000, description="Living area in m²")
    bedroom_count: int = Field(1, ge=0, le=20, description="Number of bedrooms")
    bathroom_count: int = Field(1, ge=0, le=10, description="Number of bathrooms")
    outdoor_area_m2: Optional[float] = Field(None, ge=0, description="Outdoor area in m²")
    
    # Building info
    year_built: Optional[int] = Field(None, ge=1800, le=2030, description="Year built")
    is_new_construction: bool = Field(False, description="Is new construction")
    has_garage: bool = Field(False, description="Has garage")
    
    # Renovation level (0-10) - used when no images provided for LLM analysis
    renovation_level: Optional[int] = Field(None, ge=0, le=10, description="Renovation level 0-10 (only used if no images)")
    
    # Text for AI analysis (optional)
    description: Optional[str] = Field(None, description="Listing description text")
    
    # Images for AI analysis (optional) - base64 encoded, compressed
    images: Optional[List[str]] = Field(None, description="Base64 encoded images (max 20)")


class RawDataPredictRequest(BaseModel):
    """Request body for prediction with raw listing data - processed by LLM classifier."""
    model_type: str = Field("auto", description="Model type - 'auto' selects best model automatically")
    zupanija: Optional[str] = Field("Varaždinska", description="County for location context")
    
    # Raw listing data (like from HTML/JSON scraping)
    title: Optional[str] = Field(None, description="Listing title")
    price: Optional[str] = Field(None, description="Price string (e.g., '150.000 €')")
    ad_id: Optional[str] = Field(None, description="Platform listing ID (Šifra oglasa)")
    
    # Highlighted attributes (from the header/summary box)
    highlighted_attributes: Optional[Dict[str, str]] = Field(
        None, 
        description="Key attributes like 'Stambena površina': '75 m²', 'Broj soba': '3'"
    )
    
    # Basic details (from the details section)
    basic_details: Optional[Dict[str, str]] = Field(
        None,
        description="Details like 'Lokacija': 'Varaždinska žup., Varaždin', 'Godina izgradnje': '2020'"
    )
    
    # Full description text
    description: Optional[str] = Field(None, description="Full listing description text")
    
    # Additional info
    additional_info: Optional[Dict[str, str]] = Field(None, description="Any additional info")
    category_path: Optional[List[str]] = Field(None, description="Category breadcrumb path")
    
    # Images - can be URLs or base64 encoded
    images: Optional[List[str]] = Field(
        None, 
        description="Image URLs or base64 encoded images (max 20). LLM will analyze these for rooms."
    )


class RawDataPredictResponse(BaseModel):
    """Response for raw data prediction with LLM classification."""
    title: str
    actual_price: Optional[float]
    predicted_price: float
    difference: Optional[float]
    difference_pct: Optional[float]
    deal_score: Optional[str]
    features_used: Dict[str, Any]
    model_used: str
    confidence_note: str
    
    # Additional LLM-extracted data
    classified_data: Dict[str, Any] = Field(description="Full classified data from LLM")
    rooms: Optional[List[Dict[str, Any]]] = Field(None, description="Rooms detected from images/description")


class RepredictRequest(BaseModel):
    """Request to re-predict with different model using saved features."""
    model_type: str = Field(..., description="Model type to use for prediction")
    features: Dict[str, Any] = Field(..., description="Features from previous prediction")
    actual_price: Optional[float] = Field(None, description="Actual listed price for comparison")
    title: Optional[str] = Field(None, description="Listing title")


class RepredictResponse(BaseModel):
    """Response for re-prediction."""
    predicted_price: float
    model_used: str
    difference: Optional[float]
    difference_pct: Optional[float]
    deal_score: Optional[str]
    confidence_note: str


# ==================== CORRELATION & STATS ====================

class CorrelationResponse(BaseModel):
    """Response for correlation matrix."""
    correlation_matrix: Dict[str, Dict[str, float]]
    target_correlations: Dict[str, float]
    feature_names: List[str]
    sample_count: int


class StatsResponse(BaseModel):
    """Response for statistics."""
    total_count: int
    avg_price: float
    median_price: float
    min_price: float
    max_price: float
    avg_area: float
    median_area: float
    avg_bedrooms: float
    cities: List[str]
    city_counts: Dict[str, int]
    construction_phase_counts: Dict[str, int]
    new_construction_pct: float


# ==================== DEALS ====================

class DealAnalysis(BaseModel):
    """Individual deal analysis."""
    listing_id: str
    title: str
    url: str
    location_district: Optional[str]
    actual_price: float
    predicted_price: float
    difference: float  # actual - predicted
    difference_pct: float  # percentage difference
    deal_score: str  # "great_deal", "good_deal", "fair", "overpriced", "very_overpriced"
    living_area_m2: Optional[float]
    bedroom_count: Optional[int]
    bathroom_count: Optional[int]
    year_built: Optional[int]
    is_new_construction: bool
    image_url: Optional[str]


class DealsResponse(BaseModel):
    """Response for deal analysis."""
    model_used: str
    total_analyzed: int
    good_deals: List[DealAnalysis]
    bad_deals: List[DealAnalysis]
    average_error_pct: float


# ==================== SIMILARITY ====================

class SimilaritySearchRequest(BaseModel):
    """Request body for similarity search."""
    # Core features
    living_area_m2: Optional[float] = Field(None, description="Target living area in m²")
    outdoor_area_m2: Optional[float] = Field(None, description="Target outdoor area (terrace/balcony) in m²")
    bedroom_count: Optional[int] = Field(None, description="Target number of bedrooms")
    bathroom_count: Optional[int] = Field(None, description="Target number of bathrooms")
    renovation_level: Optional[int] = Field(None, ge=1, le=10, description="Target renovation level (1-10)")
    
    # Location
    location_district: Optional[str] = Field(None, description="Preferred district")
    max_distance_from_center: Optional[float] = Field(None, description="Max distance from center in km")
    
    # Property type
    is_house: Optional[bool] = Field(None, description="True for house, False for apartment")
    is_new_construction: Optional[bool] = Field(None, description="New construction only")
    is_furnished: Optional[bool] = Field(None, description="Furnished only")
    has_cellar: Optional[bool] = Field(None, description="Must have cellar")
    has_garage: Optional[bool] = Field(None, description="Must have garage")
    
    # Price range (for filtering, not similarity)
    min_price: Optional[float] = Field(None, description="Minimum price filter")
    max_price: Optional[float] = Field(None, description="Maximum price filter")
    
    # Result options
    top_n: int = Field(3, ge=1, le=10, description="Number of similar listings to return")


class SimilarListing(BaseModel):
    """A similar listing with match details."""
    id: str
    title: Optional[str]
    url: str
    price_eur: Optional[float]
    living_area_m2: Optional[float]
    outdoor_area_m2: Optional[float]
    bedroom_count: Optional[int]
    bathroom_count: Optional[int]
    renovation_level: Optional[int]
    location_district: Optional[str]
    distance_from_center: Optional[float]
    building_type: Optional[str]
    is_new_construction: Optional[bool]
    interior_arranged: Optional[bool]
    has_cellar: Optional[bool]
    parking_type: Optional[str]
    images: List[dict]
    
    # Similarity info
    similarity_score: float = Field(..., description="Overall similarity score (0-100)")
    match_details: Dict[str, Any] = Field(..., description="Per-feature match breakdown")


class SimilaritySearchResponse(BaseModel):
    """Response from similarity search."""
    query: Dict[str, Any]
    total_candidates: int
    results: List[SimilarListing]


# ==================== DEDUPLICATION ====================

class DuplicateListing(BaseModel):
    """A listing in a duplicate comparison."""
    id: str
    url: str
    source: str
    title: Optional[str]
    price_eur: Optional[float]
    living_area_m2: Optional[float]
    bedroom_count: Optional[int]
    renovation_level: Optional[int]
    location_district: Optional[str]


class DuplicateCandidate(BaseModel):
    """A potential duplicate pair."""
    primary_listing: DuplicateListing
    duplicate_listing: DuplicateListing
    similarity_score: float = Field(..., description="Overall similarity score (0-100)")
    score_breakdown: Dict[str, float] = Field(..., description="Per-feature similarity scores")


class FindDuplicatesRequest(BaseModel):
    """Request to find duplicates for a listing."""
    listing_id: Optional[str] = Field(None, description="Specific listing ID to check")
    min_score: float = Field(75, ge=0, le=100, description="Minimum similarity score threshold")
    limit: int = Field(50, ge=1, le=200, description="Maximum results to return")


class FindDuplicatesResponse(BaseModel):
    """Response with potential duplicates."""
    total_found: int
    min_score_used: float
    duplicates: List[DuplicateCandidate]


class ResolveDuplicateRequest(BaseModel):
    """Request to resolve a duplicate relationship."""
    duplicate_id: str = Field(..., description="ID of the duplicate listing")
    primary_id: str = Field(..., description="ID of the primary listing")
    is_duplicate: bool = Field(..., description="True to confirm as duplicate, False to reject")


class ResolveDuplicateResponse(BaseModel):
    """Response from resolving a duplicate."""
    success: bool
    message: str


class DuplicateGroup(BaseModel):
    """A group of duplicate listings."""
    primary_listing: DuplicateListing
    duplicates: List[DuplicateListing]
    duplicate_count: int


class DuplicateGroupsResponse(BaseModel):
    """Response with all duplicate groups."""
    total_groups: int
    groups: List[DuplicateGroup]

