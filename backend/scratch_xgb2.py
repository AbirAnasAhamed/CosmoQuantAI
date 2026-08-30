import numpy as np
from xgboost import XGBClassifier

X = np.random.rand(10, 5)
y = np.array([0, 2, 0, 2, 0, 2, 0, 2, 0, 2]) # ONLY 0 and 2

clf = XGBClassifier(
    n_estimators=10, 
    max_depth=6, 
    learning_rate=0.01, 
    random_state=42, 
    use_label_encoder=False, 
    eval_metric='logloss'
)

print("Fitting with [0, 2]...")
clf.fit(X, y)
print("Done!")
