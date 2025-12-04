#!/usr/bin/env python3
"""Test top models on filtered data segments."""

import os
import warnings
warnings.filterwarnings('ignore')

from dotenv import load_dotenv
load_dotenv()

import numpy as np
import pandas as pd
from supabase import create_client
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.svm import NuSVR

import xgboost as xgb
from catboost import CatBoostRegressor

FEATURES = [
    'living_area_m2',
    'bedroom_count',
    'renovation_level',
    'distance_from_center',
]

def remove_outliers_iqr(df, column, threshold=1.5):
    if column not in df.columns or df[column].isna().all():
        return df
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    return df[(df[column] >= Q1 - threshold * IQR) & (df[column] <= Q3 + threshold * IQR)]

def clean_data(df):
    df = df.copy()
    df = remove_outliers_iqr(df, 'price_eur', 1.5)
    df = remove_outliers_iqr(df, 'living_area_m2', 1.5)
    df['price_per_m2'] = df['price_eur'] / df['living_area_m2']
    df = remove_outliers_iqr(df, 'price_per_m2', 1.5)
    df = df[df['distance_from_center'].notna()]
    df = remove_outliers_iqr(df, 'distance_from_center', 1.5)
    return df

def evaluate(y_true, y_pred):
    r2 = float(np.corrcoef(y_true, y_pred)[0,1]**2)
    rmse = np.sqrt(np.mean((y_true - y_pred)**2))
    mae = np.mean(np.abs(y_true - y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    return r2, rmse, mae, mape

def get_models():
    return {
        'NuSVR': (NuSVR(kernel='rbf', C=100000, nu=0.5), True),
        'CatBoost': (CatBoostRegressor(iterations=200, depth=8, learning_rate=0.1, random_state=42, verbose=0), False),
        'XGBoost': (xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42), True),
        'ExtraTrees': (ExtraTreesRegressor(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1), False),
    }

def test_segment(df, segment_name):
    """Test all models on a data segment."""
    if len(df) < 30:
        print(f"\n⚠️ {segment_name}: Not enough data (N={len(df)})")
        return None
    
    # Prepare features
    df = df.copy()
    for col in FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())
    
    X = df[FEATURES].values
    y = df['price_eur'].values
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print(f"\n{'='*80}")
    print(f"{segment_name} (N={len(df)}, Train={len(X_train)}, Test={len(X_test)})")
    print(f"{'='*80}")
    print(f"  Price range: €{df['price_eur'].min():,.0f} - €{df['price_eur'].max():,.0f}")
    print(f"  Area range: {df['living_area_m2'].min():.0f}m² - {df['living_area_m2'].max():.0f}m²")
    print(f"  Avg price/m²: €{(df['price_eur']/df['living_area_m2']).mean():,.0f}")
    print()
    
    results = []
    print(f"{'Model':<15} {'R²':>8} {'RMSE':>12} {'MAE':>12} {'MAPE':>8}")
    print("-"*60)
    
    for name, (model, needs_scaling) in get_models().items():
        try:
            X_tr = X_train_scaled if needs_scaling else X_train
            X_te = X_test_scaled if needs_scaling else X_test
            
            model.fit(X_tr, y_train)
            y_pred = model.predict(X_te)
            r2, rmse, mae, mape = evaluate(y_test, y_pred)
            
            results.append({'model': name, 'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape})
            print(f"{name:<15} {r2:>8.4f} €{rmse:>10,.0f} €{mae:>10,.0f} {mape:>7.1f}%")
        except Exception as e:
            print(f"{name:<15} FAILED: {str(e)[:30]}")
    
    if results:
        best = max(results, key=lambda x: x['r2'])
        print(f"\n🏆 Best for {segment_name}: {best['model']} (R²={best['r2']:.4f})")
    
    return results

def main():
    # Load data
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    client = create_client(url, key)
    
    result = client.table("listings_v2").select("*").gte("price_eur", 10000).gte("living_area_m2", 10).execute()
    df_raw = pd.DataFrame(result.data)
    
    print(f"Raw data: {len(df_raw)} listings")
    
    # Clean data
    df = clean_data(df_raw)
    print(f"Clean data: {len(df)} listings")
    
    all_results = {}
    
    # 1. ALL DATA
    all_results['ALL'] = test_segment(df, "ALL DATA")
    
    # 2. VARAŽDIN DISTRICT ONLY
    df_vz = df[df['location_district'] == 'Varaždin']
    all_results['VARAŽDIN'] = test_segment(df_vz, "VARAŽDIN ONLY")
    
    # 3. NEW CONSTRUCTION ONLY
    df_new = df[df['is_new_construction'] == True]
    all_results['NEW'] = test_segment(df_new, "NEW CONSTRUCTION ONLY")
    
    # 4. USED/EXISTING ONLY
    df_used = df[df['is_new_construction'] != True]
    all_results['USED'] = test_segment(df_used, "USED APARTMENTS ONLY")
    
    # 5. VARAŽDIN + NEW
    df_vz_new = df[(df['location_district'] == 'Varaždin') & (df['is_new_construction'] == True)]
    all_results['VZ_NEW'] = test_segment(df_vz_new, "VARAŽDIN + NEW")
    
    # 6. VARAŽDIN + USED
    df_vz_used = df[(df['location_district'] == 'Varaždin') & (df['is_new_construction'] != True)]
    all_results['VZ_USED'] = test_segment(df_vz_used, "VARAŽDIN + USED")
    
    # SUMMARY
    print("\n" + "="*80)
    print("SUMMARY: BEST MODEL PER SEGMENT")
    print("="*80)
    print(f"\n{'Segment':<25} {'N':>5} {'Best Model':<15} {'R²':>8} {'RMSE':>12} {'MAPE':>8}")
    print("-"*80)
    
    for segment, results in all_results.items():
        if results:
            best = max(results, key=lambda x: x['r2'])
            n = {'ALL': len(df), 'VARAŽDIN': len(df_vz), 'NEW': len(df_new), 
                 'USED': len(df_used), 'VZ_NEW': len(df_vz_new), 'VZ_USED': len(df_vz_used)}.get(segment, 0)
            print(f"{segment:<25} {n:>5} {best['model']:<15} {best['r2']:>8.4f} €{best['rmse']:>10,.0f} {best['mape']:>7.1f}%")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS BY USE CASE")
    print("="*80)
    
    recommendations = []
    for segment, results in all_results.items():
        if results:
            best = max(results, key=lambda x: x['r2'])
            recommendations.append((segment, best))
    
    print("\n📋 Model Selection Guide:")
    for segment, best in recommendations:
        print(f"   • {segment}: Use {best['model']} (R²={best['r2']:.4f}, MAPE={best['mape']:.1f}%)")

if __name__ == "__main__":
    main()

