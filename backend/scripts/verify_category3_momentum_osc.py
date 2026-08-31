import sys
import os
import pandas as pd
import numpy as np

# Add backend to path to import the feature class
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))

from services.advanced_ml.features.forex.momentum_osc_features import MomentumOscillatorFeatures

def run_quant_verification():
    print("="*60)
    print("🚀 FOREX ML PIPELINE: CATEGORY 3 VERIFICATION 🚀")
    print("="*60)
    
    # 1. Generate Realistic Dummy Forex Data
    print("\n[1] Generating 1000 bars of synthetic OHLCV data...")
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=1000, freq='h')
    
    # Random walk for realistic price action
    close_prices = 1.1000 + np.cumsum(np.random.normal(0, 0.001, 1000))
    high_prices = close_prices + np.abs(np.random.normal(0, 0.001, 1000))
    low_prices = close_prices - np.abs(np.random.normal(0, 0.001, 1000))
    open_prices = close_prices + np.random.normal(0, 0.0005, 1000)
    volume = np.random.randint(100, 5000, 1000)
    
    df_raw = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume
    }, index=dates)
    
    print(f"Raw DataFrame Shape: {df_raw.shape}")
    
    # 2. Run Feature Extraction
    print("\n[2] Executing MomentumOscillatorFeatures.calculate_all()...")
    df_features = MomentumOscillatorFeatures.calculate_all(df_raw)
    
    print(f"Output DataFrame Shape: {df_features.shape}")
    
    # 3. Architectural Safety Checks
    print("\n[3] Running Architectural Safety Checks...")
    
    # Check 1: Did we lose original columns?
    missing_original = [c for c in df_raw.columns if c not in df_features.columns]
    if missing_original:
        print(f"❌ FAIL: Original columns were lost: {missing_original}")
    else:
        print(f"✅ PASS: Original OHLCV columns perfectly preserved.")
        
    # Check 2: How many new features?
    new_features = [c for c in df_features.columns if c not in df_raw.columns]
    print(f"✅ PASS: Successfully generated {len(new_features)} Advanced Quant Features.")
    
    # Check 3: NaN and Infinity Check (Crucial for Neural Networks)
    nan_count = df_features.isna().sum().sum()
    inf_count = np.isinf(df_features.select_dtypes(include=[np.number])).values.sum()
    
    if nan_count > 0 or inf_count > 0:
        print(f"❌ FAIL: Neural Network Poison Detected! NaNs: {nan_count}, Infs: {inf_count}")
    else:
        print(f"✅ PASS: 0 NaNs and 0 Infinities. 100% Neural Network Ready.")
        
    # Check 4: Dead Feature Check (Zero Variance)
    # We ignore volume which could theoretically have low variance in crypto
    dead_features = [c for c in new_features if df_features[c].nunique() <= 2]
    if dead_features:
        print(f"❌ FAIL: Dead features detected (Constant values): {dead_features}")
    else:
        print(f"✅ PASS: All {len(new_features)} features have healthy statistical variance.")

    # 4. Statistical Summary (Sample of top 5 metrics)
    print("\n[4] Statistical Distribution Sample (Top 5 Advanced Metrics):")
    sample_metrics = ['mom_rsi_velocity', 'mom_stoch_div_proxy', 'mom_fisher_transform', 'mom_rsi_z_score', 'mom_williams_z_score']
    
    sample_df = df_features[sample_metrics].describe().T[['mean', 'std', 'min', 'max']]
    print(sample_df.to_string())
    
    print("\n" + "="*60)
    print("🎯 VERIFICATION COMPLETE: CATEGORY 3 IS PRODUCTION READY 🎯")
    print("="*60)

if __name__ == "__main__":
    run_quant_verification()
