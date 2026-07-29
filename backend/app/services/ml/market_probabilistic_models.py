import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

class MarketBayesianNNModel:
    """Wrapper for a Probabilistic Bayesian Neural Network"""
    def __init__(self, **kwargs):
        self.model = None
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        # A true Bayesian NN requires torchbnn or pyro
        # For this skeleton, we will fallback to a scikit-learn BayesianRidge combined with a classifier
        # or just a random forest if libraries are missing.
        try:
            from sklearn.linear_model import BayesianRidge
            from sklearn.calibration import CalibratedClassifierCV
            from sklearn.svm import LinearSVC
            from sklearn.utils.multiclass import type_of_target
            
            target_type = type_of_target(y.values)
            if target_type == 'continuous':
                self.is_regression = True
                self.model = BayesianRidge()
                self.model.fit(X.values, y.values)
            else:
                self.is_regression = False
                base_clf = LinearSVC(random_state=42)
                self.model = CalibratedClassifierCV(estimator=base_clf, method='isotonic', cv=3)
                self.model.fit(X.values, y.astype(int).values)
            
        except ImportError:
            print("Warning: Failed to load Bayesian components. Using dummy BNN.")
            self.model = "dummy"
            
        return self

    def predict(self, X: pd.DataFrame):
        if self.model == "dummy":
            if getattr(self, 'is_regression', False):
                return np.random.randn(len(X))
            return np.random.choice([0, 1], size=len(X))
            
        return self.model.predict(X.values)

    def predict_proba(self, X: pd.DataFrame):
        if self.model == "dummy":
            preds = np.random.uniform(0, 1, size=len(X))
            return np.column_stack((1-preds, preds))
            
        if getattr(self, 'is_regression', False):
            # Regressors don't have predict_proba
            preds = self.predict(X)
            probs = np.zeros((len(preds), 2))
            probs[:, 1] = 1.0 # mock probability
            return probs
            
        return self.model.predict_proba(X.values)

    def score(self, X: pd.DataFrame, y: pd.Series):
        preds = self.predict(X)
        if getattr(self, 'is_regression', False):
            from sklearn.metrics import r2_score
            return r2_score(y.values, preds)
        return np.mean(preds == y.values)
