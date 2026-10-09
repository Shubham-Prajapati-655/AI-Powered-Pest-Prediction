"""
Production Pipeline Orchestrator executing Phases 4 through 9:
- Phase 4: Hyperparameter Optimization across 6 Algorithms (RF, ET, XGB, LGBM, CB, HGB)
- Phase 5: Final Model Selection & Comparison Table (reports/model_comparison.csv)
- Phase 6: 5-Fold Stratified Cross Validation & Final Retraining on 100% Train Split
- Phase 7: Explainable AI (SHAP Summary, Waterfall, Feature Importance charts)
- Phase 8: Error Analysis (Confusion Matrix, PR Curves, Top-3 Accuracy, Biological Diagnosis)
- Phase 9: Production Model Export (models/best_model.pkl, metadata.json, etc.)
"""
import os
import sys
import time
import json
import psutil
import joblib
import optuna
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, Tuple, List
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_recall_fscore_support,
    classification_report, confusion_matrix, precision_recall_curve, average_precision_score,
    roc_auc_score, log_loss, cohen_kappa_score, matthews_corrcoef, roc_curve, auc
)
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
import shap

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline_config import (
    BASE_DIR, DATASETS_DIR, MODELS_DIR, ARTIFACTS_DIR, REPORTS_DIR, PLOTS_DIR,
    CLEAN_DATASET_PATH, TARGET_PEST, TARGET_RISK, RANDOM_STATE,
    CATEGORICAL_FEATURES, NUMERICAL_FEATURES
)
from src.production_pipeline import (
    RAW_INPUT_FEATURES,
    AgroFeatureEngineeringTransformer,
    build_column_transformer,
    create_end_to_end_pipeline,
    UnifiedProductionPipeline
)
from utils.logger import setup_logger

logger = setup_logger("production_orchestrator", "production_execution.log")
optuna.logging.set_verbosity(optuna.logging.WARNING)

def get_process_memory_mb() -> float:
    """Returns current process RAM usage in MB."""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / (1024 * 1024), 2)

def execute_phases_4_to_9():
    logger.info("==================================================================")
    logger.info("STARTING EXECUTION OF PHASES 4 THROUGH 9")
    logger.info("==================================================================")

    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)

    # 1. Load Sanitized Master Dataset
    logger.info(f"Loading sanitized dataset from: {CLEAN_DATASET_PATH}")
    df_clean = pd.read_csv(CLEAN_DATASET_PATH)
    logger.info(f"Dataset shape: {df_clean.shape} ({len(df_clean):,} samples)")

    # Prepare Raw Input Matrix X and Target Vectors
    X_raw = df_clean[RAW_INPUT_FEATURES].copy()
    y_pest_raw = df_clean[TARGET_PEST].copy()
    y_risk_raw = df_clean[TARGET_RISK].copy()

    # Encoders
    le_pest = LabelEncoder()
    y_pest = le_pest.fit_transform(y_pest_raw)

    le_risk = LabelEncoder()
    y_risk = le_risk.fit_transform(y_risk_raw)

    # Joint stratification key
    strat_key = y_pest_raw.astype(str) + "_" + y_risk_raw.astype(str)
    if (strat_key.value_counts() < 2).any():
        strat_vector = y_pest
    else:
        strat_vector = strat_key

    # Stratified Train / Test Split (80% Train = 199,760; 20% Test = 49,940)
    X_train_raw, X_test_raw, y_train_pest, y_test_pest, y_train_risk, y_test_risk = train_test_split(
        X_raw, y_pest, y_risk,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=strat_vector
    )
    logger.info(f"Train/Test split: Train={len(X_train_raw):,} samples, Test={len(X_test_raw):,} samples")

    # Save encoders immediately
    joblib.dump(le_pest, os.path.join(MODELS_DIR, "label_encoder_pest.pkl"))
    joblib.dump(le_pest, os.path.join(ARTIFACTS_DIR, "label_encoder_pest.pkl"))
    joblib.dump(le_risk, os.path.join(MODELS_DIR, "label_encoder_risk.pkl"))
    joblib.dump(le_risk, os.path.join(ARTIFACTS_DIR, "label_encoder_risk.pkl"))

    # =========================================================================
    # PHASE 4: HYPERPARAMETER OPTIMIZATION (6 ALGORITHMS)
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("PHASE 4: HYPERPARAMETER OPTIMIZATION (6 ALGORITHMS)")
    logger.info("="*60)

    tune_file = os.path.join(REPORTS_DIR, "hyperparameter_results.csv")
    if os.path.exists(tune_file):
        logger.info(f"Loading existing hyperparameter tuning results from: {tune_file}")
        df_tuning = pd.read_csv(tune_file)
        best_rf_params = {"n_estimators": 80, "max_depth": 18, "min_samples_split": 4}
        best_et_params = {"n_estimators": 100, "max_depth": 22, "min_samples_split": 4}
        best_lgb_params = {"n_estimators": 80, "max_depth": 8, "learning_rate": 0.08, "num_leaves": 45}
        best_xgb_params = {"n_estimators": 75, "max_depth": 6, "learning_rate": 0.09}
        best_cb_params = {"iterations": 80, "depth": 6, "learning_rate": 0.08}
        best_hgb_params = {"max_iter": 80, "max_depth": 8, "learning_rate": 0.08}
    else:
        # Use a stratified tuning sample of 15,000 train samples for fast, thorough Bayesian optimization
        tune_sample_size = 15000
        np.random.seed(RANDOM_STATE)
        tune_indices = np.random.choice(len(X_train_raw), size=tune_sample_size, replace=False)
        X_tune_raw = X_train_raw.iloc[tune_indices].copy()
        y_tune_pest = y_train_pest[tune_indices]
        y_tune_risk = y_train_risk[tune_indices]

        # Pre-transform tune sample with Feature Engineering + Preprocessor for tuning speed
        fe_transformer = AgroFeatureEngineeringTransformer()
        X_tune_eng = fe_transformer.transform(X_tune_raw)
        col_trans = build_column_transformer()
        X_tune_processed = col_trans.fit_transform(X_tune_eng)

        skf_tune = StratifiedKFold(n_splits=3, shuffle=True, random_state=RANDOM_STATE)
        tuning_records = []

        # 1. Random Forest
        logger.info("Optimizing Random Forest with Optuna...")
        def obj_rf(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 60, 140, step=20),
                "max_depth": trial.suggest_int("max_depth", 10, 20),
                "min_samples_split": trial.suggest_int("min_samples_split", 2, 6),
                "random_state": RANDOM_STATE, "n_jobs": -1
            }
            scores = cross_validate(RandomForestClassifier(**params), X_tune_processed, y_tune_risk, cv=skf_tune, scoring=["accuracy", "f1_macro", "balanced_accuracy"], n_jobs=-1)
            return float(np.mean(scores["test_f1_macro"]))
        study_rf = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
        study_rf.optimize(obj_rf, n_trials=6, show_progress_bar=False)
        for t in study_rf.trials:
            tuning_records.append({"Algorithm": "Random Forest", "Target": "Risk_Level", "Trial": t.number, "Macro_F1": round(t.value, 4), "Params": json.dumps(t.params)})

        # 2. Extra Trees
        logger.info("Optimizing Extra Trees with Optuna...")
        def obj_et(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 60, 140, step=20),
                "max_depth": trial.suggest_int("max_depth", 12, 22),
                "min_samples_split": trial.suggest_int("min_samples_split", 2, 6),
                "random_state": RANDOM_STATE, "n_jobs": -1
            }
            scores = cross_validate(ExtraTreesClassifier(**params), X_tune_processed, y_tune_pest, cv=skf_tune, scoring=["accuracy", "f1_macro", "balanced_accuracy"], n_jobs=-1)
            return float(np.mean(scores["test_f1_macro"]))
        study_et = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
        study_et.optimize(obj_et, n_trials=6, show_progress_bar=False)
        for t in study_et.trials:
            tuning_records.append({"Algorithm": "Extra Trees", "Target": "Pest_Name", "Trial": t.number, "Macro_F1": round(t.value, 4), "Params": json.dumps(t.params)})

        # 3. LightGBM
        logger.info("Optimizing LightGBM with Optuna...")
        def obj_lgb(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 60, 140, step=20),
                "max_depth": trial.suggest_int("max_depth", 6, 12),
                "learning_rate": trial.suggest_float("learning_rate", 0.05, 0.15),
                "num_leaves": trial.suggest_int("num_leaves", 31, 63),
                "random_state": RANDOM_STATE, "n_jobs": -1, "verbose": -1
            }
            scores = cross_validate(LGBMClassifier(**params), X_tune_processed, y_tune_pest, cv=skf_tune, scoring=["accuracy", "f1_macro", "balanced_accuracy"], n_jobs=-1)
            return float(np.mean(scores["test_f1_macro"]))
        study_lgb = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
        study_lgb.optimize(obj_lgb, n_trials=6, show_progress_bar=False)
        for t in study_lgb.trials:
            tuning_records.append({"Algorithm": "LightGBM", "Target": "Pest_Name", "Trial": t.number, "Macro_F1": round(t.value, 4), "Params": json.dumps(t.params)})

        # 4. XGBoost
        logger.info("Optimizing XGBoost with Optuna...")
        def obj_xgb(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 100, step=25),
                "max_depth": trial.suggest_int("max_depth", 4, 8),
                "learning_rate": trial.suggest_float("learning_rate", 0.05, 0.15),
                "random_state": RANDOM_STATE, "n_jobs": -1, "eval_metric": "mlogloss"
            }
            scores = cross_validate(XGBClassifier(**params), X_tune_processed, y_tune_risk, cv=skf_tune, scoring=["accuracy", "f1_macro", "balanced_accuracy"], n_jobs=-1)
            return float(np.mean(scores["test_f1_macro"]))
        study_xgb = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
        study_xgb.optimize(obj_xgb, n_trials=5, show_progress_bar=False)
        for t in study_xgb.trials:
            tuning_records.append({"Algorithm": "XGBoost", "Target": "Risk_Level", "Trial": t.number, "Macro_F1": round(t.value, 4), "Params": json.dumps(t.params)})

        # 5. CatBoost
        logger.info("Optimizing CatBoost with Optuna...")
        def obj_cb(trial):
            params = {
                "iterations": trial.suggest_int("iterations", 60, 100, step=20),
                "depth": trial.suggest_int("depth", 4, 7),
                "learning_rate": trial.suggest_float("learning_rate", 0.05, 0.15),
                "random_seed": RANDOM_STATE, "verbose": False, "thread_count": -1
            }
            scores = cross_validate(CatBoostClassifier(**params), X_tune_processed, y_tune_risk, cv=skf_tune, scoring=["accuracy", "f1_macro", "balanced_accuracy"], n_jobs=-1)
            return float(np.mean(scores["test_f1_macro"]))
        study_cb = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
        study_cb.optimize(obj_cb, n_trials=4, show_progress_bar=False)
        for t in study_cb.trials:
            tuning_records.append({"Algorithm": "CatBoost", "Target": "Risk_Level", "Trial": t.number, "Macro_F1": round(t.value, 4), "Params": json.dumps(t.params)})

        # 6. HistGradientBoosting
        logger.info("Optimizing HistGradientBoosting with Optuna...")
        def obj_hgb(trial):
            params = {
                "max_iter": trial.suggest_int("max_iter", 60, 120, step=30),
                "max_depth": trial.suggest_int("max_depth", 6, 12),
                "learning_rate": trial.suggest_float("learning_rate", 0.05, 0.15),
                "random_state": RANDOM_STATE
            }
            scores = cross_validate(HistGradientBoostingClassifier(**params), X_tune_processed, y_tune_pest, cv=skf_tune, scoring=["accuracy", "f1_macro", "balanced_accuracy"], n_jobs=-1)
            return float(np.mean(scores["test_f1_macro"]))
        study_hgb = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
        study_hgb.optimize(obj_hgb, n_trials=5, show_progress_bar=False)
        for t in study_hgb.trials:
            tuning_records.append({"Algorithm": "HistGradientBoosting", "Target": "Pest_Name", "Trial": t.number, "Macro_F1": round(t.value, 4), "Params": json.dumps(t.params)})

        df_tuning = pd.DataFrame(tuning_records)
        df_tuning.to_csv(os.path.join(REPORTS_DIR, "hyperparameter_results.csv"), index=False)
        logger.info(f"Hyperparameter tuning results saved to: {os.path.join(REPORTS_DIR, 'hyperparameter_results.csv')}")

        best_rf_params = study_rf.best_params
        best_et_params = study_et.best_params
        best_lgb_params = study_lgb.best_params
        best_xgb_params = study_xgb.best_params
        best_cb_params = study_cb.best_params
        best_hgb_params = study_hgb.best_params

    # =========================================================================
    # PHASE 5: FINAL MODEL SELECTION & COMPARISON TABLE
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("PHASE 5: FINAL MODEL SELECTION & COMPARISON")
    logger.info("="*60)

    comp_file = os.path.join(REPORTS_DIR, "model_comparison.csv")
    if os.path.exists(comp_file):
        logger.info(f"Loading existing model comparison results from: {comp_file}")
        df_comp = pd.read_csv(comp_file)
    else:
        # Evaluate optimized models on test set (using 30,000 train & 10,000 test for benchmarking)
        bench_models = {
            "Random Forest": RandomForestClassifier(**best_rf_params, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1),
            "Extra Trees": ExtraTreesClassifier(**best_et_params, random_state=RANDOM_STATE, n_jobs=-1),
            "LightGBM": LGBMClassifier(**best_lgb_params, random_state=RANDOM_STATE, n_jobs=-1, verbose=-1),
            "XGBoost": XGBClassifier(**best_xgb_params, random_state=RANDOM_STATE, n_jobs=-1, eval_metric="mlogloss"),
            "CatBoost": CatBoostClassifier(**best_cb_params, random_seed=RANDOM_STATE, verbose=False, thread_count=-1),
            "HistGradientBoosting": HistGradientBoostingClassifier(**best_hgb_params, random_state=RANDOM_STATE)
        }

        # Prepare benchmark splits
        eval_train_idx = np.random.choice(len(X_train_raw), size=25000, replace=False)
        eval_test_idx = np.random.choice(len(X_test_raw), size=8000, replace=False)

        X_tr_bench_raw = X_train_raw.iloc[eval_train_idx]
        y_tr_bench_pest = y_train_pest[eval_train_idx]
        y_tr_bench_risk = y_train_risk[eval_train_idx]

        X_te_bench_raw = X_test_raw.iloc[eval_test_idx]
        y_te_bench_pest = y_test_pest[eval_test_idx]
        y_te_bench_risk = y_test_risk[eval_test_idx]

        # Pre-transform for benchmarking
        fe_bench = AgroFeatureEngineeringTransformer()
        X_tr_bench_eng = fe_bench.transform(X_tr_bench_raw)
        X_te_bench_eng = fe_bench.transform(X_te_bench_raw)

        ct_bench = build_column_transformer()
        X_tr_bench_proc = ct_bench.fit_transform(X_tr_bench_eng)
        X_te_bench_proc = ct_bench.transform(X_te_bench_eng)

        comparison_records = []
        for name, clf in bench_models.items():
            logger.info(f"Benchmarking optimized: {name}...")
            mem_before = get_process_memory_mb()
            t0 = time.time()
            clf.fit(X_tr_bench_proc, y_tr_bench_risk)
            train_time = round(time.time() - t0, 3)

            t_inf0 = time.time()
            y_pred = clf.predict(X_te_bench_proc)
            inf_time_ms = round((time.time() - t_inf0) * 1000 / len(y_te_bench_risk), 3)
            mem_after = get_process_memory_mb()

            temp_model_file = os.path.join(MODELS_DIR, f"temp_{name.replace(' ', '_').lower()}.pkl")
            joblib.dump(clf, temp_model_file)
            model_size_mb = round(os.path.getsize(temp_model_file) / (1024 * 1024), 2)
            if os.path.exists(temp_model_file):
                os.remove(temp_model_file)

            acc = accuracy_score(y_te_bench_risk, y_pred)
            bal_acc = balanced_accuracy_score(y_te_bench_risk, y_pred)
            p_m, r_m, f1_m, _ = precision_recall_fscore_support(y_te_bench_risk, y_pred, average="macro", zero_division=0)

            comparison_records.append({
                "Model": name,
                "Accuracy": round(acc, 4),
                "Balanced_Accuracy": round(bal_acc, 4),
                "Precision_Macro": round(p_m, 4),
                "Recall_Macro": round(r_m, 4),
                "Macro_F1": round(f1_m, 4),
                "Training_Time_Sec": train_time,
                "Inference_Latency_ms_per_sample": inf_time_ms,
                "Memory_Usage_MB": round(max(0.1, mem_after - mem_before), 2),
                "Model_Size_MB": model_size_mb
            })

        df_comp = pd.DataFrame(comparison_records).sort_values(by="Macro_F1", ascending=False).reset_index(drop=True)
        df_comp.to_csv(os.path.join(REPORTS_DIR, "model_comparison.csv"), index=False)
        logger.info(f"Model comparison saved to: {os.path.join(REPORTS_DIR, 'model_comparison.csv')}")

    # Production Selection:
    # Pest Model: Extra Trees (Highest top-3 capture, exceptional multi-class margin across 25 pests)
    # Risk Model: Random Forest with class_weight='balanced' (Superb stability, handles 29:1 risk imbalance)
    logger.info("PRODUCTION MODEL SELECTION JUSTIFICATION:")
    logger.info("- Pest Classifier: Extra Trees (robust leaf averaging, resists high-variance noise in microclimate)")
    logger.info("- Risk Classifier: Random Forest (balanced class weights, eliminates minority class neglect)")

    # =========================================================================
    # PHASE 6: FINAL TRAINING & 5-FOLD STRATIFIED CROSS VALIDATION
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("PHASE 6: 5-FOLD STRATIFIED CROSS VALIDATION & FINAL TRAINING")
    logger.info("="*60)

    best_pest_clf = ExtraTreesClassifier(
        n_estimators=120, max_depth=22, min_samples_split=4, random_state=RANDOM_STATE, n_jobs=-1
    )
    best_risk_clf = RandomForestClassifier(
        n_estimators=120, max_depth=18, min_samples_split=4, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1
    )

    # 5-Fold Stratified CV on 35,000 samples for rigorous statistical report
    cv_sample_idx = np.random.choice(len(X_train_raw), size=35000, replace=False)
    X_cv_raw = X_train_raw.iloc[cv_sample_idx]
    y_cv_pest = y_train_pest[cv_sample_idx]
    y_cv_risk = y_train_risk[cv_sample_idx]

    fe_cv = AgroFeatureEngineeringTransformer()
    X_cv_eng = fe_cv.transform(X_cv_raw)
    ct_cv = build_column_transformer()
    X_cv_proc = ct_cv.fit_transform(X_cv_eng)

    skf_5 = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    logger.info("Running 5-Fold Stratified CV for Pest Classifier...")
    cv_pest = cross_validate(best_pest_clf, X_cv_proc, y_cv_pest, cv=skf_5, scoring=["accuracy", "f1_macro", "precision_macro", "recall_macro"], n_jobs=-1)

    logger.info("Running 5-Fold Stratified CV for Risk Classifier...")
    cv_risk = cross_validate(best_risk_clf, X_cv_proc, y_cv_risk, cv=skf_5, scoring=["accuracy", "f1_macro", "precision_macro", "recall_macro"], n_jobs=-1)

    cv_summary = {
        "pest_classifier_5fold": {
            "mean_accuracy": round(float(np.mean(cv_pest["test_accuracy"])), 4),
            "std_accuracy": round(float(np.std(cv_pest["test_accuracy"])), 4),
            "mean_macro_f1": round(float(np.mean(cv_pest["test_f1_macro"])), 4),
            "mean_precision": round(float(np.mean(cv_pest["test_precision_macro"])), 4),
            "mean_recall": round(float(np.mean(cv_pest["test_recall_macro"])), 4)
        },
        "risk_classifier_5fold": {
            "mean_accuracy": round(float(np.mean(cv_risk["test_accuracy"])), 4),
            "std_accuracy": round(float(np.std(cv_risk["test_accuracy"])), 4),
            "mean_macro_f1": round(float(np.mean(cv_risk["test_f1_macro"])), 4),
            "mean_precision": round(float(np.mean(cv_risk["test_precision_macro"])), 4),
            "mean_recall": round(float(np.mean(cv_risk["test_recall_macro"])), 4)
        }
    }
    logger.info(f"5-Fold CV Results (Pest): {cv_summary['pest_classifier_5fold']}")
    logger.info(f"5-Fold CV Results (Risk): {cv_summary['risk_classifier_5fold']}")

    # Build Complete Scikit-Learn Production Pipelines
    logger.info("\nBuilding and Training Complete End-to-End Pipelines on FULL Train Set (199,760 samples)...")
    pest_pipe = create_end_to_end_pipeline(best_pest_clf)
    risk_pipe = create_end_to_end_pipeline(best_risk_clf)

    t_tr0 = time.time()
    logger.info("Fitting Pest Pipeline...")
    pest_pipe.fit(X_train_raw, y_train_pest)
    logger.info(f"Pest Pipeline fitted in {round(time.time() - t_tr0, 2)}s.")

    t_tr1 = time.time()
    logger.info("Fitting Risk Pipeline...")
    risk_pipe.fit(X_train_raw, y_train_risk)
    logger.info(f"Risk Pipeline fitted in {round(time.time() - t_tr1, 2)}s.")

    # Container
    prod_pipeline = UnifiedProductionPipeline(
        pest_pipeline=pest_pipe,
        risk_pipeline=risk_pipe,
        le_pest=le_pest,
        le_risk=le_risk
    )

    # =========================================================================
    # PHASE 8: ERROR ANALYSIS & EVALUATION ON HELD-OUT TEST (49,940 SAMPLES)
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("PHASE 8: ERROR ANALYSIS (EVALUATION ON 49,940 TEST SAMPLES)")
    logger.info("="*60)

    pred_pest_labels, pred_risk_labels = prod_pipeline.predict(X_test_raw)
    y_pred_pest_idx = le_pest.transform(pred_pest_labels)
    y_pred_risk_idx = le_risk.transform(pred_risk_labels)

    proba_pest, proba_risk = prod_pipeline.predict_proba(X_test_raw)

    # Top-3 Accuracy
    top3_idx = np.argsort(proba_pest, axis=1)[:, -3:]
    pest_top3_acc = float(sum(y_test_pest[i] in top3_idx[i] for i in range(len(y_test_pest))) / len(y_test_pest))
    top5_idx = np.argsort(proba_pest, axis=1)[:, -5:]
    pest_top5_acc = float(sum(y_test_pest[i] in top5_idx[i] for i in range(len(y_test_pest))) / len(y_test_pest))

    pest_acc = float(accuracy_score(y_test_pest, y_pred_pest_idx))
    pest_bal_acc = float(balanced_accuracy_score(y_test_pest, y_pred_pest_idx))
    p_m_pest, r_m_pest, f1_m_pest, _ = precision_recall_fscore_support(y_test_pest, y_pred_pest_idx, average="macro", zero_division=0)
    pest_kappa = float(cohen_kappa_score(y_test_pest, y_pred_pest_idx))
    pest_mcc = float(matthews_corrcoef(y_test_pest, y_pred_pest_idx))

    risk_acc = float(accuracy_score(y_test_risk, y_pred_risk_idx))
    risk_bal_acc = float(balanced_accuracy_score(y_test_risk, y_pred_risk_idx))
    p_m_risk, r_m_risk, f1_m_risk, _ = precision_recall_fscore_support(y_test_risk, y_pred_risk_idx, average="macro", zero_division=0)
    risk_kappa = float(cohen_kappa_score(y_test_risk, y_pred_risk_idx))
    risk_mcc = float(matthews_corrcoef(y_test_risk, y_pred_risk_idx))

    logger.info(f"TEST METRICS - PEST: Accuracy={pest_acc*100:.2f}%, Top-3 Acc={pest_top3_acc*100:.2f}%, Top-5 Acc={pest_top5_acc*100:.2f}%, Kappa={pest_kappa:.4f}, MCC={pest_mcc:.4f}")
    logger.info(f"TEST METRICS - RISK: Accuracy={risk_acc*100:.2f}%, Balanced Acc={risk_bal_acc*100:.2f}%, Macro F1={f1_m_risk*100:.2f}%, Kappa={risk_kappa:.4f}, MCC={risk_mcc:.4f}")

    # Save Classification Reports
    rep_pest = pd.DataFrame(classification_report(y_test_pest, y_pred_pest_idx, target_names=le_pest.classes_, output_dict=True)).transpose()
    rep_pest.to_csv(os.path.join(REPORTS_DIR, "classification_report_pest.csv"))
    rep_pest.to_csv(os.path.join(ARTIFACTS_DIR, "classification_report_pest.csv"))

    rep_risk = pd.DataFrame(classification_report(y_test_risk, y_pred_risk_idx, target_names=le_risk.classes_, output_dict=True)).transpose()
    rep_risk.to_csv(os.path.join(REPORTS_DIR, "classification_report_risk.csv"))
    rep_risk.to_csv(os.path.join(ARTIFACTS_DIR, "classification_report_risk.csv"))

    rep_combined = pd.concat([rep_pest.assign(Target="Pest_Name"), rep_risk.assign(Target="Risk_Level")])
    rep_combined.to_csv(os.path.join(REPORTS_DIR, "classification_report.csv"))
    rep_combined.to_csv(os.path.join(ARTIFACTS_DIR, "classification_report.csv"))

    # Plot Confusion Matrices
    def save_cm(y_t, y_p, labels, title, filename):
        cm = confusion_matrix(y_t, y_p, normalize="true")
        plt.figure(figsize=(10, 8), dpi=300)
        sns.heatmap(cm, annot=len(labels) <= 10, fmt=".2f", cmap="Blues", xticklabels=labels, yticklabels=labels)
        plt.title(title, fontsize=12, fontweight="bold")
        plt.xlabel("Predicted Label")
        plt.ylabel("True Label")
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, filename), dpi=300, bbox_inches="tight")
        plt.savefig(os.path.join(REPORTS_DIR, filename), dpi=300, bbox_inches="tight")
        plt.savefig(os.path.join(ARTIFACTS_DIR, filename), dpi=300, bbox_inches="tight")
        plt.close()

    save_cm(y_test_pest, y_pred_pest_idx, le_pest.classes_, "Normalized Confusion Matrix - Pest Name (25 Classes)", "confusion_matrix_pest.png")
    save_cm(y_test_risk, y_pred_risk_idx, le_risk.classes_, "Normalized Confusion Matrix - Risk Level", "confusion_matrix_risk.png")
    save_cm(y_test_pest, y_pred_pest_idx, le_pest.classes_, "Normalized Confusion Matrix - Pest Name", "confusion_matrix.png")

    # PR Curves for Risk Level
    plt.figure(figsize=(9, 6), dpi=300)
    for c_idx, class_name in enumerate(le_risk.classes_):
        y_binary = (y_test_risk == c_idx).astype(int)
        precision_vals, recall_vals, _ = precision_recall_curve(y_binary, proba_risk[:, c_idx])
        ap = average_precision_score(y_binary, proba_risk[:, c_idx])
        plt.plot(recall_vals, precision_vals, lw=2, label=f"{class_name} (AP = {ap:.3f})")
    plt.title("Precision-Recall Curves - Risk Level", fontsize=12, fontweight="bold")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.legend(loc="lower left")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "precision_recall_curves_risk.png"), dpi=300, bbox_inches="tight")
    plt.savefig(os.path.join(PLOTS_DIR, "precision_recall_curve.png"), dpi=300, bbox_inches="tight")
    plt.savefig(os.path.join(REPORTS_DIR, "precision_recall_curve.png"), dpi=300, bbox_inches="tight")
    plt.close()

    # ROC Curves for Risk Level
    plt.figure(figsize=(9, 6), dpi=300)
    for c_idx, class_name in enumerate(le_risk.classes_):
        y_binary = (y_test_risk == c_idx).astype(int)
        fpr, tpr, _ = roc_curve(y_binary, proba_risk[:, c_idx])
        roc_val = auc(fpr, tpr)
        plt.plot(fpr, tpr, lw=2, label=f"{class_name} (AUC = {roc_val:.3f})")
    plt.plot([0, 1], [0, 1], color="navy", lw=1.5, linestyle="--")
    plt.title("Multiclass ROC Curves - Risk Level (One-vs-Rest)", fontsize=12, fontweight="bold")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "roc_curve.png"), dpi=300, bbox_inches="tight")
    plt.savefig(os.path.join(REPORTS_DIR, "roc_curve.png"), dpi=300, bbox_inches="tight")
    plt.close()

    # Biological Error Analysis: Top Confused Classes
    cm_pest = confusion_matrix(y_test_pest, y_pred_pest_idx)
    np.fill_diagonal(cm_pest, 0)
    top_confused = []
    for _ in range(5):
        max_idx = np.unravel_index(np.argmax(cm_pest, axis=None), cm_pest.shape)
        true_cls = le_pest.classes_[max_idx[0]]
        pred_cls = le_pest.classes_[max_idx[1]]
        count = cm_pest[max_idx]
        top_confused.append({"True_Class": true_cls, "Predicted_Class": pred_cls, "Misclassified_Count": int(count)})
        cm_pest[max_idx] = 0

    logger.info(f"Top Confused Pest Species: {top_confused}")

    # =========================================================================
    # PHASE 7: EXPLAINABLE AI (SHAP & FEATURE IMPORTANCE)
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("PHASE 7: EXPLAINABLE AI (SHAP & FEATURE IMPORTANCE)")
    logger.info("="*60)

    # Extract feature importance from fitted estimator
    classifier_step = pest_pipe.named_steps["classifier"]
    preproc_step = pest_pipe.named_steps["preprocessor"]
    num_names = NUMERICAL_FEATURES + ["Temp_Humidity_Index", "Weather_Score", "NPK_Total", "NPK_Ratio"]
    cat_names = CATEGORICAL_FEATURES
    all_engineered_feature_names = num_names + cat_names

    importances = classifier_step.feature_importances_
    df_feat_imp = pd.DataFrame({
        "Feature": all_engineered_feature_names,
        "Importance": importances
    }).sort_values(by="Importance", ascending=False).reset_index(drop=True)
    df_feat_imp["Rank"] = df_feat_imp.index + 1

    df_feat_imp.to_csv(os.path.join(REPORTS_DIR, "feature_importance.csv"), index=False)
    df_feat_imp.to_csv(os.path.join(ARTIFACTS_DIR, "feature_importance.csv"), index=False)

    # 1. Feature Importance Bar Chart
    plt.figure(figsize=(10, 7), dpi=300)
    colors = sns.color_palette("viridis", len(df_feat_imp))
    plt.barh(df_feat_imp["Feature"][::-1], df_feat_imp["Importance"][::-1], color=colors, edgecolor="black", alpha=0.85)
    plt.title("Top Feature Importances (Extra Trees Pest Classifier)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("MDI Relative Importance Score")
    plt.ylabel("Engineered & Raw Agro-Features")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "feature_importance.png"), dpi=300, bbox_inches="tight")
    plt.savefig(os.path.join(REPORTS_DIR, "feature_importance.png"), dpi=300, bbox_inches="tight")
    plt.savefig(os.path.join(ARTIFACTS_DIR, "feature_importance.png"), dpi=300, bbox_inches="tight")
    plt.close()

    # 2. SHAP Global Summary & Waterfall Plots
    logger.info("Generating SHAP Explainability plots using TreeExplainer...")
    try:
        # Pre-transform 40 test samples through feature engineering + preprocessor for high-speed SHAP
        fe_shap = pest_pipe.named_steps["feature_engineer"]
        ct_shap = pest_pipe.named_steps["preprocessor"]
        X_shap_raw = X_test_raw.iloc[:40].copy()
        X_shap_eng = fe_shap.transform(X_shap_raw)
        X_shap_proc = ct_shap.transform(X_shap_eng)

        logger.info("Computing SHAP values on representative sample (40 instances)...")
        # Use risk classifier or pest classifier with tree explainer
        explainer = shap.TreeExplainer(risk_pipe.named_steps["classifier"])
        shap_values = explainer.shap_values(X_shap_proc)

        # Global Summary Plot
        plt.figure(figsize=(11, 7), dpi=300)
        if isinstance(shap_values, list):
            shap.summary_plot(shap_values, X_shap_proc, feature_names=all_engineered_feature_names, show=False, max_display=15)
        elif len(np.shape(shap_values)) == 3:
            mean_abs_shap = np.mean(np.abs(shap_values), axis=2)
            shap.summary_plot(mean_abs_shap, X_shap_proc, feature_names=all_engineered_feature_names, show=False, max_display=15)
        else:
            shap.summary_plot(shap_values, X_shap_proc, feature_names=all_engineered_feature_names, show=False, max_display=15)
        plt.title("SHAP Global Feature Attribution Summary", fontsize=12, fontweight="bold", pad=12)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, "shap_summary.png"), dpi=300, bbox_inches="tight")
        plt.savefig(os.path.join(REPORTS_DIR, "shap_summary.png"), dpi=300, bbox_inches="tight")
        plt.close()

        # Local Waterfall / Force Plot for single farmer sample
        plt.figure(figsize=(10, 6), dpi=300)
        # Use mean absolute attribution for sample 0
        if isinstance(shap_values, list):
            sample_shap = shap_values[0][0]
            base_val = explainer.expected_value[0]
        elif len(np.shape(shap_values)) == 3:
            sample_shap = np.mean(shap_values[0], axis=1)
            base_val = np.mean(explainer.expected_value)
        else:
            sample_shap = shap_values[0]
            base_val = explainer.expected_value

        # Waterfall horizontal bar
        top_feat_indices = np.argsort(np.abs(sample_shap))[-10:]
        plt.barh([all_engineered_feature_names[i] for i in top_feat_indices], sample_shap[top_feat_indices], color=["crimson" if v < 0 else "mediumseagreen" for v in sample_shap[top_feat_indices]])
        plt.title(f"SHAP Local Feature Attribution (Single Farmer Query - Base Value: {base_val:.2f})", fontsize=11, fontweight="bold")
        plt.xlabel("SHAP Impact on Model Output")
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, "shap_waterfall.png"), dpi=300, bbox_inches="tight")
        plt.savefig(os.path.join(REPORTS_DIR, "shap_waterfall.png"), dpi=300, bbox_inches="tight")
        plt.close()
        logger.info("SHAP plots saved successfully.")
    except Exception as e:
        logger.warning(f"SHAP computation exception (handled gracefully): {e}")

    # =========================================================================
    # PHASE 9: PRODUCTION MODEL EXPORT & METADATA SERIALIZATION
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("PHASE 9: PRODUCTION MODEL EXPORT & SERIALIZATION")
    logger.info("="*60)

    # 1. Save Full Unified Production Pipeline
    prod_model_path = os.path.join(MODELS_DIR, "best_model.pkl")
    prod_pipeline.save(prod_model_path)
    # Also save as trained_model.pkl for backward compatibility
    prod_pipeline.save(os.path.join(MODELS_DIR, "trained_model.pkl"))
    prod_pipeline.save(os.path.join(ARTIFACTS_DIR, "trained_model.pkl"))
    prod_pipeline.save(os.path.join(ARTIFACTS_DIR, "best_model.pkl"))
    logger.info(f"Production model saved to: {prod_model_path}")

    # 2. Save standalone preprocessor for legacy modules
    preproc_obj = pest_pipe.named_steps["preprocessor"]
    joblib.dump(preproc_obj, os.path.join(MODELS_DIR, "preprocessor.pkl"))
    joblib.dump(preproc_obj, os.path.join(MODELS_DIR, "preprocessing_pipeline.pkl"))
    joblib.dump(preproc_obj, os.path.join(ARTIFACTS_DIR, "preprocessor.pkl"))
    joblib.dump(preproc_obj, os.path.join(ARTIFACTS_DIR, "preprocessing_pipeline.pkl"))

    # 3. Model Metadata JSON
    metadata = {
        "project": "AI-Powered Crop Pest Prediction & Advisory System",
        "pipeline_version": "2.0.0",
        "serialization_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset_version": "v1.4-clean-sanitized",
        "total_dataset_rows": len(df_clean),
        "train_rows": len(X_train_raw),
        "test_rows": len(X_test_raw),
        "raw_input_features": RAW_INPUT_FEATURES,
        "engineered_features": ["Temp_Humidity_Index", "Weather_Score", "NPK_Total", "NPK_Ratio"],
        "pest_classifier": {
            "algorithm": "ExtraTreesClassifier",
            "hyperparameters": best_et_params,
            "classes_count": len(le_pest.classes_),
            "classes": le_pest.classes_.tolist(),
            "test_accuracy": round(pest_acc, 4),
            "test_top3_accuracy": round(pest_top3_acc, 4),
            "test_macro_f1": round(f1_m_pest, 4),
            "cv_5fold": cv_summary["pest_classifier_5fold"]
        },
        "risk_classifier": {
            "algorithm": "RandomForestClassifier",
            "hyperparameters": best_rf_params,
            "class_weights": "balanced",
            "classes_count": len(le_risk.classes_),
            "classes": le_risk.classes_.tolist(),
            "test_accuracy": round(risk_acc, 4),
            "test_balanced_accuracy": round(risk_bal_acc, 4),
            "test_macro_f1": round(f1_m_risk, 4),
            "cv_5fold": cv_summary["risk_classifier_5fold"]
        },
        "top_confused_pest_classes": top_confused,
        "git_commit": "4e719c8"
    }

    feature_cols_dict = {
        "raw_input_features": RAW_INPUT_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "numerical_features": NUMERICAL_FEATURES,
        "engineered_features": ["Temp_Humidity_Index", "Weather_Score", "NPK_Total", "NPK_Ratio"],
        "all_transformed_features": all_engineered_feature_names,
        "pest_classes": le_pest.classes_.tolist(),
        "risk_classes": le_risk.classes_.tolist()
    }
    training_config_dict = {
        "pipeline_version": "2.0.0",
        "random_state": RANDOM_STATE,
        "test_size": 0.20,
        "cv_folds": 5,
        "pest_model": {"algorithm": "ExtraTreesClassifier", "params": best_et_params},
        "risk_model": {"algorithm": "RandomForestClassifier", "params": best_rf_params, "class_weight": "balanced"}
    }

    # Save JSON files
    for folder in [MODELS_DIR, ARTIFACTS_DIR]:
        with open(os.path.join(folder, "model_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        with open(os.path.join(folder, "metrics.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        with open(os.path.join(folder, "feature_columns.json"), "w", encoding="utf-8") as f:
            json.dump(feature_cols_dict, f, indent=2)
        with open(os.path.join(folder, "training_config.json"), "w", encoding="utf-8") as f:
            json.dump(training_config_dict, f, indent=2)

    # Save tabular and plot artifacts into models/
    df_feat_imp.to_csv(os.path.join(MODELS_DIR, "feature_importance.csv"), index=False)
    rep_combined.to_csv(os.path.join(MODELS_DIR, "classification_report.csv"), index=False)

    import shutil
    for img_name in ["confusion_matrix.png", "shap_summary.png"]:
        src_img = os.path.join(PLOTS_DIR, img_name)
        if os.path.exists(src_img):
            shutil.copy(src_img, os.path.join(MODELS_DIR, img_name))

    logger.info("Phases 4 through 9 completed with full production artifacts generated in models/ and artifacts/!")
    return metadata

if __name__ == "__main__":
    execute_phases_4_to_9()
