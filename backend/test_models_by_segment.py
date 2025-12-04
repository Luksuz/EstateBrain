#!/usr/bin/env python3
"""Test ML models across different data segments."""

import os
import warnings
warnings.filterwarnings('ignore')

from dotenv import load_dotenv
load_dotenv()

import numpy as np
import pandas as pd
from supabase import create_client
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except:
    HAS_XGBOOST = False

# Features to use
FEATURES = [
    'living_area_m2',
    'bedroom_count', 
    'bathroom_count',
    'renovation_level',
    'distance_from_center',
    'is_new_construction',
]

MODELS = {
    'Ridge': Ridge(alpha=1.0),
    'Lasso': Lasso(alpha=0.1),
    'ElasticNet': ElasticNet(alpha=0.1, l1_ratio=0.5),
    'RandomForest': RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1),
    'GradientBoosting': GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42),
    'KNN': KNeighborsRegressor(n_neighbors=5),
}

if HAS_XGBOOST:
    MODELS['XGBoost'] = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)

def prepare_data(df):
    """Prepare features from dataframe."""
    df = df.copy()
    
    # Convert boolean to float
    df['is_new_construction'] = df['is_new_construction'].fillna(False).astype(float)
    
    # Fill missing values with median
    for col in FEATURES:
        if col in df.columns:
            median = df[col].median()
            df[col] = df[col].fillna(median if pd.notna(median) else 0)
    
    return df

def evaluate_model(model, X_train, X_test, y_train, y_test):
    """Train and evaluate a model."""
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    
    # R² score
    r2 = float(np.corrcoef(y_test, y_pred)[0,1]**2)
    
    # RMSE
    rmse = np.sqrt(np.mean((y_test - y_pred)**2))
    
    # MAE
    mae = np.mean(np.abs(y_test - y_pred))
    
    return r2, rmse, mae

def test_segment(df, segment_name):
    """Test all models on a data segment."""
    if len(df) < 20:
        return None
    
    df = prepare_data(df)
    
    # Filter to rows with valid features
    available_features = [f for f in FEATURES if f in df.columns]
    df_valid = df.dropna(subset=['price_eur'] + available_features)
    
    if len(df_valid) < 20:
        return None
    
    X = df_valid[available_features].values
    y = df_valid['price_eur'].values
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
    
    results = []
    for name, model in MODELS.items():
        try:
            # Clone model for fresh training
            from sklearn.base import clone
            model_clone = clone(model)
            r2, rmse, mae = evaluate_model(model_clone, X_train, X_test, y_train, y_test)
            results.append({
                'segment': segment_name,
                'model': name,
                'n_samples': len(df_valid),
                'r2': r2,
                'rmse': rmse,
                'mae': mae,
            })
        except Exception as e:
            print(f"  Error with {name}: {e}")
    
    return results

def main():
    # Connect to Supabase
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    client = create_client(url, key)
    
    # Fetch all listings
    result = client.table("listings_v2").select("*").gte("price_eur", 10000).gte("living_area_m2", 10).execute()
    df = pd.DataFrame(result.data)
    
    print(f"Loaded {len(df)} listings")
    print(f"Features: {FEATURES}")
    print(f"Models: {list(MODELS.keys())}")
    print()
    
    all_results = []
    
    # 1. ALL DATA
    print("="*80)
    print("Testing: ALL DATA")
    print("="*80)
    results = test_segment(df, "ALL")
    if results:
        all_results.extend(results)
        best = max(results, key=lambda x: x['r2'])
        print(f"  N={best['n_samples']}, Best: {best['model']} (R²={best['r2']:.4f}, RMSE=€{best['rmse']:,.0f})")
    
    # 2. NEW CONSTRUCTION ONLY
    print("\n" + "="*80)
    print("Testing: NEW CONSTRUCTION ONLY")
    print("="*80)
    df_new = df[df['is_new_construction'] == True]
    results = test_segment(df_new, "NEW_ONLY")
    if results:
        all_results.extend(results)
        best = max(results, key=lambda x: x['r2'])
        print(f"  N={best['n_samples']}, Best: {best['model']} (R²={best['r2']:.4f}, RMSE=€{best['rmse']:,.0f})")
    else:
        print(f"  Not enough data (N={len(df_new)})")
    
    # 3. USED/EXISTING ONLY
    print("\n" + "="*80)
    print("Testing: USED/EXISTING ONLY")
    print("="*80)
    df_used = df[df['is_new_construction'] != True]
    results = test_segment(df_used, "USED_ONLY")
    if results:
        all_results.extend(results)
        best = max(results, key=lambda x: x['r2'])
        print(f"  N={best['n_samples']}, Best: {best['model']} (R²={best['r2']:.4f}, RMSE=€{best['rmse']:,.0f})")
    else:
        print(f"  Not enough data (N={len(df_used)})")
    
    # 4. PER DISTRICT
    print("\n" + "="*80)
    print("Testing: PER DISTRICT")
    print("="*80)
    districts = df['location_district'].dropna().unique()
    district_results = []
    
    for district in sorted(districts):
        df_district = df[df['location_district'] == district]
        results = test_segment(df_district, f"DISTRICT:{district}")
        if results:
            all_results.extend(results)
            district_results.append(results)
            best = max(results, key=lambda x: x['r2'])
            print(f"  {district}: N={best['n_samples']}, Best: {best['model']} (R²={best['r2']:.4f})")
        else:
            print(f"  {district}: Not enough data (N={len(df_district)})")
    
    # SUMMARY TABLE
    print("\n" + "="*80)
    print("SUMMARY: BEST MODEL PER SEGMENT")
    print("="*80)
    print(f"{'Segment':<25} {'N':>5} {'Best Model':<18} {'R²':>7} {'RMSE':>10} {'MAE':>10}")
    print("-"*80)
    
    # Group by segment and find best
    segments = {}
    for r in all_results:
        seg = r['segment']
        if seg not in segments or r['r2'] > segments[seg]['r2']:
            segments[seg] = r
    
    for seg in ['ALL', 'NEW_ONLY', 'USED_ONLY'] + [s for s in segments if s.startswith('DISTRICT:')]:
        if seg in segments:
            r = segments[seg]
            seg_display = seg.replace('DISTRICT:', '')[:24]
            print(f"{seg_display:<25} {r['n_samples']:>5} {r['model']:<18} {r['r2']:>7.4f} €{r['rmse']:>9,.0f} €{r['mae']:>9,.0f}")
    
    # MODEL COMPARISON ACROSS ALL SEGMENTS
    print("\n" + "="*80)
    print("MODEL COMPARISON (Average R² across segments with N≥50)")
    print("="*80)
    
    model_scores = {}
    for r in all_results:
        if r['n_samples'] >= 50:
            model = r['model']
            if model not in model_scores:
                model_scores[model] = []
            model_scores[model].append(r['r2'])
    
    print(f"{'Model':<18} {'Avg R²':>8} {'Min R²':>8} {'Max R²':>8} {'Segments':>8}")
    print("-"*50)
    for model in sorted(model_scores.keys(), key=lambda m: -np.mean(model_scores[m])):
        scores = model_scores[model]
        print(f"{model:<18} {np.mean(scores):>8.4f} {min(scores):>8.4f} {max(scores):>8.4f} {len(scores):>8}")
    
    # RECOMMENDATION
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    if 'ALL' in segments:
        print(f"\n🏆 OVERALL BEST: {segments['ALL']['model']} (R²={segments['ALL']['r2']:.4f})")
    
    if 'NEW_ONLY' in segments:
        print(f"🆕 FOR NEW CONSTRUCTION: {segments['NEW_ONLY']['model']} (R²={segments['NEW_ONLY']['r2']:.4f})")
    
    if 'USED_ONLY' in segments:
        print(f"🏠 FOR USED PROPERTIES: {segments['USED_ONLY']['model']} (R²={segments['USED_ONLY']['r2']:.4f})")

if __name__ == "__main__":
    main()

