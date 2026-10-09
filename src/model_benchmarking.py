"""
Step 5: Model Benchmarking Module.
Trains and compares 9 machine learning algorithms across comprehensive metrics:
1. Random Forest
2. Extra Trees
3. XGBoost
4. LightGBM
5. CatBoost
6. Gradient Boosting
7. HistGradientBoosting
8. Voting Ensemble
9. Stacking Ensemble

Calculates:
- Accuracy, Balanced Accuracy
- Macro Precision, Weighted Precision
- Macro Recall, Weighted Recall
- Macro F1, Weighted F1
- Top-3 Accuracy (for multi-class Pest)
- Multi-Class Log Loss
- ROC-AUC (ovr macro)
- Cross-Validation Score (StratifiedKFold)
- Training Time & Prediction Time
Ranks all models and outputs comprehensive benchmark leaderboard.
"""
import os
import sys
import time
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    VotingClassifier,
    StackingClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_recall_fscore_support,
    log_loss,
    roc_auc_score,
    classification_report,
    confusion_matrix
)
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

from src.pipeline_config import (
    REPORTS_DIR,
    ARTIFACTS_DIR,
    PLOTS_DIR,
    RANDOM_STATE
)
from src.preprocessor import prepare_stratified_splits
from utils.logger import setup_logger

logger = setup_logger("model_benchmarking", "benchmarking.log")

def calculate_top3_accuracy(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    """Calculates top-3 accuracy for multi-class classification."""
    top3_indices = np.argsort(y_proba, axis=1)[:, -3:]
    correct = sum(y_true[i] in top3_indices[i] for i in range(len(y_true)))
    return float(correct / len(y_true))

def get_candidate_models(num_classes: int) -> Dict[str, Any]:
    """Instantiates the 9 benchmark candidate models."""
    rf = RandomForestClassifier(n_estimators=80, max_depth=16, random_state=RANDOM_STATE, n_jobs=-1)
    et = ExtraTreesClassifier(n_estimators=80, max_depth=16, random_state=RANDOM_STATE, n_jobs=-1)
    xgb = XGBClassifier(
        n_estimators=80,
        max_depth=6,
        learning_rate=0.1,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        eval_metric="mlogloss"
    )
    lgbm = LGBMClassifier(
        n_estimators=80,
        max_depth=8,
        learning_rate=0.1,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=-1
    )
    cb = CatBoostClassifier(
        iterations=80,
        depth=6,
        learning_rate=0.1,
        random_seed=RANDOM_STATE,
        verbose=False,
        thread_count=-1
    )
    gb = GradientBoostingClassifier(
        n_estimators=40,
        max_depth=4,
        random_state=RANDOM_STATE
    )
    hgb = HistGradientBoostingClassifier(
        max_iter=80,
        max_depth=8,
        random_state=RANDOM_STATE
    )
    voting = VotingClassifier(
        estimators=[
            ("rf", RandomForestClassifier(n_estimators=50, max_depth=14, random_state=RANDOM_STATE, n_jobs=-1)),
            ("lgbm", LGBMClassifier(n_estimators=50, max_depth=6, learning_rate=0.1, random_state=RANDOM_STATE, n_jobs=-1, verbose=-1)),
            ("et", ExtraTreesClassifier(n_estimators=50, max_depth=14, random_state=RANDOM_STATE, n_jobs=-1))
        ],
        voting="soft",
        n_jobs=-1
    )
    stacking = StackingClassifier(
        estimators=[
            ("rf", RandomForestClassifier(n_estimators=40, max_depth=12, random_state=RANDOM_STATE, n_jobs=-1)),
            ("lgbm", LGBMClassifier(n_estimators=40, max_depth=6, learning_rate=0.1, random_state=RANDOM_STATE, n_jobs=-1, verbose=-1))
        ],
        final_estimator=LogisticRegression(max_iter=300, random_state=RANDOM_STATE),
        n_jobs=-1
    )

    return {
        "Random Forest": rf,
        "Extra Trees": et,
        "XGBoost": xgb,
        "LightGBM": lgbm,
        "CatBoost": cb,
        "Gradient Boosting": gb,
        "HistGradientBoosting": hgb,
        "Voting Ensemble": voting,
        "Stacking Ensemble": stacking
    }

def benchmark_single_target(
    target_name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    classes: List[str],
    cv_folds: int = 3
) -> pd.DataFrame:
    """
    Evaluates 9 models on a specific target and computes full performance metrics.
    """
    num_classes = len(classes)
    logger.info(f"\n{'='*70}\nBENCHMARKING TARGET: {target_name.upper()} ({num_classes} Classes)\n{'='*70}")

    models = get_candidate_models(num_classes)
    results = []

    for name, model in models.items():
        logger.info(f"\n>>> Evaluating: {name}...")
        t_start = time.time()
        model.fit(X_train, y_train)
        train_time = round(time.time() - t_start, 3)

        t_pred_start = time.time()
        y_pred = model.predict(X_test)
        pred_time = round(time.time() - t_pred_start, 4)

        # Predict probabilities
        if hasattr(model, "predict_proba"):
            y_proba = model.predict_proba(X_test)
        else:
            y_proba = np.zeros((len(y_test), num_classes))
            for i, p in enumerate(y_pred):
                y_proba[i, p] = 1.0

        # Primary metrics
        acc = accuracy_score(y_test, y_pred)
        bal_acc = balanced_accuracy_score(y_test, y_pred)
        p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(y_test, y_pred, average="macro", zero_division=0)
        p_weight, r_weight, f1_weight, _ = precision_recall_fscore_support(y_test, y_pred, average="weighted", zero_division=0)

        # Top-3 Accuracy
        top3_acc = calculate_top3_accuracy(y_test, y_proba) if num_classes > 3 else 1.0

        # Log Loss
        try:
            ll = log_loss(y_test, y_proba, labels=list(range(num_classes)))
        except Exception as e:
            ll = float("nan")

        # ROC-AUC
        try:
            roc_auc = roc_auc_score(y_test, y_proba, multi_class="ovr", average="macro")
        except Exception:
            roc_auc = float("nan")

        # Cross Validation Score (Stratified 3-fold on training subset)
        logger.info(f"    Running {cv_folds}-Fold Stratified CV...")
        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=RANDOM_STATE)
        try:
            cv_scores = cross_val_score(model, X_train, y_train, cv=skf, scoring="f1_macro", n_jobs=-1)
            cv_mean = float(np.mean(cv_scores))
            cv_std = float(np.std(cv_scores))
        except Exception as e:
            logger.warning(f"    CV computation failed for {name}: {e}")
            cv_mean, cv_std = f1_macro, 0.0

        res = {
            "Model": name,
            "Target": target_name,
            "Accuracy": round(acc, 4),
            "Balanced_Accuracy": round(bal_acc, 4),
            "Macro_Precision": round(p_macro, 4),
            "Weighted_Precision": round(p_weight, 4),
            "Macro_Recall": round(r_macro, 4),
            "Weighted_Recall": round(r_weight, 4),
            "Macro_F1": round(f1_macro, 4),
            "Weighted_F1": round(f1_weight, 4),
            "Top3_Accuracy": round(top3_acc, 4),
            "Log_Loss": round(ll, 4) if not np.isnan(ll) else None,
            "ROC_AUC": round(roc_auc, 4) if not np.isnan(roc_auc) else None,
            "CV_F1_Macro_Mean": round(cv_mean, 4),
            "CV_F1_Macro_Std": round(cv_std, 4),
            "Train_Time_Sec": train_time,
            "Predict_Time_Sec": pred_time
        }
        results.append(res)
        logger.info(f"    Acc: {acc*100:.2f}% | Bal Acc: {bal_acc*100:.2f}% | Macro F1: {f1_macro*100:.2f}% | Top-3 Acc: {top3_acc*100:.2f}% | Train Time: {train_time}s")

    df_res = pd.DataFrame(results)
    # Rank by Weighted composite of Macro F1 (40%), Balanced Accuracy (30%), CV Score (30%)
    df_res["Composite_Rank_Score"] = (
        0.40 * df_res["Macro_F1"] +
        0.30 * df_res["Balanced_Accuracy"] +
        0.30 * df_res["CV_F1_Macro_Mean"]
    ).round(4)

    df_res = df_res.sort_values(by="Composite_Rank_Score", ascending=False).reset_index(drop=True)
    df_res["Rank"] = df_res.index + 1
    return df_res

def run_benchmarking():
    """Executes full benchmark across both targets and exports results."""
    splits = prepare_stratified_splits(save_artifacts=True)

    X_train_full = splits["X_train"]
    X_test_full = splits["X_test"]
    y_train_pest = splits["y_train_pest"]
    y_test_pest = splits["y_test_pest"]
    y_train_risk = splits["y_train_risk"]
    y_test_risk = splits["y_test_risk"]
    pest_classes = splits["le_pest"].classes_.tolist()
    risk_classes = splits["le_risk"].classes_.tolist()

    # Stratified benchmarking sample for comprehensive 9-model comparison:
    # 25,000 training samples and 8,000 test samples to allow fast, rigorous multi-model CV
    benchmark_train_size = 25000
    benchmark_test_size = 8000

    np.random.seed(RANDOM_STATE)
    train_idx = np.random.choice(len(X_train_full), size=benchmark_train_size, replace=False)
    test_idx = np.random.choice(len(X_test_full), size=benchmark_test_size, replace=False)

    X_train_bench = X_train_full[train_idx]
    y_train_pest_bench = y_train_pest[train_idx]
    y_train_risk_bench = y_train_risk[train_idx]

    X_test_bench = X_test_full[test_idx]
    y_test_pest_bench = y_test_pest[test_idx]
    y_test_risk_bench = y_test_risk[test_idx]

    logger.info(f"Benchmarking sample prepared: Train={len(X_train_bench):,}, Test={len(X_test_bench):,}")

    # 1. Benchmark Pest Name (Multi-class 25 classes)
    pest_csv = os.path.join(REPORTS_DIR, "benchmark_results_pest.csv")
    if os.path.exists(pest_csv):
        logger.info(f"Loading existing pest benchmark results from {pest_csv}")
        df_pest_bench = pd.read_csv(pest_csv)
    else:
        df_pest_bench = benchmark_single_target(
            "Pest_Name",
            X_train_bench, y_train_pest_bench,
            X_test_bench, y_test_pest_bench,
            pest_classes
        )
        df_pest_bench.to_csv(pest_csv, index=False)
        logger.info(f"Pest benchmark saved to {pest_csv}")

    # 2. Benchmark Risk Level (Multi-class 3 classes with imbalance)
    df_risk_bench = benchmark_single_target(
        "Risk_Level",
        X_train_bench, y_train_risk_bench,
        X_test_bench, y_test_risk_bench,
        risk_classes
    )
    risk_csv = os.path.join(REPORTS_DIR, "benchmark_results_risk.csv")
    df_risk_bench.to_csv(risk_csv, index=False)
    logger.info(f"Risk benchmark saved to {risk_csv}")

    # 3. Combined Benchmark Leaderboard
    df_combined = pd.concat([df_pest_bench, df_risk_bench], ignore_index=True)
    combined_csv = os.path.join(REPORTS_DIR, "benchmark_results.csv")
    df_combined.to_csv(combined_csv, index=False)
    logger.info(f"Combined benchmark saved to {combined_csv}")

    best_pest_model = df_pest_bench.iloc[0]["Model"]
    best_risk_model = df_risk_bench.iloc[0]["Model"]
    logger.info("=========================================================")
    logger.info(f"BENCHMARKING COMPLETED!")
    logger.info(f"Best Model for Pest_Name: {best_pest_model} (Rank #1, Score: {df_pest_bench.iloc[0]['Composite_Rank_Score']})")
    logger.info(f"Best Model for Risk_Level: {best_risk_model} (Rank #1, Score: {df_risk_bench.iloc[0]['Composite_Rank_Score']})")
    logger.info("=========================================================")

    return df_pest_bench, df_risk_bench

if __name__ == "__main__":
    run_benchmarking()
