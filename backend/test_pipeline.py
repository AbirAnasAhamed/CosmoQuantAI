import pandas as pd
from app.services.ml_utils import apply_auto_feature_selection, apply_data_cleaning
from app.services.forex_ml_training_engine import ForexMLTrainingEngine
from app.database import SessionLocal
from app.models import ModelTrainingJob

def print_log(msg):
    print("LOG:", msg)

# Initialize engine with fake job to get access to _generate_technical_features
db = SessionLocal()
job = db.query(ModelTrainingJob).filter(ModelTrainingJob.id == 'forex_train_1788009559292').first()
engine = ForexMLTrainingEngine(job_id=job.id, db_session=db)

# Load dataset
data_file = "/app/data/raw/forex_snapshots/EUR_USD_20260827_160811.parquet"
df = pd.read_parquet(data_file)
print(f"Original shape: {df.shape}")

# Preprocessing
df.columns = [str(col).lower() for col in df.columns]
if 'timestamp' in df.columns:
    df.rename(columns={'timestamp': 'time'}, inplace=True)
if 'time' in df.columns:
    df['time'] = pd.to_datetime(df['time'], utc=True)
    df.set_index('time', inplace=True)
elif not isinstance(df.index, pd.DatetimeIndex):
    print("WARNING: Dataset does not have a datetime index. Attempting to use the first column.")

# Generate Target
df['Target'] = (df['close'].shift(-1) > df['close']).astype(int)

# Generate features
df = engine._generate_technical_features(df)
print(f"Shape after _generate_technical_features: {df.shape}")

# Add macro risk flag if not present (simulating)
if 'macro_risk_flag' not in df.columns:
    df['macro_risk_flag'] = 0

df = apply_data_cleaning(df, job.config, print_log)
print(f"Shape after apply_data_cleaning: {df.shape}")

df_auto, selected_features = apply_auto_feature_selection(
    df=df, 
    target_col='Target', 
    top_n=50, 
    is_classification=True, 
    add_log=print_log
)

print(f"Final selected features: {len(selected_features)}")
print("Features:", selected_features)
