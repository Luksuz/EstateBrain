#!/usr/bin/env python3
"""Test ensemble methods for price prediction."""

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
from sklearn.ensemble import (
    RandomForestRegressor, 
    GradientBoostingRegressor,
    VotingRegressor,
    StackingRegressor,
    AdaBoostRegressor,
    BaggingRegressor,
)
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except:
    HAS_XGBOOST = False

# Features to use (best from permutation testing)
FEATURES = [
    'living_area_m2',
    'bedroom_count',
    'renovation_level',
    'distance_from_center',
]

def remove_outliers_iqr(df, column, threshold=1.5):
    """Remove outliers using IQR method."""
    if column not in df.columns or df[column].isna().all():
        return df
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - threshold * IQR
    upper = Q3 + threshold * IQR
    return df[(df[column] >= lower) & (df[column] <= upper)]

def clean_data(df):
    """Apply outlier removal."""
    df = df.copy()
    df = remove_outliers_iqr(df, 'price_eur', 1.5)
    df = remove_outliers_iqr(df, 'living_area_m2', 1.5)
    df['price_per_m2'] = df['price_eur'] / df['living_area_m2']
    df = remove_outliers_iqr(df, 'price_per_m2', 1.5)
    df = df[df['distance_from_center'].notna()]
    df = remove_outliers_iqr(df, 'distance_from_center', 1.5)
    return df

def evaluate(y_true, y_pred):
    """Calculate metrics."""
    r2 = float(np.corrcoef(y_true, y_pred)[0,1]**2)
    rmse = np.sqrt(np.mean((y_true - y_pred)**2))
    mae = np.mean(np.abs(y_true - y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    return r2, rmse, mae, mape

def main():
    # Load data
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    client = create_client(url, key)
    
    result = client.table("listings_v2").select("*").gte("price_eur", 10000).gte("living_area_m2", 10).execute()
    df = pd.DataFrame(result.data)
    
    print(f"Raw data: {len(df)} listings")
    
    # Clean data
    df = clean_data(df)
    print(f"Clean data: {len(df)} listings")
    
    # Prepare features
    for col in FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())
    
    X = df[FEATURES].values
    y = df['price_eur'].values
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print(f"\nTrain: {len(X_train)}, Test: {len(X_test)}")
    print(f"Features: {FEATURES}")
    print()
    
    # ==================== BASE MODELS ====================
    print("="*80)
    print("BASE MODELS")
    print("="*80)
    
    base_models = {
        'Ridge': Ridge(alpha=1.0),
        'Lasso': Lasso(alpha=100),
        'ElasticNet': ElasticNet(alpha=100, l1_ratio=0.5),
        'KNN': KNeighborsRegressor(n_neighbors=5),
        'RandomForest': RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1),
        'GradientBoosting': GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42),
    }
    
    if HAS_XGBOOST:
        base_models['XGBoost'] = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
    
    base_results = {}
    base_predictions = {}
    
    print(f"{'Model':<20} {'R²':>8} {'RMSE':>12} {'MAE':>12} {'MAPE':>8}")
    print("-"*65)
    
    for name, model in base_models.items():
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)
        r2, rmse, mae, mape = evaluate(y_test, y_pred)
        base_results[name] = {'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape}
        base_predictions[name] = y_pred
        print(f"{name:<20} {r2:>8.4f} €{rmse:>10,.0f} €{mae:>10,.0f} {mape:>7.1f}%")
    
    # ==================== ENSEMBLE METHODS ====================
    print("\n" + "="*80)
    print("ENSEMBLE METHODS")
    print("="*80)
    
    ensemble_results = {}
    
    # 1. Simple Average Ensemble
    print("\n--- Simple Average Ensemble ---")
    avg_pred = np.mean([base_predictions[m] for m in ['Ridge', 'RandomForest', 'GradientBoosting']], axis=0)
    r2, rmse, mae, mape = evaluate(y_test, avg_pred)
    ensemble_results['SimpleAverage'] = {'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape}
    print(f"Ridge + RF + GB Average: R²={r2:.4f}, RMSE=€{rmse:,.0f}, MAE=€{mae:,.0f}")
    
    if HAS_XGBOOST:
        avg_pred2 = np.mean([base_predictions[m] for m in ['RandomForest', 'GradientBoosting', 'XGBoost']], axis=0)
        r2, rmse, mae, mape = evaluate(y_test, avg_pred2)
        ensemble_results['AvgTreeEnsembles'] = {'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape}
        print(f"RF + GB + XGB Average:   R²={r2:.4f}, RMSE=€{rmse:,.0f}, MAE=€{mae:,.0f}")
    
    # 2. Weighted Average Ensemble
    print("\n--- Weighted Average Ensemble ---")
    # Weight by R² score
    weights = np.array([base_results[m]['r2'] for m in ['Ridge', 'RandomForest', 'GradientBoosting']])
    weights = weights / weights.sum()
    weighted_pred = sum(w * base_predictions[m] for w, m in zip(weights, ['Ridge', 'RandomForest', 'GradientBoosting']))
    r2, rmse, mae, mape = evaluate(y_test, weighted_pred)
    ensemble_results['WeightedAverage'] = {'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape}
    print(f"Weighted by R²:          R²={r2:.4f}, RMSE=€{rmse:,.0f}, MAE=€{mae:,.0f}")
    
    # 3. Voting Regressor
    print("\n--- Voting Regressor ---")
    voting_models = [
        ('ridge', Ridge(alpha=1.0)),
        ('rf', RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)),
        ('gb', GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)),
    ]
    voting = VotingRegressor(voting_models)
    voting.fit(X_train_scaled, y_train)
    y_pred = voting.predict(X_test_scaled)
    r2, rmse, mae, mape = evaluate(y_test, y_pred)
    ensemble_results['VotingRegressor'] = {'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape}
    print(f"Ridge + RF + GB:         R²={r2:.4f}, RMSE=€{rmse:,.0f}, MAE=€{mae:,.0f}")
    
    if HAS_XGBOOST:
        voting_xgb = [
            ('rf', RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)),
            ('gb', GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)),
            ('xgb', xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)),
        ]
        voting2 = VotingRegressor(voting_xgb)
        voting2.fit(X_train_scaled, y_train)
        y_pred = voting2.predict(X_test_scaled)
        r2, rmse, mae, mape = evaluate(y_test, y_pred)
        ensemble_results['VotingXGB'] = {'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape}
        print(f"RF + GB + XGB:           R²={r2:.4f}, RMSE=€{rmse:,.0f}, MAE=€{mae:,.0f}")
    
    # 4. Stacking Regressor
    print("\n--- Stacking Regressor ---")
    stack_estimators = [
        ('ridge', Ridge(alpha=1.0)),
        ('knn', KNeighborsRegressor(n_neighbors=5)),
        ('rf', RandomForestRegressor(n_estimators=50, max_depth=8, random_state=42, n_jobs=-1)),
    ]
    stacking = StackingRegressor(
        estimators=stack_estimators,
        final_estimator=GradientBoostingRegressor(n_estimators=50, max_depth=3, random_state=42),
        cv=5
    )
    stacking.fit(X_train_scaled, y_train)
    y_pred = stacking.predict(X_test_scaled)
    r2, rmse, mae, mape = evaluate(y_test, y_pred)
    ensemble_results['Stacking_GB'] = {'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape}
    print(f"Stack(Ridge+KNN+RF)->GB: R²={r2:.4f}, RMSE=€{rmse:,.0f}, MAE=€{mae:,.0f}")
    
    if HAS_XGBOOST:
        stacking2 = StackingRegressor(
            estimators=stack_estimators,
            final_estimator=xgb.XGBRegressor(n_estimators=50, max_depth=4, learning_rate=0.1, random_state=42),
            cv=5
        )
        stacking2.fit(X_train_scaled, y_train)
        y_pred = stacking2.predict(X_test_scaled)
        r2, rmse, mae, mape = evaluate(y_test, y_pred)
        ensemble_results['Stacking_XGB'] = {'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape}
        print(f"Stack(Ridge+KNN+RF)->XGB:R²={r2:.4f}, RMSE=€{rmse:,.0f}, MAE=€{mae:,.0f}")
    
    # 5. Bagging
    print("\n--- Bagging ---")
    bagging_gb = BaggingRegressor(
        estimator=GradientBoostingRegressor(n_estimators=50, max_depth=4, random_state=42),
        n_estimators=10,
        random_state=42,
        n_jobs=-1
    )
    bagging_gb.fit(X_train_scaled, y_train)
    y_pred = bagging_gb.predict(X_test_scaled)
    r2, rmse, mae, mape = evaluate(y_test, y_pred)
    ensemble_results['Bagging_GB'] = {'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape}
    print(f"Bagging(GB x10):         R²={r2:.4f}, RMSE=€{rmse:,.0f}, MAE=€{mae:,.0f}")
    
    if HAS_XGBOOST:
        bagging_xgb = BaggingRegressor(
            estimator=xgb.XGBRegressor(n_estimators=50, max_depth=5, learning_rate=0.1, random_state=42),
            n_estimators=10,
            random_state=42,
            n_jobs=-1
        )
        bagging_xgb.fit(X_train_scaled, y_train)
        y_pred = bagging_xgb.predict(X_test_scaled)
        r2, rmse, mae, mape = evaluate(y_test, y_pred)
        ensemble_results['Bagging_XGB'] = {'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape}
        print(f"Bagging(XGB x10):        R²={r2:.4f}, RMSE=€{rmse:,.0f}, MAE=€{mae:,.0f}")
    
    # 6. AdaBoost
    print("\n--- AdaBoost ---")
    ada = AdaBoostRegressor(
        estimator=Ridge(alpha=1.0),
        n_estimators=50,
        random_state=42
    )
    ada.fit(X_train_scaled, y_train)
    y_pred = ada.predict(X_test_scaled)
    r2, rmse, mae, mape = evaluate(y_test, y_pred)
    ensemble_results['AdaBoost'] = {'r2': r2, 'rmse': rmse, 'mae': mae, 'mape': mape}
    print(f"AdaBoost(Ridge x50):     R²={r2:.4f}, RMSE=€{rmse:,.0f}, MAE=€{mae:,.0f}")
    
    # ==================== SUMMARY ====================
    print("\n" + "="*80)
    print("FINAL RANKING (All Methods)")
    print("="*80)
    
    all_results = {**base_results, **ensemble_results}
    sorted_results = sorted(all_results.items(), key=lambda x: x[1]['r2'], reverse=True)
    
    print(f"\n{'Rank':<5} {'Model':<25} {'R²':>8} {'RMSE':>12} {'MAE':>12} {'MAPE':>8}")
    print("-"*75)
    
    for i, (name, metrics) in enumerate(sorted_results[:15], 1):
        marker = "🏆" if i == 1 else "⭐" if i <= 3 else "  "
        print(f"{marker}{i:<4} {name:<25} {metrics['r2']:>8.4f} €{metrics['rmse']:>10,.0f} €{metrics['mae']:>10,.0f} {metrics['mape']:>7.1f}%")
    
    # Best ensemble vs best single
    best_single = max(base_results.items(), key=lambda x: x[1]['r2'])
    best_ensemble = max(ensemble_results.items(), key=lambda x: x[1]['r2'])
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print(f"\n🔹 Best Single Model:   {best_single[0]} (R²={best_single[1]['r2']:.4f})")
    print(f"🔹 Best Ensemble:       {best_ensemble[0]} (R²={best_ensemble[1]['r2']:.4f})")
    
    improvement = (best_ensemble[1]['r2'] - best_single[1]['r2']) / best_single[1]['r2'] * 100
    rmse_reduction = (best_single[1]['rmse'] - best_ensemble[1]['rmse']) / best_single[1]['rmse'] * 100
    
    if best_ensemble[1]['r2'] > best_single[1]['r2']:
        print(f"\n✅ Ensemble improves R² by {improvement:.2f}%")
        print(f"✅ RMSE reduced by {rmse_reduction:.1f}%")
    else:
        print(f"\n⚠️  Single model outperforms ensemble (no improvement)")
    
    # Overall best
    best_overall = sorted_results[0]
    print(f"\n🏆 RECOMMENDED: {best_overall[0]}")
    print(f"   R²={best_overall[1]['r2']:.4f}, RMSE=€{best_overall[1]['rmse']:,.0f}, MAPE={best_overall[1]['mape']:.1f}%")

if __name__ == "__main__":
    main()

