"""
Post-Prediction Advisory Engine Connector for Streamlit Application.
Seamlessly interfaces with the production dynamic AdvisoryEngine.
CRITICAL: Operates strictly post-inference. Zero ML feature leakage.
Farmer-friendly: Completely sanitizes technical risk badges from the UI.
"""
import os
import sys
from typing import Dict, Any, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.advisory_engine import AdvisoryEngine

_engine_instance = None

def get_engine():
    """Singleton getter for cached AdvisoryEngine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AdvisoryEngine()
    return _engine_instance

def load_recommendations_json():
    """Loads and returns the recommendation knowledge base dictionary."""
    engine = get_engine()
    return engine._kb

def get_recommendations(
    crop: str,
    pest_name: Optional[str] = None,
    risk_level: str = "Medium",
    npk: Optional[Dict[str, float]] = None,
    season: Optional[str] = None,
    weather: Optional[Dict[str, Any]] = None,
    soil: Optional[Dict[str, Any]] = None,
    district: Optional[str] = None,
    pest: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve comprehensive, context-aware agronomic recommendations dynamically calibrated by:
    Crop, Pest, Season, Real-time Weather, Soil Chemistry, and District.
    """
    actual_pest = pest_name or pest or "Stem Borer"
    engine = get_engine()
    raw_advisory = engine.get_advisory(
        crop=crop,
        predicted_pest=actual_pest,
        predicted_risk=risk_level,
        season=season,
        weather=weather,
        soil=soil,
        npk=npk,
        district=district
    )

    # Severity badge and card class for internal recommender compatibility (never shown in new UI)
    if risk_level == "High":
        severity_badge = "🚨 HIGH (Immediate Field Action Recommended)"
        card_class = "stError"
    elif risk_level == "Medium":
        severity_badge = "⚠️ MEDIUM (Field Monitoring Recommended)"
        card_class = "stWarning"
    else:
        severity_badge = "✅ LOW (Preventive Maintenance)"
        card_class = "stSuccess"

    return {
        "crop": raw_advisory["crop"],
        "pest_name": raw_advisory["predicted_pest"],
        "risk_level": raw_advisory["predicted_risk"], # Kept internally only
        "severity_badge": severity_badge,
        "card_class": card_class,

        # 12 Farmer-Friendly Advisory Fields (Steps 6, 7, 8)
        "recommended_treatment": raw_advisory["recommended_treatment"],
        "chemical_control": raw_advisory["chemical_control"],
        "organic_control": raw_advisory["organic_control"],
        "ipm": raw_advisory["ipm"],
        "dosage": raw_advisory["dosage"],
        "spray_timing": raw_advisory["spray_timing"],
        "recommended_fertilizer": raw_advisory["recommended_fertilizer"],
        "preventive_measures": raw_advisory["preventive_measures"],
        "field_monitoring_tips": raw_advisory["field_monitoring_tips"],
        "safety_precautions": raw_advisory["safety_precautions"],
        "harvest_interval": raw_advisory["harvest_interval"],
        "expected_recovery": raw_advisory["expected_recovery"],

        # Backward compatibility for legacy templates
        "pesticide": raw_advisory["chemical_control"],
        "safety_notes": raw_advisory["safety_notes"],
        "prevention": raw_advisory["preventive_measures"]
    }
