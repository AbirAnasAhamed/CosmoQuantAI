import pandas as pd
import numpy as np

def apply_imbalance_strategy(X, y, strategy="none", log_func=None):
    """
    Applies class imbalance handling strategies to the training data.
    """
    if log_func:
        log_func(f"Applying class imbalance strategy: {strategy}")

    if strategy == "none" or strategy is None:
        return X, y
        
    # Check if we have at least 2 classes
    try:
        unique_classes = np.unique(y)
        if len(unique_classes) <= 1:
            if log_func:
                log_func("Only one class present in target. Skipping imbalance handling.")
            return X, y
    except Exception as e:
        pass

    try:
        if strategy == "smote":
            from imblearn.over_sampling import SMOTE
            smote = SMOTE(random_state=42)
            X_resampled, y_resampled = smote.fit_resample(X, y)
        elif strategy == "adasyn":
            from imblearn.over_sampling import ADASYN
            adasyn = ADASYN(random_state=42)
            X_resampled, y_resampled = adasyn.fit_resample(X, y)
        elif strategy == "random_oversample":
            from imblearn.over_sampling import RandomOverSampler
            ros = RandomOverSampler(random_state=42)
            X_resampled, y_resampled = ros.fit_resample(X, y)
        elif strategy == "random_undersample":
            from imblearn.under_sampling import RandomUnderSampler
            rus = RandomUnderSampler(random_state=42)
            X_resampled, y_resampled = rus.fit_resample(X, y)
        elif strategy == "class_weights":
            # Class weights are typically handled in the model fit parameters,
            # so we don't modify X and y here. We just return them as is.
            if log_func:
                log_func("Class weights strategy selected. Please ensure your model handles class weights.")
            return X, y
        else:
            if log_func:
                log_func(f"Unknown strategy '{strategy}'. Skipping imbalance handling.")
            return X, y

        if log_func:
            log_func(f"Imbalance handling complete. Original shape: {X.shape}, New shape: {X_resampled.shape}")
        
        return X_resampled, y_resampled

    except ImportError:
        if log_func:
            log_func("imblearn library not found. Falling back to original data. Run 'pip install imbalanced-learn'.")
        return X, y
    except Exception as e:
        if log_func:
            log_func(f"Error applying imbalance strategy: {e}. Falling back to original data.")
        return X, y
