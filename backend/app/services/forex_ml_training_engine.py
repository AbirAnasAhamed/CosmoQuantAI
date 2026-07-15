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
from app import models
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
            snapshot_file = self.job.config.get('snapshot_file')
            if not snapshot_file:
                raise Exception("No forex snapshot file selected for training.")
                
            data_file = os.path.join(os.getcwd(), "data", "raw", "forex_snapshots", snapshot_file)
            
            if not os.path.exists(data_file):
                raise Exception(f"Snapshot file not found at {data_file}")
            
            # Step 1: Data Preparation
            self._log(f"Loading data from {data_file}...")
            df = pd.read_parquet(data_file)
            df['time'] = pd.to_datetime(df['time'], utc=True).dt.tz_localize(None)
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
            
            # --- Save to ML Registry ---
            registry_id = f"forex_model_{int(time.time())}"
            custom_model_name = self.job.config.get("model_name", "").strip()
            final_name = custom_model_name if custom_model_name else f"{clean_symbol} Forex {algorithm}"
            
            db_model = models.CustomMLModel(
                id=registry_id,
                name=final_name,
                model_type=algorithm,
                user_id=self.job.user_id,
                active_version_id=None,
                is_auto_retrain=0,
                retrain_interval_hours=0,
                data_lookback_hours=24 # Default
            )
            self.db.add(db_model)
            self.db.flush()
            
            version_id = f"v1.0-{int(time.time())}"
            db_version = models.ModelVersion(
                id=version_id,
                model_id=registry_id,
                version=1.0,
                description=f"Trained on {clean_symbol} using {algorithm}",
                file_path=model_filepath,
                status=models.ModelStatus.READY,
                accuracy=accuracy if 'accuracy' in locals() else 0.0,
                dataset_path=data_file
            )
            self.db.add(db_version)
            self.db.flush()
            
            db_model.active_version_id = version_id
            self.job.output_model_id = registry_id
            self._log(f"Model successfully registered in ML Registry as {registry_id}")
            # --- End ML Registry Save ---
            
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
