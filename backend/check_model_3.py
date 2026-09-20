import joblib
import json
import numpy as np
import os

dir_path = "/app/uploads/models/forex_forex_train_1789928935002/"
files = os.listdir(dir_path)

base_model_file = [f for f in files if f.endswith("_EUR_USD.pkl") and "meta" not in f][0]
meta_model_file = [f for f in files if "meta_EUR_USD.pkl" in f][0]
metadata_file = [f for f in files if f.endswith("_metadata.json")][0]

try:
    model = joblib.load(os.path.join(dir_path, base_model_file))
    print("Base model type:", type(model))
    
    with open(os.path.join(dir_path, metadata_file), "r") as f:
        metadata = json.load(f)

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

except Exception as e:
    print("Error loading base model:", e)

try:
    meta_model = joblib.load(os.path.join(dir_path, meta_model_file))
    print("\nMeta model type:", type(meta_model))
    if hasattr(meta_model, "feature_importances_"):
        importances = meta_model.feature_importances_
        print("Meta Model Importances:", importances)
    elif hasattr(meta_model, "coef_"):
        print("Meta Model Coef:", meta_model.coef_)
    else:
        print("Meta model has no importances/coef")
except Exception as e:
    print("Error loading meta model:", e)
