from app.services.ml.forex_statistical_models import ForexARIMAModel, ForexVARModel, ForexNeuralProphetModel
from app.services.ml.forex_volatility_models import ForexGARCHModel, ForexEGARCHModel
from app.services.ml.market_regime_models import MarketHMMModel, MarketMarkovSwitchingModel
from app.services.ml.market_probabilistic_models import MarketBayesianNNModel

try:
    from catboost import CatBoostClassifier, CatBoostRegressor
    from sklearn.dummy import DummyClassifier, DummyRegressor

    class FlatCatBoostClassifier(CatBoostClassifier):
        def fit(self, X, y=None, **fit_params):
            try:
                super().fit(X, y, **fit_params)
                self._fallback_model = None
            except Exception:
                self._fallback_model = DummyClassifier(strategy='prior')
                self._fallback_model.fit(X, y)
            return self

        def predict(self, X):
            if getattr(self, '_fallback_model', None) is not None:
                return self._fallback_model.predict(X)
            p = super().predict(X)
            if len(p.shape) > 1 and p.shape[1] == 1:
                return p.flatten()
            return p
            
        def predict_proba(self, X):
            if getattr(self, '_fallback_model', None) is not None:
                return self._fallback_model.predict_proba(X)
            return super().predict_proba(X)
            
        @property
        def classes_(self):
            if getattr(self, '_fallback_model', None) is not None:
                return self._fallback_model.classes_
            return super().classes_

    class FlatCatBoostRegressor(CatBoostRegressor):
        def fit(self, X, y=None, **fit_params):
            try:
                super().fit(X, y, **fit_params)
                self._fallback_model = None
            except Exception:
                self._fallback_model = DummyRegressor(strategy='mean')
                self._fallback_model.fit(X, y)
            return self

        def predict(self, X):
            if getattr(self, '_fallback_model', None) is not None:
                return self._fallback_model.predict(X)
            return super().predict(X)
except ImportError:
    CatBoostClassifier = None
    CatBoostRegressor = None
    FlatCatBoostClassifier = None
    FlatCatBoostRegressor = None

def get_forex_model(algorithm_name: str, config: dict = None):
    """
    Factory method to instantiate the correct ML model based on the algorithm name.
    Supports 31 different algorithms (Forex specific + Scikit-Learn + RL/DeepLearning fallbacks).
    """
    if config is None:
        config = {}

    base_algo = algorithm_name.replace("Crypto", "").replace("Forex", "").replace(" ", "").strip()
    
    # Re-add space for specific names if needed or just use original for sklearn models
    if algorithm_name in ["Random Forest", "Logistic Regression", "Bayesian NN", "Markov-Switching", "Neural Network (MLP)"]:
        base_algo = algorithm_name
        
    # Also handle some edge cases
    if base_algo == "LSTM": pass # example

    # 1. Econometric & Statistical (Forex Core)
    if base_algo == 'ARIMA':
        return ForexARIMAModel()
    elif base_algo == 'VAR':
        return ForexVARModel()
    elif base_algo == 'GARCH':
        return ForexGARCHModel()
    elif base_algo == 'EGARCH':
        return ForexEGARCHModel()
    elif base_algo == 'NeuralProphet':
        return ForexNeuralProphetModel()
        
    # 2. Market Regime & Macro
    elif base_algo == 'HMM':
        return MarketHMMModel()
    elif base_algo == 'Markov-Switching':
        return MarketMarkovSwitchingModel()
    elif base_algo == 'Bayesian NN':
        return MarketBayesianNNModel()

    # Extract core parameters from frontend config
    prediction_target = config.get('prediction_target', 'classification')
    is_clf = prediction_target in ['classification', 'advanced_setup', 'direction', 'multi_task'] or config.get("use_triple_barrier", False)
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
    if base_algo == 'Random Forest':
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        if is_clf:
            return RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, class_weight=cw_param, random_state=42, n_jobs=1)
        return RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42, n_jobs=1)
        
    elif base_algo == 'XGBoost':
        try:
            from xgboost import XGBClassifier, XGBRegressor
            if is_clf:
                return XGBClassifier(n_estimators=n_estimators, max_depth=max_depth or 6, learning_rate=lr, random_state=42, use_label_encoder=False, eval_metric='logloss')
            return XGBRegressor(n_estimators=n_estimators, max_depth=max_depth or 6, learning_rate=lr, random_state=42)
        except ImportError:
            from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
            if is_clf:
                return GradientBoostingClassifier(n_estimators=n_estimators, max_depth=max_depth or 3, learning_rate=lr, random_state=42)
            return GradientBoostingRegressor(n_estimators=n_estimators, max_depth=max_depth or 3, learning_rate=lr, random_state=42)
            
    elif base_algo == 'LightGBM':
        try:
            from lightgbm import LGBMClassifier, LGBMRegressor
            if is_clf:
                return LGBMClassifier(n_estimators=n_estimators, max_depth=max_depth or -1, learning_rate=lr, class_weight=cw_param, random_state=42)
            return LGBMRegressor(n_estimators=n_estimators, max_depth=max_depth or -1, learning_rate=lr, random_state=42)
        except ImportError:
            from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
            if is_clf:
                return GradientBoostingClassifier(n_estimators=n_estimators, max_depth=max_depth or 3, learning_rate=lr, random_state=42)
            return GradientBoostingRegressor(n_estimators=n_estimators, max_depth=max_depth or 3, learning_rate=lr, random_state=42)
            
    elif base_algo == 'CatBoost':
        if FlatCatBoostClassifier is not None:
            if is_clf:
                return FlatCatBoostClassifier(iterations=n_estimators, depth=max_depth or 6, learning_rate=lr, random_state=42, verbose=0)
            return FlatCatBoostRegressor(iterations=n_estimators, depth=max_depth or 6, learning_rate=lr, random_state=42, verbose=0)
        else:
            from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
            if is_clf:
                return GradientBoostingClassifier(n_estimators=n_estimators, max_depth=max_depth or 3, learning_rate=lr, random_state=42)
            return GradientBoostingRegressor(n_estimators=n_estimators, max_depth=max_depth or 3, learning_rate=lr, random_state=42)
            
    elif base_algo == 'TabNet':
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        if is_clf:
            return RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, class_weight=cw_param, random_state=42, n_jobs=1)
        return RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42, n_jobs=1)
        
    elif base_algo == 'Logistic Regression':
        from sklearn.linear_model import LogisticRegression, LinearRegression
        if is_clf:
            return LogisticRegression(class_weight=cw_param, random_state=42, max_iter=1000)
        return LinearRegression()
        
    elif base_algo in ['SVM', 'Support Vector Machine']:
        from sklearn.svm import SVC, SVR
        if is_clf:
            return SVC(class_weight=cw_param, random_state=42, probability=True)
        return SVR()
        
    elif base_algo == 'Neural Network (MLP)' or 'MLP' in base_algo:
        from sklearn.neural_network import MLPClassifier, MLPRegressor
        if is_clf:
            return MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=epochs if epochs > 200 else 500, random_state=42)
        return MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=epochs if epochs > 200 else 500, random_state=42)

    # 4. Deep Learning Models (Native PyTorch)
    elif base_algo == 'LSTM':
        from app.services.ml.forex_deep_learning_models import ForexLSTM
        return ForexLSTM(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif base_algo == 'GRU':
        from app.services.ml.forex_deep_learning_models import ForexGRU
        return ForexGRU(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif base_algo == 'TCN':
        from app.services.ml.forex_deep_learning_models import ForexTCN
        return ForexTCN(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif base_algo == '1D-CNN':
        from app.services.ml.forex_deep_learning_models import ForexCNN1D
        return ForexCNN1D(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif base_algo == 'DeepLOB':
        from app.services.ml.forex_deep_learning_models import ForexDeepLOB
        return ForexDeepLOB(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif base_algo == 'Transformer':
        from app.services.ml.forex_deep_learning_models import ForexTransformer
        return ForexTransformer(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif base_algo == 'Auto-Encoder':
        from app.services.ml.forex_deep_learning_models import ForexAutoEncoder
        return ForexAutoEncoder(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)
    elif base_algo == 'Liquid-NN':
        from app.services.ml.forex_deep_learning_models import ForexLiquidNN
        return ForexLiquidNN(epochs=epochs, seq_len=seq_len, batch_size=batch_size, lr=lr)

    # 5. Reinforcement Learning Models (Native stable-baselines3)
    elif base_algo == 'PPO-RL':
        from app.services.ml.forex_rl_models import ForexPPORL
        return ForexPPORL(epochs=epochs)
    elif base_algo == 'SAC-RL':
        from app.services.ml.forex_rl_models import ForexSACRL
        return ForexSACRL(epochs=epochs)
    elif base_algo == 'A2C-RL':
        from app.services.ml.forex_rl_models import ForexA2CRL
        return ForexA2CRL(epochs=epochs)
    elif base_algo == 'DDPG-RL':
        from app.services.ml.forex_rl_models import ForexDDPGRL
        return ForexDDPGRL(epochs=epochs)
    elif base_algo == 'TD3-RL':
        from app.services.ml.forex_rl_models import ForexTD3RL
        return ForexTD3RL(epochs=epochs)
    elif base_algo == 'DQN-RL':
        from app.services.ml.forex_rl_models import ForexDQNRL
        return ForexDQNRL(epochs=epochs)
    elif base_algo in ['QR-DQN', 'CQL', 'GAIL', 'Decision-Transformer']:
        from app.services.ml.forex_rl_models import ForexAdvancedRL
        return ForexAdvancedRL(algo_name=base_algo, epochs=epochs)
    else:
        raise ValueError(f"Algorithm '{algorithm_name}' not natively supported in Engine.")
