"""
Helper functions for ML router endpoints.
"""

from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd

from .supabase import SupabaseService
from .ml_service import get_ml_service, ModelType
from ..models.ml import DealAnalysis, SimilarListing


async def get_filtered_listings(
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
    query = supabase.client.table("listings_v2").select("*")
    
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


def calculate_deal_score(difference_pct: float) -> str:
    """Determine deal score based on price difference percentage."""
    if difference_pct <= -20:
        return "great_deal"
    elif difference_pct <= -10:
        return "good_deal"
    elif difference_pct <= 10:
        return "fair"
    elif difference_pct <= 20:
        return "overpriced"
    else:
        return "very_overpriced"


def build_hidden_layers(hidden_layer_1: int, hidden_layer_2: Optional[int]) -> tuple:
    """Build hidden layers tuple for MLP from request parameters."""
    hidden_layers = (hidden_layer_1,)
    if hidden_layer_2 and hidden_layer_2 > 0:
        hidden_layers = (hidden_layer_1, hidden_layer_2)
    return hidden_layers


def analyze_listings_for_deals(
    listings: List[Dict],
    model_type: ModelType,
    top_n: int = 10,
) -> tuple[List[DealAnalysis], List[DealAnalysis], float]:
    """
    Analyze listings to find good and bad deals.
    
    Returns:
        Tuple of (good_deals, bad_deals, average_error_pct)
    """
    ml_service = get_ml_service()
    
    # Prepare data for predictions
    df = ml_service._prepare_dataframe(listings)
    X, y, feature_names, df_valid = ml_service._prepare_features(df, fit=False)
    
    # Get predictions
    model = ml_service.models.get(model_type)
    if model is None:
        raise ValueError("Model not found after training")
    
    predictions = model.predict(X)
    
    # Analyze each listing
    deals = []
    for i, (idx, row) in enumerate(df_valid.iterrows()):
        actual = float(row['price_eur'])
        predicted = float(predictions[i])
        difference = actual - predicted
        diff_pct = (difference / predicted) * 100 if predicted > 0 else 0
        
        deal_score = calculate_deal_score(diff_pct)
        
        # Get image URL from raw listing data
        listing_data = listings[i] if i < len(listings) else {}
        image_url = extract_image_url(listing_data)
        
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
    
    return good_deals, bad_deals, avg_error


def extract_image_url(listing_data: Dict) -> Optional[str]:
    """Extract the first image URL from listing data."""
    images = listing_data.get('images', [])
    if not images:
        return None
    
    first_image = images[0]
    if isinstance(first_image, dict):
        return first_image.get('src') or first_image.get('url')
    elif isinstance(first_image, str):
        return first_image
    return None


def build_features_from_request(
    living_area_m2: float,
    bedroom_count: int,
    bathroom_count: int,
    outdoor_area_m2: Optional[float] = None,
    is_new_construction: bool = False,
    has_garage: bool = False,
    location_district: Optional[str] = None,
    parking_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Build features dictionary from request parameters."""
    features = {
        'living_area_m2': living_area_m2,
        'bedroom_count': bedroom_count,
        'bathroom_count': bathroom_count,
        'outdoor_area_m2': outdoor_area_m2 or 0,
        'is_new_construction': 1.0 if is_new_construction else 0.0,
        'has_garage': 1.0 if has_garage else 0.0,
        'location_district': location_district or 'Unknown',
    }
    if parking_type:
        features['parking_type'] = parking_type
    return features


def build_confidence_note(
    living_area_m2: Optional[float] = None,
    location_district: Optional[str] = None,
    bedroom_count: Optional[int] = None,
    area_conflict: bool = False,
) -> str:
    """Build confidence note based on data quality."""
    confidence_notes = []
    
    if not living_area_m2 or living_area_m2 < 20:
        if not living_area_m2:
            confidence_notes.append("Area not detected")
        else:
            confidence_notes.append("Very small area")
    
    if not location_district or location_district == 'Unknown':
        confidence_notes.append("Location unknown")
    
    if not bedroom_count:
        confidence_notes.append("Bedrooms not detected")
    
    if area_conflict:
        confidence_notes.append("Area conflict detected")
    
    return ", ".join(confidence_notes) if confidence_notes else "Good confidence"


def fallback_price_prediction(
    listings: List[Dict],
    living_area_m2: float,
) -> float:
    """Fallback price prediction based on average price per m²."""
    avg_price_per_m2 = sum(
        l.get('price_eur', 0) / max(l.get('living_area_m2', 1), 1) 
        for l in listings
    ) / len(listings)
    return living_area_m2 * avg_price_per_m2


# ==================== SIMILARITY SEARCH ====================

# Feature weights for similarity scoring (must sum to 1.0)
SIMILARITY_WEIGHTS = {
    "living_area_m2": 0.25,
    "renovation_level": 0.20,
    "bedroom_count": 0.15,
    "bathroom_count": 0.10,
    "outdoor_area_m2": 0.10,
    "distance_from_center": 0.10,
    "district_match": 0.10,
}


def calculate_similarity_scores(
    listings: List[Dict],
    living_area_m2: Optional[float] = None,
    outdoor_area_m2: Optional[float] = None,
    bedroom_count: Optional[int] = None,
    bathroom_count: Optional[int] = None,
    renovation_level: Optional[int] = None,
    max_distance_from_center: Optional[float] = None,
    location_district: Optional[str] = None,
) -> List[Dict]:
    """
    Calculate similarity scores for listings based on provided criteria.
    
    Returns list of dicts with listing, similarity_score, and match_details.
    """
    scored_listings = []
    
    for listing in listings:
        scores = {}
        total_weight = 0
        weighted_score = 0
        
        # Living area similarity (gaussian-like decay)
        if living_area_m2 and listing.get("living_area_m2"):
            target = living_area_m2
            actual = listing["living_area_m2"]
            diff_pct = abs(target - actual) / max(target, 1)
            score = max(0, 100 * (1 - diff_pct))
            scores["living_area_m2"] = {"score": round(score, 1), "target": target, "actual": actual}
            weighted_score += score * SIMILARITY_WEIGHTS["living_area_m2"]
            total_weight += SIMILARITY_WEIGHTS["living_area_m2"]
        
        # Outdoor area similarity
        if outdoor_area_m2 is not None and listing.get("outdoor_area_m2") is not None:
            target = outdoor_area_m2
            actual = listing["outdoor_area_m2"] or 0
            if target == 0 and actual == 0:
                score = 100
            elif target == 0:
                score = max(0, 100 - actual * 5)
            else:
                diff_pct = abs(target - actual) / max(target, 1)
                score = max(0, 100 * (1 - diff_pct))
            scores["outdoor_area_m2"] = {"score": round(score, 1), "target": target, "actual": actual}
            weighted_score += score * SIMILARITY_WEIGHTS["outdoor_area_m2"]
            total_weight += SIMILARITY_WEIGHTS["outdoor_area_m2"]
        
        # Bedroom count similarity
        if bedroom_count is not None and listing.get("bedroom_count") is not None:
            target = bedroom_count
            actual = listing["bedroom_count"]
            diff = abs(target - actual)
            score = max(0, 100 - diff * 25)
            scores["bedroom_count"] = {"score": round(score, 1), "target": target, "actual": actual}
            weighted_score += score * SIMILARITY_WEIGHTS["bedroom_count"]
            total_weight += SIMILARITY_WEIGHTS["bedroom_count"]
        
        # Bathroom count similarity
        if bathroom_count is not None and listing.get("bathroom_count") is not None:
            target = bathroom_count
            actual = listing["bathroom_count"]
            diff = abs(target - actual)
            score = max(0, 100 - diff * 33)
            scores["bathroom_count"] = {"score": round(score, 1), "target": target, "actual": actual}
            weighted_score += score * SIMILARITY_WEIGHTS["bathroom_count"]
            total_weight += SIMILARITY_WEIGHTS["bathroom_count"]
        
        # Renovation level similarity
        if renovation_level is not None and listing.get("renovation_level") is not None:
            target = renovation_level
            actual = listing["renovation_level"]
            diff = abs(target - actual)
            score = max(0, 100 - diff * 12.5)
            scores["renovation_level"] = {"score": round(score, 1), "target": target, "actual": actual}
            weighted_score += score * SIMILARITY_WEIGHTS["renovation_level"]
            total_weight += SIMILARITY_WEIGHTS["renovation_level"]
        
        # Distance from center similarity
        if max_distance_from_center and listing.get("distance_from_center") is not None:
            target = max_distance_from_center
            actual = listing["distance_from_center"]
            score = max(0, 100 * (1 - actual / target))
            scores["distance_from_center"] = {"score": round(score, 1), "max": target, "actual": actual}
            weighted_score += score * SIMILARITY_WEIGHTS["distance_from_center"]
            total_weight += SIMILARITY_WEIGHTS["distance_from_center"]
        
        # District match (exact match = 100, else 0)
        if location_district and listing.get("location_district"):
            target = location_district.lower()
            actual = (listing["location_district"] or "").lower()
            score = 100 if target == actual else 0
            scores["district_match"] = {"score": score, "target": location_district, "actual": listing["location_district"]}
            weighted_score += score * SIMILARITY_WEIGHTS["district_match"]
            total_weight += SIMILARITY_WEIGHTS["district_match"]
        
        # Calculate final score (normalize by actual weights used)
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 50  # Default middle score if no criteria provided
        
        scored_listings.append({
            "listing": listing,
            "similarity_score": round(final_score, 1),
            "match_details": scores,
        })
    
    return scored_listings


def format_similar_listing(item: Dict) -> SimilarListing:
    """Format a scored listing as a SimilarListing response."""
    listing = item["listing"]
    return SimilarListing(
        id=listing["id"],
        title=listing.get("title"),
        url=listing["url"],
        price_eur=listing.get("price_eur"),
        living_area_m2=listing.get("living_area_m2"),
        outdoor_area_m2=listing.get("outdoor_area_m2"),
        bedroom_count=listing.get("bedroom_count"),
        bathroom_count=listing.get("bathroom_count"),
        renovation_level=listing.get("renovation_level"),
        location_district=listing.get("location_district"),
        distance_from_center=listing.get("distance_from_center"),
        building_type=listing.get("building_type"),
        is_new_construction=listing.get("is_new_construction"),
        interior_arranged=listing.get("interior_arranged"),
        has_cellar=listing.get("has_cellar"),
        parking_type=listing.get("parking_type"),
        images=listing.get("images", [])[:3],  # Only first 3 images
        similarity_score=item["similarity_score"],
        match_details=item["match_details"],
    )


# ==================== MODEL CATALOG ====================

def get_available_models(ModelType) -> List[Dict]:
    """Get list of all available model types with descriptions."""
    return [
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


