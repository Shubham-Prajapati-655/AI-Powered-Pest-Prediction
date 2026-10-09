"""
Phase 3: Unified Scikit-Learn Production Pipeline.
Implements:
1. AgroFeatureEngineeringTransformer (Custom BaseEstimator & TransformerMixin)
2. ColumnTransformer (StandardScaler for numerics, OrdinalEncoder for categoricals)
3. Integrated Pipeline (Feature Engineering -> ColumnTransformer -> Estimator)
4. UnifiedProductionPipeline container for dual targets (Pest_Name + Risk_Level)
Zero external preprocessing: raw input DataFrame is passed directly to .predict()!
"""
import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List, Optional
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OrdinalEncoder, LabelEncoder
from sklearn.impute import SimpleImputer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline_config import (
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    ENGINEERED_FEATURES,
    ALL_FEATURE_COLUMNS,
    RANDOM_STATE
)

# Raw features expected from farmer / sensor / API BEFORE feature engineering
RAW_INPUT_FEATURES = [
    "District", "Crop_Name", "Season", "Soil_Type", "State",
    "Temperature", "Humidity", "Rainfall", "Wind_Speed",
    "Soil_Moisture", "Soil_pH", "Nitrogen", "Phosphorus",
    "Potassium", "Organic_Carbon"
]

class AgroFeatureEngineeringTransformer(BaseEstimator, TransformerMixin):
    """
    Scikit-Learn compliant transformer that computes scientifically verified
    bio-meteorological and edaphic features strictly from raw pre-prediction inputs:
    - Temp_Humidity_Index (Thom's bio-meteorological thermal stress index)
    - NPK_Total (Macronutrient density)
    - NPK_Ratio ((N + P) / (K + 1))
    - Weather_Score (Microclimatic pest proliferation suitability index)
    """
    def __init__(self):
        self.engineered_feature_names = ["Temp_Humidity_Index", "Weather_Score", "NPK_Total", "NPK_Ratio"]

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        # Support both pandas DataFrame and numpy array/dict
        if isinstance(X, pd.DataFrame):
            df = X.copy()
        elif isinstance(X, dict):
            df = pd.DataFrame([X])
        else:
            df = pd.DataFrame(X, columns=RAW_INPUT_FEATURES)

        # Ensure correct column naming and string stripping
        for col in ["District", "Crop_Name", "Season", "Soil_Type", "State"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        # Coerce numerics
        for col in ["Temperature", "Humidity", "Rainfall", "Wind_Speed", "Soil_Moisture", "Soil_pH", "Nitrogen", "Phosphorus", "Potassium", "Organic_Carbon"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        temp = df["Temperature"].values.astype(float)
        hum = df["Humidity"].values.astype(float)
        rain = df["Rainfall"].values.astype(float)
        n_val = df["Nitrogen"].values.astype(float)
        p_val = df["Phosphorus"].values.astype(float)
        k_val = df["Potassium"].values.astype(float)

        # 1. Thom's Temperature-Humidity Index (THI)
        thi = 0.8 * temp + (hum / 100.0) * (temp - 14.3) + 46.4
        df["Temp_Humidity_Index"] = np.round(thi, 2)

        # 2. Total Macronutrient Density
        df["NPK_Total"] = n_val + p_val + k_val

        # 3. Macronutrient Ratio (Vegetative vs Stress tolerance)
        df["NPK_Ratio"] = np.round((n_val + p_val) / (k_val + 1.0), 2)

        # 4. Proliferation Microclimate Suitability
        temp_suit = np.exp(-((temp - 28.0) ** 2) / (2.0 * (5.5 ** 2))) * 45.0
        hum_suit = np.clip((hum - 35.0) / 50.0, 0.0, 1.0) * 40.0
        rain_suit = np.clip(rain / 150.0, 0.0, 1.0) * 15.0
        df["Weather_Score"] = np.round(np.clip(temp_suit + hum_suit + rain_suit, 5.0, 100.0), 2)

        # Reorder to standard ALL_FEATURE_COLUMNS order
        ordered_cols = ALL_FEATURE_COLUMNS
        return df[ordered_cols]

def build_column_transformer():
    """
    Builds the ColumnTransformer for the processed feature matrix:
    - Numerical + Engineered -> SimpleImputer(median) + StandardScaler()
    - Categorical -> SimpleImputer(most_frequent) + OrdinalEncoder()
    """
    num_cols = NUMERICAL_FEATURES + ENGINEERED_FEATURES
    cat_cols = CATEGORICAL_FEATURES

    numeric_pipe = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])

    categorical_pipe = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, num_cols),
            ("cat", categorical_pipe, cat_cols)
        ],
        remainder="drop"
    )
    return preprocessor

def create_end_to_end_pipeline(estimator) -> Pipeline:
    """
    Creates ONE single complete Scikit-Learn Pipeline:
    Raw Inputs -> AgroFeatureEngineeringTransformer -> ColumnTransformer -> Final Estimator
    No preprocessing outside the Pipeline!
    """
    return Pipeline(steps=[
        ("feature_engineer", AgroFeatureEngineeringTransformer()),
        ("preprocessor", build_column_transformer()),
        ("classifier", estimator)
    ])

class UnifiedProductionPipeline:
    """
    Production-grade container encapsulating both dual-target end-to-end pipelines
    (Pest_Name + Risk_Level) and their corresponding target label encoders.
    Exposes clean .predict(), .predict_proba(), and .predict_top3() methods.
    """
    def __init__(
        self,
        pest_pipeline: Pipeline,
        risk_pipeline: Pipeline,
        le_pest: LabelEncoder,
        le_risk: LabelEncoder,
        raw_features: List[str] = RAW_INPUT_FEATURES
    ):
        self.pest_pipeline = pest_pipeline
        self.risk_pipeline = risk_pipeline
        self.le_pest = le_pest
        self.le_risk = le_risk
        self.raw_features = raw_features
        self.version = "2.0.0"

    def predict(self, raw_X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Accepts raw input DataFrame. Runs feature engineering, scaling, encoding,
        and predictions inside the pipelines. Returns decoded class label strings.
        """
        pred_pest_idx = self.pest_pipeline.predict(raw_X)
        pred_risk_idx = self.risk_pipeline.predict(raw_X)
        pest_labels = self.le_pest.inverse_transform(pred_pest_idx)
        risk_labels = self.le_risk.inverse_transform(pred_risk_idx)
        return pest_labels, risk_labels

    def predict_proba(self, raw_X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Returns probability distributions for both targets."""
        pest_proba = self.pest_pipeline.predict_proba(raw_X)
        risk_proba = self.risk_pipeline.predict_proba(raw_X)
        return pest_proba, risk_proba

    def predict_top3(self, raw_X: pd.DataFrame) -> List[List[Dict[str, Any]]]:
        """Returns the top 3 candidate pests with probability confidences."""
        pest_proba = self.pest_pipeline.predict_proba(raw_X)
        results = []
        for i in range(len(pest_proba)):
            top3_idx = np.argsort(pest_proba[i])[-3:][::-1]
            top3_list = [
                {
                    "pest": self.le_pest.inverse_transform([idx])[0],
                    "confidence": float(pest_proba[i][idx])
                }
                for idx in top3_idx
            ]
            results.append(top3_list)
        return results

    def save(self, filepath: str):
        """Serializes production pipeline to disk."""
        joblib.dump(self, filepath)

    @classmethod
    def load(cls, filepath: str) -> "UnifiedProductionPipeline":
        """Loads serialized production pipeline from disk."""
        return joblib.load(filepath)
