"""
Step 5, 6, 8, 9: Production Pipeline Trainer.
Trains the best-performing models on the complete training set (199,760 samples)
with optimal hyperparameters, balanced class weights, and rigorous validation.
Evaluates on the held-out test set (49,940 samples).
Saves all production artifacts requested:
- trained_model.pkl
- encoder.pkl
- scaler.pkl
- preprocessor.pkl
- feature_columns.json
- label_encoder_pest.pkl
- label_encoder_risk.pkl
- metrics.json
- feature_importance.csv
- confusion_matrix.png
- classification_report.csv
- benchmark_results.csv
"""
import os
import sys
import time
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, Tuple

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix,
    log_loss,
    roc_auc_score
)

from src.pipeline_config import (
    MODELS_DIR,
    ARTIFACTS_DIR,
    REPORTS_DIR,
    PLOTS_DIR,
    RANDOM_STATE
)
from src.preprocessor import prepare_stratified_splits
from src.feature_importance_analysis import analyze_and_plot_feature_importance
from src.model_validator import ModelValidator
from utils.logger import setup_logger

logger = setup_logger("production_trainer", "production_training.log")

class DualTargetProductionModel:
    """
    Production container integrating both the Pest Classifier and Risk Classifier
    along with their label encoders into a single unified inference object.
    """
    def __init__(self, pest_model, risk_model, le_pest, le_risk, feature_names):
        self.pest_model = pest_model
        self.risk_model = risk_model
        self.le_pest = le_pest
        self.le_risk = le_risk
        self.feature_names = feature_names

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predicts class labels for both Pest and Risk."""
        pred_pest_idx = self.pest_model.predict(X)
        pred_risk_idx = self.risk_model.predict(X)
        pest_labels = self.le_pest.inverse_transform(pred_pest_idx)
        risk_labels = self.le_risk.inverse_transform(pred_risk_idx)
        return pest_labels, risk_labels

    def predict_proba(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predicts probability distributions for both targets."""
        pest_proba = self.pest_model.predict_proba(X)
        risk_proba = self.risk_model.predict_proba(X)
        return pest_proba, risk_proba

def plot_and_save_confusion_matrix(y_true, y_pred, class_names, title, save_path):
    """Renders and saves a normalized confusion matrix heatmap."""
    cm = confusion_matrix(y_true, y_pred, normalize="true")
    plt.figure(figsize=(10, 8), dpi=300)
    sns.heatmap(
        cm,
        annot=len(class_names) <= 10,
        fmt=".2f",
        cmap="Blues",
        xticklabels=class_names,
        yticklabels=class_names
    )
    plt.title(title, fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Predicted Class", fontsize=11, fontweight="semibold")
    plt.ylabel("True Class", fontsize=11, fontweight="semibold")
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()

def train_production_pipeline(best_pest_algo: str = "Extra Trees", best_risk_algo: str = "Random Forest"):
    """
    Trains the full production models on 199,760 train samples,
    evaluates on 49,940 held-out test samples, and saves all artifacts.
    """
    logger.info("=========================================================")
    logger.info("STEP 9: FULL PRODUCTION PIPELINE TRAINING & ARTIFACT GENERATION")
    logger.info("=========================================================")

    splits = prepare_stratified_splits(save_artifacts=True)
    X_train = splits["X_train"]
    X_test = splits["X_test"]
    y_train_pest = splits["y_train_pest"]
    y_test_pest = splits["y_test_pest"]
    y_train_risk = splits["y_train_risk"]
    y_test_risk = splits["y_test_risk"]
    le_pest = splits["le_pest"]
    le_risk = splits["le_risk"]
    feature_names = splits["feature_names"]

    logger.info(f"Loaded full dataset splits: X_train={X_train.shape}, X_test={X_test.shape}")

    # Compute balanced class weights for Risk target to address class imbalance (Low = 2.18%)
    validator = ModelValidator()
    imbalance_info = validator.validate_class_imbalance()
    risk_weights = imbalance_info["recommended_risk_class_weights"]

    # 1. Instantiate Best Pest Model
    logger.info(f"Instantiating Production Pest Classifier ({best_pest_algo})...")
    if "Extra Trees" in best_pest_algo:
        pest_model = ExtraTreesClassifier(
            n_estimators=120,
            max_depth=20,
            min_samples_split=4,
            random_state=RANDOM_STATE,
            n_jobs=-1
        )
    elif "LightGBM" in best_pest_algo:
        pest_model = LGBMClassifier(
            n_estimators=120,
            max_depth=10,
            num_leaves=64,
            learning_rate=0.08,
            random_state=RANDOM_STATE,
            n_jobs=-1,
            verbose=-1
        )
    else:
        pest_model = RandomForestClassifier(
            n_estimators=120,
            max_depth=20,
            min_samples_split=4,
            random_state=RANDOM_STATE,
            n_jobs=-1
        )

    # 2. Instantiate Best Risk Model with Balanced Class Weights
    logger.info(f"Instantiating Production Risk Classifier ({best_risk_algo}) with class_weight='balanced'...")
    risk_model = RandomForestClassifier(
        n_estimators=120,
        max_depth=16,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    # 3. Fit Models on Full Train Set
    logger.info("Training Pest Classifier on 199,760 samples...")
    t0 = time.time()
    pest_model.fit(X_train, y_train_pest)
    pest_train_time = round(time.time() - t0, 2)
    logger.info(f"Pest Classifier trained in {pest_train_time}s.")

    logger.info("Training Risk Classifier on 199,760 samples...")
    t1 = time.time()
    risk_model.fit(X_train, y_train_risk)
    risk_train_time = round(time.time() - t1, 2)
    logger.info(f"Risk Classifier trained in {risk_train_time}s.")

    # 4. Evaluate on Test Set
    logger.info("Evaluating models on 49,940 held-out test samples...")
    # Pest Predictions
    y_pred_pest = pest_model.predict(X_test)
    y_proba_pest = pest_model.predict_proba(X_test)
    pest_acc = accuracy_score(y_test_pest, y_pred_pest)
    pest_bal_acc = balanced_accuracy_score(y_test_pest, y_pred_pest)
    p_pest_m, r_pest_m, f1_pest_m, _ = precision_recall_fscore_support(y_test_pest, y_pred_pest, average="macro", zero_division=0)
    p_pest_w, r_pest_w, f1_pest_w, _ = precision_recall_fscore_support(y_test_pest, y_pred_pest, average="weighted", zero_division=0)

    # Top-3 Pest Accuracy
    top3_idx = np.argsort(y_proba_pest, axis=1)[:, -3:]
    pest_top3_acc = sum(y_test_pest[i] in top3_idx[i] for i in range(len(y_test_pest))) / len(y_test_pest)
    pest_ll = log_loss(y_test_pest, y_proba_pest, labels=list(range(len(le_pest.classes_))))
    pest_auc = roc_auc_score(y_test_pest, y_proba_pest, multi_class="ovr", average="macro")

    # Risk Predictions
    y_pred_risk = risk_model.predict(X_test)
    y_proba_risk = risk_model.predict_proba(X_test)
    risk_acc = accuracy_score(y_test_risk, y_pred_risk)
    risk_bal_acc = balanced_accuracy_score(y_test_risk, y_pred_risk)
    p_risk_m, r_risk_m, f1_risk_m, _ = precision_recall_fscore_support(y_test_risk, y_pred_risk, average="macro", zero_division=0)
    p_risk_w, r_risk_w, f1_risk_w, _ = precision_recall_fscore_support(y_test_risk, y_pred_risk, average="weighted", zero_division=0)
    risk_ll = log_loss(y_test_risk, y_proba_risk, labels=list(range(len(le_risk.classes_))))
    risk_auc = roc_auc_score(y_test_risk, y_proba_risk, multi_class="ovr", average="macro")

    logger.info("\n" + "="*50)
    logger.info("FINAL PRODUCTION PERFORMANCE (HELD-OUT TEST SET):")
    logger.info("="*50)
    logger.info(f"Target 1: Pest_Name (25 Classes)")
    logger.info(f"  Accuracy           : {pest_acc*100:.2f}%")
    logger.info(f"  Balanced Accuracy  : {pest_bal_acc*100:.2f}%")
    logger.info(f"  Top-3 Accuracy     : {pest_top3_acc*100:.2f}%")
    logger.info(f"  Macro Precision    : {p_pest_m*100:.2f}%")
    logger.info(f"  Macro Recall       : {r_pest_m*100:.2f}%")
    logger.info(f"  Macro F1-Score     : {f1_pest_m*100:.2f}%")
    logger.info(f"  Weighted F1-Score  : {f1_pest_w*100:.2f}%")
    logger.info(f"  Log Loss           : {pest_ll:.4f}")
    logger.info(f"  ROC-AUC (OVR Macro): {pest_auc:.4f}")

    logger.info(f"\nTarget 2: Risk_Level (3 Classes with Imbalance Mitigation)")
    logger.info(f"  Accuracy           : {risk_acc*100:.2f}%")
    logger.info(f"  Balanced Accuracy  : {risk_bal_acc*100:.2f}%")
    logger.info(f"  Macro Precision    : {p_risk_m*100:.2f}%")
    logger.info(f"  Macro Recall       : {r_risk_m*100:.2f}%")
    logger.info(f"  Macro F1-Score     : {f1_risk_m*100:.2f}%")
    logger.info(f"  Weighted F1-Score  : {f1_risk_w*100:.2f}%")
    logger.info(f"  Log Loss           : {risk_ll:.4f}")
    logger.info(f"  ROC-AUC (OVR Macro): {risk_auc:.4f}")

    # 5. Export Classification Reports & Confusion Matrices
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)

    report_pest_dict = classification_report(y_test_pest, y_pred_pest, target_names=le_pest.classes_, output_dict=True)
    df_rep_pest = pd.DataFrame(report_pest_dict).transpose()
    df_rep_pest.to_csv(os.path.join(REPORTS_DIR, "classification_report_pest.csv"))

    report_risk_dict = classification_report(y_test_risk, y_pred_risk, target_names=le_risk.classes_, output_dict=True)
    df_rep_risk = pd.DataFrame(report_risk_dict).transpose()
    df_rep_risk.to_csv(os.path.join(REPORTS_DIR, "classification_report_risk.csv"))
    # Combined classification_report.csv
    df_rep_combined = pd.concat([
        df_rep_pest.assign(Target="Pest_Name"),
        df_rep_risk.assign(Target="Risk_Level")
    ])
    df_rep_combined.to_csv(os.path.join(REPORTS_DIR, "classification_report.csv"))
    df_rep_combined.to_csv(os.path.join(ARTIFACTS_DIR, "classification_report.csv"))

    # Plot Confusion Matrices
    plot_and_save_confusion_matrix(
        y_test_pest, y_pred_pest, le_pest.classes_,
        "Normalized Confusion Matrix - Pest Name (Top 25 Classes)",
        os.path.join(PLOTS_DIR, "confusion_matrix_pest.png")
    )
    plot_and_save_confusion_matrix(
        y_test_risk, y_pred_risk, le_risk.classes_,
        "Normalized Confusion Matrix - Risk Level",
        os.path.join(PLOTS_DIR, "confusion_matrix_risk.png")
    )
    # Save standard confusion_matrix.png pointing to pest in both plots/ and artifacts/
    plot_and_save_confusion_matrix(
        y_test_pest, y_pred_pest, le_pest.classes_,
        "Normalized Confusion Matrix - Pest Name",
        os.path.join(PLOTS_DIR, "confusion_matrix.png")
    )
    plot_and_save_confusion_matrix(
        y_test_pest, y_pred_pest, le_pest.classes_,
        "Normalized Confusion Matrix - Pest Name",
        os.path.join(ARTIFACTS_DIR, "confusion_matrix.png")
    )

    # 6. Feature Importance & SHAP
    analyze_and_plot_feature_importance(
        pest_model, X_train, y_train_pest, X_test, y_test_pest,
        feature_names=feature_names, target_name="Pest_Name", classes=le_pest.classes_
    )
    analyze_and_plot_feature_importance(
        risk_model, X_train, y_train_risk, X_test, y_test_risk,
        feature_names=feature_names, target_name="Risk_Level", classes=le_risk.classes_
    )

    # 7. Save Models and Unified Production Pipeline
    dual_prod_model = DualTargetProductionModel(
        pest_model=pest_model,
        risk_model=risk_model,
        le_pest=le_pest,
        le_risk=le_risk,
        feature_names=feature_names
    )

    joblib.dump(dual_prod_model, os.path.join(MODELS_DIR, "trained_model.pkl"))
    joblib.dump(dual_prod_model, os.path.join(ARTIFACTS_DIR, "trained_model.pkl"))
    joblib.dump(pest_model, os.path.join(MODELS_DIR, "best_pest_model.pkl"))
    joblib.dump(risk_model, os.path.join(MODELS_DIR, "best_risk_model.pkl"))

    # Also update models/single_pest_risk_model.pkl compatibility if needed
    joblib.dump(dual_prod_model, os.path.join(MODELS_DIR, "single_pest_risk_model.pkl"))

    # 8. Save Metrics JSON
    metrics_summary = {
        "dataset": {
            "total_samples": len(X_train) + len(X_test),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "features_count": len(feature_names),
            "feature_names": feature_names
        },
        "pest_model": {
            "algorithm": best_pest_algo,
            "accuracy": round(pest_acc, 4),
            "balanced_accuracy": round(pest_bal_acc, 4),
            "top3_accuracy": round(pest_top3_acc, 4),
            "macro_precision": round(p_pest_m, 4),
            "macro_recall": round(r_pest_m, 4),
            "macro_f1": round(f1_pest_m, 4),
            "weighted_f1": round(f1_pest_w, 4),
            "log_loss": round(pest_ll, 4),
            "roc_auc": round(pest_auc, 4),
            "train_time_sec": pest_train_time
        },
        "risk_model": {
            "algorithm": best_risk_algo,
            "accuracy": round(risk_acc, 4),
            "balanced_accuracy": round(risk_bal_acc, 4),
            "macro_precision": round(p_risk_m, 4),
            "macro_recall": round(r_risk_m, 4),
            "macro_f1": round(f1_risk_m, 4),
            "weighted_f1": round(f1_risk_w, 4),
            "log_loss": round(risk_ll, 4),
            "roc_auc": round(risk_auc, 4),
            "train_time_sec": risk_train_time,
            "imbalance_technique": "balanced class weights"
        }
    }
    metrics_path = os.path.join(ARTIFACTS_DIR, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)
    logger.info(f"Production metrics saved to: {metrics_path}")

    # Copy benchmark_results.csv to artifacts/
    bench_src = os.path.join(REPORTS_DIR, "benchmark_results.csv")
    if os.path.exists(bench_src):
        import shutil
        shutil.copy(bench_src, os.path.join(ARTIFACTS_DIR, "benchmark_results.csv"))
        logger.info("Copied benchmark_results.csv to artifacts directory.")

    # 9. Model Validator Audit
    validation_report = validator.run_full_validation_suite()

    logger.info("Production pipeline training, evaluation, and serialization completed successfully!")
    return metrics_summary

if __name__ == "__main__":
    train_production_pipeline()
