import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import VotingClassifier, VotingRegressor
from sklearn.metrics import accuracy_score, mean_squared_error

# Add app to path
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from Crypto Layer
from app.services.advanced_ml.moe_model_mapper import FlatCatBoostClassifier as CryptoCatBoostClassifier
from app.services.advanced_ml.moe_model_mapper import FlatCatBoostRegressor as CryptoCatBoostRegressor

# Import from Forex Layer
from app.services.ml.forex_model_factory import FlatCatBoostClassifier as ForexCatBoostClassifier
from app.services.ml.forex_model_factory import FlatCatBoostRegressor as ForexCatBoostRegressor

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_header(msg):
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {msg} ==={Colors.ENDC}")

def log_success(msg):
    print(f"{Colors.OKGREEN}[PASS]{Colors.ENDC} {msg}")

def log_error(msg):
    print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} {msg}")
    sys.exit(1)
    
def generate_datasets():
    # Normal Dataset
    X_normal = np.random.rand(100, 5)
    y_cls = np.random.choice([0, 1, 2], size=100, p=[0.2, 0.5, 0.3]) # Imbalanced prior
    y_reg = np.random.rand(100) * 10
    
    # Zero Variance Dataset (Constant Features)
    X_zero = np.ones((100, 5)) * 42.0
    
    return X_normal, X_zero, y_cls, y_reg

def test_layer(layer_name, ClsModel, RegModel):
    log_header(f"Testing {layer_name} Layer Fallback Mechanisms")
    
    X_normal, X_zero, y_cls, y_reg = generate_datasets()
    
    # ---------------------------------------------------------
    # TEST 1: Normal Classification (Should NOT trigger fallback)
    # ---------------------------------------------------------
    try:
        clf_normal = ClsModel(iterations=5, verbose=0)
        clf_normal.fit(X_normal, y_cls)
        if getattr(clf_normal, '_fallback_model', None) is not None:
            log_error("Model fell back to Dummy on NORMAL data!")
        preds = clf_normal.predict(X_normal)
        if len(preds.shape) > 1:
            log_error(f"Predict returned 2D shape: {preds.shape}. Expected 1D (N,)")
        log_success("Test 1 (Normal Data Classification): Model trained natively, predict shape flattened to 1D.")
    except Exception as e:
        log_error(f"Test 1 Failed: {e}")

    # ---------------------------------------------------------
    # TEST 2: Zero Variance Classification (MUST trigger fallback)
    # ---------------------------------------------------------
    try:
        clf_zero = ClsModel(iterations=5, verbose=0)
        clf_zero.fit(X_zero, y_cls)
        
        if getattr(clf_zero, '_fallback_model', None) is None:
            log_error("Model FAILED to fall back to Dummy on ZERO VARIANCE data!")
            
        # Prior of y_cls -> class 1 is majority (~50%)
        expected_class = int(pd.Series(y_cls).mode()[0])
        preds = clf_zero.predict(X_zero[:10])
        
        if not np.all(preds == expected_class):
            log_error(f"Fallback model did not predict majority class. Expected {expected_class}, got {preds}")
            
        probs = clf_zero.predict_proba(X_zero[:10])
        if probs.shape != (10, 3):
            log_error(f"Fallback predict_proba shape incorrect: {probs.shape}")
            
        log_success(f"Test 2 (Zero Variance Classification): Graceful fallback to DummyClassifier. Predicts prior class ({expected_class}) perfectly.")
    except Exception as e:
        log_error(f"Test 2 Failed: {e}")
        
    # ---------------------------------------------------------
    # TEST 3: Zero Variance Regression (MUST trigger fallback)
    # ---------------------------------------------------------
    try:
        reg_zero = RegModel(iterations=5, verbose=0)
        reg_zero.fit(X_zero, y_reg)
        
        if getattr(reg_zero, '_fallback_model', None) is None:
            log_error("Regressor FAILED to fall back to Dummy on ZERO VARIANCE data!")
            
        expected_mean = np.mean(y_reg)
        preds = reg_zero.predict(X_zero[:10])
        
        if not np.allclose(preds, expected_mean):
            log_error(f"Fallback regressor did not predict mean. Expected {expected_mean}, got {preds[0]}")
            
        log_success(f"Test 3 (Zero Variance Regression): Graceful fallback to DummyRegressor. Predicts exact mean ({expected_mean:.4f}).")
    except Exception as e:
        log_error(f"Test 3 Failed: {e}")
        
    # ---------------------------------------------------------
    # TEST 4: VotingClassifier Integration on Zero Variance Data
    # ---------------------------------------------------------
    try:
        from sklearn.ensemble import RandomForestClassifier
        
        ensemble = VotingClassifier(
            estimators=[
                ('rf', RandomForestClassifier(n_estimators=2, max_depth=2, random_state=42)),
                ('cat', ClsModel(iterations=5, verbose=0))
            ],
            voting='soft'
        )
        
        ensemble.fit(X_zero, y_cls)
        preds = ensemble.predict(X_zero[:10])
        
        log_success("Test 4 (VotingClassifier Integration): VotingClassifier successfully trained and predicted on zero-variance data without crashing.")
    except Exception as e:
        log_error(f"Test 4 Failed (Ensemble crashed): {e}")

if __name__ == "__main__":
    print(f"{Colors.OKCYAN}{Colors.BOLD}🚀 Initializing Deep Verification for CatBoost Dummy Fallback Architecture{Colors.ENDC}")
    
    test_layer("Crypto (moe_model_mapper)", CryptoCatBoostClassifier, CryptoCatBoostRegressor)
    test_layer("Forex (forex_model_factory)", ForexCatBoostClassifier, ForexCatBoostRegressor)
    
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}✅ ALL VERIFICATIONS PASSED SUCCESSFULLY! The codebase is 100% Future-Proof.{Colors.ENDC}\n")
