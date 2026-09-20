import pickle
import json
import numpy as np

dir_path = "/app/uploads/models/forex_forex_train_1789924234240/"

with open(dir_path + "forex_train_1789924234240_EUR_USD.pkl", "rb") as f:
    model = pickle.load(f)

with open(dir_path + "forex_train_1789924234240_meta_EUR_USD.pkl", "rb") as f:
    meta_model = pickle.load(f)

with open(dir_path + "forex_train_1789924234240_EUR_USD_metadata.json", "r") as f:
    metadata = json.load(f)

print("Base model type:", type(model))
if hasattr(model, "feature_importances_"):
    importances = model.feature_importances_
    features = metadata.get("features", [])
    if len(features) == len(importances):
        imp = sorted(zip(features, importances), key=lambda x: x[1], reverse=True)
        print("Base Model Top 10 Feature Importances:")
        for f, i in imp[:10]:
            print(f"  {f}: {i}")
        print("Number of non-zero importances:", sum(1 for x in importances if x > 0))
    else:
        print(f"Feature count mismatch: {len(features)} vs {len(importances)}")
        print("Importances:", importances)
else:
    print("Base model has no feature_importances_")

print("\nMeta model type:", type(meta_model))
if hasattr(meta_model, "feature_importances_"):
    importances = meta_model.feature_importances_
    print("Meta Model Importances:", importances)
elif hasattr(meta_model, "coef_"):
    print("Meta Model Coef:", meta_model.coef_)
else:
    print("Meta model has no importances/coef")
