"""
Step 1 & Step 2: Dataset Sanitization and Feature Engineering Module.
Strictly removes all target leakage, post-harvest features, and post-prediction advisory fields.
Rebuilds scientifically valid agro-climatic engineered features solely from pre-prediction inputs.
"""
import os
import sys
import pandas as pd
import numpy as np

# Ensure root directory is on sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline_config import (
    MASTER_DATASET_PATH,
    CLEAN_DATASET_PATH,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    ENGINEERED_FEATURES,
    ALL_FEATURE_COLUMNS,
    TARGET_PEST,
    TARGET_RISK,
    LEAKAGE_AND_POST_HARVEST_COLUMNS,
    RANDOM_STATE
)
from utils.logger import setup_logger

logger = setup_logger("dataset_sanitizer", "sanitizer.log")

def sanitize_and_engineer_dataset(input_csv_path: str = MASTER_DATASET_PATH, output_csv_path: str = CLEAN_DATASET_PATH) -> pd.DataFrame:
    """
    Loads raw master dataset, audits columns, eliminates leakage,
    re-engineers valid features, and saves sanitized dataset.
    """
    logger.info("=========================================================")
    logger.info("STEP 1: DATASET AUDIT & SANITIZATION")
    logger.info("=========================================================")
    
    if not os.path.exists(input_csv_path):
        raise FileNotFoundError(f"Master dataset not found at {input_csv_path}")

    logger.info(f"Loading master dataset from: {input_csv_path}")
    df_raw = pd.read_csv(input_csv_path)
    total_raw_rows, total_raw_cols = df_raw.shape
    logger.info(f"Loaded raw dataset with {total_raw_rows:,} rows and {total_raw_cols} columns.")

    # 1. Audit Columns
    raw_columns = df_raw.columns.tolist()
    logger.info(f"Raw Columns ({len(raw_columns)}): {raw_columns}")

    # Identify leaking, post-harvest, and advisory columns present in raw data
    removed_cols = [c for c in LEAKAGE_AND_POST_HARVEST_COLUMNS if c in raw_columns]
    logger.info("---------------------------------------------------------")
    logger.info("REMOVING LEAKING, POST-HARVEST & ADVISORY COLUMNS:")
    for col in removed_cols:
        reason = "Target Leakage" if col in ["Outbreak", "Risk_Score"] else \
                 "Post-Harvest / Chronological Leakage" if col in ["Area_Hectares", "Production_Tons", "Yield", "Crop_Health_Index"] else \
                 "Post-Prediction Advisory (Generated AFTER inference)" if col in ["Recommended_Fertilizer", "Recommended_Pesticide", "Organic_Control", "Chemical_Control"] else \
                 "Redundant Discretization / Collinear"
        logger.info(f"  [-] Dropping '{col}': Reason -> {reason}")

    # 2. Check for missing values and duplicates
    logger.info("---------------------------------------------------------")
    logger.info("AUDITING DATA INTEGRITY (MISSING VALUES & DUPLICATES):")
    n_dupes = df_raw.duplicated().sum()
    logger.info(f"Raw duplicate rows: {n_dupes}")
    if n_dupes > 0:
        df_raw = df_raw.drop_duplicates()
        logger.info(f"Dropped {n_dupes} duplicate rows. New row count: {len(df_raw):,}")

    # Check for missing values in required raw columns
    required_raw_cols = CATEGORICAL_FEATURES + NUMERICAL_FEATURES + [TARGET_PEST, TARGET_RISK]
    missing_counts = df_raw[required_raw_cols].isnull().sum()
    cols_with_missing = missing_counts[missing_counts > 0]
    if not cols_with_missing.empty:
        logger.warning(f"Columns with missing values:\n{cols_with_missing}")
        # Drop rows missing targets
        df_raw = df_raw.dropna(subset=[TARGET_PEST, TARGET_RISK])
    else:
        logger.info("Zero missing values in required raw features and targets.")

    # 3. Clean Text Columns
    for col in CATEGORICAL_FEATURES + [TARGET_PEST, TARGET_RISK]:
        df_raw[col] = df_raw[col].astype(str).str.strip()

    logger.info("=========================================================")
    logger.info("STEP 2: FEATURE ENGINEERING (SCIENTIFICALLY SOUND)")
    logger.info("=========================================================")
    # Rebuild engineered features strictly from valid inputs:
    # 1. Temp_Humidity_Index (Thom's THI): Established bio-meteorological index for insect thermal stress
    temp = df_raw["Temperature"].values
    hum = df_raw["Humidity"].values
    rain = df_raw["Rainfall"].values

    logger.info("Recomputing Thom's Temp_Humidity_Index (THI)...")
    thi = 0.8 * temp + (hum / 100.0) * (temp - 14.3) + 46.4
    df_raw["Temp_Humidity_Index"] = np.round(thi, 2)

    # 2. NPK_Total: Total macronutrient density
    n_val = df_raw["Nitrogen"].values
    p_val = df_raw["Phosphorus"].values
    k_val = df_raw["Potassium"].values

    logger.info("Recomputing NPK_Total (N + P + K)...")
    df_raw["NPK_Total"] = n_val + p_val + k_val

    # 3. NPK_Ratio: Ratio of vegetative/rooting nutrients (N+P) to stress tolerance nutrient (K)
    logger.info("Recomputing NPK_Ratio ((N + P) / (K + 1.0))...")
    df_raw["NPK_Ratio"] = np.round((n_val + p_val) / (k_val + 1.0), 2)

    # 4. Weather_Score: Proliferation microclimate suitability index (Gaussian temp around 28C, humidity excess, rainfall)
    logger.info("Computing microclimatic Weather_Score (pure weather function, ZERO target leakage)...")
    temp_suit = np.exp(-((temp - 28.0) ** 2) / (2.0 * (5.5 ** 2))) * 45.0
    hum_suit = np.clip((hum - 35.0) / 50.0, 0.0, 1.0) * 40.0
    rain_suit = np.clip(rain / 150.0, 0.0, 1.0) * 15.0
    df_raw["Weather_Score"] = np.round(np.clip(temp_suit + hum_suit + rain_suit, 5.0, 100.0), 2)

    # Assemble sanitized dataframe
    sanitized_cols = ALL_FEATURE_COLUMNS + [TARGET_PEST, TARGET_RISK]
    df_sanitized = df_raw[sanitized_cols].copy()

    logger.info(f"Sanitization complete. Final dataset shape: {df_sanitized.shape}")
    logger.info(f"Target '{TARGET_PEST}' classes ({df_sanitized[TARGET_PEST].nunique()}): {sorted(df_sanitized[TARGET_PEST].unique())}")
    logger.info(f"Target '{TARGET_RISK}' distribution:\n{df_sanitized[TARGET_RISK].value_counts(normalize=True).mul(100).round(2).to_dict()}%")

    # Save to disk
    logger.info(f"Saving sanitized dataset to: {output_csv_path}")
    df_sanitized.to_csv(output_csv_path, index=False)
    logger.info("Sanitized dataset saved successfully.")

    return df_sanitized

if __name__ == "__main__":
    sanitize_and_engineer_dataset()
