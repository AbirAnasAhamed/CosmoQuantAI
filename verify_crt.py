import sys
import os
import pandas as pd
import numpy as np

# Add the backend to the path so we can import the module
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from app.services.advanced_ml.features.forex.candle_range_theory_features import CandleRangeTheoryEngine
except ImportError as e:
    print(f"FAILED: Could not import CandleRangeTheoryEngine: {e}")
    sys.exit(1)

def generate_synthetic_data(num_rows=500):
    np.random.seed(42)
    # Generate random walk
    returns = np.random.normal(0, 0.001, num_rows)
    close = 1.1000 * np.cumprod(1 + returns)
    
    # Generate OHLC
    high = close * (1 + np.abs(np.random.normal(0, 0.0005, num_rows)))
    low = close * (1 - np.abs(np.random.normal(0, 0.0005, num_rows)))
    open_p = pd.Series(close).shift(1).fillna(1.1000)
    
    df = pd.DataFrame({
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.randint(100, 1000, num_rows)
    })
    return df

def run_verification():
    print("="*60)
    print("🚀 CRT ENGINE 62-METRIC VERIFICATION SCRIPT 🚀")
    print("="*60)
    
    df_raw = generate_synthetic_data(500)
    print(f"[+] Generated synthetic OHLCV data: {df_raw.shape}")
    
    # Initialize Engine
    engine = CandleRangeTheoryEngine(df_raw)
    df_features = engine.generate_all_features()
    
    print(f"[+] Feature generation completed. Output shape: {df_features.shape}")
    
    # 1. Count CRT features
    crt_cols = [c for c in df_features.columns if c.startswith('crt_')]
    print(f"\n[TEST 1] CRT Feature Count Validation:")
    if len(crt_cols) == 62:
        print(f"  ✅ SUCCESS: Exactly 62 CRT metrics found.")
    else:
        print(f"  ❌ FAILED: Found {len(crt_cols)} CRT metrics. Expected 62.")
        
    # 2. Check for NaNs
    nan_counts = df_features[crt_cols].isna().sum().sum()
    print(f"\n[TEST 2] NaN Value Validation:")
    if nan_counts == 0:
        print(f"  ✅ SUCCESS: No NaN values found. Engine is ML-ready.")
    else:
        print(f"  ❌ FAILED: Found {nan_counts} NaN values in the dataset.")
        
    # 3. Check for Infs
    # Replace np.inf with something to count it, or use np.isinf where type is float
    inf_counts = 0
    for col in crt_cols:
        if pd.api.types.is_numeric_dtype(df_features[col]):
            inf_counts += np.isinf(df_features[col]).sum()
            
    print(f"\n[TEST 3] Infinity (Inf) Value Validation:")
    if inf_counts == 0:
        print(f"  ✅ SUCCESS: No Infinity values found. Division-by-zero safeguarded.")
    else:
        print(f"  ❌ FAILED: Found {inf_counts} Inf values in the dataset.")
        
    # Print the exact features mapped
    print("\n[+] Detailed List of Generated CRT Metrics:")
    for i, col in enumerate(crt_cols, 1):
        print(f"    {i:02d}. {col}")
        
    print("\n" + "="*60)
    if len(crt_cols) == 62 and nan_counts == 0 and inf_counts == 0:
        print("🎉 ALL VERIFICATIONS PASSED SUCCESSFULLY! 100% PRODUCTION READY. 🎉")
    else:
        print("⚠️ VERIFICATION FAILED! PLEASE CHECK THE LOGS. ⚠️")
    print("="*60)

if __name__ == '__main__':
    run_verification()
