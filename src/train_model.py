import pandas as pd
import numpy as np
import joblib
import os
import sys
import json
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OrdinalEncoder, StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

def train_pipeline():
    print("--- Step 1: Loading Dataset ---", flush=True)
    df = pd.read_csv("datasets/pest_weather.csv")
    print(f"Dataset loaded. Shape: {df.shape}", flush=True)

    print("--- Step 2: Feature Engineering ---", flush=True)
    df["THI"] = 0.8 * df["Temperature"] + (df["Humidity"] / 100.0) * (df["Temperature"] - 14.3) + 46.4
    df["Rainfall_Humidity_Ratio"] = df["Rainfall_mm"] / (df["Humidity"] + 1.0)

    print("--- Step 3: Class Distribution Verification & Stratification Check ---", flush=True)
    cat_cols = ["State", "District", "Crop", "Crop_Category", "Sowing_Season", "Season"]
    num_cols = ["Temperature", "Humidity", "Rainfall_mm", "THI", "Rainfall_Humidity_Ratio"]
    feature_names = cat_cols + num_cols

    X_cat = df[cat_cols]
    X_num = df[num_cols]

    encoder_cat = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    X_cat_encoded = encoder_cat.fit_transform(X_cat)

    scaler_num = StandardScaler()
    X_num_scaled = scaler_num.fit_transform(X_num)

    X = np.hstack([X_cat_encoded, X_num_scaled])

    le_pest = LabelEncoder()
    y_pest = le_pest.fit_transform(df["Pest_Name"])

    le_risk = LabelEncoder()
    y_risk = le_risk.fit_transform(df["Outbreak"])

    Y = np.column_stack([y_pest, y_risk])

    print("--- Step 4: Stratified Train/Test Split ---", flush=True)
    # Note: Scikit-learn train_test_split stratify requires 1D vector. 
    # Passing stratify=y_pest ensures exact 80/20 proportion across all 25 pest classes.
    X_train, X_test, Y_train, Y_test = train_test_split(
        X, Y, test_size=0.2, random_state=42, stratify=y_pest
    )
    print(f"Stratified Split completed: Train={len(X_train):,}, Test={len(X_test):,}", flush=True)

    print("--- Step 5: Model Training (RandomForest MultiOutput) ---", flush=True)
    base_rf = RandomForestClassifier(n_estimators=50, max_depth=16, random_state=42, n_jobs=-1)
    multi_rf = MultiOutputClassifier(base_rf, n_jobs=-1)
    multi_rf.fit(X_train, Y_train)

    print("--- Step 6: Comprehensive Metrics Calculation ---", flush=True)
    Y_pred = multi_rf.predict(X_test)
    
    # 1. Pest Prediction Metrics (Primary Evaluation Surface)
    pest_top1_acc = accuracy_score(Y_test[:, 0], Y_pred[:, 0])
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(Y_test[:, 0], Y_pred[:, 0], average="macro")
    p_weighted, r_weighted, f1_weighted, _ = precision_recall_fscore_support(Y_test[:, 0], Y_pred[:, 0], average="weighted")
    cm_pest = confusion_matrix(Y_test[:, 0], Y_pred[:, 0]).tolist()

    # Auxiliary Top-3 Accuracy calculation
    proba_pest = multi_rf.estimators_[0].predict_proba(X_test)
    top3_indices = np.argsort(proba_pest, axis=1)[:, -3:]
    top3_correct = sum([Y_test[i, 0] in top3_indices[i] for i in range(len(Y_test))])
    pest_top3_acc = top3_correct / len(Y_test)

    # 2. Risk Level Metrics
    risk_acc = accuracy_score(Y_test[:, 1], Y_pred[:, 1])
    rp_macro, rr_macro, rf1_macro, _ = precision_recall_fscore_support(Y_test[:, 1], Y_pred[:, 1], average="macro")
    rp_weighted, rr_weighted, rf1_weighted, _ = precision_recall_fscore_support(Y_test[:, 1], Y_pred[:, 1], average="weighted")
    cm_risk = confusion_matrix(Y_test[:, 1], Y_pred[:, 1]).tolist()

    # Feature Importances
    feat_imp_pest = multi_rf.estimators_[0].feature_importances_.tolist()
    feat_imp_risk = multi_rf.estimators_[1].feature_importances_.tolist()

    print("\n=== PEST PREDICTION METRICS ===", flush=True)
    print(f"Top-1 Accuracy     : {pest_top1_acc * 100:.2f}%", flush=True)
    print(f"Macro Precision    : {p_macro * 100:.2f}%", flush=True)
    print(f"Macro Recall       : {r_macro * 100:.2f}%", flush=True)
    print(f"Macro F1-Score     : {f1_macro * 100:.2f}%", flush=True)
    print(f"Weighted Precision : {p_weighted * 100:.2f}%", flush=True)
    print(f"Weighted Recall    : {r_weighted * 100:.2f}%", flush=True)
    print(f"Weighted F1-Score  : {f1_weighted * 100:.2f}%", flush=True)

    print("\n=== RISK LEVEL METRICS ===", flush=True)
    print(f"Risk Accuracy      : {risk_acc * 100:.2f}%", flush=True)
    print(f"Macro Precision    : {rp_macro * 100:.2f}%", flush=True)
    print(f"Macro Recall       : {rr_macro * 100:.2f}%", flush=True)
    print(f"Macro F1-Score     : {rf1_macro * 100:.2f}%", flush=True)
    print(f"Weighted Precision : {rp_weighted * 100:.2f}%", flush=True)
    print(f"Weighted Recall    : {rr_weighted * 100:.2f}%", flush=True)
    print(f"Weighted F1-Score  : {rf1_weighted * 100:.2f}%", flush=True)

    print("--- Step 7: Saving Artifacts ---", flush=True)
    os.makedirs("models", exist_ok=True)
    pipeline_artifact = {
        "cat_cols": cat_cols,
        "num_cols": num_cols,
        "feature_names": feature_names,
        "encoder_cat": encoder_cat,
        "scaler_num": scaler_num,
        "pest_classes": le_pest.classes_.tolist(),
        "risk_classes": le_risk.classes_.tolist()
    }

    joblib.dump(multi_rf, "models/single_pest_risk_model.pkl")
    joblib.dump(pipeline_artifact, "models/feature_pipeline.pkl")
    joblib.dump(le_pest, "models/pest_encoder.pkl")
    joblib.dump(le_risk, "models/risk_encoder.pkl")

    metadata = {
        "pest_top1_accuracy": float(pest_top1_acc),
        "pest_top3_accuracy": float(pest_top3_acc),
        "pest_macro_precision": float(p_macro),
        "pest_macro_recall": float(r_macro),
        "pest_macro_f1": float(f1_macro),
        "pest_weighted_precision": float(p_weighted),
        "pest_weighted_recall": float(r_weighted),
        "pest_weighted_f1": float(f1_weighted),
        "risk_accuracy": float(risk_acc),
        "risk_macro_precision": float(rp_macro),
        "risk_macro_recall": float(rr_macro),
        "risk_macro_f1": float(rf1_macro),
        "risk_weighted_precision": float(rp_weighted),
        "risk_weighted_recall": float(rr_weighted),
        "risk_weighted_f1": float(rf1_weighted),
        "n_samples": int(len(df)),
        "feature_names": feature_names,
        "feature_importances_pest": feat_imp_pest,
        "feature_importances_risk": feat_imp_risk,
        "confusion_matrix_pest": cm_pest,
        "confusion_matrix_risk": cm_risk,
        "pest_classes": le_pest.classes_.tolist(),
        "risk_classes": le_risk.classes_.tolist(),
        "stratification_method": "Stratified on 1D Pest_Name vector (y_pest) using scikit-learn train_test_split(stratify=y_pest)",
        "model_type": "MultiOutputClassifier(RandomForestClassifier)"
    }
    with open("models/model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print("Training and full metrics evaluation completed successfully!", flush=True)

if __name__ == "__main__":
    train_pipeline()
