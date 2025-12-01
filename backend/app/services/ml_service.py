"""
Machine Learning service for real estate price prediction and analysis.
Supports Linear Regression, KNN, XGBoost, and Decision Trees.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Any, Literal
from dataclasses import dataclass
from enum import Enum

from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet, BayesianRidge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


class ModelType(str, Enum):
    # Linear models
    LINEAR_REGRESSION = "linear_regression"
    RIDGE = "ridge"                    # L2 regularization - prevents overfitting
    LASSO = "lasso"                    # L1 regularization - feature selection
    ELASTIC_NET = "elastic_net"        # L1 + L2 combined
    BAYESIAN_RIDGE = "bayesian_ridge"  # Probabilistic, uncertainty estimation
    
    # Tree-based models
    DECISION_TREE = "decision_tree"
    RANDOM_FOREST = "random_forest"    # Ensemble of trees
    GRADIENT_BOOSTING = "gradient_boosting"
    XGBOOST = "xgboost"
    
    # Other models
    KNN = "knn"
    SVR = "svr"                        # Support Vector Regression
    MLP = "mlp"                        # Multi-Layer Perceptron (Neural Network)


@dataclass
class ModelResult:
    """Result from model training/prediction."""
    model_type: str
    r2_score: float
    rmse: float
    mae: float
    cv_scores: List[float]
    cv_mean: float
    cv_std: float
    feature_importance: Optional[Dict[str, float]] = None
    coefficients: Optional[Dict[str, float]] = None
    predictions: Optional[List[float]] = None
    actual: Optional[List[float]] = None


@dataclass
class CorrelationResult:
    """Correlation matrix result."""
    correlation_matrix: Dict[str, Dict[str, float]]
    target_correlations: Dict[str, float]
    feature_names: List[str]


class MLService:
    """Machine Learning service for real estate analysis.
    
    Feature Selection based on correlation analysis:
    - living_area_m2:      0.86 (strongest predictor)
    - bathroom_count:      0.76  
    - outdoor_area_m2:     0.76 (premium properties)
    - bedroom_count:       0.65
    - has_garage:          0.47 (derived binary)
    - is_new_construction: 0.33
    - location_district: categorical (one-hot encoded)
    
    Removed (too many UNKNOWN values or redundant):
    - year_built (redundant with is_new_construction)
    - heating_system / energy_class (too many UNKNOWN)
    """
    
    # Core numeric features (correlation > 0.4)
    NUMERIC_FEATURES = [
        'living_area_m2',    # 0.86 - strongest predictor
        'bedroom_count',     # 0.65
        'bathroom_count',    # 0.76
        'outdoor_area_m2',   # 0.76 - premium properties
    ]
    
    # Derived binary features (created from categoricals)
    DERIVED_FEATURES = [
        'has_garage',        # 0.47 - parking_type == 'GARAGE'
    ]
    
    # Categorical features for one-hot encoding (cleaned location data)
    CATEGORICAL_FEATURES = [
        'location_district',  # Neighborhoods in Varaždin area
    ]
    
    # Boolean feature (already 0/1)
    BOOLEAN_FEATURES = [
        'is_new_construction',  # 0.402
    ]
    
    TARGET = 'price_eur'
    
    def __init__(self):
        self.preprocessor: Optional[ColumnTransformer] = None
        self.models: Dict[ModelType, Any] = {}
        self.feature_names_out: List[str] = []
        
    def _prepare_dataframe(self, listings: List[Dict]) -> pd.DataFrame:
        """Convert listings to DataFrame and create derived features."""
        df = pd.DataFrame(listings)
        
        # Convert numeric columns
        numeric_cols = self.NUMERIC_FEATURES + [self.TARGET]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert boolean
        if 'is_new_construction' in df.columns:
            df['is_new_construction'] = df['is_new_construction'].fillna(False).astype(float)
        
        # Create derived binary features (better than raw categoricals)
        # has_garage: parking_type == 'GARAGE' (correlation: 0.536)
        if 'parking_type' in df.columns:
            df['has_garage'] = (df['parking_type'] == 'GARAGE').astype(float)
        else:
            df['has_garage'] = 0.0
        
        return df
    
    def _get_all_feature_columns(self) -> List[str]:
        """Get all feature columns used for modeling."""
        return self.NUMERIC_FEATURES + self.DERIVED_FEATURES + self.BOOLEAN_FEATURES
    
    def _prepare_features(self, df: pd.DataFrame, fit: bool = True) -> tuple:
        """Prepare features and target for modeling."""
        # Filter rows with valid target
        df_valid = df[df[self.TARGET].notna()].copy()
        
        # Get available columns
        available_numeric = [c for c in self.NUMERIC_FEATURES if c in df_valid.columns]
        available_derived = [c for c in self.DERIVED_FEATURES if c in df_valid.columns]
        available_categorical = [c for c in self.CATEGORICAL_FEATURES if c in df_valid.columns]
        available_boolean = [c for c in self.BOOLEAN_FEATURES if c in df_valid.columns]
        
        # Fill NaN in numeric features with median
        for col in available_numeric:
            if df_valid[col].isna().any():
                df_valid[col] = df_valid[col].fillna(df_valid[col].median())
        
        # Fill NaN in derived/boolean features with 0
        for col in available_derived + available_boolean:
            if df_valid[col].isna().any():
                df_valid[col] = df_valid[col].fillna(0)
        
        # Fill NaN in categorical features with 'Unknown'
        for col in available_categorical:
            if df_valid[col].isna().any():
                df_valid[col] = df_valid[col].fillna('Unknown')
            df_valid[col] = df_valid[col].astype(str)
        
        # Combine all features
        all_features = available_numeric + available_derived + available_categorical + available_boolean
        X_df = df_valid[all_features]
        y = df_valid[self.TARGET].values
        
        if fit:
            # Create preprocessor
            transformers = []
            
            # Numeric features: StandardScaler
            if available_numeric:
                transformers.append(('num', StandardScaler(), available_numeric))
            
            # Derived binary features: passthrough (already 0/1)
            if available_derived:
                transformers.append(('derived', 'passthrough', available_derived))
            
            # Categorical features: OneHotEncoder
            if available_categorical:
                transformers.append(('cat', OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore'), available_categorical))
            
            # Boolean features: passthrough (already 0/1)
            if available_boolean:
                transformers.append(('bool', 'passthrough', available_boolean))
            
            self.preprocessor = ColumnTransformer(transformers, remainder='drop')
            X = self.preprocessor.fit_transform(X_df)
            
            # Get feature names for interpretability
            self.feature_names_out = available_numeric + available_derived
            if available_categorical and hasattr(self.preprocessor.named_transformers_.get('cat', None), 'get_feature_names_out'):
                cat_features = self.preprocessor.named_transformers_['cat'].get_feature_names_out(available_categorical)
                self.feature_names_out.extend(cat_features)
            self.feature_names_out.extend(available_boolean)
        else:
            X = self.preprocessor.transform(X_df)
        
        return X, y, self.feature_names_out, df_valid
    
    def get_model(self, model_type: ModelType, **kwargs) -> Any:
        """Get or create a model instance."""
        
        # === Linear Models ===
        if model_type == ModelType.LINEAR_REGRESSION:
            return LinearRegression()
        
        elif model_type == ModelType.RIDGE:
            # L2 regularization - good for preventing overfitting
            alpha = kwargs.get('alpha', 1.0)
            return Ridge(alpha=alpha, random_state=42)
        
        elif model_type == ModelType.LASSO:
            # L1 regularization - automatic feature selection
            alpha = kwargs.get('alpha', 1.0)
            return Lasso(alpha=alpha, random_state=42, max_iter=10000)
        
        elif model_type == ModelType.ELASTIC_NET:
            # L1 + L2 combined
            alpha = kwargs.get('alpha', 1.0)
            l1_ratio = kwargs.get('l1_ratio', 0.5)  # 0.5 = equal mix
            return ElasticNet(alpha=alpha, l1_ratio=l1_ratio, random_state=42, max_iter=10000)
        
        elif model_type == ModelType.BAYESIAN_RIDGE:
            # Probabilistic approach - provides uncertainty estimates
            return BayesianRidge()
        
        # === Tree-based Models ===
        elif model_type == ModelType.DECISION_TREE:
            max_depth = kwargs.get('max_depth', 10)
            return DecisionTreeRegressor(max_depth=max_depth, random_state=42)
        
        elif model_type == ModelType.RANDOM_FOREST:
            # Ensemble of decision trees - robust, handles non-linearity
            n_estimators = kwargs.get('n_estimators', 100)
            max_depth = kwargs.get('max_depth', 10)
            return RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=42,
                n_jobs=-1  # Use all CPU cores
            )
        
        elif model_type == ModelType.GRADIENT_BOOSTING:
            return GradientBoostingRegressor(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 6),
                learning_rate=kwargs.get('learning_rate', 0.1),
                random_state=42
            )
        
        elif model_type == ModelType.XGBOOST:
            if HAS_XGBOOST:
                return xgb.XGBRegressor(
                    n_estimators=kwargs.get('n_estimators', 100),
                    max_depth=kwargs.get('max_depth', 6),
                    learning_rate=kwargs.get('learning_rate', 0.1),
                    random_state=42
                )
            else:
                # Fallback to GradientBoosting
                return GradientBoostingRegressor(
                    n_estimators=kwargs.get('n_estimators', 100),
                    max_depth=kwargs.get('max_depth', 6),
                    learning_rate=kwargs.get('learning_rate', 0.1),
                    random_state=42
                )
        
        # === Other Models ===
        elif model_type == ModelType.KNN:
            n_neighbors = kwargs.get('n_neighbors', 5)
            return KNeighborsRegressor(n_neighbors=n_neighbors)
        
        elif model_type == ModelType.SVR:
            # Support Vector Regression - good for small datasets
            C = kwargs.get('C', 1.0)
            kernel = kwargs.get('kernel', 'rbf')
            return SVR(C=C, kernel=kernel)
        
        elif model_type == ModelType.MLP:
            # Multi-Layer Perceptron (Neural Network)
            hidden_layers = kwargs.get('hidden_layers', (100, 50))  # Two hidden layers
            activation = kwargs.get('activation', 'relu')  # relu, tanh, logistic
            learning_rate_init = kwargs.get('learning_rate_init', 0.001)
            max_iter = kwargs.get('max_iter', 500)
            early_stopping = kwargs.get('early_stopping', True)
            
            return MLPRegressor(
                hidden_layer_sizes=hidden_layers,
                activation=activation,
                solver='adam',
                learning_rate='adaptive',
                learning_rate_init=learning_rate_init,
                max_iter=max_iter,
                early_stopping=early_stopping,
                validation_fraction=0.1,
                n_iter_no_change=20,
                random_state=42,
            )
        
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def train_and_evaluate(
        self, 
        listings: List[Dict],
        model_type: ModelType,
        test_size: float = 0.2,
        cv_folds: int = 5,
        **model_kwargs
    ) -> ModelResult:
        """
        Train a model and evaluate its performance.
        
        Args:
            listings: List of listing dictionaries from database
            model_type: Type of model to train
            test_size: Proportion of data for testing
            cv_folds: Number of cross-validation folds
            **model_kwargs: Additional model parameters
            
        Returns:
            ModelResult with evaluation metrics
        """
        # Prepare data
        df = self._prepare_dataframe(listings)
        X, y, feature_cols, df_valid = self._prepare_features(df, fit=True)
        
        if len(X) < 10:
            raise ValueError(f"Not enough data for training. Got {len(X)} samples, need at least 10.")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Get model
        model = self.get_model(model_type, **model_kwargs)
        
        # Train
        model.fit(X_train, y_train)
        self.models[model_type] = model
        
        # Predict
        y_pred = model.predict(X_test)
        
        # Evaluate
        r2 = r2_score(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        
        # Cross-validation
        cv_scores = cross_val_score(model, X, y, cv=min(cv_folds, len(X) // 2), scoring='r2')
        
        # Feature importance (for tree-based models)
        feature_importance = None
        coefficients = None
        
        if hasattr(model, 'feature_importances_'):
            feature_importance = {
                col: float(imp) 
                for col, imp in zip(feature_cols, model.feature_importances_)
            }
        elif hasattr(model, 'coef_'):
            coefficients = {
                col: float(coef) 
                for col, coef in zip(feature_cols, model.coef_)
            }
        
        return ModelResult(
            model_type=model_type.value,
            r2_score=float(r2),
            rmse=float(rmse),
            mae=float(mae),
            cv_scores=[float(s) for s in cv_scores],
            cv_mean=float(cv_scores.mean()),
            cv_std=float(cv_scores.std()),
            feature_importance=feature_importance,
            coefficients=coefficients,
            predictions=[float(p) for p in y_pred[:20]],  # First 20 predictions
            actual=[float(a) for a in y_test[:20]]  # First 20 actual values
        )
    
    def calculate_correlation_matrix(self, listings: List[Dict]) -> CorrelationResult:
        """
        Calculate correlation matrix with price as target.
        Uses numeric, derived binary, and boolean features.
        (Excludes categorical features since correlation doesn't apply)
        
        Args:
            listings: List of listing dictionaries
            
        Returns:
            CorrelationResult with correlation data
        """
        df = self._prepare_dataframe(listings)
        
        # Use numeric, derived, and boolean features for correlation (not categorical)
        corr_cols = [self.TARGET] + self.NUMERIC_FEATURES + self.DERIVED_FEATURES + self.BOOLEAN_FEATURES
        available_cols = [c for c in corr_cols if c in df.columns]
        
        # Filter valid data
        df_corr = df[available_cols].dropna()
        
        # Calculate correlation matrix
        corr_matrix = df_corr.corr()
        
        # Convert to dict format
        corr_dict = {}
        for col in corr_matrix.columns:
            corr_dict[col] = {
                other_col: float(corr_matrix.loc[col, other_col])
                for other_col in corr_matrix.columns
            }
        
        # Get correlations with target
        target_corr = {
            col: float(corr_matrix.loc[self.TARGET, col])
            for col in corr_matrix.columns
            if col != self.TARGET
        }
        
        # Sort by absolute correlation
        target_corr = dict(sorted(
            target_corr.items(), 
            key=lambda x: abs(x[1]), 
            reverse=True
        ))
        
        return CorrelationResult(
            correlation_matrix=corr_dict,
            target_correlations=target_corr,
            feature_names=list(corr_matrix.columns)
        )
    
    def predict(
        self, 
        model_type: ModelType,
        features: Dict[str, Any]
    ) -> float:
        """
        Make a prediction using a trained model.
        
        Args:
            model_type: Type of model to use
            features: Feature dictionary (can include raw categoricals or derived binaries)
            
        Returns:
            Predicted price
        """
        if model_type not in self.models:
            raise ValueError(f"Model {model_type.value} not trained yet")
        
        if self.preprocessor is None:
            raise ValueError("Preprocessor not fitted. Train a model first.")
        
        model = self.models[model_type]
        
        # Build input data
        input_data = {}
        
        # Numeric features
        for col in self.NUMERIC_FEATURES:
            input_data[col] = [features.get(col, 0) or 0]
        
        # Derived binary features - compute from raw categoricals if provided
        # has_garage
        if 'has_garage' in features:
            input_data['has_garage'] = [float(features.get('has_garage', 0))]
        elif 'parking_type' in features:
            input_data['has_garage'] = [1.0 if features.get('parking_type') == 'GARAGE' else 0.0]
        else:
            input_data['has_garage'] = [0.0]
        
        # Categorical features (will be one-hot encoded by preprocessor)
        for col in self.CATEGORICAL_FEATURES:
            input_data[col] = [str(features.get(col, 'Unknown') or 'Unknown')]
        
        # Boolean features
        for col in self.BOOLEAN_FEATURES:
            input_data[col] = [float(features.get(col, 0) or 0)]
        
        X_df = pd.DataFrame(input_data)
        X = self.preprocessor.transform(X_df)
        prediction = model.predict(X)[0]
        
        return float(prediction)
    
    def get_stats(self, listings: List[Dict]) -> Dict[str, Any]:
        """Get summary statistics for listings."""
        df = self._prepare_dataframe(listings)
        
        stats = {
            'total_count': len(df),
            'avg_price': float(df[self.TARGET].mean()) if self.TARGET in df.columns else 0,
            'median_price': float(df[self.TARGET].median()) if self.TARGET in df.columns else 0,
            'min_price': float(df[self.TARGET].min()) if self.TARGET in df.columns else 0,
            'max_price': float(df[self.TARGET].max()) if self.TARGET in df.columns else 0,
            'avg_area': float(df['living_area_m2'].mean()) if 'living_area_m2' in df.columns else 0,
            'median_area': float(df['living_area_m2'].median()) if 'living_area_m2' in df.columns else 0,
            'avg_bedrooms': float(df['bedroom_count'].mean()) if 'bedroom_count' in df.columns else 0,
            'cities': df['location_city'].dropna().unique().tolist() if 'location_city' in df.columns else [],
            'city_counts': df['location_city'].value_counts().to_dict() if 'location_city' in df.columns else {},
            'construction_phase_counts': df['construction_phase'].value_counts().to_dict() if 'construction_phase' in df.columns else {},
            'new_construction_pct': float(df['is_new_construction'].mean() * 100) if 'is_new_construction' in df.columns else 0,
        }
        
        # Handle NaN values
        for key, value in stats.items():
            if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                stats[key] = 0
        
        return stats


# Singleton instance
_ml_service: Optional[MLService] = None


def get_ml_service() -> MLService:
    """Get or create ML service singleton."""
    global _ml_service
    if _ml_service is None:
        _ml_service = MLService()
    return _ml_service

