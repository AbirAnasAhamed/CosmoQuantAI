def calculate_training_eta(algorithm: str, dataset_shape: tuple, config: dict) -> str:
    """
    Heuristically estimates the time required to train a machine learning model 
    based on algorithm complexity, dataset size, and advanced pipeline configurations.
    
    Args:
        algorithm (str): The name of the algorithm (e.g., 'Random Forest', 'LSTM', 'PPO')
        dataset_shape (tuple): The shape of the training data (n_samples, n_features)
        config (dict): The job configuration dictionary containing flags like 'use_automl', 'split_method', etc.
        
    Returns:
        str: A human-readable estimated time range (e.g., "~2-3 minutes").
    """
    n_samples, n_features = dataset_shape
    
    # 1. Base time estimation (in seconds)
    # Assumes a very rough baseline: 10,000 samples with 50 features takes ~5 seconds for a simple ML model.
    base_factor = (n_samples * n_features) / (10000 * 50)
    base_time = max(2.0, base_factor * 5.0) 
    
    def get_algorithm_multiplier(algo_name: str) -> float:
        algo_upper = algo_name.upper()
        mult = 1.0
        if any(dl in algo_upper for dl in ['LSTM', 'GRU', 'CNN', 'TCN', 'TRANSFORMER', 'AUTOENCODER', 'DEEPLOB', 'LIQUIDNN']):
            mult *= 15.0
        elif any(rl in algo_upper for rl in ['PPO', 'SAC', 'A2C', 'DDPG', 'TD3', 'DQN', '-RL']):
            mult *= 25.0
        elif any(stat in algo_upper for stat in ['ARIMA', 'VAR', 'GARCH', 'HMM', 'MARKOV', 'PROPHET']):
            mult *= 8.0
        elif any(tree in algo_upper for tree in ['XGBOOST', 'LIGHTGBM', 'CATBOOST']):
            mult *= 2.0
        return mult

    # 2. Algorithm Complexity Multiplier
    is_ensemble = config.get('is_ensemble', False)
    ensemble_method = config.get('ensemble_method', 'voting')
    
    total_multiplier = 0.0
    
    if is_ensemble:
        if ensemble_method in ['voting', 'stacking']:
            base_models = config.get("base_models", ["Random Forest", "XGBoost"])
            for base_algo in base_models:
                total_multiplier += get_algorithm_multiplier(base_algo)
                
            if ensemble_method == 'stacking':
                meta_algo = config.get("meta_model", "Logistic Regression")
                total_multiplier += get_algorithm_multiplier(meta_algo)
        elif ensemble_method == 'rl_moe':
            rl_algo = config.get("rlAlgorithm", "PPO")
            total_multiplier += get_algorithm_multiplier(rl_algo) * 1.5 # MoE overhead
        else:
            total_multiplier += get_algorithm_multiplier(algorithm)
    else:
        total_multiplier += get_algorithm_multiplier(algorithm)
    
    estimated_seconds = base_time * total_multiplier
    
    # 3. Pipeline Features Multiplier
    if config.get('use_automl', False):
        n_trials = int(config.get('automl_trials', 50))
        estimated_seconds *= (n_trials * 0.4) # Assume 40% of full training time per trial due to early stopping/pruning
        
    split_method = config.get('split_method', 'chronological')
    if split_method == 'walk_forward':
        cv_splits = int(config.get('walk_forward_splits', 5))
        estimated_seconds *= cv_splits
        
    if config.get('enable_meta_labeling', False):
        estimated_seconds *= 1.5 # Extra model training
        
    if config.get('apply_shap_selection', True):
        # SHAP calculation requires a dummy RF training + explainer
        estimated_seconds += max(10, base_factor * 15.0)
        
    # 4. Add fixed initialization overhead for heavy libraries (PyTorch, Stable-Baselines)
    overhead_seconds = 0
    if is_ensemble:
        base_models = config.get("base_models", [])
        if any(any(dl in m.upper() for dl in ['LSTM', 'GRU', 'CNN', 'TRANSFORMER']) for m in base_models):
            overhead_seconds += 60 # 1 min overhead for DL
        if any(any(rl in m.upper() for rl in ['PPO', 'SAC', 'A2C', 'DDPG', 'TD3', '-RL']) for m in base_models):
            overhead_seconds += 300 # 5 min overhead per RL agent
    else:
        if any(dl in algo_upper for dl in ['LSTM', 'GRU', 'CNN', 'TRANSFORMER']):
            overhead_seconds += 60
        if any(rl in algo_upper for rl in ['PPO', 'SAC', 'A2C', 'DDPG', 'TD3', '-RL']):
            overhead_seconds += 300
            
    estimated_seconds += overhead_seconds
    
    # 5. Format into human-readable string
    min_seconds = int(estimated_seconds * 0.8) # 20% margin of error
    max_seconds = int(estimated_seconds * 1.2)
    
    if max_seconds < 60:
        return f"~{min_seconds} to {max_seconds} seconds"
    else:
        min_mins = max(1, min_seconds // 60)
        max_mins = max(2, max_seconds // 60)
        
        if max_mins > 60:
            min_hrs = round(min_mins / 60, 1)
            max_hrs = round(max_mins / 60, 1)
            return f"~{min_hrs} to {max_hrs} hours"
        else:
            return f"~{min_mins} to {max_mins} minutes"
