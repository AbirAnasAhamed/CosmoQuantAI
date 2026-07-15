import numpy as np
import pandas as pd
import warnings
from typing import Any, Dict

# Disable warnings from statsmodels
warnings.filterwarnings("ignore")

class ForexARIMAModel:
    """Wrapper for statsmodels ARIMA"""
    def __init__(self, order=(5,1,0), **kwargs):
        self.order = order
        self.model_fit = None
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
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

    def score(self, X: pd.DataFrame, y: pd.Series):
        preds = self.predict(X)
        return np.mean(preds == y.values)


class ForexVARModel:
    """Wrapper for Vector AutoRegression (VAR)"""
    def __init__(self, lags=5, **kwargs):
        self.lags = lags
        self.model_fit = None
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        try:
            from statsmodels.tsa.vector_ar.var_model import VAR
            # Combine X and y for VAR since it's multivariate
            df = X.copy()
            df['target_y'] = y
            model = VAR(df)
            self.model_fit = model.fit(self.lags)
            self.train_data = df.values[-self.lags:]
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

    def score(self, X: pd.DataFrame, y: pd.Series):
        preds = self.predict(X)
        return np.mean(preds == y.values)


class ForexNeuralProphetModel:
    """Wrapper for NeuralProphet"""
    def __init__(self, **kwargs):
        self.model = None
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        try:
            from neuralprophet import NeuralProphet
            self.model = NeuralProphet(epochs=10, batch_size=32)
            # NeuralProphet expects a dataframe with 'ds' (datetime) and 'y' (target)
            # Assuming X index is datetime
            df = pd.DataFrame({'ds': X.index, 'y': y.values})
            self.model.fit(df, freq="H")
        except ImportError:
            print("Warning: neuralprophet not installed. Using dummy NeuralProphet.")
            self.model = "dummy"
            
        return self

    def predict(self, X: pd.DataFrame):
        if self.model == "dummy":
            return np.random.choice([0, 1], size=len(X))
            
        df = pd.DataFrame({'ds': X.index, 'y': np.zeros(len(X))})
        forecast = self.model.predict(df)
        return (forecast['yhat1'] > 0.5).astype(int).values

    def score(self, X: pd.DataFrame, y: pd.Series):
        preds = self.predict(X)
        return np.mean(preds == y.values)
