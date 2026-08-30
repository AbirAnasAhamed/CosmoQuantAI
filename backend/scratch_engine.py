import numpy as np
import pandas as pd
from xgboost import XGBClassifier

# Simulate X_train and y_train right before injection
X_train = np.random.rand(10, 5)
y_train = np.array([0, 2, 0, 2, 0, 2, 0, 2, 0, 2])

target_classes = np.array([0, 1, 2])
unique_classes = np.unique(y_train)

missing_classes = np.setdiff1d(target_classes, unique_classes)
print("Missing classes:", missing_classes)

if len(missing_classes) > 0:
    if isinstance(X_train, pd.DataFrame):
        for mc in missing_classes:
            X_train = pd.concat([X_train, X_train.iloc[0:1].copy()], ignore_index=True)
            y_train = pd.concat([y_train, pd.Series([mc])], ignore_index=True) if isinstance(y_train, pd.Series) else np.append(y_train, mc)
    else:
        for mc in missing_classes:
            X_train = np.vstack([X_train, X_train[0]])
            y_train = np.append(y_train, mc)

print("y_train after injection:", y_train)

model = XGBClassifier(
    n_estimators=10, 
    max_depth=6, 
    learning_rate=0.01, 
    random_state=42, 
    use_label_encoder=False, 
    eval_metric='logloss'
)

print("Fitting...")
model.fit(X_train, y_train)
print("Done!")
