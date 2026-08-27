import sys

imports_to_test = [
    "app.services.economic_service.economic_service",
    "app.services.ml.forex_model_factory.get_forex_model",
    "app.services.ml.forex_feature_engine.generate_ohlcv_features",
    "app.services.ml.hybrid_feature_engine.generate_hybrid_features",
    "app.services.ml.forex_l2_feature_engine.generate_all_l2_features",
    "app.services.ml.triple_barrier.apply_triple_barrier",
    "app.services.helpers.ml_advanced_setup_target.generate_advanced_setup_targets",
    "app.services.ml_fractional_diff.apply_fractional_differentiation",
    "app.services.ml_utils.apply_missing_data_threshold",
    "app.services.ml_utils.apply_pca_orthogonalization",
    "app.services.ml_utils.apply_shap_feature_selection",
    "app.services.ml_utils.apply_auto_feature_selection",
    "app.services.ml.feature_selection.select_features",
    "app.services.advanced_ml.moe_engine.RLMoEEngine",
    "app.services.ml_data_prep.apply_data_split",
    "app.services.ml_imbalance.apply_imbalance_strategy",
    "app.services.ml_augmentation.apply_data_augmentation",
    "app.services.ml.optuna_optimizer.run_optuna_study",
    "app.services.ml.wfo_validator.walk_forward_split",
    "app.services.ml.meta_labeler.train_meta_model"
]

missing = []
for mod_str in imports_to_test:
    parts = mod_str.rsplit('.', 1)
    mod_name = parts[0]
    try:
        __import__(mod_name)
    except ImportError as e:
        missing.append(f"{mod_name}: {e}")

if missing:
    print("MISSING IMPORTS:")
    for m in missing:
        print(m)
else:
    print("All dynamic imports successful.")
