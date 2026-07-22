import json
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
            
            if 'close' not in df.columns and 'bid' in df.columns:
                self._log("Tick data detected (no 'close' column). Resampling to 1-minute OHLC...")
                df['bid'] = pd.to_numeric(df['bid'], errors='coerce')
                df['ask'] = pd.to_numeric(df['ask'], errors='coerce')
                df['mid'] = (df['bid'] + df['ask']) / 2
                # Resample to 1-minute OHLC
                df = df['mid'].resample('1min').ohlc()
                df.dropna(inplace=True)
                self._log(f"Resampled to {len(df)} OHLC rows.")
                
            self.job.progress = 10.0
            self.db.commit()

            # Step 2: Feature Engineering (Technical Indicators)
            self._log("Calculating Modular Technical Indicators...")
            from app.services.ml.forex_feature_engine import generate_ohlcv_features
            selected_features = self.job.config.get('selected_forex_features', [])
            
            if selected_features:
                self._log(f"Generating {len(selected_features)} selected features...")
                df = generate_ohlcv_features(df, selected_features)
            else:
                self._log("No specific features selected. Falling back to basic RSI, MACD, BBands...")
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

            # Step 4.5: L2 Orderbook Data Integration
            l2_file = self.job.config.get('l2_orderbook_file')
            if l2_file:
                self._log(f"Integrating L2 Orderbook Data from {l2_file}...")
                l2_path = os.path.join(os.getcwd(), "data", "forex", "l2_data", l2_file)
                if os.path.exists(l2_path):
                    try:
                        # Assuming L2 CSV has 'time', 'best_bid', 'best_ask', 'bid_volume', 'ask_volume'
                        l2_df = pd.read_csv(l2_path)
                        if 'time' in l2_df.columns or 'timestamp' in l2_df.columns:
                            time_col = 'time' if 'time' in l2_df.columns else 'timestamp'
                            l2_df[time_col] = pd.to_datetime(l2_df[time_col], utc=True).dt.tz_localize(None)
                            l2_df.set_index(time_col, inplace=True)
                            
                            # Standardize column names for the L2 Engine
                            if 'best_bid' in l2_df.columns and 'bid1' not in l2_df.columns: l2_df['bid1'] = l2_df['best_bid']
                            if 'best_ask' in l2_df.columns and 'ask1' not in l2_df.columns: l2_df['ask1'] = l2_df['best_ask']
                            if 'bid_volume' in l2_df.columns and 'bid_vol1' not in l2_df.columns: l2_df['bid_vol1'] = l2_df['bid_volume']
                            if 'ask_volume' in l2_df.columns and 'ask_vol1' not in l2_df.columns: l2_df['ask_vol1'] = l2_df['ask_volume']
                            
                            # Feature extraction from L2 using the new modular engine
                            from app.services.ml.forex_l2_feature_engine import generate_all_l2_features
                            selected_features = self.job.config.get('selected_forex_features', [])
                            self._log(f"Calculating advanced L2 features... ({len([f for f in selected_features if f.startswith('l1_') or f.startswith('spread_') or f.startswith('l2_') or f.startswith('top') or f.startswith('bid_') or f.startswith('ask_')])} selected)")
                            l2_df = generate_all_l2_features(l2_df, selected_features)
                            
                            # CRITICAL: Drop raw price/volume columns from L2 data to prevent data leakage and non-stationarity in the ML model.
                            # We only want to keep the explicitly generated features that the user selected.
                            raw_cols = [c for c in l2_df.columns if c not in selected_features and c not in ['time', 'timestamp']]
                            l2_df.drop(columns=raw_cols, inplace=True, errors='ignore')
                            
                            # Resample to match OHLCV (1min)
                            l2_resampled = l2_df.resample('1min').mean().fillna(0)
                            
                            # Merge with main df
                            df = df.join(l2_resampled, how='left').fillna(0)
                            self._log(f"Successfully integrated {len(l2_resampled)} rows of L2 features.")
                        else:
                            self._log("L2 CSV missing 'time' column, unable to merge.")
                    except Exception as e:
                        self._log(f"Failed to process L2 Orderbook data: {e}")
                else:
                    self._log(f"L2 Orderbook file not found at {l2_path}")

            self.job.progress = 60.0
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
            
            # Map Triple Barrier [-1, 0, 1] to [0, 1, 2] for XGBoost/LightGBM compatibility
            if use_triple_barrier:
                y = y + 1
            
            # Feature Selection
            feature_method = self.job.config.get('feature_selection_method', 'none')
            if feature_method != 'none':
                self._log(f"Applying {feature_method.upper()} Feature Selection...")
                from app.services.ml.feature_selection import select_features
                X = select_features(X, y, method=feature_method)

            # Step 6: Model Training & WFO
            algorithm = self.job.algorithm
            
            # RL Live Streaming Callback
            callback = None
            if algorithm.endswith('-RL'):
                try:
                    from stable_baselines3.common.callbacks import BaseCallback
                    import redis
                    from app.core.config import settings
                    redis_client = redis.from_url(settings.REDIS_URL)
                    
                    class ForexLiveStreamingCallback(BaseCallback):
                        def __init__(self, job, db_session, log_func):
                            super().__init__()
                            self.job = job
                            self.db = db_session
                            self.log_func = log_func
                            self.last_log_step = 0
                            
                        def _on_step(self) -> bool:
                            env = self.training_env.envs[0]
                            env = getattr(env, 'unwrapped', env)
                            
                            step = self.num_timesteps
                            total = self.locals.get('total_timesteps', 10000)
                            
                            # Log every 1000 steps
                            if step - self.last_log_step >= 1000 or step == 1:
                                pct = (step / total) * 100
                                self.log_func(f"RL Training Progress: {step}/{total} steps ({pct:.1f}%)")
                                self.job.progress = min(90.0, max(50.0, 50.0 + (pct * 0.4))) # Scale progress between 50 and 90
                                self.db.commit()
                                self.last_log_step = step
                                
                            # Payload for Live Visualizer
                            action = self.locals.get('actions', [0])
                            action_val = float(np.ravel(action)[0]) if action is not None else 0.0
                            
                            reward = self.locals.get('rewards', [0.0])
                            reward_val = float(np.ravel(reward)[0]) if reward is not None else 0.0
                            
                            # Safely extract dummy state variables
                            position = getattr(env, 'position', 0)
                            net_worth = getattr(env, 'net_worth', 10000.0)
                            balance = getattr(env, 'balance', 10000.0)
                            trade_history = getattr(env, 'trade_history', [])
                            buy_count = sum(1 for t in trade_history if t['type'] == 'open_long')
                            sell_count = sum(1 for t in trade_history if t['type'] == 'open_short')
                            profitable_count = sum(1 for t in trade_history if t.get('pnl', 0) > 0)
                            loss_count = sum(1 for t in trade_history if t.get('pnl', 0) < 0)
                            
                            payload = {
                                "step": step,
                                "net_worth": float(net_worth),
                                "position": int(position),
                                "balance": float(balance),
                                "action": action_val,
                                "reward": reward_val,
                                "price": float(net_worth), # Simulated price based on net_worth for Forex
                                "stats": {
                                    "buy_count": buy_count,
                                    "sell_count": sell_count,
                                    "profitable_count": profitable_count,
                                    "loss_count": loss_count
                                }
                            }
                            
                            capped_progress = min(100.0, (step / total) * 100)
                            message = {
                                "task_type": "RL_TRAINING_STEP",
                                "task_id": self.job.id,
                                "status": "processing",
                                "progress": int(capped_progress),
                                "data": payload,
                                "features": []
                            }
                            redis_client.publish("task_updates", json.dumps(message))
                            return True
                            
                    callback = ForexLiveStreamingCallback(self.job, self.db, self._log)
                except ImportError:
                    pass
                    
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
                        
                    if algorithm.endswith('-RL'):
                        model.fit(X_train, y_train, callback=callback)
                    else:
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
                    
                if algorithm.endswith('-RL'):
                    model.fit(X_train, y_train, callback=callback)
                else:
                    model.fit(X_train, y_train)
                accuracy = model.score(X_test, y_test)
                self._log(f"Training completed. Validation Accuracy: {accuracy*100:.2f}%")
                
            # --- Post-Training Backtest Simulation ---
            self._log("Running Post-Training Backtest on Validation Data...")
            try:
                preds = model.predict(X_test)
                # Calculate simple close-to-close returns
                test_returns = df.loc[X_test.index, 'close'].pct_change().shift(-1).fillna(0)
                
                # Signal logic
                if use_triple_barrier:
                    # 2 is Long, 0 is Short, 1 is Hold
                    strategy_returns = np.where(preds == 2, test_returns, np.where(preds == 0, -test_returns, 0.0))
                else:
                    # 1 is Long, 0 is Short
                    strategy_returns = np.where(preds == 1, test_returns, -test_returns)
                
                winning_trades = np.sum(strategy_returns > 0)
                losing_trades = np.sum(strategy_returns < 0)
                total_trades = winning_trades + losing_trades
                
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
                
                mean_ret = np.mean(strategy_returns)
                std_ret = np.std(strategy_returns)
                # Approximate Sharpe for 1m data (252 days * 1440 mins)
                sharpe = (mean_ret / std_ret) * np.sqrt(252 * 1440) if std_ret > 0 else 0.0 
                
                total_return = np.sum(strategy_returns) * 100
                
                self._log(f"📊 Backtest Results -> Win Rate: {win_rate:.2f}% | Sharpe Ratio: {sharpe:.2f} | Net Profit: {total_return:.2f}%")
                
                # Expose metrics so they can be saved in the database
                backtest_win_rate = float(win_rate)
                backtest_sharpe = float(sharpe)
            except Exception as e:
                self._log(f"Post-Training Backtest simulation failed: {e}")
                backtest_win_rate = 0.0
                
            self.job.progress = 90.0
            self.db.commit()
            
            # Step 7: Meta Labeling & Saving
            models_dir = os.path.join(os.getcwd(), "uploads", "models", f"forex_{self.job_id}")
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
            
            explainability_data = {
                "total_return_pct": float(total_return) if 'total_return' in locals() else 0.0,
                "win_rate": float(backtest_win_rate) if 'backtest_win_rate' in locals() else 0.0,
                "sharpe_ratio": float(backtest_sharpe) if 'backtest_sharpe' in locals() else 0.0,
                "trades_count": int(total_trades) if 'total_trades' in locals() else 0
            }

            # Generate and save metadata.json
            metadata_path = os.path.join(models_dir, f"{self.job_id}_{clean_symbol}_metadata.json")
            metadata = {
                "features": list(X.columns),
                "dataset_type": "forex",
                "indicators": [],
                "timeframe": self.job.timeframe,
                "symbol": clean_symbol,
                "prediction_target": "classification"
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)
            
            version_id = f"v1.0-{int(time.time())}"
            db_version = models.ModelVersion(
                id=version_id,
                model_id=registry_id,
                version=1.0,
                description=f"Trained on {clean_symbol} using {algorithm}",
                file_path=model_filepath,
                status=models.ModelStatus.READY,
                accuracy=float(accuracy) if 'accuracy' in locals() else 0.0,
                dataset_path=data_file,
                explainability=explainability_data,
                metadata_path=metadata_path
            )
            self.db.add(db_version)
            self.db.flush()
            
            db_model.active_version_id = version_id
            self.job.output_model_id = registry_id
            self._log(f"Model successfully registered in ML Registry as {registry_id}")
            # --- End ML Registry Save ---
            
            # --- Generate UI Metrics and Feature Importance Logs ---
            metrics = {
                "ACCURACY": float(accuracy) if 'accuracy' in locals() else 0.0,
                "WIN_RATE": float(backtest_win_rate) if 'backtest_win_rate' in locals() else 0.0,
                "SHARPE_RATIO": float(backtest_sharpe) if 'backtest_sharpe' in locals() else 0.0,
                "NET_PROFIT": float(total_return) if 'total_return' in locals() else 0.0
            }
            self._log(f"[METRICS] {json.dumps(metrics)}")
            
            try:
                # Try to extract feature importances if the model supports it
                if hasattr(model, 'feature_importances_'):
                    importances = model.feature_importances_
                    feature_names = X.columns
                    # Create dictionary of feature importance
                    feat_imp = {feat: float(imp) for feat, imp in zip(feature_names, importances)}
                    # Sort and take top 5
                    top_5_features = dict(sorted(feat_imp.items(), key=lambda item: item[1], reverse=True)[:5])
                    self._log(f"[FEATURE_IMPORTANCE] {json.dumps(top_5_features)}")
            except Exception as e:
                self._log(f"Could not extract feature importance: {e}")
            # -----------------------------------------------------

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
