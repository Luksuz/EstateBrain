"""
Machine Learning API endpoints for price prediction and analysis.
"""

from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query

from ..services.ml_service import get_ml_service, ModelType
from ..services.supabase import SupabaseService
from ..services.ml_router_helpers import (
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
from ..services.deduplication import get_deduplication_service
from ..models.ml import (
    # Training
    TrainRequest,
    ModelResultResponse,
    FeatureSet,
    FeatureSetInfo,
    FeatureSetComparisonResult,
    CompareFeatureSetsRequest,
    CompareFeatureSetsResponse,
    FEATURE_SET_DEFINITIONS,
    # Predictions
    PredictRequest,
    PredictResponse,
    PredictFromUrlRequest,
    PredictFromUrlResponse,
    ManualPredictRequest,
    RawDataPredictRequest,
    RawDataPredictResponse,
    RepredictRequest,
    RepredictResponse,
    # Correlation & Stats
    CorrelationResponse,
    StatsResponse,
    # Deals
    DealsResponse,
    # Similarity
    SimilaritySearchRequest,
    SimilaritySearchResponse,
    # Deduplication
    DuplicateListing,
    DuplicateCandidate,
    FindDuplicatesRequest,
    FindDuplicatesResponse,
    ResolveDuplicateRequest,
    ResolveDuplicateResponse,
    DuplicateGroup,
    DuplicateGroupsResponse,
)

router = APIRouter()


# ==================== TRAINING ====================

@router.get("/feature-sets")
async def get_feature_sets():
    """
    Get available feature sets for model training.
    
    Feature sets allow training with different feature combinations:
    - minimal: Just area + bedrooms (2 features)
    - core: Area, bedrooms, bathrooms, renovation (4 features)
    - standard: Core + new_construction, garage (6 features)
    - numeric: All numeric features, no location encoding
    - full: All features including location (one-hot encoded)
    """
    feature_sets = []
    for fs in FeatureSet:
        if fs == FeatureSet.CUSTOM:
            continue  # Skip custom as it needs user-provided features
        
        config = FEATURE_SET_DEFINITIONS[fs]
        all_features = (
            config["numeric"] + 
            config["derived"] + 
            config["boolean"] + 
            config["categorical"]
        )
        
        feature_sets.append(FeatureSetInfo(
            name=fs.value,
            description=config["description"],
            feature_count=len(all_features),
            features=all_features,
        ))
    
    return {"feature_sets": feature_sets}


@router.post("/train", response_model=ModelResultResponse)
async def train_model(request: TrainRequest):
    """
    Train a machine learning model on filtered listings data.
    
    Feature sets:
    - minimal: Just area + bedrooms (simplest, often performs well!)
    - core: Area, bedrooms, bathrooms, renovation
    - standard: Core + new_construction, garage
    - numeric: All numeric features without location
    - full: All features including location (default)
    
    Supported models:
    - linear_regression, ridge, lasso, elastic_net, bayesian_ridge
    - decision_tree, random_forest, gradient_boosting, xgboost
    - knn, svr, mlp
    """
    try:
        model_type = ModelType(request.model_type)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid model type: {request.model_type}. "
                   f"Valid types: {[m.value for m in ModelType]}"
        )
    
    listings = await get_filtered_listings(
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
        hidden_layers = build_hidden_layers(request.hidden_layer_1, request.hidden_layer_2)
        
        # Get feature set config
        feature_set_value = request.feature_set.value if isinstance(request.feature_set, FeatureSet) else request.feature_set
        
        result = ml_service.train_and_evaluate(
            listings=listings,
            model_type=model_type,
            test_size=request.test_size,
            cv_folds=request.cv_folds,
            feature_set=feature_set_value,
            custom_features=request.custom_features,
            alpha=request.alpha,
            l1_ratio=request.l1_ratio,
            max_depth=request.max_depth,
            n_estimators=request.n_estimators,
            learning_rate=request.learning_rate,
            n_neighbors=request.n_neighbors,
            C=request.C,
            kernel=request.kernel,
            hidden_layers=hidden_layers,
            activation=request.activation,
            learning_rate_init=request.learning_rate_init,
            max_iter=request.max_iter,
        )
        
        # Get features used
        features_used = ml_service.feature_names_out if ml_service.feature_names_out else []
        
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
            feature_set=feature_set_value,
            features_used=features_used,
            feature_count=len(features_used),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-feature-sets", response_model=CompareFeatureSetsResponse)
async def compare_feature_sets(request: CompareFeatureSetsRequest):
    """
    Compare model performance across different feature sets.
    
    This helps identify the optimal feature combination for your data.
    Often, simpler feature sets (minimal/core) perform just as well as full feature sets,
    with less risk of overfitting.
    """
    try:
        model_type = ModelType(request.model_type)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid model type: {request.model_type}. "
                   f"Valid types: {[m.value for m in ModelType]}"
        )
    
    listings = await get_filtered_listings(
        min_price=request.min_price,
        max_price=request.max_price,
    )
    
    if len(listings) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough data for comparison. Got {len(listings)} listings, need at least 10."
        )
    
    ml_service = get_ml_service()
    results = []
    
    for feature_set in request.feature_sets:
        if feature_set == FeatureSet.CUSTOM:
            continue  # Skip custom
        
        try:
            feature_set_value = feature_set.value
            result = ml_service.train_and_evaluate(
                listings=listings,
                model_type=model_type,
                test_size=request.test_size,
                cv_folds=request.cv_folds,
                feature_set=feature_set_value,
            )
            
            config = FEATURE_SET_DEFINITIONS[feature_set]
            all_features = config["numeric"] + config["derived"] + config["boolean"] + config["categorical"]
            
            results.append(FeatureSetComparisonResult(
                feature_set=feature_set_value,
                feature_count=len(ml_service.feature_names_out),
                features=ml_service.feature_names_out,
                r2_score=result.r2_score,
                rmse=result.rmse,
                mae=result.mae,
                cv_mean=result.cv_mean,
                cv_std=result.cv_std,
            ))
        except Exception as e:
            print(f"[ML] Error with feature set {feature_set}: {e}")
            continue
    
    if not results:
        raise HTTPException(status_code=500, detail="Failed to train any feature set")
    
    # Find best feature set by R² score
    best_result = max(results, key=lambda r: r.r2_score)
    
    # Generate recommendation
    if best_result.feature_set == "minimal":
        recommendation = "Minimal features (area + bedrooms) perform best! Your model benefits from simplicity."
    elif best_result.feature_set == "core":
        recommendation = "Core features work best. Adding more features may cause overfitting."
    elif best_result.feature_set in ["numeric", "standard"]:
        recommendation = f"{best_result.feature_set.title()} features are optimal. Consider this as your default."
    else:
        recommendation = "Full feature set performs best. You have enough data to use all features."
    
    # Add comparison insight
    minimal_r2 = next((r.r2_score for r in results if r.feature_set == "minimal"), None)
    full_r2 = next((r.r2_score for r in results if r.feature_set == "full"), None)
    
    if minimal_r2 and full_r2:
        diff = full_r2 - minimal_r2
        if abs(diff) < 0.02:
            recommendation += f" Note: Minimal and full features have similar R² (diff: {diff:.3f}). Prefer simpler model."
    
    return CompareFeatureSetsResponse(
        model_type=request.model_type,
        sample_count=len(listings),
        results=sorted(results, key=lambda r: r.r2_score, reverse=True),
        best_feature_set=best_result.feature_set,
        best_r2_score=best_result.r2_score,
        recommendation=recommendation,
    )


# ==================== CORRELATION & STATS ====================

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
    listings = await get_filtered_listings(
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
    """Get summary statistics for listings."""
    listings = await get_filtered_listings(
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


# ==================== PREDICTIONS ====================

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
            'metadata_area_m2': request.living_area_m2,
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
    
    if "njuskalo.hr" not in request.url:
        raise HTTPException(status_code=400, detail="URL must be from njuskalo.hr")
    
    try:
        model_type_enum = ModelType(request.model_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model type: {request.model_type}"
        )
    
    # Train the model on existing data
    listings = await get_filtered_listings()
    
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
        
        listing_data = await ListingParser.parse(html_content, request.url)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scrape listing: {str(e)}")
    
    # Calculate distance from center based on district
    district = listing_data.location_district or 'Varaždin'
    if district == 'Varaždin':
        distance_from_center = 0.5  # City center
    elif district in ['Novi Marof', 'Ivanec', 'Ludbreg']:
        distance_from_center = 15.0  # Other towns
    else:
        distance_from_center = 5.0  # Small settlements
    
    # Use actual distance if available from scraping
    if listing_data.distance_from_center and listing_data.distance_from_center > 0:
        distance_from_center = listing_data.distance_from_center
    
    # Build features from parsed listing
    features = build_features_from_request(
        living_area_m2=listing_data.living_area_m2 or 0,
        bedroom_count=listing_data.bedroom_count or 1,
        bathroom_count=listing_data.bathroom_count or 1,
        outdoor_area_m2=listing_data.outdoor_area_m2,
        renovation_level=listing_data.renovation_level,
        distance_from_center=distance_from_center,
        is_new_construction=listing_data.is_new_construction or False,
        parking_type=listing_data.parking_type.value if listing_data.parking_type else 'UNKNOWN',
        location_district=district,
    )
    
    try:
        predicted_price = ml_service.predict(model_type_enum, features)
    except Exception:
        predicted_price = fallback_price_prediction(listings, features['living_area_m2'] or 70)
    
    # Calculate difference
    actual_price = listing_data.price_eur
    difference = None
    difference_pct = None
    deal_score = None
    
    if actual_price and actual_price > 0:
        difference = actual_price - predicted_price
        difference_pct = (difference / predicted_price) * 100 if predicted_price > 0 else 0
        deal_score = calculate_deal_score(difference_pct)
    
    confidence_note = build_confidence_note(
        living_area_m2=features['living_area_m2'],
        location_district=features['location_district'],
        bedroom_count=features['bedroom_count'],
    )
    
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
            "renovation_level": features.get('renovation_level', 0),
            "distance_from_center": features.get('distance_from_center', 0),
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
    
    This allows users to input listing details directly without needing a URL.
    If description or images are provided, uses LLM to analyze them (like when scraping).
    """
    from ..services.classifier import ListingClassifier
    
    try:
        model_type_enum = ModelType(request.model_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model type: {request.model_type}"
        )
    
    listings = await get_filtered_listings()
    
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
    
    # Calculate distance from center based on district
    district = request.location_district or 'Varaždin'
    if district == 'Varaždin':
        distance_from_center = 0.5  # City center
    elif district in ['Novi Marof', 'Ivanec', 'Ludbreg']:
        distance_from_center = 15.0  # Other towns
    else:
        distance_from_center = 5.0  # Small settlements
    
    # Check if we should use LLM classifier (if description or images provided)
    use_llm = bool(request.description) or bool(request.images)
    
    if use_llm:
        # Use LLM classifier to analyze description/images (same as scraping)
        raw_data = {
            "title": request.title or f"{request.living_area_m2}m² apartment",
            "description": request.description or "",
            "highlighted_attributes": {
                "Stambena površina": f"{request.living_area_m2} m²",
                "Broj soba": str(request.bedroom_count),
                "Broj kupaonica": str(request.bathroom_count),
            },
            "basic_details": {},
        }
        
        if request.outdoor_area_m2:
            raw_data["highlighted_attributes"]["Balkon/Terasa"] = f"{request.outdoor_area_m2} m²"
        if request.year_built:
            raw_data["basic_details"]["Godina izgradnje"] = str(request.year_built)
        if request.actual_price:
            raw_data["price"] = f"€{request.actual_price:,.0f}"
        
        # Add images if provided
        if request.images:
            raw_data["images"] = [
                {"src": img} if img.startswith("http") else {"src": img}
                for img in request.images[:20]
            ]
        else:
            raw_data["images"] = []
        
        # Get location context
        location_context = None
        if request.location_district:
            location_context = {
                "zupanija": "Varaždinska",
                "city": "Varaždin",
                "districts": [request.location_district],
            }
        
        # Run LLM classifier
        classifier = ListingClassifier()
        
        try:
            classified = await classifier.classify(raw_data, location_context)
            
            # Use LLM-classified features (renovation_level comes from image analysis!)
            features = build_features_from_request(
                living_area_m2=classified.dimensions.description_living_area_m2 or classified.dimensions.metadata_area_m2 or request.living_area_m2,
                bedroom_count=classified.building_specs.bedroom_count or request.bedroom_count,
                bathroom_count=classified.building_specs.bathroom_count or request.bathroom_count,
                outdoor_area_m2=classified.dimensions.outdoor_area_m2 or request.outdoor_area_m2,
                renovation_level=classified.condition.renovation_level or 8,
                distance_from_center=distance_from_center,
                is_new_construction=classified.building_specs.is_new_construction or request.is_new_construction,
                parking_type=classified.building_specs.parking_type.value if classified.building_specs.parking_type else ('GARAGE' if request.has_garage else 'UNKNOWN'),
                location_district=classified.location.district or request.location_district or 'Varaždin',
            )
        except Exception as e:
            # Fallback to manual fields if LLM fails
            print(f"[ML] LLM classification failed, using manual fields: {e}")
            renovation = request.renovation_level if request.renovation_level is not None else (9 if request.is_new_construction else 7)
            features = build_features_from_request(
                living_area_m2=request.living_area_m2,
                bedroom_count=request.bedroom_count,
                bathroom_count=request.bathroom_count,
                outdoor_area_m2=request.outdoor_area_m2,
                renovation_level=renovation,
                distance_from_center=distance_from_center,
                is_new_construction=request.is_new_construction,
                has_garage=request.has_garage,
                location_district=request.location_district or 'Varaždin',
            )
    else:
        # Use manual fields directly (no LLM)
        # Use user-provided renovation_level, or default based on construction type
        renovation = request.renovation_level if request.renovation_level is not None else (9 if request.is_new_construction else 7)
        features = build_features_from_request(
            living_area_m2=request.living_area_m2,
            bedroom_count=request.bedroom_count,
            bathroom_count=request.bathroom_count,
            outdoor_area_m2=request.outdoor_area_m2,
            renovation_level=renovation,
            distance_from_center=distance_from_center,
            is_new_construction=request.is_new_construction,
            has_garage=request.has_garage,
            location_district=request.location_district or 'Varaždin',
        )
    
    try:
        predicted_price = ml_service.predict(model_type_enum, features)
    except Exception:
        predicted_price = fallback_price_prediction(listings, features['living_area_m2'])
    
    # Calculate difference
    actual_price = request.actual_price
    difference = None
    difference_pct = None
    deal_score = None
    
    if actual_price and actual_price > 0:
        difference = actual_price - predicted_price
        difference_pct = (difference / predicted_price) * 100 if predicted_price > 0 else 0
        deal_score = calculate_deal_score(difference_pct)
    
    confidence_note = build_confidence_note(
        living_area_m2=request.living_area_m2,
        location_district=request.location_district,
        bedroom_count=request.bedroom_count,
    )
    
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
            "renovation_level": features.get('renovation_level', 0),
            "distance_from_center": features.get('distance_from_center', 0),
            "is_new_construction": bool(features['is_new_construction']),
            "has_garage": bool(features['has_garage']),
            "location": features['location_district'],
        },
        model_used=request.model_type,
        confidence_note=confidence_note,
    )


@router.post("/predict-from-data", response_model=RawDataPredictResponse)
async def predict_from_raw_data(request: RawDataPredictRequest):
    """
    Predict price from raw listing data using LLM classifier.
    
    This endpoint mimics the full URL scraping workflow but with manual data input.
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
    
    listings = await get_filtered_listings()
    
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
    
    # Build raw data dict for classifier
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
    
    if request.images:
        raw_data["images"] = [
            {"src": img} if img.startswith("http") else {"src": img}
            for img in request.images[:20]
        ]
    else:
        raw_data["images"] = []
    
    # Get location context
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
    
    # Calculate distance from center based on district
    district = classified.location.district or classified.location.city or 'Unknown'
    if district == 'Varaždin':
        distance_from_center = 0.5  # City center
    elif district in ['Novi Marof', 'Ivanec', 'Ludbreg']:
        distance_from_center = 15.0  # Other towns
    else:
        distance_from_center = 5.0  # Small settlements
    
    # Extract features for ML prediction (renovation_level comes from LLM image analysis!)
    features = build_features_from_request(
        living_area_m2=classified.dimensions.description_living_area_m2 or classified.dimensions.metadata_area_m2 or 0,
        bedroom_count=classified.building_specs.bedroom_count or 1,
        bathroom_count=classified.building_specs.bathroom_count or 1,
        outdoor_area_m2=classified.dimensions.outdoor_area_m2,
        renovation_level=classified.condition.renovation_level,
        distance_from_center=distance_from_center,
        is_new_construction=classified.building_specs.is_new_construction or False,
        parking_type=classified.building_specs.parking_type.value if classified.building_specs.parking_type else 'UNKNOWN',
        location_district=district,
    )
    
    try:
        predicted_price = ml_service.predict(model_type_enum, features)
    except Exception:
        predicted_price = fallback_price_prediction(listings, features['living_area_m2'] or 70)
    
    # Get actual price
    actual_price = classified.basic_info.price_euros
    difference = None
    difference_pct = None
    deal_score = None
    
    if actual_price and actual_price > 0:
        difference = actual_price - predicted_price
        difference_pct = (difference / predicted_price) * 100 if predicted_price > 0 else 0
        deal_score = calculate_deal_score(difference_pct)
    
    confidence_note = build_confidence_note(
        living_area_m2=features['living_area_m2'],
        location_district=features['location_district'],
        area_conflict=classified.dimensions.area_conflict_detected,
    )
    
    # Format rooms
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
    
    # Build classified data response
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
            "renovation_level": features.get('renovation_level', 0),
            "distance_from_center": features.get('distance_from_center', 0),
            "is_new_construction": bool(features['is_new_construction']),
            "has_garage": features.get('parking_type') == 'GARAGE',
            "location": features['location_district'],
        },
        model_used=request.model_type,
        confidence_note=confidence_note,
        classified_data=classified_dict,
        rooms=rooms_data,
    )


@router.post("/repredict", response_model=RepredictResponse)
async def repredict_with_model(request: RepredictRequest):
    """
    Re-predict price with a different model using previously extracted features.
    
    Fast endpoint that skips LLM classification.
    """
    try:
        model_type_enum = ModelType(request.model_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model type: {request.model_type}. Valid: {[m.value for m in ModelType]}"
        )
    
    listings = await get_filtered_listings()
    
    if len(listings) < 20:
        raise HTTPException(
            status_code=400,
            detail="Not enough listings in database. Need at least 20."
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
    
    features = build_features_from_request(
        living_area_m2=request.features.get('living_area_m2', 0),
        bedroom_count=request.features.get('bedroom_count', 1),
        bathroom_count=request.features.get('bathroom_count', 1),
        outdoor_area_m2=request.features.get('outdoor_area_m2', 0),
        renovation_level=request.features.get('renovation_level', 8),
        distance_from_center=request.features.get('distance_from_center', 1.0),
        is_new_construction=request.features.get('is_new_construction', False),
        has_garage=request.features.get('has_garage', False),
        location_district=request.features.get('location') or request.features.get('location_district') or 'Unknown',
    )
    
    try:
        predicted_price = ml_service.predict(model_type_enum, features)
    except Exception:
        predicted_price = fallback_price_prediction(listings, features['living_area_m2'] or 70)
    
    # Calculate difference
    difference = None
    difference_pct = None
    deal_score = None
    
    if request.actual_price and request.actual_price > 0:
        difference = request.actual_price - predicted_price
        difference_pct = (difference / predicted_price) * 100 if predicted_price > 0 else 0
        deal_score = calculate_deal_score(difference_pct)
    
    confidence_note = build_confidence_note(
        living_area_m2=features['living_area_m2'],
        location_district=features['location_district'],
    )
    
    return RepredictResponse(
        predicted_price=round(predicted_price, 0),
        model_used=request.model_type,
        difference=round(difference, 0) if difference else None,
        difference_pct=round(difference_pct, 1) if difference_pct else None,
        deal_score=deal_score,
        confidence_note=confidence_note,
    )


# ==================== DEALS ====================

@router.get("/deals", response_model=DealsResponse)
async def analyze_deals(
    model_type: str = Query("auto", description="Model type - 'auto' selects best model automatically"),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    exclude_new_construction: bool = Query(False),
    location_district: Optional[str] = Query(None),
    top_n: int = Query(10, ge=1, le=50, description="Number of deals to return"),
):
    """
    Analyze listings to find good deals (underpriced) and bad deals (overpriced).
    
    Deal scores:
    - great_deal: >20% below predicted price
    - good_deal: 10-20% below predicted
    - fair: within ±10% of predicted
    - overpriced: 10-20% above predicted
    - very_overpriced: >20% above predicted
    """
    try:
        model_type_enum = ModelType(model_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model type: {model_type}. Must be one of: {[mt.value for mt in ModelType]}"
        )
    
    listings = await get_filtered_listings(
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
    
    ml_service = get_ml_service()
    
    try:
        ml_service.train_and_evaluate(
            listings=listings,
            model_type=model_type_enum,
            test_size=0.1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")
    
    try:
        good_deals, bad_deals, avg_error = analyze_listings_for_deals(
            listings=listings,
            model_type=model_type_enum,
            top_n=top_n,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return DealsResponse(
        model_used=model_type,
        total_analyzed=len(listings),
        good_deals=good_deals,
        bad_deals=bad_deals,
        average_error_pct=round(avg_error, 1),
    )


# ==================== MODELS ====================

@router.get("/models")
async def list_available_models():
    """List all available model types and their descriptions."""
    return {"models": get_available_models(ModelType)}


# ==================== NEIGHBORHOODS ====================

@router.get("/neighborhoods")
async def get_neighborhoods():
    """Get list of available neighborhoods with stats."""
    supabase = SupabaseService()
    
    # Direct query to get neighborhood data
    query = supabase.client.table("listings_v2").select("location_district, price_eur, living_area_m2")
    result = query.not_.is_("price_eur", "null").execute()
    
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
    
    neighborhoods.sort(key=lambda x: x["count"], reverse=True)
    return {"neighborhoods": neighborhoods}


# ==================== SIMILARITY ====================

@router.post("/similarity", response_model=SimilaritySearchResponse)
async def find_similar_listings(request: SimilaritySearchRequest):
    """
    Find the most similar listings based on provided criteria.
    
    The similarity algorithm uses weighted scoring across multiple features:
    - Living area: 25% weight (most important)
    - Renovation level: 20% weight
    - Bedrooms: 15% weight
    - Bathrooms: 10% weight
    - Outdoor area: 10% weight
    - Distance from center: 10% weight
    - District match: 10% weight
    
    Binary features (house/apartment, furnished, etc.) are used as filters when specified.
    """
    supabase = SupabaseService()
    
    # Build query with filters
    query = supabase.client.table("listings_v2").select("*")
    
    # Apply hard filters
    if request.min_price:
        query = query.gte("price_eur", request.min_price)
    if request.max_price:
        query = query.lte("price_eur", request.max_price)
    if request.is_new_construction is not None:
        query = query.eq("is_new_construction", request.is_new_construction)
    if request.is_furnished is not None:
        query = query.eq("interior_arranged", request.is_furnished)
    if request.has_cellar is not None:
        query = query.eq("has_cellar", request.has_cellar)
    if request.has_garage:
        query = query.eq("parking_type", "GARAGE")
    if request.is_house is not None:
        building_type = "HOUSE" if request.is_house else "BUILDING"
        query = query.eq("building_type", building_type)
    if request.max_distance_from_center:
        query = query.lte("distance_from_center", request.max_distance_from_center)
    
    query = query.not_.is_("price_eur", "null")
    query = query.not_.is_("living_area_m2", "null")
    
    result = query.execute()
    listings = result.data
    
    if not listings:
        return SimilaritySearchResponse(
            query=request.model_dump(exclude_none=True),
            total_candidates=0,
            results=[]
        )
    
    # Calculate similarity scores
    scored_listings = calculate_similarity_scores(
        listings=listings,
        living_area_m2=request.living_area_m2,
        outdoor_area_m2=request.outdoor_area_m2,
        bedroom_count=request.bedroom_count,
        bathroom_count=request.bathroom_count,
        renovation_level=request.renovation_level,
        max_distance_from_center=request.max_distance_from_center,
        location_district=request.location_district,
    )
    
    # Sort by similarity score descending
    scored_listings.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    # Take top N and format
    top_results = scored_listings[:request.top_n]
    results = [format_similar_listing(item) for item in top_results]
    
    return SimilaritySearchResponse(
        query=request.model_dump(exclude_none=True),
        total_candidates=len(listings),
        results=results
    )


# ==================== DEDUPLICATION ====================

def _listing_to_duplicate_listing(listing: dict) -> DuplicateListing:
    """Convert a listing dict to DuplicateListing model."""
    return DuplicateListing(
        id=listing.get("id", ""),
        url=listing.get("url", ""),
        source=listing.get("source", "njuskalo"),
        title=listing.get("title"),
        price_eur=listing.get("price_eur"),
        living_area_m2=listing.get("living_area_m2"),
        bedroom_count=listing.get("bedroom_count"),
        renovation_level=listing.get("renovation_level"),
        location_district=listing.get("location_district"),
    )


@router.post("/find-duplicates", response_model=FindDuplicatesResponse)
async def find_duplicates(request: FindDuplicatesRequest):
    """
    Find potential duplicate listings across marketplaces.
    
    Uses fuzzy matching on price, area, rooms, renovation level, and location
    to identify properties that may be listed on multiple platforms.
    
    The similarity score is calculated as:
    - Price: 30% weight (±15% tolerance)
    - Area: 30% weight (±10% tolerance)
    - Rooms: 20% weight (exact or ±1)
    - Renovation: 10% weight (±3 levels)
    - Location: 10% weight (same district)
    
    Default threshold is 75 for likely duplicates.
    """
    dedup_service = get_deduplication_service()
    
    if request.listing_id:
        # Find duplicates for specific listing
        candidates = await dedup_service.find_duplicates_for_listing(
            listing_id=request.listing_id,
            min_score=request.min_score,
        )
    else:
        # Find all cross-source duplicates
        candidates = await dedup_service.find_all_cross_source_duplicates(
            min_score=request.min_score,
            limit=request.limit,
        )
    
    # Convert to response format
    duplicates = [
        DuplicateCandidate(
            primary_listing=_listing_to_duplicate_listing(c.primary_listing),
            duplicate_listing=_listing_to_duplicate_listing(c.duplicate_listing),
            similarity_score=c.similarity_score,
            score_breakdown=c.score_breakdown,
        )
        for c in candidates
    ]
    
    return FindDuplicatesResponse(
        total_found=len(duplicates),
        min_score_used=request.min_score,
        duplicates=duplicates,
    )


@router.post("/duplicates/resolve", response_model=ResolveDuplicateResponse)
async def resolve_duplicate(request: ResolveDuplicateRequest):
    """
    Mark or unmark a listing as a duplicate.
    
    If is_duplicate=True, the duplicate_id listing will be marked as a duplicate
    of the primary_id listing.
    
    If is_duplicate=False, any duplicate marking will be removed.
    """
    dedup_service = get_deduplication_service()
    
    if request.is_duplicate:
        success = await dedup_service.mark_as_duplicate(
            duplicate_id=request.duplicate_id,
            primary_id=request.primary_id,
        )
        message = "Listing marked as duplicate" if success else "Failed to mark duplicate"
    else:
        success = await dedup_service.unmark_duplicate(request.duplicate_id)
        message = "Duplicate marking removed" if success else "Failed to remove duplicate marking"
    
    return ResolveDuplicateResponse(success=success, message=message)


@router.get("/duplicates", response_model=DuplicateGroupsResponse)
async def get_duplicate_groups():
    """
    Get all listings that have been marked as duplicates, grouped by primary listing.
    
    Returns groups where each group contains:
    - The primary listing
    - All listings marked as duplicates of it
    """
    dedup_service = get_deduplication_service()
    
    groups = await dedup_service.get_duplicate_groups()
    
    # Convert to response format
    response_groups = []
    for group in groups:
        if group.get("primary_listing"):
            response_groups.append(DuplicateGroup(
                primary_listing=_listing_to_duplicate_listing(group["primary_listing"]),
                duplicates=[
                    _listing_to_duplicate_listing(d) for d in group.get("duplicates", [])
                ],
                duplicate_count=len(group.get("duplicates", [])),
            ))
    
    return DuplicateGroupsResponse(
        total_groups=len(response_groups),
        groups=response_groups,
    )


@router.get("/sources")
async def get_listing_sources():
    """Get count of listings by source marketplace."""
    supabase = SupabaseService()
    
    # Get counts by source
    result = supabase.client.table("listings_v3").select("source").execute()
    
    source_counts = defaultdict(int)
    for row in result.data:
        source = row.get("source") or "njuskalo"
        source_counts[source] += 1
    
    return {
        "sources": [
            {"source": source, "count": count}
            for source, count in sorted(source_counts.items())
        ],
        "total": sum(source_counts.values()),
    }
