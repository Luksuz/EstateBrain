#!/usr/bin/env python3
"""Feature permutation search with outlier removal."""

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
    'distance_from_center',
    'is_new_construction',
]

def remove_outliers(df, column, method='iqr', threshold=1.5):
    """Remove outliers using IQR or percentile method."""
    if method == 'iqr':
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - threshold * IQR
        upper = Q3 + threshold * IQR
        return df[(df[column] >= lower) & (df[column] <= upper)]
    elif method == 'percentile':
        lower = df[column].quantile(0.01)
        upper = df[column].quantile(0.99)
        return df[(df[column] >= lower) & (df[column] <= upper)]
    return df

def prepare_df(df):
    """Prepare DataFrame with derived features."""
    df = df.copy()
    df['is_new_construction'] = df['is_new_construction'].fillna(False).astype(float)
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
    
    df = pd.DataFrame(listings)
    print(f"Loaded {len(df)} listings (raw)")
    
    # REMOVE OUTLIERS
    print("\n" + "="*60)
    print("OUTLIER REMOVAL")
    print("="*60)
    
    df_clean = df.copy()
    
    # Price outliers (IQR method)
    before = len(df_clean)
    df_clean = remove_outliers(df_clean, 'price_eur', method='iqr', threshold=1.5)
    print(f"Price outliers removed: {before - len(df_clean)} (IQR 1.5x)")
    
    # Area outliers (IQR method)
    before = len(df_clean)
    df_clean = remove_outliers(df_clean, 'living_area_m2', method='iqr', threshold=1.5)
    print(f"Area outliers removed: {before - len(df_clean)} (IQR 1.5x)")
    
    # Price per m² outliers
    df_clean['price_per_m2'] = df_clean['price_eur'] / df_clean['living_area_m2']
    before = len(df_clean)
    df_clean = remove_outliers(df_clean, 'price_per_m2', method='iqr', threshold=1.5)
    print(f"Price/m² outliers removed: {before - len(df_clean)} (IQR 1.5x)")
    
    # Distance from center outliers
    df_clean = df_clean[df_clean['distance_from_center'].notna()]
    before = len(df_clean)
    df_clean = remove_outliers(df_clean, 'distance_from_center', method='iqr', threshold=1.5)
    print(f"Distance outliers removed: {before - len(df_clean)} (IQR 1.5x)")
    
    print(f"\n✓ Clean dataset: {len(df_clean)} listings ({len(df_clean)/len(df)*100:.1f}% retained)")
    
    # Show data ranges
    print(f"\nData ranges (after cleaning):")
    print(f"  Price: €{df_clean['price_eur'].min():,.0f} - €{df_clean['price_eur'].max():,.0f}")
    print(f"  Area: {df_clean['living_area_m2'].min():.0f}m² - {df_clean['living_area_m2'].max():.0f}m²")
    print(f"  Price/m²: €{df_clean['price_per_m2'].min():,.0f} - €{df_clean['price_per_m2'].max():,.0f}")
    print(f"  Distance: {df_clean['distance_from_center'].min():.1f}km - {df_clean['distance_from_center'].max():.1f}km")
    
    df_prepared = prepare_df(df_clean)
    
    n_cores = multiprocessing.cpu_count()
    print(f"\nUsing {n_cores} CPU cores")
    
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
    print(f"\nTesting {total} feature combinations...\n")
    
    # Run in parallel
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
    print("TOP 15 FEATURE COMBINATIONS (CLEAN DATA)")
    print("="*90)
    print(f"{'#':<3} {'R²':>7} {'RMSE':>11} {'N':>2}  Features")
    print("-"*90)
    
    for i, r in enumerate(results[:15], 1):
        feat_str = ', '.join(r['features'])
        print(f"{i:<3} {r['r2']:>7.4f} €{r['rmse']:>9,.0f} {r['num']:>2}  {feat_str}")
    
    print("\n" + "="*90)
    print("BEST BY # OF FEATURES")
    print("="*90)
    
    for n in range(1, len(ALL_FEATURES)+1):
        n_results = [r for r in results if r['num'] == n]
        if n_results:
            best = max(n_results, key=lambda x: x['r2'])
            print(f"\n{n} feature{'s' if n>1 else ''}: R²={best['r2']:.4f}, RMSE=€{best['rmse']:,.0f}")
            print(f"   {', '.join(best['features'])}")
    
    print("\n" + "="*90)
    print("COMPARISON: CLEAN vs RAW DATA")
    print("="*90)
    
    # Test best combo on raw data too
    best_features = list(results[0]['features'])
    
    # Raw data result
    df_raw_prepared = prepare_df(df)
    raw_result = test_feature_combo(best_features, df_raw_prepared, model_params)
    
    print(f"\nBest features: {', '.join(best_features)}")
    print(f"  Clean data (N={len(df_clean)}): R²={results[0]['r2']:.4f}, RMSE=€{results[0]['rmse']:,.0f}")
    if raw_result:
        print(f"  Raw data (N={len(df)}):   R²={raw_result['r2']:.4f}, RMSE=€{raw_result['rmse']:,.0f}")
    
    print("\n" + "="*90)
    print("RECOMMENDATION")  
    print("="*90)
    
    best = results[0]
    print(f"\n🏆 BEST: R²={best['r2']:.4f} with {best['num']} features")
    print(f"   {', '.join(best['features'])}")

if __name__ == "__main__":
    main()

