"""
Machine Learning service for real estate price prediction and analysis.
Supports Linear Regression, KNN, XGBoost, and Decision Trees.

Updated for listings_v2 with renovation_level, distance_from_center, and building_type.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Any, Literal
from dataclasses import dataclass
from enum import Enum

from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet, BayesianRidge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, ExtraTreesRegressor
from sklearn.svm import SVR, NuSVR
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

try:
    from catboost import CatBoostRegressor
    HAS_CATBOOST = True
except ImportError:
    HAS_CATBOOST = False


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
    EXTRA_TREES = "extra_trees"        # Extremely Randomized Trees
    CATBOOST = "catboost"              # CatBoost - handles categoricals well
    
    # Other models
    KNN = "knn"
    SVR = "svr"                        # Support Vector Regression
    NU_SVR = "nu_svr"                  # Nu-Support Vector Regression
    MLP = "mlp"                        # Multi-Layer Perceptron (Neural Network)
    
    # Auto-selection (picks best model based on data segment)
    AUTO = "auto"


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
    
    Feature Selection for listings_v2:
    - living_area_m2:       Strong predictor (size matters most)
    - bedroom_count:        Number of bedrooms
    - bathroom_count:       Bathrooms add value
    - outdoor_area_m2:      Terrace/balcony premium
    - renovation_level:     1-10 condition score (NEW in v2)
    - distance_from_center: km from city center (NEW in v2)
    - is_house:            Derived from building_type (NEW in v2)
    - has_garage:          Derived from parking_type
    - is_new_construction: New build premium
    - is_furnished:        Interior arranged/furnished (NEW in v2)
    - has_cellar:          Includes cellar/storage (NEW in v2)
    - location_district:   Categorical (one-hot encoded)
    """
    
    # Core numeric features
    NUMERIC_FEATURES = [
        'living_area_m2',       # Size - strongest predictor
        'bedroom_count',        # Room count
        'bathroom_count',       # Bathroom count
        'outdoor_area_m2',      # Outdoor space premium
        'renovation_level',     # 1-10 condition score (NEW)
        'distance_from_center', # Distance from city center in km (NEW)
    ]
    
    # Derived binary features (created from categoricals/enums)
    DERIVED_FEATURES = [
        'has_garage',           # parking_type == 'GARAGE'
        'is_house',             # building_type == 'HOUSE' (NEW)
        'is_furnished',         # interior_arranged == True (NEW)
        'has_cellar',           # has_cellar == True (NEW)
    ]
    
    # Categorical features for one-hot encoding
    CATEGORICAL_FEATURES = [
        'location_district',    # Neighborhoods
    ]
    
    # Boolean feature (already 0/1)
    BOOLEAN_FEATURES = [
        'is_new_construction',  # New build premium
    ]
    
    # Optimal features from empirical testing (R²=91.77%, RMSE=€29,856)
    # These 4 features give the best performance after deduplication & outlier removal
    OPTIMAL_FEATURES = [
        'living_area_m2',       # Size - strongest predictor
        'bedroom_count',        # Room count
        'distance_from_center', # Location factor
        'is_new_construction',  # New vs resale
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
        
        # Fill missing outdoor_area_m2 with 0 (no balcony/terrace)
        if 'outdoor_area_m2' in df.columns:
            df['outdoor_area_m2'] = df['outdoor_area_m2'].fillna(0)
        
        # Convert boolean
        if 'is_new_construction' in df.columns:
            df['is_new_construction'] = df['is_new_construction'].fillna(False).infer_objects(copy=False)
            df['is_new_construction'] = df['is_new_construction'].astype(float)
        
        # Create derived binary features
        
        # has_garage: parking_type == 'GARAGE'
        if 'parking_type' in df.columns:
            df['has_garage'] = (df['parking_type'] == 'GARAGE').astype(float)
        else:
            df['has_garage'] = 0.0
        
        # is_house: building_type == 'HOUSE' (NEW in v2)
        if 'building_type' in df.columns:
            df['is_house'] = (df['building_type'] == 'HOUSE').astype(float)
        else:
            df['is_house'] = 0.0
        
        # is_furnished: interior_arranged == True (NEW in v2)
        if 'interior_arranged' in df.columns:
            df['is_furnished'] = df['interior_arranged'].fillna(False).infer_objects(copy=False).astype(float)
        else:
            df['is_furnished'] = 0.0
        
        # has_cellar: directly from database (NEW in v2)
        if 'has_cellar' in df.columns:
            df['has_cellar'] = df['has_cellar'].fillna(False).infer_objects(copy=False).astype(float)
        else:
            df['has_cellar'] = 0.0
        
        return df
    
    def _get_all_feature_columns(self) -> List[str]:
        """Get all feature columns used for modeling."""
        return self.NUMERIC_FEATURES + self.DERIVED_FEATURES + self.BOOLEAN_FEATURES
    
    def _get_feature_set_config(self, feature_set: str) -> Dict[str, List[str]]:
        """Get feature configuration for a given feature set."""
        from ..models.ml import FEATURE_SET_DEFINITIONS, FeatureSet
        
        # Handle "optimal" - the 4 best features from empirical testing
        if feature_set == "optimal":
            return {
                "numeric": self.OPTIMAL_FEATURES,  # living_area_m2, bedroom_count, renovation_level, distance_from_center
                "derived": [],
                "boolean": [],
                "categorical": [],
            }
        
        # Handle predefined feature sets
        if feature_set in [fs.value for fs in FeatureSet]:
            fs_enum = FeatureSet(feature_set)
            if fs_enum in FEATURE_SET_DEFINITIONS:
                return FEATURE_SET_DEFINITIONS[fs_enum]
        
        # Fallback to full features
        return {
            "numeric": self.NUMERIC_FEATURES,
            "derived": self.DERIVED_FEATURES,
            "boolean": self.BOOLEAN_FEATURES,
            "categorical": self.CATEGORICAL_FEATURES,
        }
    
    def _prepare_features(
        self, 
        df: pd.DataFrame, 
        fit: bool = True,
        feature_set: str = "optimal",
        custom_features: Optional[List[str]] = None
    ) -> tuple:
        """
        Prepare features and target for modeling.
        
        Args:
            df: DataFrame with listings
            fit: Whether to fit the preprocessor
            feature_set: Which feature set to use (minimal, core, standard, numeric, full)
            custom_features: Custom list of features (only used when feature_set='custom')
        """
        # Filter rows with valid target
        df_valid = df[df[self.TARGET].notna()].copy()
        
        # Get feature configuration based on feature set
        if feature_set == "custom" and custom_features:
            # Parse custom features into categories
            available_numeric = [f for f in custom_features if f in self.NUMERIC_FEATURES and f in df_valid.columns]
            available_derived = [f for f in custom_features if f in self.DERIVED_FEATURES and f in df_valid.columns]
            available_categorical = [f for f in custom_features if f in self.CATEGORICAL_FEATURES and f in df_valid.columns]
            available_boolean = [f for f in custom_features if f in self.BOOLEAN_FEATURES and f in df_valid.columns]
        else:
            config = self._get_feature_set_config(feature_set)
            available_numeric = [c for c in config["numeric"] if c in df_valid.columns]
            available_derived = [c for c in config["derived"] if c in df_valid.columns]
            available_categorical = [c for c in config["categorical"] if c in df_valid.columns]
            available_boolean = [c for c in config["boolean"] if c in df_valid.columns]
        
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
            # Ensemble of decision trees - R²=91.77% with optimal 4 features
            return RandomForestRegressor(
                n_estimators=kwargs.get('n_estimators', 200),
                max_depth=kwargs.get('max_depth', 10),  # Tuned for optimal features
                min_samples_split=2,
                min_samples_leaf=1,
                random_state=42,
                n_jobs=-1
            )
        
        elif model_type == ModelType.GRADIENT_BOOSTING:
            return GradientBoostingRegressor(
                n_estimators=kwargs.get('n_estimators', 200),
                max_depth=kwargs.get('max_depth', 5),
                learning_rate=kwargs.get('learning_rate', 0.05),
                min_samples_split=5,
                min_samples_leaf=3,
                subsample=0.8,
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
            C = kwargs.get('C', 1.0)  # Standard C for scaled data
            kernel = kwargs.get('kernel', 'rbf')
            return SVR(C=C, kernel=kernel, gamma='scale')
        
        elif model_type == ModelType.NU_SVR:
            # Nu-Support Vector Regression
            C = kwargs.get('C', 1.0)  # Standard C for scaled data
            nu = kwargs.get('nu', 0.5)
            return NuSVR(kernel='rbf', C=C, nu=nu)
        
        elif model_type == ModelType.EXTRA_TREES:
            # Extremely Randomized Trees - best for Varaždin and Used segments
            return ExtraTreesRegressor(
                n_estimators=kwargs.get('n_estimators', 200),
                max_depth=kwargs.get('max_depth', 12),
                min_samples_split=3,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
        
        elif model_type == ModelType.CATBOOST:
            # CatBoost - best for new construction
            if HAS_CATBOOST:
                return CatBoostRegressor(
                    iterations=kwargs.get('iterations', 200),
                    depth=kwargs.get('depth', 8),
                    learning_rate=kwargs.get('learning_rate', 0.1),
                    random_state=42,
                    verbose=0
                )
            else:
                # Fallback to GradientBoosting
                return GradientBoostingRegressor(
                    n_estimators=200,
                    max_depth=8,
                    learning_rate=0.1,
                    random_state=42
                )
        
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
        
        elif model_type == ModelType.AUTO:
            # Auto-select will be handled in train_and_evaluate
            # Return a default model here as fallback
            return NuSVR(kernel='rbf', C=100000, nu=0.5)
        
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def _auto_select_model(self, listings: List[Dict]) -> ModelType:
        """
        Automatically select the best model based on data characteristics.
        
        Selection logic based on comprehensive empirical testing (2024-12):
        - All data (mixed) → RandomForest (R²=91.77% with 4 optimal features)
        - Varaždin district only → ExtraTrees
        - New construction only → RandomForest
        - Used apartments only → ExtraTrees
        """
        if not listings:
            return ModelType.RANDOM_FOREST
        
        df = pd.DataFrame(listings)
        
        # Check district composition
        districts = df['location_district'].dropna().unique() if 'location_district' in df.columns else []
        is_varazdin_only = len(districts) == 1 and 'Varaždin' in districts
        
        # Check construction type composition
        new_count = df['is_new_construction'].sum() if 'is_new_construction' in df.columns else 0
        total = len(df)
        is_new_only = new_count == total
        is_used_only = new_count == 0
        
        # Selection logic - RandomForest works best with new optimal features
        if is_varazdin_only:
            selected = ModelType.EXTRA_TREES
            reason = "Varaždin district"
        elif is_new_only:
            selected = ModelType.RANDOM_FOREST
            reason = "New construction"
        elif is_used_only:
            selected = ModelType.EXTRA_TREES
            reason = "Used apartments"
        else:
            # RandomForest with optimal 4 features achieves R²=91.77%
            selected = ModelType.RANDOM_FOREST
            reason = "Mixed data (R²=91.77% with optimal features)"
        
        print(f"[ML] Auto-selected model: {selected.value} - {reason}")
        return selected
    
    def train_and_evaluate(
        self, 
        listings: List[Dict],
        model_type: ModelType = ModelType.AUTO,
        test_size: float = 0.2,
        cv_folds: int = 5,
        feature_set: str = "optimal",
        custom_features: Optional[List[str]] = None,
        **model_kwargs
    ) -> ModelResult:
        """
        Train a model and evaluate its performance.
        
        Args:
            listings: List of listing dictionaries from database
            model_type: Type of model to train (default: AUTO - automatically selects best)
            test_size: Proportion of data for testing
            cv_folds: Number of cross-validation folds
            feature_set: Feature set to use (minimal, core, standard, numeric, full)
            custom_features: Custom feature list (when feature_set='custom')
            **model_kwargs: Additional model parameters
            
        Returns:
            ModelResult with evaluation metrics
        """
        # Track if AUTO was requested
        was_auto = model_type == ModelType.AUTO
        
        # Auto-select model if requested
        if was_auto:
            model_type = self._auto_select_model(listings)
        
        # Prepare data
        df = self._prepare_dataframe(listings)
        X, y, feature_cols, df_valid = self._prepare_features(
            df, fit=True, feature_set=feature_set, custom_features=custom_features
        )
        
        if len(X) < 10:
            raise ValueError(f"Not enough data for training. Got {len(X)} samples, need at least 10.")
        
        print(f"[ML] Training {model_type.value} with feature_set={feature_set}, {len(feature_cols)} features")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Get model
        model = self.get_model(model_type, **model_kwargs)
        
        # Train
        model.fit(X_train, y_train)
        self.models[model_type] = model
        
        # Also store under AUTO key if that was the original request
        if was_auto:
            self.models[ModelType.AUTO] = model
        
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
        Uses the 5 optimal features from empirical testing for cleaner analysis.
        
        Args:
            listings: List of listing dictionaries
            
        Returns:
            CorrelationResult with correlation data
        """
        df = self._prepare_dataframe(listings)
        
        # Use only the 4 optimal features for cleaner correlation analysis
        corr_cols = [self.TARGET] + self.OPTIMAL_FEATURES
        available_cols = [c for c in corr_cols if c in df.columns]
        
        # Filter valid data - drop rows where target is NaN
        df_corr = df[available_cols].copy()
        df_corr = df_corr[df_corr[self.TARGET].notna()]
        
        # Fill NaN values with column median for numeric columns to avoid correlation NaN
        for col in available_cols:
            if df_corr[col].isna().any():
                median_val = df_corr[col].median()
                if pd.isna(median_val):
                    median_val = 0
                df_corr[col] = df_corr[col].fillna(median_val)
        
        # Calculate correlation matrix
        corr_matrix = df_corr.corr()
        
        # Helper function to safely convert to float, replacing NaN/inf with 0
        def safe_float(val):
            if pd.isna(val) or np.isinf(val):
                return 0.0
            return float(val)
        
        # Convert to dict format, handling NaN values
        corr_dict = {}
        for col in corr_matrix.columns:
            corr_dict[col] = {
                other_col: safe_float(corr_matrix.loc[col, other_col])
                for other_col in corr_matrix.columns
            }
        
        # Get correlations with target
        target_corr = {}
        for col in corr_matrix.columns:
            if col != self.TARGET:
                val = corr_matrix.loc[self.TARGET, col]
                target_corr[col] = safe_float(val)
        
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
        
        # is_house (NEW in v2)
        if 'is_house' in features:
            input_data['is_house'] = [float(features.get('is_house', 0))]
        elif 'building_type' in features:
            input_data['is_house'] = [1.0 if features.get('building_type') == 'HOUSE' else 0.0]
        else:
            input_data['is_house'] = [0.0]
        
        # is_furnished (NEW in v2)
        if 'is_furnished' in features:
            input_data['is_furnished'] = [float(features.get('is_furnished', 0))]
        elif 'interior_arranged' in features:
            input_data['is_furnished'] = [1.0 if features.get('interior_arranged') else 0.0]
        else:
            input_data['is_furnished'] = [0.0]
        
        # has_cellar (NEW in v2)
        if 'has_cellar' in features:
            input_data['has_cellar'] = [1.0 if features.get('has_cellar') else 0.0]
        else:
            input_data['has_cellar'] = [0.0]
        
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
            'avg_renovation_level': float(df['renovation_level'].mean()) if 'renovation_level' in df.columns else 0,
            'avg_distance_from_center': float(df['distance_from_center'].mean()) if 'distance_from_center' in df.columns else 0,
            'cities': df['location_city'].dropna().unique().tolist() if 'location_city' in df.columns else [],
            'city_counts': df['location_city'].value_counts().to_dict() if 'location_city' in df.columns else {},
            'construction_phase_counts': df['construction_phase'].value_counts().to_dict() if 'construction_phase' in df.columns else {},
            'building_type_counts': df['building_type'].value_counts().to_dict() if 'building_type' in df.columns else {},
            'new_construction_pct': float(df['is_new_construction'].mean() * 100) if 'is_new_construction' in df.columns else 0,
            'house_pct': float(df['is_house'].mean() * 100) if 'is_house' in df.columns else 0,
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
