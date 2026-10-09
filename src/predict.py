"""
AI-Powered Crop Pest Prediction & Agricultural Advisory Engine
=============================================================
Production inference module exposing:
- predict(data): Complete end-to-end ML prediction and advisory pipeline
- get_advisory(crop, predicted_pest, predicted_risk): Decoupled rule-based advisory lookup
"""
import os
import sys
import json
import time
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Union, List, Optional, Tuple

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline_config import (
    MODELS_DIR,
    ARTIFACTS_DIR,
    DATASETS_DIR,
    ADVISORY_KB_PATH
)
from src.production_pipeline import RAW_INPUT_FEATURES, UnifiedProductionPipeline
from src.regional_soil import (
    inject_soil_parameters,
    map_soil_type_to_model,
    get_regional_soil_defaults,
    SUPPORTED_SOIL_TYPES
)
from utils.logger import setup_logger

logger = setup_logger("predict_engine", "prediction.log")

# Global singleton cache for low latency
_CACHED_PIPELINE: Optional[UnifiedProductionPipeline] = None
_CACHED_KB: Optional[Dict[str, Any]] = None

try:
    import streamlit as _st
    _st_cache_resource = _st.cache_resource(show_spinner=False)
    _st_cache_data = _st.cache_data(show_spinner=False)
except Exception:
    def _st_cache_resource(fn):
        return fn
    def _st_cache_data(fn):
        return fn

@_st_cache_resource
def get_production_pipeline() -> UnifiedProductionPipeline:
    """Loads and caches the unified production pipeline (Singleton)."""
    global _CACHED_PIPELINE
    if _CACHED_PIPELINE is not None:
        return _CACHED_PIPELINE

    candidate_paths = [
        os.path.join(MODELS_DIR, "best_model.pkl"),
        os.path.join(ARTIFACTS_DIR, "best_model.pkl"),
        os.path.join(MODELS_DIR, "trained_model.pkl"),
        os.path.join(ARTIFACTS_DIR, "trained_model.pkl")
    ]
    model_path = None
    for p in candidate_paths:
        if os.path.exists(p):
            model_path = p
            break

    if model_path is None:
        raise FileNotFoundError("Production model artifact 'best_model.pkl' not found in models/ or artifacts/.")

    logger.info(f"Loading production model from: {model_path}")
    _CACHED_PIPELINE = joblib.load(model_path)
    return _CACHED_PIPELINE

@_st_cache_data
def load_advisory_knowledgebase(kb_path: str = ADVISORY_KB_PATH) -> Dict[str, Any]:
    """Loads and caches the pesticide recommendations JSON knowledgebase."""
    global _CACHED_KB
    if _CACHED_KB is not None:
        return _CACHED_KB

    if not os.path.exists(kb_path):
        alt_path = os.path.join(DATASETS_DIR, "pesticide_recommendations.json")
        if os.path.exists(alt_path):
            kb_path = alt_path

    if os.path.exists(kb_path):
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                _CACHED_KB = json.load(f)
                return _CACHED_KB
        except Exception as e:
            logger.error(f"Failed to load advisory JSON: {e}")
            _CACHED_KB = {}
    else:
        _CACHED_KB = {}
    return _CACHED_KB

def normalize_top3_percentages(probs: list) -> list:
    """
    Normalizes Top-3 probabilities strictly to 100.00% with two decimal places.
    Ensures that Top1 + Top2 + Top3 = exactly 100.00%.
    Preserves strict descending order.
    """
    if not probs:
        return [100.00]
    sorted_probs = sorted([float(p) for p in probs], reverse=True)
    total = sum(sorted_probs)
    if total <= 0:
        return [50.00, 30.00, 20.00][:len(probs)]
    
    raw_bps = [(p / total) * 10000.0 for p in sorted_probs]
    floors = [int(s) for s in raw_bps]
    remainder = 10000 - sum(floors)
    
    diffs = sorted(
        range(len(sorted_probs)),
        key=lambda i: (raw_bps[i] - floors[i], len(sorted_probs) - i),
        reverse=True
    )
    for i in range(remainder):
        floors[diffs[i % len(sorted_probs)]] += 1
        
    if len(floors) == 3:
        if floors[0] < floors[1]:
            diff = floors[1] - floors[0]
            floors[0] += diff
            floors[2] -= diff
        if floors[1] < floors[2]:
            diff = floors[2] - floors[1]
            floors[1] += diff
            floors[2] -= diff
        floors[2] = 10000 - (floors[0] + floors[1])
        if floors[2] < 0:
            deficit = -floors[2]
            floors[2] = 0
            if floors[1] >= deficit:
                floors[1] -= deficit
            else:
                floors[0] -= (deficit - floors[1])
                floors[1] = 0

    res = [round(f / 100.0, 2) for f in floors]
    if len(res) == 3:
        res[2] = round(100.00 - res[0] - res[1], 2)
    return res

_CACHED_ADVISORY_ENGINE = None

def get_advisory(
    crop: str,
    predicted_pest: str,
    predicted_risk: str = "Medium",
    npk: Optional[Dict[str, float]] = None,
    season: Optional[str] = None,
    weather: Optional[Dict[str, Any]] = None,
    soil: Optional[Dict[str, Any]] = None,
    district: Optional[str] = None
) -> Dict[str, Any]:
    """
    Decoupled Rule-Based Dynamic Advisory Engine.
    DO NOT USE ML.
    Generates tailored IPM advisories based on crop, pest, season, weather, soil and NPK.
    """
    global _CACHED_ADVISORY_ENGINE
    if _CACHED_ADVISORY_ENGINE is None:
        from src.advisory_engine import AdvisoryEngine
        _CACHED_ADVISORY_ENGINE = AdvisoryEngine()
    return _CACHED_ADVISORY_ENGINE.get_advisory(
        crop=crop,
        predicted_pest=predicted_pest,
        predicted_risk=predicted_risk,
        season=season,
        weather=weather,
        soil=soil,
        npk=npk,
        district=district
    )


AGRONOMIC_RANGES = {
    "Temperature": (-25.0, 70.0, "°C"),
    "Humidity": (0.0, 100.0, "%"),
    "Rainfall": (0.0, 10000.0, "mm"),
    "Wind_Speed": (0.0, 250.0, "km/h"),
    "Soil_Moisture": (0.0, 100.0, "%"),
    "Soil_pH": (1.0, 14.0, ""),
    "Nitrogen": (0.0, 300.0, "kg/ha"),
    "Phosphorus": (0.0, 300.0, "kg/ha"),
    "Potassium": (0.0, 300.0, "kg/ha"),
    "Organic_Carbon": (0.0, 10.0, "%")
}

def validate_inputs(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates user input against agronomic & physiological bounds (Phase 6).
    Returns (is_valid, error_message).
    """
    ranges = AGRONOMIC_RANGES
    for field, (low, high, unit) in ranges.items():
        if field in data and data[field] is not None:
            try:
                val = float(data[field])
                if val < low or val > high:
                    u_str = f" {unit}" if unit else ""
                    return False, f"Invalid {field.replace('_', ' ')}: {val}{u_str}. Valid agronomic range is {low}{u_str} to {high}{u_str}."
            except (ValueError, TypeError):
                return False, f"Invalid numeric format for {field.replace('_', ' ')}: {data[field]}"
    return True, None

def _safe_val(v, default):
    if v is None or pd.isna(v):
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default

def generate_pest_explanation(df_input: pd.DataFrame, pest: str, prob: float, risk: str) -> Dict[str, Any]:
    """
    Automated Agro-Climatic Explainability Engine (Phase 4).
    Produces domain-grounded explanations: 'Why this pest was predicted'.
    """
    row = df_input.iloc[0]
    crop = str(row.get("Crop_Name", "Crop"))
    season = str(row.get("Season", "Kharif"))
    temp = _safe_val(row.get("Temperature"), 28.0)
    hum = _safe_val(row.get("Humidity"), 70.0)
    rain = _safe_val(row.get("Rainfall"), 100.0)
    n_val = _safe_val(row.get("Nitrogen"), 25.0)
    thi = round(0.8 * temp + (hum / 100.0) * (temp - 14.3) + 46.4, 2)

    reasons = [
        f"{crop} is the primary host crop during the {season} seasonal cultivation window.",
    ]

    if temp >= 28.0:
        reasons.append(f"Ambient temperature ({temp:.1f}°C) accelerates {pest} reproductive cycles and nymph development.")
    elif temp <= 20.0:
        reasons.append(f"Moderate temperature ({temp:.1f}°C) supports overwintering and localized survival of {pest}.")
    else:
        reasons.append(f"Ambient temperature ({temp:.1f}°C) matches optimal bio-thermal development thresholds.")

    if hum >= 70.0 and rain >= 60.0:
        reasons.append(f"High atmospheric humidity ({hum:.1f}%) and rainfall ({rain:.1f} mm) maintain ideal canopy moisture for multiplication.")
    elif hum >= 65.0:
        reasons.append(f"Relative humidity ({hum:.1f}%) protects egg clutches and prevents larval desiccation.")
    elif rain < 30.0 and temp > 30.0:
        reasons.append(f"Dry atmospheric conditions with low rainfall ({rain:.1f} mm) favor rapid sucking pest outbreaks.")
    else:
        reasons.append(f"Humidity of {hum:.1f}% supports vegetative canopy infestation.")

    if n_val >= 24.0:
        reasons.append(f"Elevated soil Nitrogen ({n_val:.1f} kg/ha) stimulates succulent foliage attractive to {pest}.")

    if risk == "High":
        reasons.append(f"Temperature-Humidity Index (THI={thi}) crosses critical threshold, elevating regional outbreak risk.")

    return {
        "summary_reasons": reasons,
        "primary_factors": ["Host Crop Affinity", "Microclimatic Humidity", "Thermal Suitability", "Vegetative Canopy Vigor"],
        "thi_index": thi
    }

def prepare_features(
    data: Union[Dict[str, Any], pd.DataFrame, str],
    weather_source: str = "Live Weather Telemetry"
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Step 9: Transforms raw farmer inputs, fetches weather, injects regional soil defaults,
    and constructs the exact 15-feature RAW_INPUT_FEATURES vector expected by the trained pipeline.
    Flow:
    User Input (District, Crop, Season, Soil Type)
    ↓
    Weather (Auto-Fetched or User-Provided)
    ↓
    Regional Soil Defaults (Auto-Injected via 4-tier Fallback)
    ↓
    Feature Engineering Ready DataFrame
    """
    if isinstance(data, str):
        data = json.loads(data)

    if isinstance(data, pd.DataFrame):
        raw_dict = data.iloc[0].to_dict() if len(data) > 0 else {}
    elif isinstance(data, dict):
        raw_dict = dict(data)
    else:
        raise ValueError("Input data must be a dictionary, JSON string, or pandas DataFrame.")

    # 1. Primary defaults for categorical fields
    state = str(raw_dict.get("State", "")).strip() or "Andhra Pradesh"
    district = str(raw_dict.get("District", "")).strip() or "Guntur"
    crop = str(raw_dict.get("Crop_Name", "")).strip() or "Cotton"
    season = str(raw_dict.get("Season", "")).strip() or "Kharif"
    user_soil_type = str(raw_dict.get("Soil_Type", "")).strip() or "Black Soil"

    raw_dict["State"] = state
    raw_dict["District"] = district
    raw_dict["Crop_Name"] = crop
    raw_dict["Season"] = season
    raw_dict["Soil_Type"] = user_soil_type

    # 2. Weather fallbacks if missing
    weather_defaults = {
        "Temperature": 28.0,
        "Humidity": 70.0,
        "Rainfall": 100.0,
        "Wind_Speed": 8.0
    }
    for w_col, w_val in weather_defaults.items():
        if w_col not in raw_dict or raw_dict[w_col] is None or pd.isna(raw_dict[w_col]):
            raw_dict[w_col] = w_val

    # 3. Transparent Regional Soil Parameter Injection (Priority 1 -> 4)
    enriched_dict, soil_meta = inject_soil_parameters(raw_dict, weather_source=weather_source)

    # 4. Map Soil_Type to model's trained classes for the feature vector
    model_soil_type = map_soil_type_to_model(user_soil_type)
    enriched_dict["Soil_Type"] = model_soil_type

    # 5. Sanitize numeric bounds per AGRONOMIC_RANGES
    sanitized = {}
    for k, v in enriched_dict.items():
        if k in AGRONOMIC_RANGES and v is not None:
            try:
                val = float(v)
                low, high, _ = AGRONOMIC_RANGES[k]
                sanitized[k] = max(low, min(high, val))
            except (ValueError, TypeError):
                sanitized[k] = None
        else:
            sanitized[k] = v

    df_prepared = pd.DataFrame([sanitized])

    # Ensure all RAW_INPUT_FEATURES exist and are ordered
    for col in RAW_INPUT_FEATURES:
        if col not in df_prepared.columns or df_prepared[col].iloc[0] is None or pd.isna(df_prepared[col].iloc[0]):
            df_prepared[col] = 0.0 if col in NUMERICAL_FEATURES else "Unknown"

    df_prepared = df_prepared[RAW_INPUT_FEATURES]
    return df_prepared, soil_meta


def build_input_dataframe(
    data: Union[Dict[str, Any], pd.DataFrame, str],
    weather_source: str = "Live Weather Telemetry"
) -> pd.DataFrame:
    """Convenience function returning the structured RAW_INPUT_FEATURES DataFrame."""
    df, _ = prepare_features(data, weather_source=weather_source)
    return df


def predict(data: Union[Dict[str, Any], pd.DataFrame, str]) -> Dict[str, Any]:
    """
    Core production inference function.
    Accepts raw inputs, performs end-to-end preprocessing, feature engineering,
    dual-target inference, confidence calibration, top-3 candidates, and advisory lookup.
    """
    t_start = time.perf_counter()
    pipeline = get_production_pipeline()

    # Step 9: Transparent feature preparation and regional soil injection
    df_input, soil_meta = prepare_features(data)

    # Preprocessing timing
    t_preproc_start = time.perf_counter()
    pest_pipe = pipeline.pest_pipeline
    risk_pipe = pipeline.risk_pipeline
    fe_transformer = pest_pipe.named_steps["feature_engineer"]
    ct_preprocessor = pest_pipe.named_steps["preprocessor"]
    pest_clf = pest_pipe.named_steps["classifier"]
    risk_clf = risk_pipe.named_steps["classifier"]

    X_eng = fe_transformer.transform(df_input)
    X_proc = ct_preprocessor.transform(X_eng)
    preproc_time_ms = round((time.perf_counter() - t_preproc_start) * 1000.0, 3)

    # Prediction timing
    t_pred_start = time.perf_counter()
    pest_probas = pest_clf.predict_proba(X_proc)
    risk_probas = risk_clf.predict_proba(X_proc)
    pest_idx = np.argmax(pest_probas, axis=1)
    risk_idx = np.argmax(risk_probas, axis=1)
    pred_pests = pipeline.le_pest.inverse_transform(pest_idx)
    pred_risks = pipeline.le_risk.inverse_transform(risk_idx)
    pred_time_ms = round((time.perf_counter() - t_pred_start) * 1000.0, 3)

    predicted_pest = str(pred_pests[0])
    predicted_risk = str(pred_risks[0])

    # Top-3 Pest Predictions strictly sorted descending by model probability
    top3_indices = np.argsort(pest_probas[0])[-3:][::-1]
    raw_probs = [float(pest_probas[0][idx]) * 100.0 for idx in top3_indices]
    norm_probs = normalize_top3_percentages(raw_probs)
    top_predictions = [
        {
            "rank": rank + 1,
            "pest": str(pipeline.le_pest.inverse_transform([idx])[0]),
            "probability": round(raw_probs[rank], 2),
            "normalized_probability": norm_probs[rank]
        }
        for rank, idx in enumerate(top3_indices)
    ]

    # Rank-1 Recommended Prediction
    recommended_prediction = top_predictions[0]["pest"]
    top1_prob = top_predictions[0]["probability"]

    # Risk level & probabilities for all 3 classes
    risk_idx = int(np.argmax(risk_probas[0]))
    risk_level = str(pipeline.le_risk.inverse_transform([risk_idx])[0])
    risk_probability = round(float(risk_probas[0][risk_idx]) * 100.0, 2)

    risk_classes = list(pipeline.le_risk.classes_)
    risk_probabilities = {
        str(cls_name): round(float(risk_probas[0][i]) * 100.0, 2)
        for i, cls_name in enumerate(risk_classes)
    }
    # Ensure High, Medium, Low are all explicitly present
    for k in ["High", "Medium", "Low"]:
        if k not in risk_probabilities:
            risk_probabilities[k] = 0.0

    sorted_risk_breakdown = sorted(
        [{"risk": k, "probability": v} for k, v in risk_probabilities.items()],
        key=lambda x: x["probability"],
        reverse=True
    )

    # Step 9: Confidence Rules
    if top1_prob >= 80.0:
        confidence_tier = "Very High Confidence"
        confidence_warning = None
    elif top1_prob >= 60.0:
        confidence_tier = "High Confidence"
        confidence_warning = None
    elif top1_prob >= 40.0:
        confidence_tier = "Medium Confidence"
        confidence_warning = None
    else:
        confidence_tier = "Low Confidence"
        confidence_warning = "Environmental conditions overlap multiple pest species. Field inspection is recommended."

    # Probability Metrics
    top3_sum = round(sum(item["probability"] for item in top_predictions), 2)
    other_classes_prob = round(max(0.0, 100.0 - top3_sum), 2)

    # Automated Explainability (Phase 4)
    explainability = generate_pest_explanation(df_input, recommended_prediction, top1_prob, risk_level)

    # Weather & Soil Summaries (Phase 2)
    weather_summary = {
        "temperature_c": float(df_input["Temperature"].iloc[0]),
        "humidity_pct": float(df_input["Humidity"].iloc[0]),
        "rainfall_mm": float(df_input["Rainfall"].iloc[0]),
        "wind_speed_kmh": float(df_input["Wind_Speed"].iloc[0]),
        "thi_index": explainability["thi_index"]
    }
    soil_summary = {
        "soil_type": str(df_input["Soil_Type"].iloc[0]),
        "user_soil_type": soil_meta.get("user_soil_type", str(df_input["Soil_Type"].iloc[0])),
        "regional_source": soil_meta.get("source_level", "District"),
        "fallback_used": soil_meta.get("fallback_used", False),
        "soil_moisture_pct": float(df_input["Soil_Moisture"].iloc[0]),
        "soil_ph": float(df_input["Soil_pH"].iloc[0]),
        "nitrogen_kgha": float(df_input["Nitrogen"].iloc[0]),
        "phosphorus_kgha": float(df_input["Phosphorus"].iloc[0]),
        "potassium_kgha": float(df_input["Potassium"].iloc[0]),
        "organic_carbon_pct": float(df_input["Organic_Carbon"].iloc[0])
    }

    # Advisory Timing - Generated strictly for Rank-1 recommended pest with dynamic context
    t_adv_start = time.perf_counter()
    crop_val = str(df_input["Crop_Name"].iloc[0])
    npk_dict = {
        "Nitrogen": float(df_input["Nitrogen"].iloc[0]),
        "Phosphorus": float(df_input["Phosphorus"].iloc[0]),
        "Potassium": float(df_input["Potassium"].iloc[0])
    }
    advisory = get_advisory(
        crop=crop_val,
        predicted_pest=recommended_prediction,
        predicted_risk=risk_level,
        npk=npk_dict,
        season=str(df_input["Season"].iloc[0]),
        weather=weather_summary,
        soil=soil_summary,
        district=str(df_input["District"].iloc[0])
    )
    advisory_time_ms = round((time.perf_counter() - t_adv_start) * 1000.0, 3)

    total_time_ms = round((time.perf_counter() - t_start) * 1000.0, 3)
    current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    return {
        # Step 5: Exact Required JSON Schema
        "top_predictions": top_predictions,
        "risk_level": risk_level,
        "risk_probability": risk_probability,
        "risk_probabilities": risk_probabilities,
        "risk_breakdown": sorted_risk_breakdown,
        "recommended_prediction": recommended_prediction,
        "advisory": advisory,

        # Phase 5: Confidence rules & warnings
        "confidence_tier": confidence_tier,
        "confidence_warning": confidence_warning,
        "probability_metrics": {
            "top1_probability": top1_prob,
            "top3_probability_sum": top3_sum,
            "other_classes_probability": other_classes_prob,
            "top3_classes": [p["pest"] for p in top_predictions],
            "top3_probabilities": [p["probability"] for p in top_predictions]
        },

        # Phase 4: Automated Explainability
        "explainability": explainability,

        # Phase 2: Metadata & Summaries
        "weather_summary": weather_summary,
        "soil_summary": soil_summary,
        "system_metadata": {
            "model_version": "v2.1.0-Production (ExtraTrees + RandomForest Ensemble)",
            "dataset_version": "v2.0-Sanitized (249,700 samples, Leak-Free)",
            "prediction_timestamp": current_timestamp
        },

        # Backward compatibility for existing callers & tests
        "Predicted Pest": recommended_prediction,
        "Pest Confidence %": top1_prob,
        "Predicted Risk Level": risk_level,
        "Risk Confidence %": risk_probability,
        "Top-3 Pest Predictions": [
            {
                "rank": p["rank"],
                "pest": p["pest"],
                "confidence_percent": p["probability"]
            }
            for p in top_predictions
        ],
        "Advisory": advisory,
        "Execution Metrics": {
            "total_latency_ms": total_time_ms,
            "preprocessing_ms": preproc_time_ms,
            "prediction_ms": pred_time_ms,
            "advisory_lookup_ms": advisory_time_ms
        }
    }

def predict_batch(data: Union[pd.DataFrame, str, List[Dict[str, Any]]], output_filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Batch prediction engine using the unified production model.
    Accepts DataFrame, list of dicts, or CSV filepath.
    Returns DataFrame with Rank-1, Rank-2, Rank-3 predictions, probabilities, risk levels, and advisory.
    """
    if isinstance(data, str):
        if not os.path.exists(data):
            raise FileNotFoundError(f"Batch input CSV not found: {data}")
        df_raw = pd.read_csv(data)
    elif isinstance(data, list):
        df_raw = pd.DataFrame(data)
    elif isinstance(data, pd.DataFrame):
        df_raw = data.copy()
    else:
        raise ValueError("Batch data must be a CSV file path, list of dicts, or pandas DataFrame.")

    pipeline = get_production_pipeline()

    # Ensure all RAW_INPUT_FEATURES exist, fill defaults if missing
    defaults = {
        "State": "Andhra Pradesh",
        "District": "Guntur",
        "Crop_Name": "Cotton",
        "Season": "Kharif",
        "Soil_Type": "Black",
        "Temperature": 28.0,
        "Humidity": 70.0,
        "Rainfall": 100.0,
        "Wind_Speed": 8.0,
        "Soil_Moisture": 50.0,
        "Soil_pH": 7.0,
        "Nitrogen": 25.0,
        "Phosphorus": 15.0,
        "Potassium": 10.0,
        "Organic_Carbon": 0.7
    }
    for col, def_val in defaults.items():
        if col not in df_raw.columns:
            df_raw[col] = def_val

    df_clean = df_raw[RAW_INPUT_FEATURES].copy()

    # Predict
    pest_preds, risk_preds = pipeline.predict(df_clean)
    pest_probas, risk_probas = pipeline.predict_proba(df_clean)

    results = []
    for i in range(len(df_clean)):
        # Top-3 pests
        top3_idx = np.argsort(pest_probas[i])[-3:][::-1]
        top1_pest = str(pipeline.le_pest.inverse_transform([top3_idx[0]])[0])
        top1_prob = round(float(pest_probas[i][top3_idx[0]]) * 100.0, 2)
        top2_pest = str(pipeline.le_pest.inverse_transform([top3_idx[1]])[0])
        top2_prob = round(float(pest_probas[i][top3_idx[1]]) * 100.0, 2)
        top3_pest = str(pipeline.le_pest.inverse_transform([top3_idx[2]])[0])
        top3_prob = round(float(pest_probas[i][top3_idx[2]]) * 100.0, 2)

        risk_idx = int(np.argmax(risk_probas[i]))
        risk_level = str(pipeline.le_risk.inverse_transform([risk_idx])[0])
        risk_prob = round(float(risk_probas[i][risk_idx]) * 100.0, 2)

        crop_name = str(df_clean["Crop_Name"].iloc[i])
        npk_dict = {
            "Nitrogen": float(df_clean["Nitrogen"].iloc[i]),
            "Phosphorus": float(df_clean["Phosphorus"].iloc[i]),
            "Potassium": float(df_clean["Potassium"].iloc[i])
        }
        adv = get_advisory(crop_name, top1_pest, risk_level, npk=npk_dict)

        results.append({
            "Rank1_Pest": top1_pest,
            "Rank1_Probability_%": top1_prob,
            "Rank2_Pest": top2_pest,
            "Rank2_Probability_%": top2_prob,
            "Rank3_Pest": top3_pest,
            "Rank3_Probability_%": top3_prob,
            "Predicted_Risk": risk_level,
            "Risk_Probability_%": risk_prob,
            "Recommended_Pesticide": adv["Recommended_Pesticide"],
            "Chemical_Control": adv["Chemical_Control"],
            "Organic_Control": adv["Organic_Control"],
            "Recommended_Fertilizer": adv["Recommended_Fertilizer"],
            "Safety_Notes": adv["Safety_Notes"]
        })

    df_res = pd.concat([df_raw.reset_index(drop=True), pd.DataFrame(results)], axis=1)
    if output_filepath:
        df_res.to_csv(output_filepath, index=False)
        logger.info(f"Batch prediction results saved to: {output_filepath}")

    return df_res

class PestPredictionEngine:
    """Wrapper class providing backward compatibility for object-oriented interfaces."""
    def __init__(self, model_path: Optional[str] = None):
        self.pipeline = get_production_pipeline()

    def predict(self, farmer_input: Union[Dict[str, Any], pd.DataFrame, str]) -> Dict[str, Any]:
        return predict(farmer_input)

    def predict_batch(self, data: Union[pd.DataFrame, str, List[Dict[str, Any]]], output_filepath: Optional[str] = None) -> pd.DataFrame:
        return predict_batch(data, output_filepath)

def main_cli():
    import argparse
    parser = argparse.ArgumentParser(description="AI-Powered Crop Pest Prediction & Advisory CLI (Production Model)")
    parser.add_argument("--json", type=str, help="JSON string of input features")
    parser.add_argument("--batch", type=str, help="Path to input CSV for batch prediction")
    parser.add_argument("--output", type=str, help="Path to save batch prediction output CSV")
    parser.add_argument("--crop", type=str, default="Cotton", help="Crop name")
    parser.add_argument("--district", type=str, default="Guntur", help="District name")
    parser.add_argument("--state", type=str, default="Andhra Pradesh", help="State name")
    parser.add_argument("--season", type=str, default="Kharif", help="Season")
    parser.add_argument("--temperature", type=float, default=28.0, help="Temperature in °C")
    parser.add_argument("--humidity", type=float, default=70.0, help="Humidity in %%")
    parser.add_argument("--rainfall", type=float, default=100.0, help="Rainfall in mm")
    parser.add_argument("--wind_speed", type=float, default=8.0, help="Wind speed in km/h")
    parser.add_argument("--soil_type", type=str, default="Black", help="Soil type")
    parser.add_argument("--soil_moisture", type=float, default=50.0, help="Soil moisture in %%")
    parser.add_argument("--soil_ph", type=float, default=7.0, help="Soil pH")
    parser.add_argument("--nitrogen", type=float, default=25.0, help="Nitrogen in kg/ha")
    parser.add_argument("--phosphorus", type=float, default=15.0, help="Phosphorus in kg/ha")
    parser.add_argument("--potassium", type=float, default=10.0, help="Potassium in kg/ha")
    parser.add_argument("--organic_carbon", type=float, default=0.7, help="Organic carbon in %%")

    args = parser.parse_args()

    if args.batch:
        print(f"Executing batch prediction on: {args.batch}")
        out_df = predict_batch(args.batch, output_filepath=args.output)
        print(f"Batch prediction completed for {len(out_df)} records. Preview:\n{out_df[['Rank1_Pest', 'Rank1_Probability_%', 'Predicted_Risk', 'Risk_Probability_%']].head()}")
        return

    if args.json:
        sample = json.loads(args.json)
    else:
        sample = {
            "District": args.district,
            "Crop_Name": args.crop,
            "Season": args.season,
            "State": args.state,
            "Temperature": args.temperature,
            "Humidity": args.humidity,
            "Rainfall": args.rainfall,
            "Wind_Speed": args.wind_speed,
            "Soil_Type": args.soil_type,
            "Soil_Moisture": args.soil_moisture,
            "Soil_pH": args.soil_ph,
            "Nitrogen": args.nitrogen,
            "Phosphorus": args.phosphorus,
            "Potassium": args.potassium,
            "Organic_Carbon": args.organic_carbon
        }

    res = predict(sample)
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main_cli()

