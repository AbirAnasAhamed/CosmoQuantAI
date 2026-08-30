import pandas as pd
import numpy as np

# Create a dummy dataframe with 10 features, all highly correlated
np.random.seed(42)
x1 = np.random.randn(100)
data = {
    'feat1': x1,
    'feat2': x1 + np.random.randn(100)*0.01,
    'feat3': x1 + np.random.randn(100)*0.01,
    'feat4': x1 + np.random.randn(100)*0.01,
    'macro_risk_flag': np.random.randn(100) # not correlated
}
df = pd.DataFrame(data)

corr_matrix = df.corr().abs()
upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
to_drop = [column for column in upper.columns if any(upper[column] > 0.85)]
print("To drop:", to_drop)
print("Kept:", [c for c in df.columns if c not in to_drop])
