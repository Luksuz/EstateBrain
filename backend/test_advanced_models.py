#!/usr/bin/env python3
"""Test advanced/unexplored models for price prediction."""

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

# Base models for comparison
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor,
    ExtraTreesRegressor,  # NEW
    HistGradientBoostingRegressor,  # NEW - sklearn's fast GB
)
from sklearn.linear_model import (
    Ridge,
    BayesianRidge,  # NEW
    HuberRegressor,  # NEW - robust to outliers
)
from sklearn.kernel_ridge import KernelRidge  # NEW
from sklearn.svm import SVR, NuSVR  # NEW - NuSVR
from sklearn.neural_network import MLPRegressor
from sklearn.gaussian_process import GaussianProcessRegressor  # NEW
from sklearn.gaussian_process.kernels import RBF, ConstantKernel

# Try importing optional libraries
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except:
    HAS_XGBOOST = False

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except:
    HAS_LIGHTGBM = False
    print("LightGBM not installed - skipping")

try:
    from catboost import CatBoostRegressor
    HAS_CATBOOST = True
except:
    HAS_CATBOOST = False
    print("CatBoost not installed - skipping")

# Features
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

def test_model(name, model, X_train, X_test, y_train, y_test, scale=True):
    """Test a model and return results."""
    try:
        if scale:
            scaler = StandardScaler()
            X_tr = scaler.fit_transform(X_train)
            X_te = scaler.transform(X_test)
        else:
            X_tr, X_te = X_train, X_test
        
        model.fit(X_tr, y_train)
        y_pred = model.predict(X_te)
        r2, rmse, mae, mape = evaluate(y_test, y_pred)
        return {'name': name, 'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape, 'success': True}
    except Exception as e:
        print(f"  ⚠️ {name} failed: {str(e)[:50]}")
        return {'name': name, 'success': False}

def main():
    # Load data
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    client = create_client(url, key)
    
    result = client.table("listings_v2").select("*").gte("price_eur", 10000).gte("living_area_m2", 10).execute()
    df = pd.DataFrame(result.data)
    df = clean_data(df)
    
    print(f"Clean data: {len(df)} listings")
    
    # Prepare features
    for col in FEATURES:
        df[col] = df[col].fillna(df[col].median())
    
    X = df[FEATURES].values
    y = df['price_eur'].values
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")
    print(f"Features: {FEATURES}\n")
    
    results = []
    
    # ==================== BASELINE ====================
    print("="*80)
    print("BASELINE (Previous Best)")
    print("="*80)
    
    if HAS_XGBOOST:
        results.append(test_model(
            "XGBoost (baseline)", 
            xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42),
            X_train, X_test, y_train, y_test, scale=True
        ))
    
    results.append(test_model(
        "GradientBoosting (baseline)",
        GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42),
        X_train, X_test, y_train, y_test, scale=True
    ))
    
    # ==================== NEW TREE-BASED ====================
    print("\n" + "="*80)
    print("NEW TREE-BASED MODELS")
    print("="*80)
    
    # ExtraTrees - more randomized than RandomForest
    results.append(test_model(
        "ExtraTrees",
        ExtraTreesRegressor(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1),
        X_train, X_test, y_train, y_test, scale=False
    ))
    
    # HistGradientBoosting - sklearn's fast implementation
    results.append(test_model(
        "HistGradientBoosting",
        HistGradientBoostingRegressor(max_iter=200, max_depth=8, learning_rate=0.1, random_state=42),
        X_train, X_test, y_train, y_test, scale=False
    ))
    
    # LightGBM
    if HAS_LIGHTGBM:
        results.append(test_model(
            "LightGBM",
            lgb.LGBMRegressor(n_estimators=200, max_depth=8, learning_rate=0.1, random_state=42, verbose=-1),
            X_train, X_test, y_train, y_test, scale=False
        ))
        
        # LightGBM with dart booster
        results.append(test_model(
            "LightGBM (DART)",
            lgb.LGBMRegressor(n_estimators=200, max_depth=8, learning_rate=0.1, boosting_type='dart', random_state=42, verbose=-1),
            X_train, X_test, y_train, y_test, scale=False
        ))
    
    # CatBoost
    if HAS_CATBOOST:
        results.append(test_model(
            "CatBoost",
            CatBoostRegressor(iterations=200, depth=8, learning_rate=0.1, random_state=42, verbose=0),
            X_train, X_test, y_train, y_test, scale=False
        ))
    
    # ==================== TUNED XGBOOST ====================
    if HAS_XGBOOST:
        print("\n" + "="*80)
        print("TUNED XGBOOST VARIANTS")
        print("="*80)
        
        # More estimators
        results.append(test_model(
            "XGBoost (n=200)",
            xgb.XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42),
            X_train, X_test, y_train, y_test, scale=True
        ))
        
        # Deeper trees
        results.append(test_model(
            "XGBoost (depth=10)",
            xgb.XGBRegressor(n_estimators=100, max_depth=10, learning_rate=0.05, random_state=42),
            X_train, X_test, y_train, y_test, scale=True
        ))
        
        # With regularization
        results.append(test_model(
            "XGBoost (regularized)",
            xgb.XGBRegressor(n_estimators=150, max_depth=6, learning_rate=0.1, 
                           reg_alpha=0.1, reg_lambda=1.0, random_state=42),
            X_train, X_test, y_train, y_test, scale=True
        ))
        
        # DART booster
        results.append(test_model(
            "XGBoost (DART)",
            xgb.XGBRegressor(n_estimators=150, max_depth=6, learning_rate=0.1,
                           booster='dart', random_state=42),
            X_train, X_test, y_train, y_test, scale=True
        ))
    
    # ==================== LINEAR VARIANTS ====================
    print("\n" + "="*80)
    print("ADVANCED LINEAR MODELS")
    print("="*80)
    
    results.append(test_model(
        "BayesianRidge",
        BayesianRidge(),
        X_train, X_test, y_train, y_test, scale=True
    ))
    
    results.append(test_model(
        "HuberRegressor",
        HuberRegressor(epsilon=1.35, max_iter=200),
        X_train, X_test, y_train, y_test, scale=True
    ))
    
    results.append(test_model(
        "KernelRidge (RBF)",
        KernelRidge(alpha=1.0, kernel='rbf', gamma=0.1),
        X_train, X_test, y_train, y_test, scale=True
    ))
    
    results.append(test_model(
        "KernelRidge (Poly)",
        KernelRidge(alpha=1.0, kernel='poly', degree=2),
        X_train, X_test, y_train, y_test, scale=True
    ))
    
    # ==================== SVR VARIANTS ====================
    print("\n" + "="*80)
    print("SVR VARIANTS")
    print("="*80)
    
    results.append(test_model(
        "SVR (RBF)",
        SVR(kernel='rbf', C=100000, gamma='scale'),
        X_train, X_test, y_train, y_test, scale=True
    ))
    
    results.append(test_model(
        "NuSVR",
        NuSVR(kernel='rbf', C=100000, nu=0.5),
        X_train, X_test, y_train, y_test, scale=True
    ))
    
    # ==================== NEURAL NETWORKS ====================
    print("\n" + "="*80)
    print("NEURAL NETWORK VARIANTS")
    print("="*80)
    
    results.append(test_model(
        "MLP (64-32)",
        MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42, early_stopping=True),
        X_train, X_test, y_train, y_test, scale=True
    ))
    
    results.append(test_model(
        "MLP (128-64-32)",
        MLPRegressor(hidden_layer_sizes=(128, 64, 32), max_iter=500, random_state=42, early_stopping=True),
        X_train, X_test, y_train, y_test, scale=True
    ))
    
    results.append(test_model(
        "MLP (256-128-64)",
        MLPRegressor(hidden_layer_sizes=(256, 128, 64), max_iter=500, random_state=42, 
                    early_stopping=True, alpha=0.001),
        X_train, X_test, y_train, y_test, scale=True
    ))
    
    # ==================== RESULTS ====================
    print("\n" + "="*80)
    print("FINAL RANKING")
    print("="*80)
    
    # Filter successful results
    valid_results = [r for r in results if r.get('success', False)]
    valid_results.sort(key=lambda x: x['r2'], reverse=True)
    
    print(f"\n{'Rank':<5} {'Model':<30} {'R²':>8} {'RMSE':>12} {'MAE':>12} {'MAPE':>8}")
    print("-"*80)
    
    baseline_r2 = next((r['r2'] for r in valid_results if 'baseline' in r['name']), 0)
    
    for i, r in enumerate(valid_results, 1):
        is_better = r['r2'] > baseline_r2 and 'baseline' not in r['name']
        marker = "🏆" if i == 1 else ("🆕" if is_better else "  ")
        print(f"{marker}{i:<4} {r['name']:<30} {r['r2']:>8.4f} €{r['rmse']:>10,.0f} €{r['mae']:>10,.0f} {r['mape']:>7.1f}%")
    
    # Summary
    best = valid_results[0]
    baseline = next((r for r in valid_results if 'baseline' in r['name']), None)
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if baseline:
        print(f"\n📊 Baseline (XGBoost): R²={baseline['r2']:.4f}, RMSE=€{baseline['rmse']:,.0f}")
    
    print(f"🏆 Best Model: {best['name']}")
    print(f"   R²={best['r2']:.4f}, RMSE=€{best['rmse']:,.0f}, MAPE={best['mape']:.1f}%")
    
    if baseline and best['r2'] > baseline['r2']:
        improvement = (best['r2'] - baseline['r2']) / baseline['r2'] * 100
        print(f"\n✅ Improvement over baseline: +{improvement:.2f}% R²")
    
    # New models that beat baseline
    if baseline:
        better_models = [r for r in valid_results if r['r2'] > baseline['r2'] and 'baseline' not in r['name']]
        if better_models:
            print(f"\n🆕 Models that beat baseline ({len(better_models)}):")
            for r in better_models[:5]:
                print(f"   • {r['name']}: R²={r['r2']:.4f} (+{(r['r2']-baseline['r2'])/baseline['r2']*100:.2f}%)")

if __name__ == "__main__":
    main()

