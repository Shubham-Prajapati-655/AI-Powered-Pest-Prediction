"""
Central Configuration for AI-Powered Crop Pest Prediction & Advisory Pipeline.
Defines paths, feature definitions, model hyperparameters, random seeds, and constants.
"""
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Directory Paths
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
MODELS_DIR = os.path.join(BASE_DIR, "models")
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
PLOTS_DIR = os.path.join(BASE_DIR, "plots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Raw Datasets
MASTER_DATASET_PATH = os.path.join(DATASETS_DIR, "master_crop_pest_advisory.csv")
SAMPLE_DATASET_PATH = os.path.join(DATASETS_DIR, "master_crop_pest_advisory_sample.csv")
ADVISORY_KB_PATH = os.path.join(DATASETS_DIR, "pesticide_recommendations.json")

# Clean Serialized Splits
CLEAN_DATASET_PATH = os.path.join(DATASETS_DIR, "clean_pest_risk_dataset.csv")

# Random Seed for Reproducibility
RANDOM_STATE = 42

# --- FEATURE TAXONOMY ---
# 1. Valid Input Categorical Features (Available BEFORE prediction)
CATEGORICAL_FEATURES = [
    "District",
    "Crop_Name",
    "Season",
    "Soil_Type",
    "State"
]

# 2. Valid Input Numerical Features (Microclimate & Soil chemistry available BEFORE prediction)
NUMERICAL_FEATURES = [
    "Temperature",
    "Humidity",
    "Rainfall",
    "Wind_Speed",
    "Soil_Moisture",
    "Soil_pH",
    "Nitrogen",
    "Phosphorus",
    "Potassium",
    "Organic_Carbon"
]

# 3. Valid Scientifically Engineered Features (Constructed ONLY from clean inputs)
ENGINEERED_FEATURES = [
    "Temp_Humidity_Index",
    "Weather_Score",
    "NPK_Total",
    "NPK_Ratio"
]

# Raw Features expected before feature engineering
RAW_INPUT_FEATURES = CATEGORICAL_FEATURES + NUMERICAL_FEATURES

# All Features for ML Model Input
ALL_FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERICAL_FEATURES + ENGINEERED_FEATURES

# Targets
TARGET_PEST = "Pest_Name"
TARGET_RISK = "Risk_Level"

# Columns to strictly REMOVE from ML inputs due to:
# - Target Leakage (Outbreak, Risk_Score)
# - Post-Harvest / Chronological Leakage (Area_Hectares, Production_Tons, Yield, Crop_Health_Index)
# - Post-Prediction Advisory Outputs (Recommended_Fertilizer, Recommended_Pesticide, Organic_Control, Chemical_Control)
# - Redundant Step Discretizations (Rainfall_Category, Moisture_Level, Soil_Health_Index)
LEAKAGE_AND_POST_HARVEST_COLUMNS = [
    "Outbreak",
    "Risk_Score",
    "Crop_Health_Index",
    "Soil_Health_Index",
    "Area_Hectares",
    "Production_Tons",
    "Yield",
    "Recommended_Fertilizer",
    "Recommended_Pesticide",
    "Organic_Control",
    "Chemical_Control",
    "Rainfall_Category",
    "Moisture_Level",
    "Pressure",       # optional / non-essential microclimate
    "Cloud_Cover",    # optional
    "Crop_Category",  # redundant with Crop_Name
    "Sowing_Season"   # redundant with Season
]
