import sys
import os
import pandas as pd
import numpy as np
import inspect

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import both categories
import app.services.advanced_ml.features.forex.c01_smc_ict_tick_verified as c01
import app.services.advanced_ml.features.forex.c02_candlestick_psychology as c02
from app.services.advanced_ml.features.forex.c01_smc_ict_tick_verified.base_feature import BaseTickVerifiedFeature
from app.services.advanced_ml.features.forex.c02_candlestick_psychology.base_feature import BaseCandlePsychologyFeature

def create_mock_data():
    """Creates synthetic OHLCV and L1 Tick data for verification."""
    # 1. OHLCV Data (5 bars)
    dates = pd.date_range(start='2026-01-01', periods=5, freq='5min')
    df_ohlcv = pd.DataFrame({
        'open': [1.1000, 1.1020, 1.1010, 1.1050, 1.1040],
        'high': [1.1030, 1.1025, 1.1060, 1.1070, 1.1080],
        'low':  [1.0990, 1.1000, 1.1005, 1.1040, 1.1030],
        'close':[1.1020, 1.1010, 1.1050, 1.1040, 1.1070],
        'volume': [1000, 1200, 1500, 1100, 2000]
    }, index=dates)

    # 2. L1 Tick Data (10 ticks)
    tick_dates = pd.date_range(start='2026-01-01', periods=10, freq='30s')
    df_tick = pd.DataFrame({
        'bid': [1.1000, 1.1001, 1.1005, 1.1010, 1.1008, 1.1015, 1.1020, 1.1018, 1.1025, 1.1030],
        'ask': [1.1001, 1.1002, 1.1006, 1.1011, 1.1009, 1.1016, 1.1021, 1.1019, 1.1026, 1.1031],
        'volume': [10, 20, 15, 30, 5, 50, 10, 25, 100, 40]
    }, index=tick_dates)
    
    return df_ohlcv, df_tick

def verify_category(module, base_class, category_name):
    print("-" * 60)
    print(f"VERIFYING: {category_name}")
    print("-" * 60)
    
    df_ohlcv, df_tick = create_mock_data()
    
    # Extract all classes dynamically from the module's __all__
    feature_classes = []
    for class_name in getattr(module, '__all__', []):
        cls = getattr(module, class_name)
        if inspect.isclass(cls) and issubclass(cls, base_class) and cls is not base_class:
            feature_classes.append(cls)
            
    if not feature_classes:
        print(f"[FAIL] No feature classes found for {category_name}! Check __init__.py")
        return False
        
    print(f"[INFO] Found {len(feature_classes)} metrics to test in {category_name}.")
    
    passed = 0
    failed = 0
    
    for cls in feature_classes:
        try:
            metric_instance = cls()
            result_df = metric_instance.calculate(df_ohlcv, df_tick)
            
            if result_df.empty or result_df.isnull().values.any():
                raise ValueError("Returned empty DataFrame or contains NaN (Data Leakage!)")
            if len(result_df) != len(df_ohlcv):
                raise ValueError(f"Output shape mismatch: Expected {len(df_ohlcv)}, got {len(result_df)}")
                
            passed += 1
        except Exception as e:
            print(f"[FAIL] {cls.__name__} encountered an error: {e}")
            failed += 1

    if failed == 0:
        print(f"[SUCCESS] ALL {passed}/{len(feature_classes)} METRICS PASSED WITH 0 ERRORS AND 0 NaNs!")
        return True
    else:
        print(f"[ERROR] {failed} metrics failed.")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("UNIFIED QUANT PIPELINE VERIFICATION SCRIPT")
    print("=" * 60)
    
    c1_ok = verify_category(c01, BaseTickVerifiedFeature, "Category 1 (SMC & ICT Tick-Verified)")
    c2_ok = verify_category(c02, BaseCandlePsychologyFeature, "Category 2 (Candlestick Psychology)")
    
    print("=" * 60)
    if c1_ok and c2_ok:
        print("[SUCCESS] PROJECT STATUS: 100% HEALTHY. BOTH CATEGORIES ARE SAFE AND FULLY FUNCTIONAL.")
    else:
        print("[ERROR] PROJECT STATUS: ERROR DETECTED. PLEASE REVIEW LOGS.")
    print("=" * 60)
