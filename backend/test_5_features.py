#!/usr/bin/env python3
"""
Test multiple models with 5 features:
- living_area_m2
- renovation_level
- distance_from_center
- bedroom_count
- is_new_construction
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
    from sklearn.linear_model import Ridge, Lasso, ElasticNet, BayesianRidge
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.svm import SVR
    from sklearn.metrics import r2_score, mean_absolute_error, mean_absolute_percentage_error
    
    # Get listings
    print("Loading listings...")
    listings = await get_filtered_listings()
    print(f"Loaded {len(listings)} listings")
    
    df = pd.DataFrame(listings)
    
    # 5 features as requested
    features = [
        'living_area_m2',       # Living area
        'renovation_level',     # Renovation level (0-10)
        'distance_from_center', # Distance from city center
        'bedroom_count',        # Number of bedrooms
        'is_new_construction',  # Whether it's new construction
    ]
    
    print(f"\n📊 Features: {', '.join(features)}")
    
    # Prepare data
    for col in features + ['price_eur']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Fill missing values
    df['renovation_level'] = df['renovation_level'].fillna(7)  # Default average
    df['distance_from_center'] = df['distance_from_center'].fillna(5)  # Default 5km
    df['is_new_construction'] = df['is_new_construction'].fillna(0).astype(float)
    
    df = df.dropna(subset=['living_area_m2', 'bedroom_count', 'price_eur'])
    df = df[df['price_eur'] > 0]
    df = df[df['living_area_m2'] > 10]
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
    
    print(f"\nTrain: {len(X_train)}, Test: {len(X_test)}")
    
    print("\n" + "=" * 80)
    print("MODEL COMPARISON - 5 Features")
    print("=" * 80)
    
    # Models to test
    models = {
        'Ridge': Ridge(alpha=1.0),
        'Lasso': Lasso(alpha=100),
        'ElasticNet': ElasticNet(alpha=100, l1_ratio=0.5),
        'BayesianRidge': BayesianRidge(),
        'KNN (k=3)': KNeighborsRegressor(n_neighbors=3),
        'KNN (k=5)': KNeighborsRegressor(n_neighbors=5),
        'KNN (k=7)': KNeighborsRegressor(n_neighbors=7),
        'SVR': SVR(kernel='rbf', C=100000),
        'RandomForest': RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42),
        'RandomForest (deep)': RandomForestRegressor(n_estimators=300, max_depth=15, random_state=42),
        'GradientBoosting': GradientBoostingRegressor(
            n_estimators=200, learning_rate=0.08, max_depth=4, random_state=42
        ),
        'GradientBoosting (tuned)': GradientBoostingRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=5, random_state=42
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
        models['XGBoost (tuned)'] = XGBRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=6, random_state=42
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
            iterations=200, learning_rate=0.08, depth=6, random_state=42, verbose=0
        )
    except ImportError:
        pass
    
    results = []
    
    print(f"\n{'Model':<25} {'R² Test':>10} {'CV Mean':>10} {'CV Std':>10} {'MAPE':>10} {'RMSE':>12}")
    print("-" * 77)
    
    for name, model in models.items():
        try:
            # Cross-validation
            cv_scores = cross_val_score(model, X_scaled, y, cv=5, scoring='r2')
            
            # Train and test
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            
            r2 = r2_score(y_test, y_pred)
            mape = mean_absolute_percentage_error(y_test, y_pred) * 100
            rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))
            
            results.append({
                'name': name,
                'r2_test': r2,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'mape': mape,
                'rmse': rmse,
                'model': model
            })
            
            print(f"{name:<25} {r2:>9.1%} {cv_scores.mean():>9.1%} {cv_scores.std():>9.1%} {mape:>9.1f}% €{rmse:>10,.0f}")
        except Exception as e:
            print(f"{name:<25} ERROR: {e}")
    
    print("-" * 77)
    
    # Sort by CV mean
    results.sort(key=lambda x: x['cv_mean'], reverse=True)
    
    # Top 5
    print("\n" + "=" * 80)
    print("🏆 TOP 5 MODELS")
    print("=" * 80)
    
    for i, r in enumerate(results[:5]):
        print(f"\n{i+1}. {r['name']}")
        print(f"   R² (test):  {r['r2_test']:.1%}")
        print(f"   CV Mean:    {r['cv_mean']:.1%} ± {r['cv_std']:.1%}")
        print(f"   MAPE:       {r['mape']:.1f}%")
        print(f"   RMSE:       €{r['rmse']:,.0f}")
    
    # Best model feature importance
    best = results[0]
    print("\n" + "=" * 80)
    print(f"📊 FEATURE IMPORTANCE ({best['name']})")
    print("=" * 80)
    
    if hasattr(best['model'], 'feature_importances_'):
        importances = best['model'].feature_importances_
        importance_list = list(zip(features, importances))
        importance_list.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n{'Feature':<25} {'Importance':>12} {'Bar'}")
        print("-" * 60)
        
        max_imp = max(importances)
        for feat, imp in importance_list:
            bar = "█" * int(imp / max_imp * 30)
            print(f"{feat:<25} {imp:>11.1%} {bar}")
    
    # Recommendation
    print("\n" + "=" * 80)
    print("💡 RECOMMENDATION")
    print("=" * 80)
    
    best = results[0]
    print(f"\n✅ Use {best['name']} for best results:")
    print(f"   • R² = {best['cv_mean']:.1%}")
    print(f"   • MAPE = {best['mape']:.1f}% (average prediction error)")
    print(f"   • RMSE = €{best['rmse']:,.0f}")
    
    # Compare with 4 features
    print("\n📊 Dataset Stats:")
    print(f"   • Total listings: {len(df)}")
    print(f"   • Price range: €{y.min():,.0f} - €{y.max():,.0f}")
    print(f"   • Mean price: €{y.mean():,.0f}")

if __name__ == "__main__":
    asyncio.run(test_models())


