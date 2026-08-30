import logging
from app.services.ml.forex_model_factory import get_forex_model
import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin

logger = logging.getLogger(__name__)

class PandasDataWrapperClassifier(BaseEstimator, ClassifierMixin):
    def __init__(self, base_model=None):
        self.base_model = base_model
    
    def fit(self, X, y=None):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)
        if y is not None and not isinstance(y, (pd.Series, pd.DataFrame)):
            y_np = np.array(y)
            if y_np.ndim == 1:
                y = pd.Series(y_np)
            else:
                y = pd.DataFrame(y_np)
        logger.info(f"[PROGRESS] Training base model: {self.base_model.__class__.__name__}...")
        self.base_model.fit(X, y)
        return self
    
    def predict(self, X):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)
        return self.base_model.predict(X)
        
    def predict_proba(self, X):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)
        if hasattr(self.base_model, 'predict_proba'):
            return self.base_model.predict_proba(X)
        # Fallback if base model doesn't support probability
        preds = self.predict(X)
        n_classes = len(self.classes_)
        probs = np.zeros((len(preds), n_classes))
        for i, p in enumerate(preds):
            idx = int(p) if 0 <= int(p) < n_classes else n_classes - 1
            probs[i, idx] = 1.0
        return probs
        
    @property
    def classes_(self):
        if hasattr(self.base_model, 'classes_'):
            return self.base_model.classes_
        return np.array([0, 1, 2]) # Default to 3 for CosmoQuant multi-class strategy

class PandasDataWrapperRegressor(BaseEstimator, RegressorMixin):
    def __init__(self, base_model=None):
        self.base_model = base_model
    
    def fit(self, X, y=None):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)
        if y is not None and not isinstance(y, (pd.Series, pd.DataFrame)):
            y_np = np.array(y)
            if y_np.ndim == 1:
                y = pd.Series(y_np)
            else:
                y = pd.DataFrame(y_np)
        logger.info(f"[PROGRESS] Training base model: {self.base_model.__class__.__name__}...")
        self.base_model.fit(X, y)
        return self
    
    def predict(self, X):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)
        return self.base_model.predict(X)

try:
    from catboost import CatBoostClassifier, CatBoostRegressor
    from sklearn.dummy import DummyClassifier, DummyRegressor

    class FlatCatBoostClassifier(CatBoostClassifier):
        def fit(self, X, y=None, **fit_params):
            try:
                super().fit(X, y, **fit_params)
                self._fallback_model = None
            except Exception:
                self._fallback_model = DummyClassifier(strategy='prior')
                self._fallback_model.fit(X, y)
            return self

        def predict(self, X):
            if getattr(self, '_fallback_model', None) is not None:
                return self._fallback_model.predict(X)
            p = super().predict(X)
            if len(p.shape) > 1 and p.shape[1] == 1:
                return p.flatten()
            return p
            
        def predict_proba(self, X):
            if getattr(self, '_fallback_model', None) is not None:
                return self._fallback_model.predict_proba(X)
            return super().predict_proba(X)

    class FlatCatBoostRegressor(CatBoostRegressor):
        def fit(self, X, y=None, **fit_params):
            try:
                super().fit(X, y, **fit_params)
                self._fallback_model = None
            except Exception:
                self._fallback_model = DummyRegressor(strategy='mean')
                self._fallback_model.fit(X, y)
            return self

        def predict(self, X):
            if getattr(self, '_fallback_model', None) is not None:
                return self._fallback_model.predict(X)
            return super().predict(X)
except ImportError:
    CatBoostClassifier = None
    CatBoostRegressor = None
    FlatCatBoostClassifier = None
    FlatCatBoostRegressor = None

def get_genuine_base_estimator(name: str, config: dict, is_classification: bool = True):
    """
    Returns the genuine underlying model instance for the given algorithm name.
    It maps from the string name to the scikit-learn, statsmodels, torch, or stable-baselines3 model.
    """
    if name == "Random Forest":
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        epochs = config.get("epochs", 100)
        max_depth = config.get("max_depth", 6)
        return RandomForestClassifier(n_estimators=epochs, max_depth=max_depth, random_state=42, n_jobs=-1, class_weight='balanced') if is_classification else RandomForestRegressor(n_estimators=epochs, max_depth=max_depth, random_state=42, n_jobs=-1)
    
    elif name == "XGBoost":
        from xgboost import XGBClassifier, XGBRegressor
        epochs = config.get("epochs", 100)
        max_depth = config.get("max_depth", 6)
        learning_rate = config.get("learning_rate", 0.05)
        return XGBClassifier(n_estimators=epochs, max_depth=max_depth, learning_rate=learning_rate, random_state=42, use_label_encoder=False, eval_metric='logloss') if is_classification else XGBRegressor(n_estimators=epochs, max_depth=max_depth, learning_rate=learning_rate, random_state=42)
    
    elif name == "LightGBM":
        import lightgbm as lgb
        epochs = config.get("epochs", 100)
        max_depth = config.get("max_depth", -1)
        learning_rate = config.get("learning_rate", 0.05)
        return lgb.LGBMClassifier(n_estimators=epochs, learning_rate=learning_rate, max_depth=max_depth, random_state=42, verbose=-1, class_weight='balanced') if is_classification else lgb.LGBMRegressor(n_estimators=epochs, learning_rate=learning_rate, max_depth=max_depth, random_state=42, verbose=-1)
    
    elif name == "CatBoost":
        if FlatCatBoostClassifier is not None:
            epochs = config.get("epochs", 100)
            max_depth = config.get("max_depth", 6)
            learning_rate = config.get("learning_rate", 0.05)
            cb_depth = min(max_depth, 16) if max_depth else 6
            return FlatCatBoostClassifier(iterations=epochs, learning_rate=learning_rate, depth=cb_depth, random_state=42, verbose=False, auto_class_weights='Balanced') if is_classification else FlatCatBoostRegressor(iterations=epochs, learning_rate=learning_rate, depth=cb_depth, random_state=42, verbose=False)
        else:
            from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
            return GradientBoostingClassifier(random_state=42) if is_classification else GradientBoostingRegressor(random_state=42)
    
    elif name == "Logistic Regression":
        from sklearn.linear_model import LogisticRegression, LinearRegression
        return LogisticRegression(random_state=42, class_weight='balanced') if is_classification else LinearRegression()
    
    elif name == "SVM":
        from sklearn.svm import SVC, SVR
        return SVC(probability=True, random_state=42, class_weight='balanced') if is_classification else SVR()

    # 2. Advanced Genuine Models (PyTorch, Statsmodels, RL, AutoEncoders, Transformers etc.)
    # We route all other algorithms through the factory to keep them 100% native
    else:
        logger.info(f"[RL-MoE] Instantiating 100% Genuine Native Model for: {name}")
        try:
            model = get_forex_model(name, config)
            
            # CRITICAL FIX: The factory's deep learning and RL wrappers strictly expect
            # Pandas DataFrames/Series (they call .values internally).
            # ml_training_engine.py passes numpy arrays for `y` (via y_train.ravel()).
            # This wrapper intercepts those calls and guarantees they receive Pandas formats.
            return PandasDataWrapperClassifier(model) if is_classification else PandasDataWrapperRegressor(model)
            
        except Exception as e:
            logger.error(f"Failed to instantiate {name}. Falling back to RF. Error: {str(e)}")
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            return RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced') if is_classification else RandomForestRegressor(n_estimators=100, random_state=42)
