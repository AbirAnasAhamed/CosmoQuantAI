from app.services.ml.forex_statistical_models import ForexARIMAModel, ForexVARModel, ForexNeuralProphetModel
from app.services.ml.forex_volatility_models import ForexGARCHModel, ForexEGARCHModel
from app.services.ml.forex_regime_models import ForexHMMModel, ForexMarkovSwitchingModel
from app.services.ml.forex_probabilistic_models import ForexBayesianNNModel

def get_forex_model(algorithm_name: str, config: dict = None):
    """
    Factory method to instantiate the correct ML model based on the algorithm name.
    Supports 31 different algorithms (Forex specific + Scikit-Learn + RL/DeepLearning fallbacks).
    """
    if config is None:
        config = {}

    # 1. Econometric & Statistical (Forex Core)
    if algorithm_name == 'ARIMA':
        return ForexARIMAModel()
    elif algorithm_name == 'VAR':
        return ForexVARModel()
    elif algorithm_name == 'GARCH':
        return ForexGARCHModel()
    elif algorithm_name == 'EGARCH':
        return ForexEGARCHModel()
    elif algorithm_name == 'NeuralProphet':
        return ForexNeuralProphetModel()
        
    # 2. Market Regime & Macro
    elif algorithm_name == 'HMM':
        return ForexHMMModel()
    elif algorithm_name == 'Markov-Switching':
        return ForexMarkovSwitchingModel()
    elif algorithm_name == 'Bayesian NN':
        return ForexBayesianNNModel()

    # Extract core parameters from frontend config
    n_estimators = config.get('n_estimators', config.get('epochs', 100))
    epochs = config.get('epochs', 10)
    tree_depth = config.get('tree_depth', None)
    # Some algorithms don't like max_depth=0 or None, handle accordingly per algo
    max_depth = tree_depth if tree_depth and tree_depth > 0 else None
    
    lr = config.get('learning_rate', 1e-3)
    batch_size = config.get('batch_size', 32)
    seq_len = config.get('sequence_length', 10)
    class_weight = config.get('class_weight', None)
    if class_weight == 'balanced':
        cw_param = 'balanced'
    else:
        cw_param = None

    # 3. Indicator & Tabular Engines (Scikit-Learn / Boosters)
    if algorithm_name == 'Random Forest':
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, class_weight=cw_param, random_state=42, n_jobs=1)
    elif algorithm_name == 'XGBoost':
        try:
            from xgboost import XGBClassifier
            return XGBClassifier(n_estimators=n_estimators, max_depth=max_depth or 6, learning_rate=lr, random_state=42, use_label_encoder=False, eval_metric='logloss')
        except ImportError:
            from sklearn.ensemble import GradientBoostingClassifier
            return GradientBoostingClassifier(n_estimators=n_estimators, max_depth=max_depth or 3, learning_rate=lr, random_state=42)
    elif algorithm_name == 'LightGBM':
        try:
            from lightgbm import LGBMClassifier
            return LGBMClassifier(n_estimators=n_estimators, max_depth=max_depth or -1, learning_rate=lr, class_weight=cw_param, random_state=42)
        except ImportError:
            from sklearn.ensemble import GradientBoostingClassifier
            return GradientBoostingClassifier(n_estimators=n_estimators, max_depth=max_depth or 3, learning_rate=lr, random_state=42)
    elif algorithm_name == 'CatBoost':
        try:
            from catboost import CatBoostClassifier
            return CatBoostClassifier(iterations=n_estimators, depth=max_depth or 6, learning_rate=lr, random_state=42, verbose=0)
        except ImportError:
            from sklearn.ensemble import GradientBoostingClassifier
            return GradientBoostingClassifier(n_estimators=n_estimators, max_depth=max_depth or 3, learning_rate=lr, random_state=42)
    elif algorithm_name == 'TabNet':
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, class_weight=cw_param, random_state=42, n_jobs=1)

    # 4. Deep Learning Models (Native PyTorch)
    elif algorithm_name == 'LSTM':
        from app.services.ml.forex_deep_learning_models import ForexLSTM
        return ForexLSTM(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif algorithm_name == 'GRU':
        from app.services.ml.forex_deep_learning_models import ForexGRU
        return ForexGRU(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif algorithm_name == 'TCN':
        from app.services.ml.forex_deep_learning_models import ForexTCN
        return ForexTCN(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif algorithm_name == '1D-CNN':
        from app.services.ml.forex_deep_learning_models import ForexCNN1D
        return ForexCNN1D(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif algorithm_name == 'DeepLOB':
        from app.services.ml.forex_deep_learning_models import ForexDeepLOB
        return ForexDeepLOB(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif algorithm_name == 'Transformer':
        from app.services.ml.forex_deep_learning_models import ForexTransformer
        return ForexTransformer(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif algorithm_name == 'Auto-Encoder':
        from app.services.ml.forex_deep_learning_models import ForexAutoEncoder
        return ForexAutoEncoder(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif algorithm_name == 'Liquid-NN':
        from app.services.ml.forex_deep_learning_models import ForexLiquidNN
        return ForexLiquidNN(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)

    # 5. Reinforcement Learning Models (Native stable-baselines3)
    elif algorithm_name == 'PPO-RL':
        from app.services.ml.forex_rl_models import ForexPPORL
        return ForexPPORL(epochs=epochs)
    elif algorithm_name == 'SAC-RL':
        from app.services.ml.forex_rl_models import ForexSACRL
        return ForexSACRL(epochs=epochs)
    elif algorithm_name == 'A2C-RL':
        from app.services.ml.forex_rl_models import ForexA2CRL
        return ForexA2CRL(epochs=epochs)
    elif algorithm_name == 'DDPG-RL':
        from app.services.ml.forex_rl_models import ForexDDPGRL
        return ForexDDPGRL(epochs=epochs)
    elif algorithm_name == 'TD3-RL':
        from app.services.ml.forex_rl_models import ForexTD3RL
        return ForexTD3RL(epochs=epochs)
    elif algorithm_name == 'DQN-RL':
        from app.services.ml.forex_rl_models import ForexDQNRL
        return ForexDQNRL(epochs=epochs)
    elif algorithm_name in ['QR-DQN', 'CQL', 'GAIL', 'Decision-Transformer']:
        from app.services.ml.forex_rl_models import ForexAdvancedRL
        return ForexAdvancedRL(algo_name=algorithm_name, epochs=epochs)
    else:
        print(f"Algorithm '{algorithm_name}' not natively supported in Forex Engine yet. Falling back to Random Forest.")
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42, n_jobs=1)
