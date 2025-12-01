"""
Machine Learning API endpoints for price prediction and analysis.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..services.ml_service import get_ml_service, ModelType, ModelResult, CorrelationResult
from ..services.supabase import SupabaseService
from ..models.listing import ListingFilter

router = APIRouter()


class TrainRequest(BaseModel):
    """Request body for model training."""
    model_type: str = Field(..., description="Model type (see /models endpoint for full list)")
    test_size: float = Field(0.2, ge=0.1, le=0.5, description="Test set proportion")
    cv_folds: int = Field(5, ge=2, le=10, description="Cross-validation folds")
    
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


class PredictResponse(BaseModel):
    """Response for prediction."""
    predicted_price: float
    model_type: str


async def _get_filtered_listings(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    location_district: Optional[str] = None,
    exclude_new_construction: bool = False,
    only_new_construction: bool = False,
) -> List[Dict]:
    """Fetch listings from database with optional filters.
    
    Always filters out outliers:
    - price_eur < 10000 (invalid/placeholder prices)
    - living_area_m2 < 10 (invalid areas)
    """
    supabase = SupabaseService()
    
    # Build query
    query = supabase.client.table("listings").select("*")
    
    # Always filter out outliers (invalid data)
    query = query.gte("price_eur", 10000)  # Min €10k
    query = query.gte("living_area_m2", 10)  # Min 10m²
    
    # Apply user filters on top of outlier filtering
    if min_price is not None and min_price > 10000:
        query = query.gte("price_eur", min_price)
    if max_price is not None:
        query = query.lte("price_eur", max_price)
    if min_area is not None:
        query = query.gte("living_area_m2", min_area)
    if max_area is not None:
        query = query.lte("living_area_m2", max_area)
    if location_district:
        query = query.ilike("location_district", f"%{location_district}%")
    
    # Construction type filters
    if exclude_new_construction:
        query = query.eq("is_new_construction", False)
    elif only_new_construction:
        query = query.eq("is_new_construction", True)
    
    # Filter out null prices
    query = query.not_.is_("price_eur", "null")
    
    result = query.execute()
    return result.data


@router.post("/train", response_model=ModelResultResponse)
async def train_model(request: TrainRequest):
    """
    Train a machine learning model on filtered listings data.
    
    Supported models:
    - linear_regression: Linear Regression
    - knn: K-Nearest Neighbors
    - decision_tree: Decision Tree
    - xgboost: XGBoost (or Gradient Boosting fallback)
    - gradient_boosting: Gradient Boosting
    """
    try:
        model_type = ModelType(request.model_type)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid model type: {request.model_type}. "
                   f"Valid types: {[m.value for m in ModelType]}"
        )
    
    # Get filtered listings
    listings = await _get_filtered_listings(
        min_price=request.min_price,
        max_price=request.max_price,
        min_area=request.min_area,
        max_area=request.max_area,
        location_district=request.location_district,
        exclude_new_construction=request.exclude_new_construction or False,
        only_new_construction=request.only_new_construction or False,
    )
    
    if len(listings) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough data for training. Got {len(listings)} listings, need at least 10."
        )
    
    ml_service = get_ml_service()
    
    try:
        # Build hidden layers tuple for MLP
        hidden_layers = (request.hidden_layer_1,)
        if request.hidden_layer_2 and request.hidden_layer_2 > 0:
            hidden_layers = (request.hidden_layer_1, request.hidden_layer_2)
        
        result = ml_service.train_and_evaluate(
            listings=listings,
            model_type=model_type,
            test_size=request.test_size,
            cv_folds=request.cv_folds,
            # Regularization params
            alpha=request.alpha,
            l1_ratio=request.l1_ratio,
            # Tree params
            max_depth=request.max_depth,
            n_estimators=request.n_estimators,
            learning_rate=request.learning_rate,
            # KNN params
            n_neighbors=request.n_neighbors,
            # SVR params
            C=request.C,
            kernel=request.kernel,
            # MLP params
            hidden_layers=hidden_layers,
            activation=request.activation,
            learning_rate_init=request.learning_rate_init,
            max_iter=request.max_iter,
        )
        
        return ModelResultResponse(
            model_type=result.model_type,
            r2_score=result.r2_score,
            rmse=result.rmse,
            mae=result.mae,
            cv_scores=result.cv_scores,
            cv_mean=result.cv_mean,
            cv_std=result.cv_std,
            feature_importance=result.feature_importance,
            coefficients=result.coefficients,
            predictions=result.predictions,
            actual=result.actual,
            sample_count=len(listings),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/correlation", response_model=CorrelationResponse)
async def get_correlation_matrix(
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_area: Optional[float] = Query(None),
    max_area: Optional[float] = Query(None),
    location_district: Optional[str] = Query(None),
    exclude_new_construction: bool = Query(False),
    only_new_construction: bool = Query(False),
):
    """
    Get correlation matrix with price as the target variable.
    Shows which features have the strongest correlation with price.
    """
    listings = await _get_filtered_listings(
        min_price=min_price,
        max_price=max_price,
        min_area=min_area,
        max_area=max_area,
        location_district=location_district,
        exclude_new_construction=exclude_new_construction,
        only_new_construction=only_new_construction,
    )
    
    if len(listings) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough data for correlation. Got {len(listings)} listings, need at least 5."
        )
    
    ml_service = get_ml_service()
    
    try:
        result = ml_service.calculate_correlation_matrix(listings)
        
        return CorrelationResponse(
            correlation_matrix=result.correlation_matrix,
            target_correlations=result.target_correlations,
            feature_names=result.feature_names,
            sample_count=len(listings),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_statistics(
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_area: Optional[float] = Query(None),
    max_area: Optional[float] = Query(None),
    location_district: Optional[str] = Query(None),
    exclude_new_construction: bool = Query(False),
    only_new_construction: bool = Query(False),
):
    """
    Get summary statistics for listings.
    """
    listings = await _get_filtered_listings(
        min_price=min_price,
        max_price=max_price,
        min_area=min_area,
        max_area=max_area,
        location_district=location_district,
        exclude_new_construction=exclude_new_construction,
        only_new_construction=only_new_construction,
    )
    
    ml_service = get_ml_service()
    stats = ml_service.get_stats(listings)
    
    return StatsResponse(**stats)


@router.post("/predict", response_model=PredictResponse)
async def predict_price(request: PredictRequest):
    """
    Predict price for a property using a trained model.
    Must train the model first using /train endpoint.
    """
    try:
        model_type = ModelType(request.model_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model type: {request.model_type}"
        )
    
    ml_service = get_ml_service()
    
    try:
        features = {
            'living_area_m2': request.living_area_m2,
            'metadata_area_m2': request.living_area_m2,  # Use same as living area
            'outdoor_area_m2': 0,
            'bedroom_count': request.bedroom_count,
            'bathroom_count': request.bathroom_count,
            'year_built': request.year_built or 2020,
            'location_city': request.location_city or 'UNKNOWN',
            'construction_phase': request.construction_phase or 'UNKNOWN',
            'heating_system': request.heating_system or 'UNKNOWN',
            'parking_type': request.parking_type or 'UNKNOWN',
            'is_new_construction': 1.0 if request.is_new_construction else 0.0,
        }
        
        predicted_price = ml_service.predict(model_type, features)
        
        return PredictResponse(
            predicted_price=predicted_price,
            model_type=model_type.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_available_models():
    """List all available model types and their descriptions."""
    return {
        "models": [
            # === Linear Models ===
            {
                "type": ModelType.LINEAR_REGRESSION.value,
                "name": "Linear Regression",
                "category": "linear",
                "description": "Simple baseline. Shows raw feature coefficients.",
                "params": [],
                "recommended": False
            },
            {
                "type": ModelType.RIDGE.value,
                "name": "Ridge Regression",
                "category": "linear",
                "description": "L2 regularization prevents overfitting. Best for small datasets.",
                "params": ["alpha"],
                "recommended": True
            },
            {
                "type": ModelType.LASSO.value,
                "name": "Lasso Regression",
                "category": "linear",
                "description": "L1 regularization. Automatically selects important features.",
                "params": ["alpha"],
                "recommended": False
            },
            {
                "type": ModelType.ELASTIC_NET.value,
                "name": "Elastic Net",
                "category": "linear",
                "description": "Combines Ridge + Lasso. Good balance.",
                "params": ["alpha", "l1_ratio"],
                "recommended": False
            },
            {
                "type": ModelType.BAYESIAN_RIDGE.value,
                "name": "Bayesian Ridge",
                "category": "linear",
                "description": "Probabilistic. Provides uncertainty estimates.",
                "params": [],
                "recommended": False
            },
            # === Tree-based Models ===
            {
                "type": ModelType.DECISION_TREE.value,
                "name": "Decision Tree",
                "category": "tree",
                "description": "Simple tree. Shows feature importance but can overfit.",
                "params": ["max_depth"],
                "recommended": False
            },
            {
                "type": ModelType.RANDOM_FOREST.value,
                "name": "Random Forest",
                "category": "tree",
                "description": "Ensemble of trees. Robust and handles non-linearity.",
                "params": ["n_estimators", "max_depth"],
                "recommended": True
            },
            {
                "type": ModelType.GRADIENT_BOOSTING.value,
                "name": "Gradient Boosting",
                "category": "tree",
                "description": "Sequential boosting. Often best performance.",
                "params": ["n_estimators", "max_depth", "learning_rate"],
                "recommended": True
            },
            {
                "type": ModelType.XGBOOST.value,
                "name": "XGBoost",
                "category": "tree",
                "description": "Optimized gradient boosting. Industry standard.",
                "params": ["n_estimators", "max_depth", "learning_rate"],
                "recommended": True
            },
            # === Other Models ===
            {
                "type": ModelType.KNN.value,
                "name": "K-Nearest Neighbors",
                "category": "other",
                "description": "Predicts based on similar properties.",
                "params": ["n_neighbors"],
                "recommended": False
            },
            {
                "type": ModelType.SVR.value,
                "name": "Support Vector Regression",
                "category": "other",
                "description": "Good for small datasets. Handles non-linearity.",
                "params": ["C", "kernel"],
                "recommended": True
            },
            # === Neural Networks ===
            {
                "type": ModelType.MLP.value,
                "name": "Multi-Layer Perceptron (Neural Network)",
                "category": "neural_network",
                "description": "Deep learning model. Can capture complex non-linear patterns. Best for larger datasets.",
                "params": ["hidden_layer_1", "hidden_layer_2", "activation", "learning_rate_init", "max_iter"],
                "recommended": True
            },
        ]
    }


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


@router.get("/deals", response_model=DealsResponse)
async def analyze_deals(
    model_type: str = Query("ridge", description="Model type to use for predictions"),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    exclude_new_construction: bool = Query(False),
    location_district: Optional[str] = Query(None),
    top_n: int = Query(10, ge=1, le=50, description="Number of deals to return"),
):
    """
    Analyze listings to find good deals (underpriced) and bad deals (overpriced).
    
    Uses a trained ML model to predict fair prices, then compares with actual prices.
    
    Deal scores:
    - great_deal: >20% below predicted price
    - good_deal: 10-20% below predicted
    - fair: within ±10% of predicted
    - overpriced: 10-20% above predicted
    - very_overpriced: >20% above predicted
    """
    import numpy as np
    
    try:
        model_type_enum = ModelType(model_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model type: {model_type}. Must be one of: {[mt.value for mt in ModelType]}"
        )
    
    # Get listings
    listings = await _get_filtered_listings(
        min_price=min_price,
        max_price=max_price,
        exclude_new_construction=exclude_new_construction,
        location_district=location_district,
    )
    
    if len(listings) < 20:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough listings for deal analysis. Got {len(listings)}, need at least 20."
        )
    
    # Train model on all data
    ml_service = get_ml_service()
    
    try:
        # Train the model
        ml_service.train_and_evaluate(
            listings=listings,
            model_type=model_type_enum,
            test_size=0.1,  # Use most data for training
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")
    
    # Now predict for each listing and compare
    import pandas as pd
    
    df = ml_service._prepare_dataframe(listings)
    X, y, feature_names, df_valid = ml_service._prepare_features(df, fit=False)
    
    # Get predictions
    model = ml_service.models.get(model_type_enum)
    if model is None:
        raise HTTPException(status_code=500, detail="Model not found after training")
    
    predictions = model.predict(X)
    
    # Analyze each listing
    deals = []
    for i, (idx, row) in enumerate(df_valid.iterrows()):
        actual = float(row['price_eur'])
        predicted = float(predictions[i])
        difference = actual - predicted
        diff_pct = (difference / predicted) * 100 if predicted > 0 else 0
        
        # Determine deal score
        if diff_pct <= -20:
            deal_score = "great_deal"
        elif diff_pct <= -10:
            deal_score = "good_deal"
        elif diff_pct <= 10:
            deal_score = "fair"
        elif diff_pct <= 20:
            deal_score = "overpriced"
        else:
            deal_score = "very_overpriced"
        
        # Get image URL from raw listing data
        listing_data = listings[i] if i < len(listings) else {}
        images = listing_data.get('images', [])
        # Images can be dicts with 'src' field or plain strings
        image_url = None
        if images:
            first_image = images[0]
            if isinstance(first_image, dict):
                image_url = first_image.get('src') or first_image.get('url')
            elif isinstance(first_image, str):
                image_url = first_image
        
        deals.append(DealAnalysis(
            listing_id=str(row.get('id', '')),
            title=str(row.get('title', 'Unknown')),
            url=str(row.get('source_url', '')),
            location_district=row.get('location_district'),
            actual_price=actual,
            predicted_price=round(predicted, 0),
            difference=round(difference, 0),
            difference_pct=round(diff_pct, 1),
            deal_score=deal_score,
            living_area_m2=row.get('living_area_m2'),
            bedroom_count=int(row['bedroom_count']) if pd.notna(row.get('bedroom_count')) else None,
            bathroom_count=int(row['bathroom_count']) if pd.notna(row.get('bathroom_count')) else None,
            year_built=int(row['year_built']) if pd.notna(row.get('year_built')) else None,
            is_new_construction=bool(row.get('is_new_construction', False)),
            image_url=image_url,
        ))
    
    # Sort by difference percentage
    good_deals = sorted(
        [d for d in deals if d.difference_pct < -5],
        key=lambda x: x.difference_pct
    )[:top_n]
    
    bad_deals = sorted(
        [d for d in deals if d.difference_pct > 5],
        key=lambda x: x.difference_pct,
        reverse=True
    )[:top_n]
    
    # Calculate average error
    avg_error = float(np.mean([abs(d.difference_pct) for d in deals]))
    
    return DealsResponse(
        model_used=model_type,
        total_analyzed=len(deals),
        good_deals=good_deals,
        bad_deals=bad_deals,
        average_error_pct=round(avg_error, 1),
    )


class PredictFromUrlRequest(BaseModel):
    """Request to predict price from a listing URL."""
    url: str = Field(..., description="The njuskalo.hr listing URL")
    model_type: str = Field("ridge", description="Model type to use for prediction")


class ManualPredictRequest(BaseModel):
    """Request body for manual price prediction with custom listing data (no LLM)."""
    model_type: str = Field("ridge", description="Model type to use for prediction")
    
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
    
    # Text for AI analysis (optional)
    description: Optional[str] = Field(None, description="Listing description text")
    
    # Images for AI analysis (optional) - base64 encoded, compressed
    images: Optional[List[str]] = Field(None, description="Base64 encoded images (max 20)")


class RawDataPredictRequest(BaseModel):
    """Request body for prediction with raw listing data - processed by LLM classifier."""
    model_type: str = Field("ridge", description="Model type to use for prediction")
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


@router.post("/predict-url", response_model=PredictFromUrlResponse)
async def predict_from_url(request: PredictFromUrlRequest):
    """
    Scrape a listing URL and predict its fair market price.
    
    This will:
    1. Fetch the listing HTML from the provided URL
    2. Parse and classify the listing using AI
    3. Use a trained ML model to predict the fair price
    4. Compare with actual price if available
    """
    from ..services.firecrawl import FirecrawlService
    from ..services.parser import ListingParser
    
    # Validate URL
    if "njuskalo.hr" not in request.url:
        raise HTTPException(status_code=400, detail="URL must be from njuskalo.hr")
    
    try:
        model_type_enum = ModelType(request.model_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model type: {request.model_type}"
        )
    
    # First, train the model on existing data
    supabase = SupabaseService()
    listings = await _get_filtered_listings()
    
    if len(listings) < 20:
        raise HTTPException(
            status_code=400,
            detail="Not enough listings in database to make predictions. Need at least 20."
        )
    
    ml_service = get_ml_service()
    
    try:
        ml_service.train_and_evaluate(
            listings=listings,
            model_type=model_type_enum,
            test_size=0.1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")
    
    # Fetch and parse the listing
    firecrawl = FirecrawlService()
    
    try:
        html_content = await firecrawl.fetch_html(request.url)
        if not html_content:
            raise HTTPException(status_code=400, detail="Failed to fetch listing HTML")
        
        # Parse the listing using AI classifier
        listing_data = await ListingParser.parse(html_content, request.url)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scrape listing: {str(e)}")
    
    # Build feature dict from parsed listing
    features = {
        'living_area_m2': listing_data.living_area_m2 or 0,
        'bedroom_count': listing_data.bedroom_count or 1,
        'bathroom_count': listing_data.bathroom_count or 1,
        'outdoor_area_m2': listing_data.outdoor_area_m2 or 0,
        'is_new_construction': 1.0 if listing_data.is_new_construction else 0.0,
        'parking_type': listing_data.parking_type.value if listing_data.parking_type else 'UNKNOWN',
        'location_district': listing_data.location_district or 'Unknown',
    }
    
    try:
        # Use the ML service's predict method which handles preprocessing correctly
        predicted_price = ml_service.predict(model_type_enum, features)
        
    except Exception as e:
        # If preprocessing fails, use a simpler approach
        # Estimate based on area and average price per m2
        avg_price_per_m2 = sum(l.get('price_eur', 0) / max(l.get('living_area_m2', 1), 1) for l in listings) / len(listings)
        predicted_price = (features['living_area_m2'] or 70) * avg_price_per_m2
    
    # Get actual price if available
    actual_price = listing_data.price_eur
    
    # Calculate difference
    difference = None
    difference_pct = None
    deal_score = None
    
    if actual_price and actual_price > 0:
        difference = actual_price - predicted_price
        difference_pct = (difference / predicted_price) * 100 if predicted_price > 0 else 0
        
        # Determine deal score
        if difference_pct <= -20:
            deal_score = "great_deal"
        elif difference_pct <= -10:
            deal_score = "good_deal"
        elif difference_pct <= 10:
            deal_score = "fair"
        elif difference_pct <= 20:
            deal_score = "overpriced"
        else:
            deal_score = "very_overpriced"
    
    # Confidence note based on data quality
    confidence_notes = []
    if not features['living_area_m2']:
        confidence_notes.append("Area not detected")
    if features['location_district'] == 'Unknown':
        confidence_notes.append("Location unknown")
    if not features['bedroom_count']:
        confidence_notes.append("Bedrooms not detected")
    
    confidence_note = ", ".join(confidence_notes) if confidence_notes else "Good confidence"
    
    return PredictFromUrlResponse(
        url=request.url,
        title=listing_data.title or "Unknown Listing",
        actual_price=actual_price,
        predicted_price=round(predicted_price, 0),
        difference=round(difference, 0) if difference else None,
        difference_pct=round(difference_pct, 1) if difference_pct else None,
        deal_score=deal_score,
        features_used={
            "living_area_m2": features['living_area_m2'],
            "bedroom_count": features['bedroom_count'],
            "bathroom_count": features['bathroom_count'],
            "outdoor_area_m2": features.get('outdoor_area_m2', 0),
            "is_new_construction": bool(features['is_new_construction']),
            "has_garage": features.get('parking_type') == 'GARAGE',
            "location": features['location_district'],
        },
        model_used=request.model_type,
        confidence_note=confidence_note,
    )


@router.post("/predict-manual", response_model=PredictFromUrlResponse)
async def predict_manual(request: ManualPredictRequest):
    """
    Predict price from manually input listing data.
    
    This allows users to input listing details directly (title, description, 
    area, location, etc.) without needing a URL. Useful for:
    - Testing hypothetical properties
    - Properties not listed online
    - Quick estimates without scraping
    
    Images should be base64 encoded and compressed to reduce token usage.
    """
    try:
        model_type_enum = ModelType(request.model_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model type: {request.model_type}"
        )
    
    # Train the model on existing data
    listings = await _get_filtered_listings()
    
    if len(listings) < 20:
        raise HTTPException(
            status_code=400,
            detail="Not enough listings in database to make predictions. Need at least 20."
        )
    
    ml_service = get_ml_service()
    
    try:
        ml_service.train_and_evaluate(
            listings=listings,
            model_type=model_type_enum,
            test_size=0.1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")
    
    # Build feature dict from manual input
    features = {
        'living_area_m2': request.living_area_m2,
        'bedroom_count': request.bedroom_count,
        'bathroom_count': request.bathroom_count,
        'outdoor_area_m2': request.outdoor_area_m2 or 0,
        'is_new_construction': 1.0 if request.is_new_construction else 0.0,
        'has_garage': 1.0 if request.has_garage else 0.0,
        'location_district': request.location_district or 'Varaždin',
    }
    
    try:
        # Use the ML service's predict method which handles preprocessing correctly
        predicted_price = ml_service.predict(model_type_enum, features)
        
    except Exception as e:
        # Fallback: estimate based on area and average price per m2
        avg_price_per_m2 = sum(l.get('price_eur', 0) / max(l.get('living_area_m2', 1), 1) for l in listings) / len(listings)
        predicted_price = features['living_area_m2'] * avg_price_per_m2
    
    # Get actual price if provided
    actual_price = request.actual_price
    
    # Calculate difference
    difference = None
    difference_pct = None
    deal_score = None
    
    if actual_price and actual_price > 0:
        difference = actual_price - predicted_price
        difference_pct = (difference / predicted_price) * 100 if predicted_price > 0 else 0
        
        # Determine deal score
        if difference_pct <= -20:
            deal_score = "great_deal"
        elif difference_pct <= -10:
            deal_score = "good_deal"
        elif difference_pct <= 10:
            deal_score = "fair"
        elif difference_pct <= 20:
            deal_score = "overpriced"
        else:
            deal_score = "very_overpriced"
    
    # Confidence note based on data quality
    confidence_notes = []
    if request.living_area_m2 < 20:
        confidence_notes.append("Very small area")
    if not request.location_district:
        confidence_notes.append("Location assumed (Varaždin)")
    if not request.bedroom_count:
        confidence_notes.append("No bedrooms specified")
    
    confidence_note = ", ".join(confidence_notes) if confidence_notes else "Good confidence"
    
    return PredictFromUrlResponse(
        url="manual-input",
        title=request.title or f"{request.living_area_m2}m² - {request.bedroom_count} bed - {request.location_district or 'Varaždin'}",
        actual_price=actual_price,
        predicted_price=round(predicted_price, 0),
        difference=round(difference, 0) if difference else None,
        difference_pct=round(difference_pct, 1) if difference_pct else None,
        deal_score=deal_score,
        features_used={
            "living_area_m2": features['living_area_m2'],
            "bedroom_count": features['bedroom_count'],
            "bathroom_count": features['bathroom_count'],
            "outdoor_area_m2": features['outdoor_area_m2'],
            "is_new_construction": bool(features['is_new_construction']),
            "has_garage": bool(features['has_garage']),
            "location": features['location_district'],
        },
        model_used=request.model_type,
        confidence_note=confidence_note,
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


@router.post("/predict-from-data", response_model=RawDataPredictResponse)
async def predict_from_raw_data(request: RawDataPredictRequest):
    """
    Predict price from raw listing data using LLM classifier.
    
    This endpoint mimics the full URL scraping workflow but with manual data input:
    1. Takes raw listing data (title, description, attributes, images)
    2. Passes it through the LLM classifier to extract structured data
    3. Analyzes images for room detection, condition, features
    4. Uses trained ML model to predict fair market price
    
    Perfect for:
    - Testing listings from other sources
    - Analyzing properties without a URL
    - Debugging/verifying the classification process
    """
    from ..services.classifier import ListingClassifier
    from ..locations_config.locations import get_location_context
    
    try:
        model_type_enum = ModelType(request.model_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model type: {request.model_type}"
        )
    
    # Train the model on existing data
    listings = await _get_filtered_listings()
    
    if len(listings) < 20:
        raise HTTPException(
            status_code=400,
            detail="Not enough listings in database to make predictions. Need at least 20."
        )
    
    ml_service = get_ml_service()
    
    try:
        ml_service.train_and_evaluate(
            listings=listings,
            model_type=model_type_enum,
            test_size=0.1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")
    
    # Build raw data dict for classifier (same format as scraper output)
    raw_data = {
        "title": request.title,
        "price": request.price,
        "ad_id": request.ad_id,
        "highlighted_attributes": request.highlighted_attributes or {},
        "basic_details": request.basic_details or {},
        "description": request.description or "",
        "additional_info": request.additional_info or {},
        "category_path": request.category_path or [],
    }
    
    # Process images - convert base64 to image objects if needed
    if request.images:
        # If images are URLs, format them for the classifier
        # If they're base64, the classifier will handle them
        raw_data["images"] = [
            {"src": img} if img.startswith("http") else {"src": img}
            for img in request.images[:20]  # Max 20 images
        ]
    else:
        raw_data["images"] = []
    
    # Get location context for the classifier
    location_context = None
    if request.zupanija:
        loc_ctx = get_location_context(request.zupanija)
        if loc_ctx:
            location_context = {
                "zupanija": loc_ctx.get("zupanija"),
                "city": loc_ctx.get("city"),
                "districts": loc_ctx.get("districts", []),
            }
    
    # Run the LLM classifier
    classifier = ListingClassifier()
    
    try:
        classified = await classifier.classify(raw_data, location_context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM classification failed: {str(e)}")
    
    # Extract features for ML prediction
    features = {
        'living_area_m2': classified.dimensions.description_living_area_m2 or classified.dimensions.metadata_area_m2 or 0,
        'bedroom_count': classified.building_specs.bedroom_count or 1,
        'bathroom_count': classified.building_specs.bathroom_count or 1,
        'outdoor_area_m2': classified.dimensions.outdoor_area_m2 or 0,
        'is_new_construction': 1.0 if classified.building_specs.is_new_construction else 0.0,
        'parking_type': classified.building_specs.parking_type.value if classified.building_specs.parking_type else 'UNKNOWN',
        'location_district': classified.location.district or classified.location.city or 'Unknown',
    }
    
    try:
        predicted_price = ml_service.predict(model_type_enum, features)
    except Exception as e:
        # Fallback: estimate based on area and average price per m2
        avg_price_per_m2 = sum(l.get('price_eur', 0) / max(l.get('living_area_m2', 1), 1) for l in listings) / len(listings)
        predicted_price = (features['living_area_m2'] or 70) * avg_price_per_m2
    
    # Get actual price from classified data
    actual_price = classified.basic_info.price_euros
    
    # Calculate difference
    difference = None
    difference_pct = None
    deal_score = None
    
    if actual_price and actual_price > 0:
        difference = actual_price - predicted_price
        difference_pct = (difference / predicted_price) * 100 if predicted_price > 0 else 0
        
        if difference_pct <= -20:
            deal_score = "great_deal"
        elif difference_pct <= -10:
            deal_score = "good_deal"
        elif difference_pct <= 10:
            deal_score = "fair"
        elif difference_pct <= 20:
            deal_score = "overpriced"
        else:
            deal_score = "very_overpriced"
    
    # Confidence note
    confidence_notes = []
    if not features['living_area_m2']:
        confidence_notes.append("Area not detected")
    if features['location_district'] == 'Unknown':
        confidence_notes.append("Location unknown")
    if classified.dimensions.area_conflict_detected:
        confidence_notes.append("Area conflict detected")
    
    confidence_note = ", ".join(confidence_notes) if confidence_notes else "Good confidence"
    
    # Format rooms for response
    rooms_data = None
    if classified.rooms:
        rooms_data = [
            {
                "room_type": room.room_type.value if room.room_type else None,
                "image_url": room.image_url,
                "condition": room.condition.value if room.condition else None,
                "condition_reasoning": room.condition_reasoning,
                "features": [f.value for f in room.features] if room.features else [],
                "notes": room.notes,
                "from_description": room.from_description,
            }
            for room in classified.rooms
        ]
    
    # Full classified data
    classified_dict = {
        "basic_info": {
            "title": classified.basic_info.title,
            "price_euros": classified.basic_info.price_euros,
            "listing_id": classified.basic_info.listing_id,
        },
        "location": {
            "city": classified.location.city,
            "district": classified.location.district,
            "floor_level": classified.location.floor_level,
        },
        "dimensions": {
            "metadata_area_m2": classified.dimensions.metadata_area_m2,
            "living_area_m2": classified.dimensions.description_living_area_m2,
            "outdoor_area_m2": classified.dimensions.outdoor_area_m2,
            "area_conflict": classified.dimensions.area_conflict_detected,
        },
        "building_specs": {
            "year_built": classified.building_specs.year_built,
            "is_new_construction": classified.building_specs.is_new_construction,
            "bedroom_count": classified.building_specs.bedroom_count,
            "bathroom_count": classified.building_specs.bathroom_count,
            "parking_type": classified.building_specs.parking_type.value if classified.building_specs.parking_type else None,
        },
        "condition": {
            "construction_phase": classified.condition.construction_phase.value if classified.condition.construction_phase else None,
            "heating_system": classified.condition.heating_system.value if classified.condition.heating_system else None,
            "energy_class": classified.condition.energy_class,
        },
    }
    
    return RawDataPredictResponse(
        title=classified.basic_info.title or request.title or "Unknown Listing",
        actual_price=actual_price,
        predicted_price=round(predicted_price, 0),
        difference=round(difference, 0) if difference else None,
        difference_pct=round(difference_pct, 1) if difference_pct else None,
        deal_score=deal_score,
        features_used={
            "living_area_m2": features['living_area_m2'],
            "bedroom_count": features['bedroom_count'],
            "bathroom_count": features['bathroom_count'],
            "outdoor_area_m2": features['outdoor_area_m2'],
            "is_new_construction": bool(features['is_new_construction']),
            "has_garage": features.get('parking_type') == 'GARAGE',
            "location": features['location_district'],
        },
        model_used=request.model_type,
        confidence_note=confidence_note,
        classified_data=classified_dict,
        rooms=rooms_data,
    )


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


@router.post("/repredict", response_model=RepredictResponse)
async def repredict_with_model(request: RepredictRequest):
    """
    Re-predict price with a different model using previously extracted features.
    
    This is a fast endpoint that skips LLM classification - just uses the features
    that were already extracted from a previous prediction.
    
    Perfect for comparing predictions across different models without re-analyzing.
    """
    try:
        model_type_enum = ModelType(request.model_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model type: {request.model_type}. Valid: {[m.value for m in ModelType]}"
        )
    
    # Get listings to train model
    listings = await _get_filtered_listings()
    
    if len(listings) < 20:
        raise HTTPException(
            status_code=400,
            detail="Not enough listings in database. Need at least 20."
        )
    
    ml_service = get_ml_service()
    
    # Train the model (fast if already trained with same data)
    try:
        ml_service.train_and_evaluate(
            listings=listings,
            model_type=model_type_enum,
            test_size=0.1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")
    
    # Build features dict from request
    features = {
        'living_area_m2': request.features.get('living_area_m2', 0),
        'bedroom_count': request.features.get('bedroom_count', 1),
        'bathroom_count': request.features.get('bathroom_count', 1),
        'outdoor_area_m2': request.features.get('outdoor_area_m2', 0),
        'is_new_construction': 1.0 if request.features.get('is_new_construction') else 0.0,
        'has_garage': 1.0 if request.features.get('has_garage') else 0.0,
        'location_district': request.features.get('location') or request.features.get('location_district') or 'Unknown',
    }
    
    try:
        predicted_price = ml_service.predict(model_type_enum, features)
    except Exception as e:
        # Fallback
        avg_price_per_m2 = sum(l.get('price_eur', 0) / max(l.get('living_area_m2', 1), 1) for l in listings) / len(listings)
        predicted_price = (features['living_area_m2'] or 70) * avg_price_per_m2
    
    # Calculate difference if actual price provided
    difference = None
    difference_pct = None
    deal_score = None
    
    if request.actual_price and request.actual_price > 0:
        difference = request.actual_price - predicted_price
        difference_pct = (difference / predicted_price) * 100 if predicted_price > 0 else 0
        
        if difference_pct <= -20:
            deal_score = "great_deal"
        elif difference_pct <= -10:
            deal_score = "good_deal"
        elif difference_pct <= 10:
            deal_score = "fair"
        elif difference_pct <= 20:
            deal_score = "overpriced"
        else:
            deal_score = "very_overpriced"
    
    # Confidence note
    confidence_notes = []
    if not features['living_area_m2']:
        confidence_notes.append("Area not detected")
    if features['location_district'] == 'Unknown':
        confidence_notes.append("Location unknown")
    
    confidence_note = ", ".join(confidence_notes) if confidence_notes else "Good confidence"
    
    return RepredictResponse(
        predicted_price=round(predicted_price, 0),
        model_used=request.model_type,
        difference=round(difference, 0) if difference else None,
        difference_pct=round(difference_pct, 1) if difference_pct else None,
        deal_score=deal_score,
        confidence_note=confidence_note,
    )


@router.get("/neighborhoods")
async def get_neighborhoods():
    """Get list of available neighborhoods with stats."""
    from collections import defaultdict
    
    supabase = SupabaseService()
    
    # Direct query to get neighborhood data
    query = supabase.client.table("listings").select("location_district, price_eur, living_area_m2")
    result = query.not_.is_("price_eur", "null").execute()
    
    # Aggregate manually
    stats = defaultdict(lambda: {"count": 0, "total_price": 0, "total_area": 0})
    
    for row in result.data:
        neighborhood = row.get("location_district") or "Unknown"
        price = float(row.get("price_eur") or 0)
        area = float(row.get("living_area_m2") or 0)
        
        stats[neighborhood]["count"] += 1
        stats[neighborhood]["total_price"] += price
        stats[neighborhood]["total_area"] += area
    
    neighborhoods = []
    for name, data in stats.items():
        count = data["count"]
        avg_price = data["total_price"] / count if count > 0 else 0
        avg_area = data["total_area"] / count if count > 0 else 0
        price_per_m2 = avg_price / avg_area if avg_area > 0 else 0
        
        neighborhoods.append({
            "name": name,
            "count": count,
            "avg_price": round(avg_price),
            "price_per_m2": round(price_per_m2),
        })
    
    # Sort by count descending
    neighborhoods.sort(key=lambda x: x["count"], reverse=True)
    return {"neighborhoods": neighborhoods}

