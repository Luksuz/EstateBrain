#!/usr/bin/env python3
"""Compare different feature sets for ML model training - standalone version."""

import os
from dotenv import load_dotenv
load_dotenv()

import numpy as np
import pandas as pd
from supabase import create_client

from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except:
    HAS_XGBOOST = False

# Feature set definitions
FEATURE_SETS = {
    "minimal": ["living_area_m2", "bedroom_count"],
    "core": ["living_area_m2", "bedroom_count", "bathroom_count", "renovation_level"],
    "standard": ["living_area_m2", "bedroom_count", "bathroom_count", "renovation_level", 
                 "is_new_construction", "has_garage"],
    "numeric": ["living_area_m2", "bedroom_count", "bathroom_count", "outdoor_area_m2",
               "renovation_level", "distance_from_center", "has_garage", "is_house", 
               "is_furnished", "has_cellar", "is_new_construction"],
}

def prepare_data(df, feature_set_name):
    """Prepare features for a specific feature set."""
    features = FEATURE_SETS.get(feature_set_name, FEATURE_SETS["minimal"])
    
    # Create derived features
    df = df.copy()
    df['has_garage'] = (df['parking_type'] == 'GARAGE').astype(float) if 'parking_type' in df.columns else 0.0
    df['is_house'] = (df['building_type'] == 'HOUSE').astype(float) if 'building_type' in df.columns else 0.0
    df['is_furnished'] = df['interior_arranged'].fillna(False).astype(float) if 'interior_arranged' in df.columns else 0.0
    df['has_cellar'] = df['has_cellar'].fillna(False).astype(float) if 'has_cellar' in df.columns else 0.0
    df['is_new_construction'] = df['is_new_construction'].fillna(False).astype(float) if 'is_new_construction' in df.columns else 0.0
    
    # Get available features
    available = [f for f in features if f in df.columns]
    
    # Filter valid rows
    df_valid = df[df['price_eur'].notna()].copy()
    
    # Fill NaN with median for numeric, 0 for binary
    for col in available:
        if df_valid[col].dtype in ['float64', 'int64']:
            df_valid[col] = df_valid[col].fillna(df_valid[col].median())
        else:
            df_valid[col] = df_valid[col].fillna(0)
    
    X = df_valid[available].values
    y = df_valid['price_eur'].values
    
    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    return X_scaled, y, available

def train_and_eval(X, y, model, cv_folds=5):
    """Train and evaluate a model."""
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    
    cv = cross_val_score(model, X, y, cv=min(cv_folds, len(X)//2), scoring='r2')
    
    return r2, rmse, mae, cv.mean(), cv.std()

def main():
    # Connect to Supabase
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("Missing SUPABASE_URL or SUPABASE_KEY in environment")
        return
    
    client = create_client(url, key)
    
    # Fetch listings
    result = client.table("listings_v2").select("*").gte("price_eur", 10000).gte("living_area_m2", 10).execute()
    listings = result.data
    
    print(f"Loaded {len(listings)} listings")
    
    if len(listings) < 10:
        print("Not enough data!")
        return
    
    df = pd.DataFrame(listings)
    
    # Models to test
    models = {
        "Ridge": Ridge(alpha=1.0),
        "RandomForest": RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1),
    }
    if HAS_XGBOOST:
        models["XGBoost"] = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
    
    print("\n" + "="*90)
    print("FEATURE SET COMPARISON")
    print("="*90)
    
    for model_name, model in models.items():
        print(f"\n{'─'*90}")
        print(f"Model: {model_name}")
        print(f"{'─'*90}")
        print(f"  {'Feature Set':<12} │ {'R²':>8} │ {'RMSE':>12} │ {'MAE':>12} │ {'CV Mean':>10} │ {'# Feat':>6}")
        print(f"  {'─'*12}─┼─{'─'*8}─┼─{'─'*12}─┼─{'─'*12}─┼─{'─'*10}─┼─{'─'*6}")
        
        results = []
        for fs_name in FEATURE_SETS.keys():
            try:
                X, y, feat_names = prepare_data(df, fs_name)
                r2, rmse, mae, cv_mean, cv_std = train_and_eval(X, y, model)
                results.append((fs_name, r2, rmse, mae, cv_mean, cv_std, len(feat_names)))
                print(f"  {fs_name:<12} │ {r2:>8.4f} │ €{rmse:>10,.0f} │ €{mae:>10,.0f} │ {cv_mean:>7.4f}±{cv_std:.2f} │ {len(feat_names):>6}")
            except Exception as e:
                print(f"  {fs_name:<12} │ ERROR: {e}")
        
        if results:
            best = max(results, key=lambda x: x[1])
            print(f"\n  🏆 Best: {best[0]} (R²={best[1]:.4f}) with {best[6]} features")
            
            # Compare minimal vs numeric
            minimal = next((r for r in results if r[0] == "minimal"), None)
            numeric = next((r for r in results if r[0] == "numeric"), None)
            if minimal and numeric:
                diff = numeric[1] - minimal[1]
                if abs(diff) < 0.03:
                    print(f"  💡 Minimal (2 feat) vs Numeric (11 feat): Only {diff:+.4f} R² difference!")
                    print(f"     → Consider using minimal for simplicity")

if __name__ == "__main__":
    main()
