import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

from app.services.ml_architectures import TradingEnv

class StableBaselinesWrapper:
    """
    Scikit-Learn compatible wrapper for Reinforcement Learning (RL) agents via stable-baselines3.
    It encapsulates the environment creation and RL training loops.
    """
    def __init__(self, algo_name="PPO", total_timesteps=10000, **kwargs):
        self.algo_name = algo_name
        self.total_timesteps = total_timesteps
        self.model = None

    def fit(self, X: pd.DataFrame, y: pd.Series):
        try:
            from stable_baselines3 import PPO, SAC, A2C, DDPG, TD3, DQN
            # Map strings to classes
            algo_map = {
                'PPO': PPO,
                'SAC': SAC,
                'A2C': A2C,
                'DDPG': DDPG,
                'TD3': TD3,
                'DQN': DQN
            }
            
            # Create Custom Gym Environment for Trading
            env = TradingEnv(X=X.values, y=y.values)
            
            # Select algorithm
            RLClass = algo_map.get(self.algo_name.split('-')[0], PPO)
            
            # Initialize Agent
            self.model = RLClass("MlpPolicy", env, verbose=0)
            
            # Train Agent
            self.model.learn(total_timesteps=self.total_timesteps)
            
        except ImportError:
            print("Warning: stable_baselines3 not installed. Using dummy RL.")
            self.model = "dummy"
            
        return self

    def predict(self, X: pd.DataFrame):
        if self.model == "dummy":
            return np.random.choice([0, 1], size=len(X))
            
        env = TradingEnv(X=X.values)
        obs, _ = env.reset()
        
        preds = []
        done = False
        while not done:
            # Predict action from observation
            action, _states = self.model.predict(obs, deterministic=True)
            preds.append(action)
            obs, reward, done, truncated, info = env.step(action)
            if done or truncated:
                break
                
        # Ensure length matches X (env loop might be missing 1 step based on max_steps setup)
        preds = np.array(preds)
        if len(preds) < len(X):
            padding = [preds[-1]] * (len(X) - len(preds)) if len(preds) > 0 else [0]*len(X)
            preds = np.append(preds, padding)
            
        return preds

    def score(self, X: pd.DataFrame, y: pd.Series):
        preds = self.predict(X)
        return np.mean(preds == y.values)


# Explicit RL Wrappers for the Factory
class ForexPPORL(StableBaselinesWrapper):
    def __init__(self, **kwargs):
        super().__init__(algo_name="PPO", **kwargs)

class ForexSACRL(StableBaselinesWrapper):
    def __init__(self, **kwargs):
        print("Warning: SAC requires continuous action space. Falling back to PPO for discrete TradingEnv.")
        super().__init__(algo_name="PPO", **kwargs)

class ForexA2CRL(StableBaselinesWrapper):
    def __init__(self, **kwargs):
        super().__init__(algo_name="A2C", **kwargs)

class ForexDDPGRL(StableBaselinesWrapper):
    def __init__(self, **kwargs):
        print("Warning: DDPG requires continuous action space. Falling back to PPO for discrete TradingEnv.")
        super().__init__(algo_name="PPO", **kwargs)

class ForexTD3RL(StableBaselinesWrapper):
    def __init__(self, **kwargs):
        print("Warning: TD3 requires continuous action space. Falling back to PPO for discrete TradingEnv.")
        super().__init__(algo_name="PPO", **kwargs)

class ForexDQNRL(StableBaselinesWrapper):
    def __init__(self, **kwargs):
        super().__init__(algo_name="DQN", **kwargs)

class ForexAdvancedRL(StableBaselinesWrapper):
    # Fallback for QR-DQN, CQL, GAIL, Decision-Transformer using PPO for now 
    # until d3rlpy/custom offline RL libraries are fully wired up
    def __init__(self, algo_name="PPO", **kwargs):
        super().__init__(algo_name="PPO", **kwargs)
