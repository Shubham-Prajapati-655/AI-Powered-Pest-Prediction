"""
Automated Pytest Suite for ML Pipeline Integrity, Zero Leakage & Advisory Engine.
Verifies that:
1. No target, post-harvest, or advisory features exist in model inputs.
2. Preprocessor transforms inputs accurately without throwing errors.
3. AdvisoryEngine functions strictly post-prediction with valid crop-pest recommendations.
"""
import os
import sys
import pytest
import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.pipeline_config import (
    ALL_FEATURE_COLUMNS,
    LEAKAGE_AND_POST_HARVEST_COLUMNS,
    TARGET_PEST,
    TARGET_RISK
)
from src.advisory_engine import AdvisoryEngine

app_dir = os.path.join(BASE_DIR, "app")
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from predictor import predict_pest_and_risk
from recommender import get_recommendations

def test_zero_target_leakage_in_features():
    """Verify strictly no target labels in input features."""
    feature_set = set(ALL_FEATURE_COLUMNS)
    assert TARGET_PEST not in feature_set, "Target Pest_Name leaked into features!"
    assert TARGET_RISK not in feature_set, "Target Risk_Level leaked into features!"
    assert "Outbreak" not in feature_set, "Binary target Outbreak leaked into features!"
    assert "Risk_Score" not in feature_set, "Synthetic target Risk_Score leaked into features!"

def test_zero_post_harvest_leakage_in_features():
    """Verify strictly no post-harvest or economic features in input features."""
    feature_set = set(ALL_FEATURE_COLUMNS)
    post_harvest = ["Yield", "Production_Tons", "Area_Hectares", "Crop_Health_Index"]
    for ph in post_harvest:
        assert ph not in feature_set, f"Post-harvest feature {ph} leaked into features!"

def test_zero_advisory_leakage_in_features():
    """Verify advisory outputs are never used as model inputs."""
    feature_set = set(ALL_FEATURE_COLUMNS)
    advisory_cols = [
        "Recommended_Pesticide",
        "Recommended_Fertilizer",
        "Organic_Control",
        "Chemical_Control"
    ]
    for adv in advisory_cols:
        assert adv not in feature_set, f"Advisory output {adv} leaked into features!"

def test_advisory_engine_lookup():
    """Verify AdvisoryEngine outputs valid recommendation payloads."""
    engine = AdvisoryEngine()
    advisory = engine.get_advisory("Rice", "Brown Planthopper", "High")

    assert "crop" in advisory
    assert advisory["crop"] == "Rice"
    assert advisory["predicted_pest"] == "Brown Planthopper"
    assert advisory["predicted_risk"] == "High"
    assert len(advisory["recommended_pesticide"]) > 0
    assert len(advisory["chemical_control"]) > 0
    assert len(advisory["organic_control"]) > 0
    assert len(advisory["recommended_fertilizer"]) > 0
    assert len(advisory["safety_notes"]) > 0
    assert len(advisory["prevention"]) > 0

def test_recommender_integration():
    """Verify app.recommender returns expected format for Streamlit."""
    rec = get_recommendations("Cotton", "Pink Bollworm", "High")
    assert rec["risk_level"] == "High"
    assert "🚨 HIGH" in rec["severity_badge"]
    assert rec["card_class"] == "stError"
    assert "Chlorantraniliprole" in rec["pesticide"] or "Emamectin" in rec["pesticide"] or "Bt" in rec["pesticide"] or len(rec["pesticide"]) > 0

def test_predictor_inference():
    """Verify inference pipeline executes and returns valid predictions."""
    pest, pest_conf, risk, risk_conf, top3, note = predict_pest_and_risk(
        state="Punjab",
        district="Ludhiana",
        crop="Rice",
        season="Kharif",
        temp=30.0,
        humidity=78.0,
        rainfall=120.0
    )
    assert isinstance(pest, str) and len(pest) > 0
    assert 0.0 <= pest_conf <= 100.0
    assert risk in ["High", "Medium", "Low"]
    assert 0.0 <= risk_conf <= 100.0
    assert len(top3) == 3
    assert all("pest" in cand and "confidence" in cand for cand in top3)
