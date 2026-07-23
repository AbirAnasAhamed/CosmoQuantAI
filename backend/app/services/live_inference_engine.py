import asyncio
import json
import os
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from app.db.session import SessionLocal
from app import models

class LiveFeatureExtractor:
    def __init__(self, metadata: Dict[str, Any]):
        self.metadata = metadata
        self.features = metadata.get("features", [])
        self.target_columns = metadata.get("target_column", [])
        self.state = {} # Keep rolling history if needed (e.g., last 100 candles for RSI)
        
        self.scaler = None
        scaler_path = metadata.get("scaler_path")
        if scaler_path:
            # Need to resolve correct absolute path inside docker
            abs_scaler_path = os.path.join("/app", scaler_path) if not scaler_path.startswith("/") else scaler_path
            if os.path.exists(abs_scaler_path):
                try:
                    self.scaler = joblib.load(abs_scaler_path)
                    print(f"[LiveFeatureExtractor] Scaler loaded from {abs_scaler_path}")
                except Exception as e:
                    print(f"[LiveFeatureExtractor] Failed to load scaler: {e}")
            else:
                print(f"[LiveFeatureExtractor] Scaler path not found: {abs_scaler_path}")
        
    def process_tick(self, market_data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        # Here we maintain a rolling buffer of market data (candles, orderbook)
        # and calculate the required features dynamically.
        # For simplicity in this skeleton, we extract directly if available,
        # or pad with 0.0 to match the exact feature shape the model expects.
        
        row = {}
        for feature in self.features:
            # Try to get from market data or state
            row[feature] = market_data.get(feature, 0.0)
            
        df = pd.DataFrame([row])
        
        if self.scaler is not None and hasattr(self.scaler, 'transform'):
            try:
                # The scaler might expect specific column names or order
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    scaled_values = self.scaler.transform(df.values)
                df = pd.DataFrame(scaled_values, columns=df.columns)
            except Exception as e:
                print(f"[LiveFeatureExtractor] Scaling error: {e}")
                
        return df

class LiveInferenceEngine:
    def __init__(self):
        self.active_model_id = None
        self.model = None
        self.extractor = None
        self.metadata = None
        self.is_running = False
        self._last_prediction_time = 0
        self.throttle_ms = 1000 # 1 second throttle

    def load_model(self, model_id: str) -> bool:
        if self.active_model_id == model_id and self.model is not None:
            return True
            
        db = SessionLocal()
        try:
            db_model = db.query(models.CustomMLModel).filter(models.CustomMLModel.id == model_id).first()
            if not db_model or not db_model.active_version_id:
                print(f"[InferenceEngine] Model {model_id} not found or no active version.")
                return False
                
            version = db.query(models.ModelVersion).filter(models.ModelVersion.id == db_model.active_version_id).first()
            if not version or not os.path.exists(version.file_path):
                print(f"[InferenceEngine] Model file missing for {model_id}.")
                return False
                
            # Load metadata
            meta = {}
            if version.metadata_path and os.path.exists(version.metadata_path):
                with open(version.metadata_path, 'r') as f:
                    meta = json.load(f)
                    
            print(f"[InferenceEngine] Loading model {model_id} from {version.file_path}")
            
            try:
                algorithm = meta.get("algorithm", "")
                rl_algos = ["PPO-RL", "SAC-RL", "A2C-RL", "DDPG-RL", "DQN-RL", "TD3-RL"]
                
                if algorithm in rl_algos:
                    from stable_baselines3 import PPO, SAC, A2C, DDPG, DQN, TD3
                    algo_map = {
                        "PPO-RL": PPO, "SAC-RL": SAC, "A2C-RL": A2C,
                        "DDPG-RL": DDPG, "DQN-RL": DQN, "TD3-RL": TD3
                    }
                    ModelClass = algo_map.get(algorithm)
                    if ModelClass:
                        self.model = ModelClass.load(version.file_path)
                    else:
                        print(f"[InferenceEngine] Unsupported RL algorithm: {algorithm}")
                        return False
                elif algorithm in ["1D-CNN", "LSTM", "GRU"]:
                    # Placeholder for PyTorch models
                    print(f"[InferenceEngine] Dynamic PyTorch loading not yet implemented for live inference.")
                    return False
                else:
                    # Load joblib/pickle model
                    self.model = joblib.load(version.file_path)
            except Exception as e:
                print(f"[InferenceEngine] Failed to load model file: {e}")
                return False
                
            self.metadata = meta
            self.extractor = LiveFeatureExtractor(meta)
            self.active_model_id = model_id
            return True
        finally:
            db.close()

    def process_market_data(self, market_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Called when new market data (tick/candle) arrives.
        Returns predicted TP/SL if inference runs.
        """
        if not self.model or not self.extractor:
            return None
            
        current_time = asyncio.get_event_loop().time() * 1000
        if current_time - self._last_prediction_time < self.throttle_ms:
            # Throttled
            return None
            
        self._last_prediction_time = current_time
        
        # 1. Feature Extraction
        features_df = self.extractor.process_tick(market_data)
        if features_df is None:
            return None
            
        # 2. Prediction
        try:
            algorithm = self.metadata.get("algorithm", "")
            rl_algos = ["PPO-RL", "SAC-RL", "A2C-RL", "DDPG-RL", "DQN-RL", "TD3-RL"]
            
            if algorithm in rl_algos:
                obs = features_df.values
                action, _ = self.model.predict(obs, deterministic=True)
                preds = action
                
                # RL Scaling Logic for advanced_setup
                if self.metadata.get("prediction_target") == "advanced_setup" and isinstance(action, (list, np.ndarray)):
                    if len(action.shape) > 1:
                        action = action[0]
                    
                    # Extract current price from market data
                    current_price = float(market_data.get("currentPrice", market_data.get("price", market_data.get("Close", market_data.get("midPrice", 0.0)))))
                    
                    # Debug log
                    print(f"[InferenceEngine] Action: {action}, len: {len(action)}, price: {current_price}")
                    
                    if len(action) >= 3 and current_price > 0:
                        sl_dist = max(0.001, (action[1] + 1.0) / 2.0 * 0.1 * current_price)
                        tp_dist = max(0.001, (action[2] + 1.0) / 2.0 * 0.1 * current_price)
                        
                        action_val = action[0]
                    elif len(action) == 1 and current_price > 0:
                        # Legacy models trained without proper action space shape
                        sl_dist = 0.005 * current_price
                        tp_dist = 0.005 * current_price
                        action_val = action[0]
                    else:
                        print(f"[InferenceEngine] Failed condition: len(action)={len(action)}, current_price={current_price} > 0")
                        return {}
                    
                    if action_val > 0.33: # Long
                        target_tp = current_price + tp_dist
                        target_sl = current_price - sl_dist
                    elif action_val < -0.33: # Short
                        target_tp = current_price - tp_dist
                        target_sl = current_price + sl_dist
                    else: # Neutral
                        target_tp = current_price + tp_dist
                        target_sl = current_price - sl_dist
                        
                    result_dict = {
                        "Target_TP": float(target_tp),
                        "Target_SL": float(target_sl)
                    }
                    print(f"[InferenceEngine] Returning RL Result: {result_dict}")
                    return result_dict
            else:
                preds = self.model.predict(features_df)
            
            # Format output based on metadata target columns
            result = {}
            
            if isinstance(preds, (list, np.ndarray)):
                if len(preds.shape) > 1:
                    preds = preds[0]
                    
                target_cols = self.metadata.get("target_column", [])
                prediction_target = self.metadata.get("prediction_target", "")
                
                if prediction_target == "advanced_setup" and len(preds) >= 3:
                    direction = float(preds[0]) # 1.0 (Long) or 0.0 (Short)
                    sl_raw = float(preds[1])
                    tp_raw = float(preds[2])
                    
                    current_price = float(market_data.get("currentPrice", market_data.get("price", market_data.get("Close", market_data.get("midPrice", 0.0)))))
                    
                    if current_price > 0:
                        # If values are < 1.0, they were likely MinMax scaled. Treat as percentage of a 5% move.
                        # If values are > 1.0, they are likely absolute price distances.
                        sl_dist = sl_raw if sl_raw > 1.0 else max(0.001, sl_raw * 0.05 * current_price)
                        tp_dist = tp_raw if tp_raw > 1.0 else max(0.001, tp_raw * 0.05 * current_price)
                        
                        if direction >= 0.5: # Long
                            target_tp = current_price + tp_dist
                            target_sl = current_price - sl_dist
                        else: # Short
                            target_tp = current_price - tp_dist
                            target_sl = current_price + sl_dist
                            
                        result = {
                            "Target_TP": float(target_tp),
                            "Target_SL": float(target_sl)
                        }
                        print(f"[InferenceEngine] Returning Multi-Output Result: {result}")
                        return result

                if isinstance(target_cols, list) and len(target_cols) > 0:
                    for i, col in enumerate(target_cols):
                        if i < len(preds):
                            result[col] = float(preds[i])
                else:
                    # Fallback mapping if targets aren't clearly defined
                    if len(preds) >= 2:
                        if len(preds) == 2:
                            result["Target_TP"] = float(preds[0])
                            result["Target_SL"] = float(preds[1])
                        else:
                            result["Target_TP"] = float(preds[1])
                            result["Target_SL"] = float(preds[2])
                        
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[InferenceEngine] Prediction error: {e}")
            return None

# Global Singleton Instance
inference_engine = LiveInferenceEngine()
