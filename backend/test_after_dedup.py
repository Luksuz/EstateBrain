#!/usr/bin/env python3
"""
Test models and feature importance after deduplication.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def test_models():
    from app.services.ml_router_helpers import get_filtered_listings
    import pandas as pd
    import numpy as np
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.ensemble import (
        GradientBoostingRegressor, RandomForestRegressor, 
        ExtraTreesRegressor, AdaBoostRegressor
    )
    from sklearn.linear_model import Ridge, Lasso, ElasticNet
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.metrics import r2_score, mean_absolute_error, mean_absolute_percentage_error
    
    # Get listings (after deduplication)
    print("Loading listings (after deduplication)...")
    listings = await get_filtered_listings()
    print(f"Loaded {len(listings)} listings")
    
    df = pd.DataFrame(listings)
    
    # Optimal features
    features = ['living_area_m2', 'bedroom_count', 'outdoor_area_m2', 
                'renovation_level', 'distance_from_center']
    
    # Prepare data
    for col in features + ['price_eur']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Fill missing outdoor_area_m2 with 0 (no balcony/terrace)
    df['outdoor_area_m2'] = df['outdoor_area_m2'].fillna(0)
    
    df = df.dropna(subset=features + ['price_eur'])
    df = df[df['price_eur'] > 0]
    print(f"Valid rows: {len(df)}")
    
    X = df[features].values
    y = df['price_eur'].values
    
    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42
    )
    
    print("\n" + "=" * 70)
    print("MODEL COMPARISON (After Deduplication)")
    print("=" * 70)
    
    # Models to test
    models = {
        'Ridge': Ridge(alpha=1.0),
        'Lasso': Lasso(alpha=100),
        'ElasticNet': ElasticNet(alpha=100, l1_ratio=0.5),
        'KNN': KNeighborsRegressor(n_neighbors=5),
        'RandomForest': RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42),
        'GradientBoosting': GradientBoostingRegressor(
            n_estimators=200, learning_rate=0.08, max_depth=4, random_state=42
        ),
        'ExtraTrees': ExtraTreesRegressor(n_estimators=200, max_depth=12, random_state=42),
        'AdaBoost': AdaBoostRegressor(n_estimators=100, random_state=42),
    }
    
    # Try XGBoost if available
    try:
        from xgboost import XGBRegressor
        models['XGBoost'] = XGBRegressor(
            n_estimators=200, learning_rate=0.08, max_depth=4, random_state=42
        )
    except ImportError:
        pass
    
    # Try LightGBM if available
    try:
        from lightgbm import LGBMRegressor
        models['LightGBM'] = LGBMRegressor(
            n_estimators=200, learning_rate=0.08, max_depth=4, random_state=42, verbose=-1
        )
    except ImportError:
        pass
    
    # Try CatBoost if available
    try:
        from catboost import CatBoostRegressor
        models['CatBoost'] = CatBoostRegressor(
            iterations=200, learning_rate=0.08, depth=4, random_state=42, verbose=0
        )
    except ImportError:
        pass
    
    results = []
    
    print(f"\n{'Model':<20} {'R² Test':>10} {'CV Mean':>10} {'CV Std':>10} {'MAPE':>10}")
    print("-" * 60)
    
    best_model = None
    best_score = -float('inf')
    best_model_name = None
    
    for name, model in models.items():
        # Cross-validation
        cv_scores = cross_val_score(model, X_scaled, y, cv=5, scoring='r2')
        
        # Train and test
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        r2 = r2_score(y_test, y_pred)
        mape = mean_absolute_percentage_error(y_test, y_pred) * 100
        
        results.append({
            'name': name,
            'r2': r2,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'mape': mape,
            'model': model
        })
        
        print(f"{name:<20} {r2:>9.1%} {cv_scores.mean():>9.1%} {cv_scores.std():>9.1%} {mape:>9.1f}%")
        
        if cv_scores.mean() > best_score:
            best_score = cv_scores.mean()
            best_model = model
            best_model_name = name
    
    print("-" * 60)
    
    # Sort by CV mean
    results.sort(key=lambda x: x['cv_mean'], reverse=True)
    
    print(f"\n🏆 BEST MODEL: {best_model_name} (CV R²={best_score:.1%})")
    
    # Feature importance for best model
    print("\n" + "=" * 70)
    print(f"FEATURE IMPORTANCE ({best_model_name})")
    print("=" * 70)
    
    if hasattr(best_model, 'feature_importances_'):
        importances = best_model.feature_importances_
        importance_list = list(zip(features, importances))
        importance_list.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n{'Feature':<25} {'Importance':>12} {'Bar'}")
        print("-" * 60)
        
        max_imp = max(importances)
        for feat, imp in importance_list:
            bar = "█" * int(imp / max_imp * 30)
            print(f"{feat:<25} {imp:>11.1%} {bar}")
    
    elif hasattr(best_model, 'coef_'):
        coefs = best_model.coef_
        coef_list = list(zip(features, np.abs(coefs)))
        coef_list.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n{'Feature':<25} {'Coefficient':>12}")
        print("-" * 40)
        for feat, coef in coef_list:
            print(f"{feat:<25} {coef:>12.2f}")
    
    # Top 3 models comparison
    print("\n" + "=" * 70)
    print("TOP 3 MODELS")
    print("=" * 70)
    
    for i, r in enumerate(results[:3]):
        print(f"\n{i+1}. {r['name']}")
        print(f"   R² (test):  {r['r2']:.1%}")
        print(f"   CV Mean:    {r['cv_mean']:.1%}")
        print(f"   MAPE:       {r['mape']:.1f}%")
    
    # Recommendation
    print("\n" + "=" * 70)
    print("💡 RECOMMENDATION")
    print("=" * 70)
    
    top = results[0]
    print(f"\nUse {top['name']} for predictions:")
    print(f"  • R² = {top['cv_mean']:.1%} (explains {top['cv_mean']*100:.0f}% of price variance)")
    print(f"  • MAPE = {top['mape']:.1f}% (average prediction error)")
    print(f"  • Stable (CV std = {top['cv_std']:.1%})")
    
    # Show dataset stats
    print("\n📊 Dataset Stats (after dedup):")
    print(f"  • Total listings: {len(df)}")
    print(f"  • Price range: €{y.min():,.0f} - €{y.max():,.0f}")
    print(f"  • Avg price: €{y.mean():,.0f}")
    print(f"  • Median price: €{np.median(y):,.0f}")

if __name__ == "__main__":
    asyncio.run(test_models())

