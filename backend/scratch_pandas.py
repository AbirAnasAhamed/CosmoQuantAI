import pandas as pd
import numpy as np

X_train = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
y_train = pd.Series([0, 2])

missing_classes = [1]
for mc in missing_classes:
    X_train = pd.concat([X_train, X_train.iloc[0:1].copy()], ignore_index=True)
    y_train = pd.concat([y_train, pd.Series([mc])], ignore_index=True) if isinstance(y_train, pd.Series) else np.append(y_train, mc)

print("X_train:")
print(X_train)
print("y_train:")
print(y_train)
print("y_train unique:", np.unique(y_train))
