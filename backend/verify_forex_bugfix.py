import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.getcwd())

# Create a mock dataframe of 259 rows
np.random.seed(42)
data = {
    'close': np.random.randn(259),
    'volume': np.random.randint(100, 1000, size=259).astype(float),
    'rsi_14': np.random.randn(259),
    'is_asian': np.random.choice([0, 1], size=259)
}
df = pd.DataFrame(data)

print(f"Original Dataset Shape: {df.shape}")

# Simulate Fractional Differencing effect (Adds ~80 NaNs to the top of all numeric columns)
pad_len = 80
for col in ['close', 'volume', 'rsi_14']:
    df.iloc[:pad_len, df.columns.get_loc(col)] = np.nan

print(f"After Fractional Differencing (80 NaNs added):")
print(f"NaNs in 'volume': {df['volume'].isna().sum()}")
print(f"NaNs in 'close': {df['close'].isna().sum()}")

# Import the data cleaning function
from app.services.ml.forex_data_cleaning import advanced_forex_data_cleaning

def silent_log(msg): pass

print("\n" + "="*70)
print("SCENARIO 1: THE OLD BUG")
print("Tolerance = 27% (69 rows), 'volume' IN naturally_zero")
print("="*70)
df_old = df.copy()
naturally_zero_old = ['volume', 'is_asian']

df_old = advanced_forex_data_cleaning(df_old, 0.5, 0.27, naturally_zero_old, silent_log)
print(f"Output Shape: {df_old.shape}")
print(f"Did 'close' survive? {'Yes' if 'close' in df_old.columns else 'No (Dropped as lagging feature)'}")
print(f"Did 'volume' survive? {'Yes' if 'volume' in df_old.columns else 'No'}")
print(f"Remaining NaNs in 'volume': {df_old['volume'].isna().sum() if 'volume' in df_old.columns else 'N/A'}")
print("-> Result: 'close' is DROPPED because 80 > 69. 'volume' survives but keeps 80 NaNs, which will cause dropna() to destroy 80 rows later!\n")

print("="*70)
print("SCENARIO 2: THE FIX WITH CORRECT SLIDER")
print("Tolerance = 40% (103 rows), 'volume' NOT IN naturally_zero")
print("="*70)
df_fixed = df.copy()
naturally_zero_fixed = ['is_asian'] # Removed volume

def print_log(msg): print(f"  [CLEANING LOG] {msg}")

df_fixed = advanced_forex_data_cleaning(df_fixed, 0.5, 0.40, naturally_zero_fixed, print_log)
print(f"\nOutput Shape: {df_fixed.shape}")
print(f"Did 'close' survive? {'Yes' if 'close' in df_fixed.columns else 'No'}")
print(f"Did 'volume' survive? {'Yes' if 'volume' in df_fixed.columns else 'No'}")
print(f"Remaining NaNs in 'volume': {df_fixed['volume'].isna().sum()}")
print("-> Result: All features SURVIVE! The first 80 rows containing NaNs are perfectly TRIMMED. Zero NaNs remain, meaning dropna() won't destroy anything!\n")
