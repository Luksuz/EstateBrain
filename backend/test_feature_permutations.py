#!/usr/bin/env python3
"""Parallel feature permutation search - uses all CPU cores."""

import os
import warnings
warnings.filterwarnings('ignore')

from dotenv import load_dotenv
load_dotenv()

import numpy as np
import pandas as pd
from supabase import create_client
from itertools import combinations
from joblib import Parallel, delayed
import multiprocessing

from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except:
    HAS_XGBOOST = False

# All available features
ALL_FEATURES = [
    'living_area_m2',
    'bedroom_count',
    'bathroom_count',
    'renovation_level',
    'outdoor_area_m2',
    'distance_from_center',
    'is_new_construction',
    'has_garage',
    'is_house',
    'is_furnished',
    'has_cellar',
]

# Global DataFrame (shared across workers)
DF = None

def prepare_df(df):
    """Prepare DataFrame with derived features."""
    df = df.copy()
    df['has_garage'] = (df['parking_type'] == 'GARAGE').astype(float) if 'parking_type' in df.columns else 0.0
    df['is_house'] = (df['building_type'] == 'HOUSE').astype(float) if 'building_type' in df.columns else 0.0
    df['is_furnished'] = df['interior_arranged'].fillna(False).astype(float) if 'interior_arranged' in df.columns else 0.0
    df['has_cellar'] = df['has_cellar'].fillna(False).astype(float) if 'has_cellar' in df.columns else 0.0
    df['is_new_construction'] = df['is_new_construction'].fillna(False).astype(float) if 'is_new_construction' in df.columns else 0.0
    return df

def test_feature_combo(features, df_prepared, model_params):
    """Test a single feature combination."""
    try:
        available = [f for f in features if f in df_prepared.columns]
        if not available:
            return None
        
        df_valid = df_prepared[df_prepared['price_eur'].notna()].copy()
        
        for col in available:
            median = df_valid[col].median()
            df_valid[col] = df_valid[col].fillna(median if pd.notna(median) else 0)
        
        X = df_valid[available].values
        y = df_valid['price_eur'].values
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        
        if HAS_XGBOOST:
            model = xgb.XGBRegressor(**model_params)
        else:
            model = RandomForestRegressor(**model_params)
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        r2 = float(np.corrcoef(y_test, y_pred)[0,1]**2)
        rmse = np.sqrt(np.mean((y_test - y_pred)**2))
        
        return {
            'features': tuple(available),
            'num': len(available),
            'r2': r2,
            'rmse': rmse,
        }
    except:
        return None

def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    client = create_client(url, key)
    result = client.table("listings_v2").select("*").gte("price_eur", 10000).gte("living_area_m2", 10).execute()
    listings = result.data
    
    print(f"Loaded {len(listings)} listings")
    df = pd.DataFrame(listings)
    df_prepared = prepare_df(df)
    
    n_cores = multiprocessing.cpu_count()
    print(f"Using {n_cores} CPU cores")
    
    if HAS_XGBOOST:
        model_params = {'n_estimators': 100, 'max_depth': 6, 'learning_rate': 0.1, 'random_state': 42, 'n_jobs': 1}
        model_name = "XGBoost"
    else:
        model_params = {'n_estimators': 100, 'max_depth': 10, 'random_state': 42, 'n_jobs': 1}
        model_name = "RandomForest"
    
    print(f"Model: {model_name}")
    
    # Generate all combinations
    all_combos = []
    for num_features in range(1, len(ALL_FEATURES) + 1):
        for combo in combinations(ALL_FEATURES, num_features):
            all_combos.append(list(combo))
    
    total = len(all_combos)
    print(f"\nTesting {total} feature combinations in parallel...\n")
    
    # Run in parallel with progress
    results = Parallel(n_jobs=n_cores, verbose=10)(
        delayed(test_feature_combo)(combo, df_prepared, model_params) 
        for combo in all_combos
    )
    
    # Filter None results
    results = [r for r in results if r is not None]
    
    print(f"\n✓ Tested {len(results)} valid combinations\n")
    
    # Sort by R²
    results.sort(key=lambda x: x['r2'], reverse=True)
    
    print("="*90)
    print("TOP 15 FEATURE COMBINATIONS")
    print("="*90)
    print(f"{'#':<3} {'R²':>7} {'RMSE':>11} {'N':>2}  Features")
    print("-"*90)
    
    for i, r in enumerate(results[:15], 1):
        feat_str = ', '.join(r['features'])
        print(f"{i:<3} {r['r2']:>7.4f} €{r['rmse']:>9,.0f} {r['num']:>2}  {feat_str}")
    
    print("\n" + "="*90)
    print("BEST BY # OF FEATURES")
    print("="*90)
    
    for n in range(1, min(7, len(ALL_FEATURES)+1)):
        n_results = [r for r in results if r['num'] == n]
        if n_results:
            best = max(n_results, key=lambda x: x['r2'])
            print(f"\n{n} feature{'s' if n>1 else ''}: R²={best['r2']:.4f}, RMSE=€{best['rmse']:,.0f}")
            print(f"   {', '.join(best['features'])}")
    
    print("\n" + "="*90)
    print("RECOMMENDATION")  
    print("="*90)
    
    best = results[0]
    print(f"\n🏆 BEST: R²={best['r2']:.4f} with {best['num']} features")
    print(f"   {', '.join(best['features'])}")
    
    # Simplest within 2% of best
    threshold = best['r2'] * 0.98
    for r in sorted(results, key=lambda x: x['num']):
        if r['r2'] >= threshold:
            if r['num'] < best['num']:
                print(f"\n💡 SIMPLER (within 2%): R²={r['r2']:.4f} with {r['num']} features")
                print(f"   {', '.join(r['features'])}")
            break

if __name__ == "__main__":
    main()
