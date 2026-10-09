"""
AgriAI Advisor - Model Performance & Validation Evaluation Suite
================================================================
Empirical evaluation pipeline for multi-output pest species classification
and outbreak risk probability prediction models.
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import OrdinalEncoder, StandardScaler, LabelEncoder
from sklearn.multioutput import MultiOutputClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay
)

def run_model_evaluation():
    """
    Executes model verification against the test dataset and generates
    confusion matrices, feature importance graphs, and metrics JSON.
    """
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)

    # 1. Dataset Loading
    data_path = "datasets/pest_weather.csv" if os.path.exists("datasets/pest_weather.csv") else "../datasets/pest_weather.csv"
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}")
    df = pd.read_csv(data_path)

    # 2. Feature Engineering
    if "THI" not in df.columns:
        df["THI"] = 0.8 * df["Temperature"] + (df["Humidity"] / 100.0) * (df["Temperature"] - 14.3) + 46.4
    if "Rainfall_Humidity_Ratio" not in df.columns:
        df["Rainfall_Humidity_Ratio"] = df["Rainfall_mm"] / (df["Humidity"] + 1.0)

    cat_cols = ["State", "District", "Crop", "Crop_Category", "Sowing_Season", "Season"]
    num_cols = ["Temperature", "Humidity", "Rainfall_mm", "THI", "Rainfall_Humidity_Ratio"]
    feature_names = cat_cols + num_cols

    # 3. Preprocessing
    pipeline_path = "models/feature_pipeline.pkl"
    pest_enc_path = "models/pest_encoder.pkl"
    risk_enc_path = "models/risk_encoder.pkl"

    if os.path.exists(pipeline_path):
        pipeline = joblib.load(pipeline_path)
        encoder_cat = pipeline["encoder_cat"]
        scaler_num = pipeline["scaler_num"]
        X_cat_encoded = encoder_cat.transform(df[cat_cols])
        X_num_scaled = scaler_num.transform(df[num_cols])
    else:
        encoder_cat = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        scaler_num = StandardScaler()
        X_cat_encoded = encoder_cat.fit_transform(df[cat_cols])
        X_num_scaled = scaler_num.fit_transform(df[num_cols])

    X = np.hstack([X_cat_encoded, X_num_scaled])

    if os.path.exists(pest_enc_path):
        le_pest = joblib.load(pest_enc_path)
        y_pest = le_pest.transform(df["Pest_Name"])
    else:
        le_pest = LabelEncoder()
        y_pest = le_pest.fit_transform(df["Pest_Name"])

    if os.path.exists(risk_enc_path):
        le_risk = joblib.load(risk_enc_path)
        y_risk = le_risk.transform(df["Outbreak"])
    else:
        le_risk = LabelEncoder()
        y_risk = le_risk.fit_transform(df["Outbreak"])

    Y = np.column_stack([y_pest, y_risk])

    # 4. Stratified Split (80% Train, 20% Test)
    X_train, X_test, Y_train, Y_test = train_test_split(
        X, Y, test_size=0.2, random_state=42, stratify=y_pest
    )

    # 5. Load Trained Production Model
    model_path = "models/best_model.pkl" if os.path.exists("models/best_model.pkl") else ("artifacts/trained_model.pkl" if os.path.exists("artifacts/trained_model.pkl") else "models/single_pest_risk_model.pkl")
    loaded_obj = joblib.load(model_path)
    if hasattr(loaded_obj, "pest_pipeline"):
        pest_model = loaded_obj.pest_pipeline
        risk_model = loaded_obj.risk_pipeline
        # If pipeline, evaluation uses raw df features
        raw_cols = ["State", "District", "Crop", "Crop_Category", "Sowing_Season", "Season", "Temperature", "Humidity", "Rainfall_mm"]
        X_eval_train = df[raw_cols].iloc[:len(X_train)]
        X_eval_test = df[raw_cols].iloc[-len(X_test):]
    elif hasattr(loaded_obj, "estimators_"):
        pest_model = loaded_obj.estimators_[0]
        risk_model = loaded_obj.estimators_[1]
    else:
        pest_model = loaded_obj.pest_model
        risk_model = loaded_obj.risk_model

    # 6. Evaluate Pest Model
    y_train_pest_pred = pest_model.predict(X_train)
    pest_train_acc = accuracy_score(Y_train[:, 0], y_train_pest_pred)

    y_test_pest_pred = pest_model.predict(X_test)
    pest_top1_acc = accuracy_score(Y_test[:, 0], y_test_pest_pred)

    pest_proba = pest_model.predict_proba(X_test)
    top3_indices = np.argsort(pest_proba, axis=1)[:, -3:]
    pest_top3_acc = np.mean([Y_test[i, 0] in top3_indices[i] for i in range(len(Y_test))])

    pest_p_wgt, pest_r_wgt, pest_f1_wgt, _ = precision_recall_fscore_support(
        Y_test[:, 0], y_test_pest_pred, average="weighted", zero_division=0
    )

    # 7. Evaluate Risk Model
    y_train_risk_pred = risk_model.predict(X_train)
    risk_train_acc = accuracy_score(Y_train[:, 1], y_train_risk_pred)

    y_test_risk_pred = risk_model.predict(X_test)
    risk_test_acc = accuracy_score(Y_test[:, 1], y_test_risk_pred)

    risk_p_wgt, risk_r_wgt, risk_f1_wgt, _ = precision_recall_fscore_support(
        Y_test[:, 1], y_test_risk_pred, average="weighted", zero_division=0
    )

    metrics_summary = {
        "platform": "AgriAI Advisor",
        "version": "v2.1.0",
        "dataset_samples": len(df),
        "test_samples": len(X_test),
        "pest_model": {
            "top1_accuracy": round(float(pest_top1_acc), 4),
            "top3_accuracy": round(float(pest_top3_acc), 4),
            "weighted_precision": round(float(pest_p_wgt), 4),
            "weighted_recall": round(float(pest_r_wgt), 4),
            "weighted_f1": round(float(pest_f1_wgt), 4)
        },
        "risk_model": {
            "accuracy": round(float(risk_test_acc), 4),
            "weighted_precision": round(float(risk_p_wgt), 4),
            "weighted_recall": round(float(risk_r_wgt), 4),
            "weighted_f1": round(float(risk_f1_wgt), 4)
        }
    }

    with open(os.path.join(results_dir, "evaluation_summary.json"), "w") as f:
        json.dump(metrics_summary, f, indent=4)

    print("=" * 60)
    print("AGRIAI ADVISOR (v2.1.0) - MODEL EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Pest Top-1 Accuracy : {pest_top1_acc*100:.2f}%")
    print(f"Pest Top-3 Accuracy : {pest_top3_acc*100:.2f}%")
    print(f"Risk Level Accuracy : {risk_test_acc*100:.2f}%")
    print(f"Risk Weighted F1    : {risk_f1_wgt*100:.2f}%")
    print(f"Evaluation report saved to {results_dir}/evaluation_summary.json")

if __name__ == "__main__":
    run_model_evaluation()
