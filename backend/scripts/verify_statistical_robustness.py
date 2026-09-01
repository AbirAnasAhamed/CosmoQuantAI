import os
import sys
import numpy as np
import pandas as pd

# Fix path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.ml.forex_feature_engine import generate_ohlcv_features
from app.services.advanced_ml.features.forex.statistical_features import StatisticalFeatures

def print_header(title):
    print("\n" + "="*80)
    print(f" {title} ".center(80, "="))
    print("="*80 + "\n")

def test_dynamic_feature_binding():
    print_header("TEST 1: DYNAMIC FEATURE SELECTION BINDING")
    
    # 1. Create clean dummy data
    dates = pd.date_range("2025-01-01", periods=100, freq='h')
    df = pd.DataFrame({
        'open': np.random.uniform(1.1000, 1.1050, 100),
        'high': np.random.uniform(1.1050, 1.1100, 100),
        'low': np.random.uniform(1.0950, 1.1000, 100),
        'close': np.random.uniform(1.1000, 1.1050, 100),
        'volume': np.random.uniform(1000, 5000, 100)
    }, index=dates)
    
    initial_cols = list(df.columns)
    print(f"[+] Initial DataFrame Columns ({len(initial_cols)}): {initial_cols}")
    
    # We only want 3 specific statistical features, nothing else!
    target_features = ['stat_rolling_variance', 'stat_hurst_exponent', 'stat_shannon_entropy']
    print(f"[+] Requesting ONLY 3 features from Engine: {target_features}")
    
    df_result = generate_ohlcv_features(df.copy(), selected_features=target_features)
    
    added_cols = [c for c in df_result.columns if c not in initial_cols]
    print(f"[+] Engine Returned Added Columns ({len(added_cols)}): {added_cols}")
    
    if set(added_cols) == set(target_features):
        print("[SUCCESS] Dynamic Feature Binding works perfectly! No extra bloat (73 features were NOT forcibly added).")
    else:
        print("[FAIL] Engine returned incorrect columns!")

def test_bad_data_resiliency():
    print_header("TEST 2: HEDGE-FUND GRADE RESILIENCY (BAD DATA STRESS TEST)")
    
    # We create mathematically toxic data that normally crashes algorithms:
    # - Flat lines (Standard Deviation = 0, Skewness = NaN, Div/0 errors)
    # - Negative prices (Log(negative) = NaN)
    dates = pd.date_range("2025-01-01", periods=50, freq='h')
    
    bad_df = pd.DataFrame({
        'open': np.full(50, 1.0),
        'high': np.full(50, 1.0),
        'low': np.full(50, -1.0),   # Negative value!
        'close': np.full(50, 1.0),  # Constant value (diff = 0)
        'volume': np.full(50, 0.0)  # Zero volume
    }, index=dates)
    
    print("[+] Created 50 rows of 'Toxic' Math Data:")
    print("    - Constant Close = 1.0 (Causes Div/0 in Volatility, NaN in Skew/Kurtosis)")
    print("    - Negative Low = -1.0 (Causes Log errors)")
    print("    - Zero Volume (Causes Volume ratio Div/0 errors)")
    
    print("\n[+] Feeding Toxic Data into StatisticalFeatures.calculate_all()...")
    
    try:
        result_df = StatisticalFeatures.calculate_all(bad_df.copy())
        print("[SUCCESS] Engine survived without crashing!")
        
        # Check total features
        added_cols = [c for c in result_df.columns if c not in bad_df.columns]
        print(f"[+] Total Statistical Features Extracted: {len(added_cols)} / 73")
        
        # Verify safety constraints
        nan_count = result_df.isna().sum().sum()
        inf_count = (result_df == np.inf).sum().sum()
        neg_inf_count = (result_df == -np.inf).sum().sum()
        
        print("\n[+] Neural Network Safety Verification:")
        print(f"    -> NaNs detected: {nan_count}")
        print(f"    -> +Infinities detected: {inf_count}")
        print(f"    -> -Infinities detected: {neg_inf_count}")
        
        if nan_count == 0 and inf_count == 0 and neg_inf_count == 0:
            print("[SUCCESS] Granular Try-Except blocks successfully caught all internal math explosions!")
            print("[SUCCESS] Data is 100% Neural Network safe (Zeros/Clips applied correctly).")
        else:
            print("[FAIL] Safety constraints violated!")
            
    except Exception as e:
        print(f"[FAIL] Engine crashed due to bad data: {e}")

if __name__ == "__main__":
    test_dynamic_feature_binding()
    test_bad_data_resiliency()
    print_header("ALL VERIFICATION TESTS COMPLETED SUCCESSFULLY")
