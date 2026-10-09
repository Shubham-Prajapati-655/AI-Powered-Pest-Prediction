"""
Step 7: Feature Importance & Model Explainability Module.
Generates:
1. Gini / Gain Tree Feature Importance
2. Permutation Feature Importance on Test Split
3. SHAP (SHapley Additive exPlanations) Global & Local Attribution
4. Publication-Quality Plots: Top 20 Features & SHAP Summary
5. Agronomic Rationale & Pest Proliferation Interpretations
"""
import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.inspection import permutation_importance
import shap

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline_config import (
    PLOTS_DIR,
    REPORTS_DIR,
    ARTIFACTS_DIR,
    RANDOM_STATE
)
from utils.logger import setup_logger

logger = setup_logger("feature_importance", "importance.log")
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["font.family"] = "sans-serif"

def analyze_and_plot_feature_importance(
    model,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list,
    target_name: str = "Pest_Name",
    classes: list = None
):
    """
    Computes MDI importance, Permutation importance, SHAP values,
    and generates plots and CSV reports.
    """
    logger.info(f"=========================================================")
    logger.info(f"STEP 7: FEATURE IMPORTANCE ANALYSIS FOR {target_name.upper()}")
    logger.info(f"=========================================================")

    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # 1. Native Model Feature Importance (MDI / Gain)
    if hasattr(model, "feature_importances_"):
        raw_importances = model.feature_importances_
    elif hasattr(model, "estimators_") and hasattr(model.estimators_[0], "feature_importances_"):
        raw_importances = model.estimators_[0].feature_importances_
    else:
        raw_importances = np.ones(len(feature_names)) / len(feature_names)

    df_importance = pd.DataFrame({
        "Feature": feature_names,
        "MDI_Importance": raw_importances
    })

    # 2. Permutation Importance on Test Set
    logger.info("Computing Permutation Feature Importance on test data (n_repeats=5)...")
    sub_test_size = min(3000, len(X_test))
    perm_result = permutation_importance(
        model,
        X_test[:sub_test_size],
        y_test[:sub_test_size],
        n_repeats=5,
        random_state=RANDOM_STATE,
        scoring="accuracy",
        n_jobs=-1
    )
    df_importance["Permutation_Importance_Mean"] = perm_result.importances_mean
    df_importance["Permutation_Importance_Std"] = perm_result.importances_std

    df_importance = df_importance.sort_values(by="MDI_Importance", ascending=False).reset_index(drop=True)
    df_importance["Rank"] = df_importance.index + 1

    # Save to CSV
    imp_csv_path = os.path.join(REPORTS_DIR, f"feature_importance_{target_name.lower()}.csv")
    df_importance.to_csv(imp_csv_path, index=False)
    # Also save the primary feature_importance.csv requested
    primary_imp_csv = os.path.join(REPORTS_DIR, "feature_importance.csv")
    df_importance.to_csv(primary_imp_csv, index=False)
    df_importance.to_csv(os.path.join(ARTIFACTS_DIR, "feature_importance.csv"), index=False)
    logger.info(f"Feature importance table saved to {imp_csv_path}, {primary_imp_csv}, and artifacts/")

    # 3. Plot Top 20 Feature Importances
    logger.info("Rendering Top 20 Feature Importance chart...")
    top20 = df_importance.head(20).copy()

    plt.figure(figsize=(10, 8), dpi=300)
    colors = sns.color_palette("viridis", len(top20))
    bars = plt.barh(top20["Feature"][::-1], top20["MDI_Importance"][::-1], color=colors, edgecolor="black", alpha=0.85)

    plt.title(f"Top 20 Feature Importances - {target_name.replace('_', ' ')}", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("Relative Importance Score (Gini / Gain MDI)", fontsize=11, fontweight="semibold")
    plt.ylabel("Features", fontsize=11, fontweight="semibold")
    plt.tight_layout()

    plot_path = os.path.join(PLOTS_DIR, f"feature_importance_{target_name.lower()}.png")
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.savefig(os.path.join(PLOTS_DIR, "feature_importance.png"), dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"Feature importance plot saved to: {plot_path}")

    # 4. SHAP Values
    logger.info("Computing SHAP attribution values using TreeExplainer...")
    try:
        sample_shap_size = min(500, len(X_test))
        X_shap_sample = X_test[:sample_shap_size]
        
        # Use TreeExplainer
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_shap_sample)

        # Plot SHAP summary
        plt.figure(figsize=(11, 7), dpi=300)
        if isinstance(shap_values, list):
            # Multi-class: plot bar of mean absolute SHAP per class or first class
            shap.summary_plot(shap_values, X_shap_sample, feature_names=feature_names, show=False, max_display=15)
        elif len(shap_values.shape) == 3:
            # Multi-class 3D array: [samples, features, classes]
            mean_abs_shap = np.mean(np.abs(shap_values), axis=2)
            shap.summary_plot(mean_abs_shap, X_shap_sample, feature_names=feature_names, show=False, max_display=15)
        else:
            shap.summary_plot(shap_values, X_shap_sample, feature_names=feature_names, show=False, max_display=15)

        shap_plot_path = os.path.join(PLOTS_DIR, f"shap_summary_{target_name.lower()}.png")
        plt.title(f"SHAP Global Feature Impact Summary - {target_name.replace('_', ' ')}", fontsize=13, fontweight="bold", pad=15)
        plt.tight_layout()
        plt.savefig(shap_plot_path, dpi=300, bbox_inches="tight")
        plt.savefig(os.path.join(PLOTS_DIR, "shap_summary.png"), dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"SHAP summary plot saved to: {shap_plot_path}")
    except Exception as e:
        logger.warning(f"SHAP computation encountered exception (skipped): {e}")

    # 5. Agronomic Explanation Documentation
    explanations = {
        "Crop_Name": "Pest host specificity is the strongest taxonomic determinant (e.g. Pink Bollworm infests only Cotton; Brown Planthopper infests only Rice).",
        "Temperature": "Insects are poikilothermic. Ambient temperatures dictate thermal metabolic rates, egg development velocity, and reproduction rate.",
        "Humidity": "High relative humidity (>75%) triggers high survival of sucking pests (Aphids, Planthoppers) and spore germination.",
        "Temp_Humidity_Index": "Integrates temperature and water vapor pressure deficit, indicating acute pest proliferation comfort zone.",
        "Soil_Moisture": "Governs soil pupation survival (e.g. Cutworm, Armyworm larvae) and plant tissue hydration.",
        "NPK_Ratio": "Excessive vegetative nitrogen creates succulent leaf tissues vulnerable to chewing caterpillars and stem borers.",
        "Weather_Score": "Composite bio-climatic suitability index reflecting microclimate conducive to population explosion."
    }

    logger.info("Feature importance analysis completed successfully.")
    return df_importance, explanations

if __name__ == "__main__":
    pass
