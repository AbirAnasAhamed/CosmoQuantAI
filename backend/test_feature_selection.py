import pandas as pd
from app.services.ml_utils import apply_auto_feature_selection

# Load the dataset
data_file = "/app/data/raw/forex_snapshots/EUR_USD_20260827_160811.parquet"
df = pd.read_parquet(data_file)

print(f"Original columns: {len(df.columns)}")
print("Columns:", list(df.columns)[:10], "...")

def print_log(msg):
    print("LOG:", msg)

df_auto, selected_features = apply_auto_feature_selection(
    df=df, 
    target_col='Target', 
    top_n=50, 
    is_classification=True, 
    add_log=print_log
)

print(f"Final selected features: {len(selected_features)}")
print("Features:", selected_features)
