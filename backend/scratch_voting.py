import numpy as np
import pandas as pd
from sklearn.ensemble import VotingClassifier
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier

X_train = pd.DataFrame(np.random.rand(10, 5))
y_train = np.array([0, 2, 0, 2, 0, 2, 0, 2, 0, 2])

target_classes = np.array([0, 1, 2])
unique_classes = np.unique(y_train)

missing_classes = np.setdiff1d(target_classes, unique_classes)

if len(missing_classes) > 0:
    for mc in missing_classes:
        X_train = pd.concat([X_train, X_train.iloc[0:1].copy()], ignore_index=True)
        y_train = np.append(y_train, mc)

print("y_train unique:", np.unique(y_train))

model = VotingClassifier(
    estimators=[
        ('rf', RandomForestClassifier()),
        ('xgb', XGBClassifier(use_label_encoder=False, eval_metric='logloss'))
    ],
    voting='soft'
)

print("Fitting...")
model.fit(X_train, y_train)
print("Done!")
