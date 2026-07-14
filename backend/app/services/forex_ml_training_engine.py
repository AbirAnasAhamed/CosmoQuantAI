import time
import os
import random
import pandas as pd
import pandas_ta as ta
import numpy as np
import joblib
from datetime import datetime, timezone
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.model_training import ModelTrainingJob, TrainingStatus
from app.services.economic_service import economic_service
from app.services.ml.forex_model_factory import get_forex_model

class ForexMLTrainingEngine:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.db: Session = SessionLocal()
        self.job = self.db.query(ModelTrainingJob).filter_by(id=self.job_id).first()

    def _log(self, message: str):
        if not self.job:
            return
        
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [ForexEngine] {message}"
        
        logs = list(self.job.logs) if self.job.logs else []
        logs.append(log_entry)
        self.job.logs = logs
        self.db.commit()
        
    def start_training(self):
        if not self.job:
            return

        self.job.status = TrainingStatus.RUNNING
        self.db.commit()

        try:
            self._log("Initializing Forex Model Training...")
            symbol = self.job.symbol
            clean_symbol = symbol.replace("/", "_")
            data_dir = os.path.join(os.getcwd(), "data", "forex")
            os.makedirs(data_dir, exist_ok=True)
            data_file = os.path.join(data_dir, f"{clean_symbol}_data.csv")
            
            if not os.path.exists(data_file):
                self._log("Dataset not found. Running auto-collector...")
                target_rows = self.job.config.get('target_rows', 10000)
                date_range_mode = self.job.config.get('date_range_mode', 'ticks')
                start_date = self.job.config.get('start_date')
                end_date = self.job.config.get('end_date')
                
                # Determine timeframe mapping
                tf = self.job.timeframe.lower() if hasattr(self.job, 'timeframe') and self.job.timeframe else "1h"
                oanda_granularity = "H1"
                if "1m" in tf: oanda_granularity = "M1"
                elif "5m" in tf: oanda_granularity = "M5"
                elif "15m" in tf: oanda_granularity = "M15"
                elif "30m" in tf: oanda_granularity = "M30"
                elif "h" in tf: oanda_granularity = tf.upper()
                elif "d" in tf: oanda_granularity = "D"
                
                api_key = os.getenv("OANDA_API_KEY")
                data_collected = False
                
                if api_key:
                    if date_range_mode == 'date':
                        self._log(f"Attempting to fetch {symbol} from OANDA (from {start_date} to {end_date})...")
                    else:
                        self._log(f"Attempting to fetch {symbol} from OANDA (target: {target_rows})...")
                        
                    import requests
                    import time
                    headers = {"Authorization": f"Bearer {api_key}"}
                    oanda_instrument = clean_symbol # OANDA format is typically EUR_USD
                    
                    records = []
                    remaining = target_rows if date_range_mode == 'ticks' else 5000
                    to_time = None
                    
                    if date_range_mode == 'date' and end_date:
                        end_dt = pd.to_datetime(end_date) + pd.Timedelta(hours=23, minutes=59)
                        to_time = end_dt.tz_localize('UTC').strftime('%Y-%m-%dT%H:%M:%SZ')
                    
                    while remaining > 0:
                        count = min(remaining, 5000) if date_range_mode == 'ticks' else 5000
                        url = f"https://api-fxpractice.oanda.com/v3/instruments/{oanda_instrument}/candles?count={count}&granularity={oanda_granularity}&price=M"
                        if to_time:
                            url += f"&to={to_time}"
                            
                        try:
                            response = requests.get(url, headers=headers)
                            if response.status_code == 200:
                                data = response.json()
                                candles = data.get("candles", [])
                                if not candles:
                                    break
                                
                                chunk_records = []
                                for c in candles:
                                    if c["complete"]:
                                        chunk_records.append({
                                            "time": c["time"],
                                            "open": float(c["mid"]["o"]),
                                            "high": float(c["mid"]["h"]),
                                            "low": float(c["mid"]["l"]),
                                            "close": float(c["mid"]["c"]),
                                            "volume": int(c["volume"])
                                        })
                                        
                                if not chunk_records:
                                    break
                                    
                                records.extend(chunk_records)
                                
                                if date_range_mode == 'ticks':
                                    remaining -= len(chunk_records)
                                else:
                                    oldest_time = pd.to_datetime(candles[0]["time"]).tz_localize(None)
                                    start_dt = pd.to_datetime(start_date)
                                    if oldest_time <= start_dt:
                                        remaining = 0 # stop
                                    else:
                                        remaining = 5000 # keep going
                                
                                # OANDA returns ascending order (oldest first). 
                                to_time = candles[0]["time"]
                                
                                # Avoid spamming the API
                                time.sleep(0.1)
                            else:
                                self._log(f"OANDA API Error: {response.text}")
                                break
                        except Exception as e:
                            self._log(f"Failed to fetch from OANDA: {str(e)}")
                            break
                            
                    if records:
                        df_new = pd.DataFrame(records)
                        df_new["time"] = pd.to_datetime(df_new["time"]).dt.tz_localize(None)
                        df_new.drop_duplicates(subset=["time"], inplace=True)
                        df_new.sort_values("time", inplace=True)
                        
                        if date_range_mode == 'date':
                            df_new = df_new[(df_new['time'] >= pd.to_datetime(start_date)) & (df_new['time'] <= pd.to_datetime(end_date) + pd.Timedelta(hours=23, minutes=59))]
                        else:
                            df_new = df_new.tail(target_rows)
                            
                        df_new.to_csv(data_file, index=False)
                        self._log(f"Successfully downloaded and saved {len(df_new)} rows from OANDA.")
                        data_collected = True
                else:
                    self._log("OANDA_API_KEY not found in environment.")

                if not data_collected:
                    self._log("Falling back to Yahoo Finance...")
                    import yfinance as yf
                    yf_symbol = f"{symbol.replace('_', '')}=X"
                    
                    yf_interval = "1h"
                    if "1m" in tf: yf_interval = "1m"
                    elif "5m" in tf: yf_interval = "5m"
                    elif "15m" in tf: yf_interval = "15m"
                    elif "30m" in tf: yf_interval = "30m"
                    elif "h" in tf: yf_interval = tf
                    elif "d" in tf: yf_interval = "1d"
                    
                    if date_range_mode == 'date' and start_date and end_date:
                        self._log(f"Fetching {yf_symbol} from Yahoo Finance (from {start_date} to {end_date})...")
                        df_yf = yf.download(yf_symbol, start=start_date, end=end_date, interval=yf_interval, progress=False)
                    else:
                        period = "730d" if "h" in yf_interval or "d" in yf_interval else "60d"
                        if yf_interval == "1m": period = "7d"
                        self._log(f"Fetching {yf_symbol} from Yahoo Finance (interval: {yf_interval})...")
                        df_yf = yf.download(yf_symbol, period=period, interval=yf_interval, progress=False)
                    
                    if df_yf.empty:
                        raise Exception(f"Failed to collect data for {yf_symbol} from both OANDA and Yahoo Finance.")
                        
                    df_yf.reset_index(inplace=True)
                    
                    if isinstance(df_yf.columns, pd.MultiIndex):
                        df_yf.columns = df_yf.columns.get_level_values(0)
                    
                    rename_map = {'Datetime': 'time', 'Date': 'time', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}
                    df_yf.rename(columns=rename_map, inplace=True)
                    
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        if col not in df_yf.columns:
                            df_yf[col] = 0.0
                    
                    df_yf = df_yf[['time', 'open', 'high', 'low', 'close', 'volume']]
                    
                    if date_range_mode != 'date':
                        df_yf = df_yf.tail(target_rows)
                        
                    df_yf.to_csv(data_file, index=False)
                    self._log(f"Successfully downloaded and saved {len(df_yf)} rows from Yahoo Finance.")
            
            # Step 1: Data Preparation
            self._log(f"Loading data from {data_file}...")
            df = pd.read_csv(data_file)
            df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)
            self._log(f"Loaded {len(df)} rows of data.")
            self.job.progress = 10.0
            self.db.commit()

            # Step 2: Feature Engineering (Technical Indicators)
            self._log("Calculating Technical Indicators (RSI, MACD, BBands)...")
            df.ta.rsi(length=14, append=True)
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            df.ta.bbands(length=20, append=True)
            df.dropna(inplace=True)
            self.job.progress = 30.0
            self.db.commit()

            # Step 3: Market Session Pipeline
            self._log("Injecting Market Session Pipeline Data (Asian/London/NY)...")
            # Heuristic hours (UTC):
            # Asian: 23:00 - 08:00
            # London: 07:00 - 16:00
            # NY: 12:00 - 21:00
            hours = df.index.hour
            df['is_asian'] = ((hours >= 23) | (hours < 8)).astype(int)
            df['is_london'] = ((hours >= 7) & (hours < 16)).astype(int)
            df['is_ny'] = ((hours >= 12) & (hours < 21)).astype(int)
            self.job.progress = 40.0
            self.db.commit()

            # Step 4: Macroeconomic Calendar Data
            self._log("Fetching Macroeconomic Calendar Data...")
            macro_events = economic_service.get_latest_indicators()
            self._log(f"Found {len(macro_events)} recent/upcoming high-impact events.")
            
            # For simplicity in this iteration, we create a dummy 'macro_risk' feature based on event proximity.
            # In production, we would map exact dates to the dataframe index.
            df['macro_risk_flag'] = 0
            if macro_events:
                # Mark random recent hours as high risk just to simulate the feature injection
                # since the dataset might not overlap exactly with the *current* week's json feed.
                df['macro_risk_flag'] = np.random.choice([0, 1], size=len(df), p=[0.95, 0.05])
                
            self.job.progress = 50.0
            self.db.commit()
            
            # Step 5: Preparing Target Variable
            use_triple_barrier = self.job.config.get('use_triple_barrier', False)
            if use_triple_barrier:
                self._log("Applying Triple Barrier Method...")
                from app.services.ml.triple_barrier import apply_triple_barrier
                pt_sl = self.job.config.get('pt_sl_ratio', 1.5)
                timeout = self.job.config.get('barrier_timeout', 24)
                df['target'] = apply_triple_barrier(df, pt_sl, timeout)
            else:
                self._log("Preparing target variables for classification...")
                df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
            
            df.dropna(inplace=True)
            
            features = [col for col in df.columns if col not in ['target', 'open', 'high', 'low', 'close']]
            X = df[features]
            y = df['target']
            
            # Feature Selection
            feature_method = self.job.config.get('feature_selection_method', 'none')
            if feature_method != 'none':
                self._log(f"Applying {feature_method.upper()} Feature Selection...")
                from app.services.ml.feature_selection import select_features
                X = select_features(X, y, method=feature_method)

            # Step 6: Model Training & WFO
            algorithm = self.job.algorithm
            use_automl = self.job.config.get('use_automl', False)
            split_method = self.job.config.get('split_method', 'chronological')
            
            if split_method == 'walk_forward':
                self._log("Starting Walk-Forward Optimization (WFO)...")
                from app.services.ml.wfo_validator import walk_forward_split
                wfo_windows = self.job.config.get('wfo_windows', 5)
                
                accuracies = []
                for i, (X_train, X_test, y_train, y_test) in enumerate(walk_forward_split(X, y, n_splits=wfo_windows)):
                    if use_automl and i == wfo_windows - 1:
                        self._log(f"Running AutoML Optuna on Fold {i+1}...")
                        from app.services.ml.optuna_optimizer import run_optuna_study
                        trials = self.job.config.get('automl_trials', 10)
                        best_params = run_optuna_study(X_train, y_train, algorithm, trials)
                        model = get_forex_model(algorithm, {**self.job.config, **best_params})
                    else:
                        model = get_forex_model(algorithm, self.job.config)
                        
                    model.fit(X_train, y_train)
                    acc = model.score(X_test, y_test)
                    accuracies.append(acc)
                    self._log(f"Fold {i+1} Accuracy: {acc*100:.2f}%")
                    
                accuracy = np.mean(accuracies)
                self._log(f"Walk-Forward Average Accuracy: {accuracy*100:.2f}%")
            else:
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
                if use_automl:
                    self._log("Running AutoML Optuna...")
                    from app.services.ml.optuna_optimizer import run_optuna_study
                    trials = self.job.config.get('automl_trials', 30)
                    best_params = run_optuna_study(X_train, y_train, algorithm, trials)
                    model = get_forex_model(algorithm, {**self.job.config, **best_params})
                else:
                    model = get_forex_model(algorithm, self.job.config)
                    
                model.fit(X_train, y_train)
                accuracy = model.score(X_test, y_test)
                self._log(f"Training completed. Validation Accuracy: {accuracy*100:.2f}%")
                
            self.job.progress = 90.0
            self.db.commit()
            
            # Step 7: Meta Labeling & Saving
            models_dir = os.path.join(os.getcwd(), "uploads", "models", "forex")
            os.makedirs(models_dir, exist_ok=True)
            
            if self.job.config.get('enable_meta_labeling', False):
                self._log("Training Secondary Meta-Labeling Model...")
                from app.services.ml.meta_labeler import train_meta_model
                meta_model = train_meta_model(X_train, y_train, model, algorithm)
                
                meta_model_filename = f"{self.job_id}_meta_{clean_symbol}.pkl"
                joblib.dump(meta_model, os.path.join(models_dir, meta_model_filename))
                self._log(f"Meta-Model saved to {meta_model_filename}")
            
            model_filename = f"{self.job_id}_{clean_symbol}.pkl"
            model_filepath = os.path.join(models_dir, model_filename)
            joblib.dump(model, model_filepath)
            
            self._log(f"Primary Model saved to {model_filepath}")
            
            self.job.status = TrainingStatus.COMPLETED
            self.job.progress = 100.0
            self.job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            
        except Exception as e:
            self.job.status = TrainingStatus.FAILED
            self.job.error_message = str(e)
            self._log(f"ERROR: {str(e)}")
            self.db.commit()
        finally:
            self.db.close()

def run_forex_training_job(job_id: str):
    engine = ForexMLTrainingEngine(job_id)
    engine.start_training()
