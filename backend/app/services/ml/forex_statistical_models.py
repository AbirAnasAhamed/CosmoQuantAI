import numpy as np
import pandas as pd
import warnings
from typing import Any, Dict
from sklearn.base import BaseEstimator, ClassifierMixin

# Disable warnings from statsmodels
warnings.filterwarnings("ignore")

# Numpy 2.0 compatibility for NeuralProphet
if not hasattr(np, 'NaN'):
    np.NaN = np.nan

class ForexARIMAModel(BaseEstimator, ClassifierMixin):
    """Wrapper for statsmodels ARIMA"""
    _estimator_type = "classifier"

    def __init__(self, order=(5,1,0), **kwargs):
        self.order = order
        self.model_fit = None
        self.classes_ = np.array([0, 1, 2])
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        # Handle multi-output y (e.g. advanced_setup) by taking the first column (Direction)
        if isinstance(y, np.ndarray) and len(y.shape) > 1 and y.shape[1] > 1:
            y = y[:, 0]
        elif isinstance(y, pd.DataFrame) and len(y.columns) > 1:
            y = y.iloc[:, 0]
            
        try:
            from statsmodels.tsa.arima.model import ARIMA
            # ARIMA is univariate, we fit on the target directly
            # For a true exog model we would pass X as exog
            exog_data = X if (hasattr(X, 'empty') and not X.empty) or (isinstance(X, np.ndarray) and X.size > 0) else None
            model = ARIMA(y, exog=exog_data, order=self.order)
            self.model_fit = model.fit()
        except ImportError:
            print("Warning: statsmodels not installed. Using dummy ARIMA.")
            self.model_fit = "dummy"
            
        return self

    def predict(self, X: pd.DataFrame):
        if self.model_fit == "dummy":
            return np.random.choice([0, 1], size=len(X))
            
        # Statsmodels forecasting with exog
        exog_data = X if (hasattr(X, 'empty') and not X.empty) or (isinstance(X, np.ndarray) and X.size > 0) else None
        predictions = self.model_fit.forecast(steps=len(X), exog=exog_data)
        # Convert continuous predictions back to binary classification (0 or 1)
        # assuming the target y was binary 0/1 for price going up/down
        return (predictions > 0.5).astype(int).values


    def predict_proba(self, X):
        preds = self.predict(X)
        n_classes = len(self.classes_) if hasattr(self, 'classes_') else 3
        probs = __import__('numpy').zeros((len(preds), n_classes))
        for i, p in enumerate(preds):
            if int(p) < n_classes:
                probs[i, int(p)] = 1.0
        return probs

    def score(self, X: pd.DataFrame, y: pd.Series):
        preds = self.predict(X)
        y_vals = getattr(y, 'values', y)
        return np.mean(preds == y_vals)


class ForexVARModel(BaseEstimator, ClassifierMixin):
    """Wrapper for Vector AutoRegression (VAR)"""
    _estimator_type = "classifier"

    def __init__(self, lags=5, **kwargs):
        self.lags = lags
        self.model_fit = None
        self.classes_ = np.array([0, 1, 2])
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        # Handle multi-output y (e.g. advanced_setup) by taking the first column (Direction)
        if isinstance(y, np.ndarray) and len(y.shape) > 1 and y.shape[1] > 1:
            y = y[:, 0]
        elif isinstance(y, pd.DataFrame) and len(y.columns) > 1:
            y = y.iloc[:, 0]
            
        try:
            from statsmodels.tsa.vector_ar.var_model import VAR
            # Combine X and y for VAR since it's multivariate
            df = X.copy() if hasattr(X, 'copy') else pd.DataFrame(X)
            df['target_y'] = y
            model = VAR(df)
            self.model_fit = model.fit(self.lags)
            X_vals = getattr(df, 'values', df)
            self.train_data = X_vals[-self.lags:]
        except ImportError:
            print("Warning: statsmodels not installed. Using dummy VAR.")
            self.model_fit = "dummy"
            
        return self

    def predict(self, X: pd.DataFrame):
        if self.model_fit == "dummy":
            return np.random.choice([0, 1], size=len(X))
            
        predictions = self.model_fit.forecast(y=self.train_data, steps=len(X))
        # target_y is the last column
        target_preds = predictions[:, -1]
        return (target_preds > 0.5).astype(int)


    def predict_proba(self, X):
        preds = self.predict(X)
        n_classes = len(self.classes_) if hasattr(self, 'classes_') else 3
        probs = __import__('numpy').zeros((len(preds), n_classes))
        for i, p in enumerate(preds):
            if int(p) < n_classes:
                probs[i, int(p)] = 1.0
        return probs

    def score(self, X: pd.DataFrame, y: pd.Series):
        preds = self.predict(X)
        y_vals = getattr(y, 'values', y)
        return np.mean(preds == y_vals)


class ForexNeuralProphetModel(BaseEstimator, ClassifierMixin):
    """Wrapper for NeuralProphet"""
    _estimator_type = "classifier"

    def __init__(self, epochs=10, **kwargs):
        self.epochs = epochs
        self.model = None
        self.model_fit = None
        self.classes_ = np.array([0, 1, 2])
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        # Handle multi-output y (e.g. advanced_setup) by taking the first column (Direction)
        if isinstance(y, np.ndarray) and len(y.shape) > 1 and y.shape[1] > 1:
            y = y[:, 0]
        elif isinstance(y, pd.DataFrame) and len(y.columns) > 1:
            y = y.iloc[:, 0]
            
        try:
            import torch
            # PyTorch 2.6+ defaults weights_only=True, which breaks NeuralProphet/PTL checkpoint loading
            if not hasattr(torch, '_patched_load'):
                _original_load = torch.load
                def _patched_load(*args, **kwargs):
                    if 'weights_only' not in kwargs:
                        kwargs['weights_only'] = False
                    return _original_load(*args, **kwargs)
                torch.load = _patched_load
                torch._patched_load = True

            import pytorch_lightning.core.optimizer as opt
            # Bypass PyTorch Lightning 1.7 check that fails with PyTorch 2.0+ LRScheduler
            if hasattr(opt, '_validate_scheduler_api'):
                opt._validate_scheduler_api = lambda *args, **kwargs: None
                
            from neuralprophet import NeuralProphet
            self.model = NeuralProphet(epochs=10, batch_size=32)
            # NeuralProphet expects a dataframe with 'ds' (datetime) and 'y' (target)
            if hasattr(X, 'index') and pd.api.types.is_datetime64_any_dtype(X.index):
                ds = X.index
            else:
                ds = pd.date_range(start='2020-01-01', periods=len(X), freq='H')
                
            y_vals = getattr(y, 'values', y) if hasattr(y, 'values') else y
            df = pd.DataFrame({'ds': ds, 'y': y_vals})
            import multiprocessing
            current_proc = multiprocessing.current_process()
            is_daemon = current_proc.daemon
            current_proc.daemon = False
            try:
                self.model.fit(df, freq="H")
            finally:
                current_proc.daemon = is_daemon
        except ImportError:
            print("Warning: neuralprophet not installed. Using dummy NeuralProphet.")
            self.model = "dummy"
            
        return self

    def predict(self, X: pd.DataFrame):
        if self.model == "dummy":
            return np.random.choice([0, 1], size=len(X))
            
        if pd.api.types.is_datetime64_any_dtype(X.index):
            ds = X.index
        else:
            ds = pd.date_range(start='2020-01-01', periods=max(2, len(X)), freq='h')

        df = pd.DataFrame({'ds': ds, 'y': np.zeros(max(2, len(X)))})
        import multiprocessing
        current_proc = multiprocessing.current_process()
        is_daemon = current_proc.daemon
        current_proc.daemon = False
        try:
            forecast = self.model.predict(df)
        except Exception as e:
            print(f"⚠️ Warning: Statistical model prediction failed: {e}")
            preds = np.zeros(len(X), dtype=int)
            if len(X) == 1 and len(preds) > 1:
                return preds[-1:]
            return preds
        finally:
            current_proc.daemon = is_daemon
        
        preds = (forecast['yhat1'] > 0.5).astype(int).values
        if len(X) == 1 and len(preds) > 1:
            return preds[-1:]
        return preds


    def predict_proba(self, X):
        preds = self.predict(X)
        n_classes = len(self.classes_) if hasattr(self, 'classes_') else 3
        probs = __import__('numpy').zeros((len(preds), n_classes))
        for i, p in enumerate(preds):
            if int(p) < n_classes:
                probs[i, int(p)] = 1.0
        return probs

    def score(self, X: pd.DataFrame, y: pd.Series):
        preds = self.predict(X)
        y_vals = getattr(y, 'values', y)
        return np.mean(preds == y_vals)
