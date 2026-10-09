"""
Step 6: Hyperparameter Tuning Module.
Employs Optuna with Bayesian Optimization (Tree-structured Parzen Estimator - TPE)
to fine-tune tree depth, estimators, learning rate, regularization, and sampling parameters.
"""
import os
import sys
import json
import optuna
import numpy as np
import pandas as pd
from typing import Dict, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier

from src.pipeline_config import (
    REPORTS_DIR,
    ARTIFACTS_DIR,
    RANDOM_STATE
)
from utils.logger import setup_logger

logger = setup_logger("hyperparameter_tuning", "tuning.log")
optuna.logging.set_verbosity(optuna.logging.WARNING)

def tune_lightgbm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_trials: int = 15,
    cv_folds: int = 3
) -> Dict[str, Any]:
    """Tunes LightGBM hyperparameters with Optuna."""
    logger.info(f"Starting Bayesian Optimization for LightGBM ({n_trials} trials, {cv_folds}-Fold CV)...")

    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=RANDOM_STATE)

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 60, 160, step=20),
            "max_depth": trial.suggest_int("max_depth", 5, 14),
            "learning_rate": trial.suggest_float("learning_rate", 0.03, 0.20, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 20, 80),
            "subsample": trial.suggest_float("subsample", 0.65, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.65, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
            "random_state": RANDOM_STATE,
            "n_jobs": -1,
            "verbose": -1
        }
        model = LGBMClassifier(**params)
        scores = cross_val_score(model, X_train, y_train, cv=skf, scoring="f1_macro", n_jobs=-1)
        return float(np.mean(scores))

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    logger.info(f"Optimization finished! Best Trial Score (Macro F1): {study.best_value:.4f}")
    logger.info(f"Best Hyperparameters: {study.best_params}")

    return {
        "best_score": study.best_value,
        "best_params": study.best_params,
        "all_trials": [
            {"trial": t.number, "value": t.value, "params": t.params}
            for t in study.trials if t.value is not None
        ]
    }

def tune_random_forest(
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_trials: int = 15,
    cv_folds: int = 3
) -> Dict[str, Any]:
    """Tunes Random Forest hyperparameters with Optuna."""
    logger.info(f"Starting Bayesian Optimization for Random Forest ({n_trials} trials, {cv_folds}-Fold CV)...")

    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=RANDOM_STATE)

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 150, step=25),
            "max_depth": trial.suggest_int("max_depth", 10, 24),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 8),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 4),
            "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", 0.7]),
            "random_state": RANDOM_STATE,
            "n_jobs": -1
        }
        model = RandomForestClassifier(**params)
        scores = cross_val_score(model, X_train, y_train, cv=skf, scoring="f1_macro", n_jobs=-1)
        return float(np.mean(scores))

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    logger.info(f"Optimization finished! Best Trial Score (Macro F1): {study.best_value:.4f}")
    logger.info(f"Best Hyperparameters: {study.best_params}")

    return {
        "best_score": study.best_value,
        "best_params": study.best_params,
        "all_trials": [
            {"trial": t.number, "value": t.value, "params": t.params}
            for t in study.trials if t.value is not None
        ]
    }

def run_tuning(best_model_name: str, X_train: np.ndarray, y_train: np.ndarray, target_label: str) -> Dict[str, Any]:
    """Runs hyperparameter tuning for the top model and saves results."""
    logger.info(f"=========================================================")
    logger.info(f"STEP 6: HYPERPARAMETER TUNING FOR TARGET: {target_label} ({best_model_name})")
    logger.info(f"=========================================================")

    if "LightGBM" in best_model_name or "XGBoost" in best_model_name or "CatBoost" in best_model_name:
        tune_results = tune_lightgbm(X_train, y_train)
    else:
        tune_results = tune_random_forest(X_train, y_train)

    tune_path = os.path.join(REPORTS_DIR, f"hyperparameter_tuning_{target_label.lower()}.json")
    with open(tune_path, "w", encoding="utf-8") as f:
        json.dump(tune_results, f, indent=2)
    logger.info(f"Tuning results exported to {tune_path}")

    return tune_results

if __name__ == "__main__":
    from src.preprocessor import prepare_stratified_splits
    splits = prepare_stratified_splits(save_artifacts=False)
    # Stratified subset of 15,000 samples for fast, thorough Bayesian optimization
    X_sub = splits["X_train"][:15000]
    y_sub_pest = splits["y_train_pest"][:15000]
    y_sub_risk = splits["y_train_risk"][:15000]

    logger.info("Executing Optuna Bayesian Hyperparameter Optimization...")
    run_tuning("LightGBM", X_sub, y_sub_pest, "pest_name")
    run_tuning("Random Forest", X_sub, y_sub_risk, "risk_level")
    logger.info("Hyperparameter tuning completed for both targets.")
