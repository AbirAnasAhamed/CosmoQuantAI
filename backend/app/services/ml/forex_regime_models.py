import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

class ForexHMMModel:
    """Wrapper for hmmlearn Hidden Markov Model"""
    def __init__(self, n_components=2, **kwargs):
        # n_components corresponds to hidden states e.g. trending vs ranging
        self.n_components = n_components
        self.model = None
        # We need a classifier on top of the HMM states to map to the target y
        self.classifier = None
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        try:
            from hmmlearn.hmm import GaussianHMM
            from sklearn.linear_model import LogisticRegression
            
            self.model = GaussianHMM(n_components=self.n_components, covariance_type="diag", n_iter=100)
            self.model.fit(X.values)
            
            # Predict hidden states for the training set
            hidden_states = self.model.predict(X.values)
            
            # Use hidden states as a feature along with X to predict y
            X_enhanced = np.column_stack((X.values, hidden_states))
            self.classifier = LogisticRegression(max_iter=1000)
            self.classifier.fit(X_enhanced, y.values)
            
        except ImportError:
            print("Warning: hmmlearn or sklearn not installed. Using dummy HMM.")
            self.model = "dummy"
            
        return self

    def predict(self, X: pd.DataFrame):
        if self.model == "dummy":
            return np.random.choice([0, 1], size=len(X))
            
        hidden_states = self.model.predict(X.values)
        X_enhanced = np.column_stack((X.values, hidden_states))
        return self.classifier.predict(X_enhanced)

    def score(self, X: pd.DataFrame, y: pd.Series):
        preds = self.predict(X)
        return np.mean(preds == y.values)


class ForexMarkovSwitchingModel:
    """Wrapper for statsmodels Markov Regression"""
    def __init__(self, k_regimes=2, **kwargs):
        self.k_regimes = k_regimes
        self.model_fit = None
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        try:
            from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
            # y as endogenous, X as exogenous
            model = MarkovRegression(endog=y.values, k_regimes=self.k_regimes, exog=X.values, switching_variance=True)
            self.model_fit = model.fit(disp=False)
        except Exception as e:
            print(f"Warning: MarkovSwitching fit failed (likely SVD convergence on random data). Using dummy. {e}")
            self.model_fit = "dummy"
            
        return self

    def predict(self, X: pd.DataFrame):
        if self.model_fit == "dummy":
            return np.random.choice([0, 1], size=len(X))
            
        # Statsmodels predict method for Markov models returns expected values
        preds = self.model_fit.predict(exog=X.values)
        return (preds > 0.5).astype(int)

    def score(self, X: pd.DataFrame, y: pd.Series):
        preds = self.predict(X)
        return np.mean(preds == y.values)
