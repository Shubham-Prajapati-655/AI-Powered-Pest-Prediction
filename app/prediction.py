import os
import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = os.path.join(BASE_DIR, "models")

def load_prediction_artifacts():
    """Load Random Forest, XGBoost, Scaler, and Label Encoder models."""
    rf_path = os.path.join(MODELS_DIR, "random_forest.pkl")
    xgb_path = os.path.join(MODELS_DIR, "xgboost.pkl")
    scaler_path = os.path.join(MODELS_DIR, "scaler.pkl")
    encoder_path = os.path.join(MODELS_DIR, "label_encoder.pkl")
    
    artifacts = {}
    if os.path.exists(rf_path):
        artifacts['random_forest'] = joblib.load(rf_path)
    if os.path.exists(xgb_path):
        artifacts['xgboost'] = joblib.load(xgb_path)
    if os.path.exists(scaler_path):
        artifacts['scaler'] = joblib.load(scaler_path)
    if os.path.exists(encoder_path):
        artifacts['encoders'] = joblib.load(encoder_path)
        
    return artifacts

def predict_pest_outbreak(model_name, state, crop, season, temp, humidity, rainfall):
    """
    Predict pest outbreak risk using selected machine learning model artifact.
    Returns predicted risk level ('Low', 'Medium', 'High') and model metadata.
    """
    artifacts = load_prediction_artifacts()
    
    model_key = 'random_forest' if 'random' in model_name.lower() else 'xgboost'
    model = artifacts.get(model_key)
    scaler = artifacts.get('scaler')
    encoders = artifacts.get('encoders')
    
    if model is None or scaler is None or encoders is None:
        # Rule-based fallback if model artifacts are not present
        if humidity > 75 and temp > 25:
            return "High", "Rule-based Fallback (High Humidity & Temp)"
        elif humidity > 50:
            return "Medium", "Rule-based Fallback (Moderate Humidity)"
        else:
            return "Low", "Rule-based Fallback (Normal Conditions)"
            
    try:
        # Scale numerical features
        scaled_num = scaler.transform([[temp, humidity, rainfall]])[0]
        
        # Encode categorical features with safe fallback
        default_cats = {
            'State': state,
            'District': 'Guntur',
            'Crop': crop,
            'Crop_Category': 'Cereal',
            'Sowing_Season': 'Kharif',
            'Season': season,
            'Pest_Name': 'Stem Borer'
        }
        
        cat_encoded = []
        for k, val in default_cats.items():
            if k in encoders:
                le = encoders[k]
                encoded_v = le.transform([val])[0] if val in le.classes_ else 0
            else:
                encoded_v = 0
            cat_encoded.append(encoded_v)
            
        # Combine scaled numerical + encoded categorical features
        features = np.array([list(scaled_num) + cat_encoded])
        
        pred_class = model.predict(features)[0]
        
        if 'target' in encoders:
            risk_level = str(encoders['target'].inverse_transform([pred_class])[0])
        else:
            risk_level = str(pred_class)
            
        return risk_level, f"ML Model: {model_key.upper()}"
        
    except Exception as e:
        print(f"Inference error: {e}")
        return "Medium", "Fallback due to inference exception"
