#!/usr/bin/env python3
"""
Test if adding is_new_construction improves model performance.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def test_new_construction():
    from app.services.ml_router_helpers import get_filtered_listings
    from app.services.ml_service import MLService, ModelType
    import pandas as pd
    import numpy as np
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import GradientBoostingRegressor
    
    # Get listings
    print("Loading listings...")
    listings = await get_filtered_listings()
    print(f"Loaded {len(listings)} listings")
    
    df = pd.DataFrame(listings)
    
    # Check is_new_construction distribution
    new_count = df['is_new_construction'].sum() if 'is_new_construction' in df.columns else 0
    print(f"\nData distribution:")
    print(f"  - New construction: {new_count} ({new_count/len(df)*100:.1f}%)")
    print(f"  - Resale: {len(df) - new_count} ({(len(df) - new_count)/len(df)*100:.1f}%)")
    
    # Features WITHOUT is_new_construction
    features_without = ['living_area_m2', 'bedroom_count', 'outdoor_area_m2', 
                        'renovation_level', 'distance_from_center']
    
    # Features WITH is_new_construction
    features_with = features_without + ['is_new_construction']
    
    # Prepare data
    for col in features_with + ['price_eur']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=features_with + ['price_eur'])
    print(f"Valid rows for analysis: {len(df)}")
    
    X_without = df[features_without].values
    X_with = df[features_with].values
    y = df['price_eur'].values
    
    # Scale
    scaler_without = StandardScaler()
    scaler_with = StandardScaler()
    
    X_without_scaled = scaler_without.fit_transform(X_without)
    X_with_scaled = scaler_with.fit_transform(X_with)
    
    # Train and evaluate both
    model_without = GradientBoostingRegressor(
        n_estimators=200, learning_rate=0.08, max_depth=4, 
        min_samples_split=5, min_samples_leaf=3, random_state=42
    )
    model_with = GradientBoostingRegressor(
        n_estimators=200, learning_rate=0.08, max_depth=4,
        min_samples_split=5, min_samples_leaf=3, random_state=42
    )
    
    print("\n" + "=" * 60)
    print("MODEL COMPARISON: With vs Without is_new_construction")
    print("=" * 60)
    
    # Cross-validation
    cv_without = cross_val_score(model_without, X_without_scaled, y, cv=5, scoring='r2')
    cv_with = cross_val_score(model_with, X_with_scaled, y, cv=5, scoring='r2')
    
    print(f"\n{'Feature Set':<30} {'CV R² Mean':>12} {'CV R² Std':>12}")
    print("-" * 54)
    print(f"{'WITHOUT is_new_construction':<30} {cv_without.mean():>11.1%} {cv_without.std():>11.1%}")
    print(f"{'WITH is_new_construction':<30} {cv_with.mean():>11.1%} {cv_with.std():>11.1%}")
    
    diff = cv_with.mean() - cv_without.mean()
    print("-" * 54)
    print(f"{'Difference':<30} {diff:>+11.1%}")
    
    # Train final models for feature importance
    model_with.fit(X_with_scaled, y)
    
    print("\n📊 Feature Importance (with is_new_construction):")
    importances = list(zip(features_with, model_with.feature_importances_))
    importances.sort(key=lambda x: x[1], reverse=True)
    for feat, imp in importances:
        print(f"  {feat:<25} {imp:>6.1%}")
    
    # Test prediction difference
    print("\n" + "=" * 60)
    print("PREDICTION COMPARISON: Same 75m² property")
    print("=" * 60)
    
    # Fit models on full data
    model_without.fit(X_without_scaled, y)
    model_with.fit(X_with_scaled, y)
    
    # Test property
    test_without = scaler_without.transform([[75, 3, 3, 7, 0.5]])
    test_with_new = scaler_with.transform([[75, 3, 3, 7, 0.5, 1]])  # New construction
    test_with_used = scaler_with.transform([[75, 3, 3, 7, 0.5, 0]])  # Resale
    
    pred_without = model_without.predict(test_without)[0]
    pred_new = model_with.predict(test_with_new)[0]
    pred_used = model_with.predict(test_with_used)[0]
    
    print(f"\n{'Scenario':<35} {'Predicted Price':>15}")
    print("-" * 50)
    print(f"{'Without is_new (current model)':<35} €{pred_without:>13,.0f}")
    print(f"{'With is_new=True (new build)':<35} €{pred_new:>13,.0f}")
    print(f"{'With is_new=False (resale)':<35} €{pred_used:>13,.0f}")
    print("-" * 50)
    print(f"{'New vs Resale difference':<35} €{pred_new - pred_used:>+13,.0f}")
    
    # Recommendation
    print("\n💡 RECOMMENDATION:")
    if diff > 0.01:
        print(f"   ✅ Adding is_new_construction IMPROVES model by {diff:.1%}")
        print("   → Consider adding it to OPTIMAL_FEATURES")
    elif diff > -0.01:
        print(f"   ➖ is_new_construction has MINIMAL impact ({diff:+.1%})")
        print("   → Current features are sufficient")
    else:
        print(f"   ❌ Adding is_new_construction HURTS model by {diff:.1%}")
        print("   → Keep current OPTIMAL_FEATURES")

if __name__ == "__main__":
    asyncio.run(test_new_construction())

