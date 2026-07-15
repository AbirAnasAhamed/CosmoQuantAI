import time
import argparse
import sys
import os
import requests
import pandas as pd
from datetime import datetime

# Ensure we can import app modules if running as a standalone script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.db.session import SessionLocal
from app.models.model_training import ModelTrainingJob, TrainingStatus

def run_forex_collector(symbol: str, target_rows: int, job_id: str, mode: str = "ticks", start_date: str = None, end_date: str = None, timeframe: str = "15m"):
    db = SessionLocal()
    job = db.query(ModelTrainingJob).filter_by(id=job_id).first()
    
    if not job:
        print(f"Job {job_id} not found.")
        return

    def _log(msg: str):
        timestamp = time.strftime("%H:%M:%S")
        logs = list(job.logs) if job.logs else []
        logs.append(f"[{timestamp}] [ForexCollector] {msg}")
        job.logs = logs
        db.commit()

    account_id = os.getenv("OANDA_ACCOUNT_ID")
    api_key = os.getenv("OANDA_API_KEY")
    
    if not account_id or not api_key:
        _log("ERROR: OANDA API credentials are not set in the environment.")
        job.status = TrainingStatus.FAILED
        db.commit()
        return

    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.getcwd(), "data", "raw", "forex_snapshots")
    os.makedirs(data_dir, exist_ok=True)
    
    clean_symbol = symbol.replace("/", "_")
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(data_dir, f"{clean_symbol}_{timestamp_str}.parquet")

    try:
        _log(f"Starting OANDA Collector for {symbol} (Target: {target_rows} rows)...")
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        # OANDA v20 API uses EUR_USD format
        instrument = symbol.replace("/", "_")
        
        # Map common timeframes to OANDA granularity
        tf_map = {
            "5s": "S5",
            "10s": "S10",
            "30s": "S30",
            "1m": "M1",
            "5m": "M5",
            "15m": "M15",
            "30m": "M30",
            "1h": "H1",
            "4h": "H4",
            "1d": "D",
        }
        granularity = tf_map.get(timeframe.lower(), "M15")
        
        if mode == "date" and start_date and end_date:
            _log(f"Fetching {timeframe} data from OANDA API for range {start_date} to {end_date}...")
            # Convert YYYY-MM-DD to RFC3339 for OANDA (e.g., 2023-10-01T00:00:00Z)
            from_time = f"{start_date}T00:00:00Z"
            to_time = f"{end_date}T23:59:59Z"
            url = f"https://api-fxpractice.oanda.com/v3/instruments/{instrument}/candles?from={from_time}&to={to_time}&granularity={granularity}&price=M"
        else:
            _log(f"Fetching recent {target_rows} candles ({timeframe}) from OANDA API...")
            count = min(target_rows, 5000)
            url = f"https://api-fxpractice.oanda.com/v3/instruments/{instrument}/candles?count={count}&granularity={granularity}&price=M"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        candles = data.get("candles", [])
        
        if not candles:
            _log("No candles returned from OANDA.")
            job.status = TrainingStatus.FAILED
            db.commit()
            return
            
        _log(f"Received {len(candles)} candles. Parsing data...")
        
        records = []
        for c in candles:
            if not c["complete"]:
                continue
            records.append({
                "time": c["time"],
                "open": float(c["mid"]["o"]),
                "high": float(c["mid"]["h"]),
                "low": float(c["mid"]["l"]),
                "close": float(c["mid"]["c"]),
                "volume": int(c["volume"]) # Tick volume
            })
            
        df = pd.DataFrame(records)
        # Convert time to standard datetime
        df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
        
        df.to_parquet(output_file, index=False)
        _log(f"Successfully saved {len(df)} rows to {output_file}")
            
        if job.status == TrainingStatus.RUNNING:
            job.status = TrainingStatus.COMPLETED
            job.progress = 100.0
            db.commit()
            
    except Exception as e:
        job.status = TrainingStatus.FAILED
        job.error_message = str(e)
        _log(f"ERROR: {str(e)}")
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, required=True)
    parser.add_argument("--target", type=int, required=True)
    parser.add_argument("--job_id", type=str, required=True)
    parser.add_argument("--mode", type=str, default="ticks")
    parser.add_argument("--start_date", type=str, default=None)
    parser.add_argument("--end_date", type=str, default=None)
    parser.add_argument("--timeframe", type=str, default="15m")
    args = parser.parse_args()
    
    run_forex_collector(args.symbol, args.target, args.job_id, args.mode, args.start_date, args.end_date, args.timeframe)
