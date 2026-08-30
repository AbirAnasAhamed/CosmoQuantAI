import joblib
import sys
import os

model_path = r"/app/uploads/models/forex_forex_train_1788009559292/forex_train_1788009559292_EUR_USD.pkl"
try:
    model = joblib.load(model_path)
    print("Model Type:", type(model).__name__)
    
    if hasattr(model, 'estimators_'):
        print(f"Number of trained base estimators: {len(model.estimators_)}")
        for idx, est in enumerate(model.estimators_):
            print(f"  Estimator {idx}: {type(est).__name__}")
            if type(est).__name__ == "XGBClassifier":
                print(f"    XGB classes_: {est.classes_}")
            elif type(est).__name__ == "RandomForestClassifier":
                print(f"    RF classes_: {est.classes_}")
                print(f"    RF n_estimators: {est.n_estimators}")
    
    if hasattr(model, 'final_estimator_'):
        print(f"Meta Estimator (Final): {type(model.final_estimator_).__name__}")
        
    if hasattr(model, 'classes_'):
        print(f"Ensemble Classes: {model.classes_}")
        
except Exception as e:
    print(f"Error loading or inspecting model: {e}")
