#!/usr/bin/env python3
"""
Test if adding is_furnished improves model performance.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def test_furnished():
    from app.services.ml_router_helpers import get_filtered_listings
    import pandas as pd
    import numpy as np
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import GradientBoostingRegressor
    
    # Get listings
    print("Loading listings...")
    listings = await get_filtered_listings()
    print(f"Loaded {len(listings)} listings")
    
    df = pd.DataFrame(listings)
    
    # Check is_furnished distribution
    if 'is_furnished' in df.columns:
        furnished_count = df['is_furnished'].sum()
        print(f"\nData distribution:")
        print(f"  - Furnished: {furnished_count} ({furnished_count/len(df)*100:.1f}%)")
        print(f"  - Unfurnished: {len(df) - furnished_count} ({(len(df) - furnished_count)/len(df)*100:.1f}%)")
    else:
        print("\n⚠️ is_furnished column not found in data!")
        return
    
    # Also check is_new_construction for comparison
    if 'is_new_construction' in df.columns:
        new_count = df['is_new_construction'].sum()
        print(f"  - New construction: {new_count} ({new_count/len(df)*100:.1f}%)")
    
    # Features WITHOUT is_furnished (current optimal)
    base_features = ['living_area_m2', 'bedroom_count', 'outdoor_area_m2', 
                     'renovation_level', 'distance_from_center']
    
    # Test different combinations
    test_sets = [
        ("Current optimal (5 features)", base_features),
        ("+ is_furnished", base_features + ['is_furnished']),
        ("+ is_new_construction", base_features + ['is_new_construction']),
        ("+ both furnished & new", base_features + ['is_furnished', 'is_new_construction']),
    ]
    
    # Prepare data
    all_features = base_features + ['is_furnished', 'is_new_construction']
    for col in all_features + ['price_eur']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=all_features + ['price_eur'])
    print(f"\nValid rows for analysis: {len(df)}")
    
    y = df['price_eur'].values
    
    print("\n" + "=" * 70)
    print("MODEL COMPARISON: Testing Additional Features")
    print("=" * 70)
    print(f"\n{'Feature Set':<35} {'CV R² Mean':>12} {'CV R² Std':>10} {'Δ vs Base':>12}")
    print("-" * 70)
    
    base_score = None
    results = []
    
    for name, features in test_sets:
        X = df[features].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        model = GradientBoostingRegressor(
            n_estimators=200, learning_rate=0.08, max_depth=4,
            min_samples_split=5, min_samples_leaf=3, random_state=42
        )
        
        cv_scores = cross_val_score(model, X_scaled, y, cv=5, scoring='r2')
        mean_score = cv_scores.mean()
        std_score = cv_scores.std()
        
        if base_score is None:
            base_score = mean_score
            diff_str = "baseline"
        else:
            diff = mean_score - base_score
            diff_str = f"{diff:+.2%}"
        
        results.append((name, mean_score, std_score, features))
        print(f"{name:<35} {mean_score:>11.1%} {std_score:>9.1%} {diff_str:>12}")
    
    print("-" * 70)
    
    # Find best
    best = max(results, key=lambda x: x[1])
    print(f"\n🏆 Best performing: {best[0]} (R²={best[1]:.1%})")
    
    # Feature importance analysis for furnished model
    print("\n📊 Feature Importance (with is_furnished):")
    features_with_furnished = base_features + ['is_furnished']
    X = df[features_with_furnished].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = GradientBoostingRegressor(
        n_estimators=200, learning_rate=0.08, max_depth=4,
        min_samples_split=5, min_samples_leaf=3, random_state=42
    )
    model.fit(X_scaled, y)
    
    importances = list(zip(features_with_furnished, model.feature_importances_))
    importances.sort(key=lambda x: x[1], reverse=True)
    for feat, imp in importances:
        marker = "⭐" if feat == 'is_furnished' else "  "
        print(f"  {marker} {feat:<25} {imp:>6.1%}")
    
    # Price impact test
    print("\n" + "=" * 70)
    print("PREDICTION COMPARISON: 75m² apartment in Varaždin")
    print("=" * 70)
    
    test_unfurnished = scaler.transform([[75, 3, 3, 7, 0.5, 0]])
    test_furnished = scaler.transform([[75, 3, 3, 7, 0.5, 1]])
    
    pred_unfurnished = model.predict(test_unfurnished)[0]
    pred_furnished = model.predict(test_furnished)[0]
    
    print(f"\n{'Scenario':<30} {'Predicted Price':>15}")
    print("-" * 45)
    print(f"{'Unfurnished':<30} €{pred_unfurnished:>13,.0f}")
    print(f"{'Furnished':<30} €{pred_furnished:>13,.0f}")
    print("-" * 45)
    print(f"{'Furnished premium':<30} €{pred_furnished - pred_unfurnished:>+13,.0f} ({((pred_furnished - pred_unfurnished) / pred_unfurnished) * 100:+.1f}%)")
    
    # Final recommendation
    print("\n💡 RECOMMENDATION:")
    best_diff = best[1] - base_score
    if best[0] == "Current optimal (5 features)":
        print("   ✅ Current OPTIMAL_FEATURES are already the best!")
        print("   → No changes needed")
    elif best_diff > 0.005:
        print(f"   ✅ '{best[0]}' improves model by {best_diff:+.2%}")
        print(f"   → Consider updating OPTIMAL_FEATURES")
    else:
        print(f"   ➖ Differences are minimal (<0.5%)")
        print("   → Current features are sufficient")

if __name__ == "__main__":
    asyncio.run(test_furnished())

