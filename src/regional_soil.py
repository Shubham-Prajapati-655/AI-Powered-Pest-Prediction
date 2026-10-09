"""
AI-Powered Regional Soil Knowledge Base & Parameter Injection Engine
====================================================================
Implements:
1. Singleton cached loading of regional soil defaults JSON.
2. 4-tier prioritized fallback lookup strategy:
   - Priority 1: District + Soil Type
   - Priority 2: State + Soil Type average
   - Priority 3: Soil Type nationwide average
   - Priority 4: Global dataset median
3. Model-compatible soil type taxonomy mapping (One-Hot / Ordinal encoder alignment).
4. Silent parameter injection transparent to end users (< 1 ms latency).
5. Internal logging for auditable agronomic traceability.
"""
import os
import sys
import json
import logging
from typing import Dict, Any, Tuple, List, Optional

logger = logging.getLogger("agriai.regional_soil")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JSON_PATHS = [
    os.path.join(BASE_DIR, "datasets", "regional_soil_defaults.json"),
    os.path.join(BASE_DIR, "artifacts", "regional_soil_defaults.json")
]

# Supported user-facing soil types per specification
SUPPORTED_SOIL_TYPES: List[str] = [
    "Black Soil",
    "Red Soil",
    "Loamy Soil",
    "Clayey Soil",
    "Sandy Soil",
    "Alluvial Soil",
    "Laterite Soil",
    "Silty Soil",
    "Peaty Soil",
    "Chalky Soil"
]

# Alignment with the trained ML model's OrdinalEncoder categories:
# ['Black', 'Clayey', 'Loamy', 'Red', 'Sandy']
SOIL_TYPE_TO_MODEL_MAP: Dict[str, str] = {
    "Black Soil": "Black",
    "Black": "Black",
    "Red Soil": "Red",
    "Red": "Red",
    "Loamy Soil": "Loamy",
    "Loamy": "Loamy",
    "Clayey Soil": "Clayey",
    "Clayey": "Clayey",
    "Sandy Soil": "Sandy",
    "Sandy": "Sandy",
    "Alluvial Soil": "Loamy",
    "Alluvial": "Loamy",
    "Laterite Soil": "Red",
    "Laterite": "Red",
    "Silty Soil": "Loamy",
    "Silty": "Loamy",
    "Peaty Soil": "Clayey",
    "Peaty": "Clayey",
    "Chalky Soil": "Sandy",
    "Chalky": "Sandy"
}

# Global dataset median values (Priority 4 Fallback)
GLOBAL_SOIL_MEDIANS: Dict[str, float] = {
    "Nitrogen": 18.0,
    "Phosphorus": 18.0,
    "Potassium": 4.0,
    "Soil_Moisture": 48.0,
    "Soil_pH": 7.1,
    "Organic_Carbon": 0.64
}

# Global singleton cache
_CACHED_SOIL_KB: Optional[Dict[str, Any]] = None
_CACHED_STATE_AVGS: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None
_CACHED_TYPE_AVGS: Optional[Dict[str, Dict[str, float]]] = None


def load_regional_soil_kb() -> Dict[str, Any]:
    """Loads and caches the regional soil defaults JSON (singleton pattern)."""
    global _CACHED_SOIL_KB
    if _CACHED_SOIL_KB is not None:
        return _CACHED_SOIL_KB

    for path in JSON_PATHS:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _CACHED_SOIL_KB = json.load(f)
                    logger.info(f"Loaded regional soil knowledge base from {path} ({len(_CACHED_SOIL_KB)} states)")
                    _precalculate_averages(_CACHED_SOIL_KB)
                    return _CACHED_SOIL_KB
            except Exception as e:
                logger.error(f"Error loading regional soil JSON from {path}: {e}")

    logger.warning("Regional soil defaults JSON not found on disk. Falling back to built-in templates.")
    _CACHED_SOIL_KB = {}
    return _CACHED_SOIL_KB


def _precalculate_averages(kb: Dict[str, Any]) -> None:
    """Pre-calculates state-level and soil-type-level averages for sub-millisecond fallback lookups."""
    global _CACHED_STATE_AVGS, _CACHED_TYPE_AVGS
    _CACHED_STATE_AVGS = {}
    _CACHED_TYPE_AVGS = {}

    type_aggregates: Dict[str, Dict[str, List[float]]] = {}

    for state, districts in kb.items():
        _CACHED_STATE_AVGS[state] = {}
        state_type_agg: Dict[str, Dict[str, List[float]]] = {}

        for dist, soils in districts.items():
            for soil_name, params in soils.items():
                clean_name = soil_name.strip()
                if clean_name not in state_type_agg:
                    state_type_agg[clean_name] = {k: [] for k in GLOBAL_SOIL_MEDIANS.keys()}
                if clean_name not in type_aggregates:
                    type_aggregates[clean_name] = {k: [] for k in GLOBAL_SOIL_MEDIANS.keys()}

                for k in GLOBAL_SOIL_MEDIANS.keys():
                    if k in params:
                        state_type_agg[clean_name][k].append(float(params[k]))
                        type_aggregates[clean_name][k].append(float(params[k]))

        for stype, vals_dict in state_type_agg.items():
            _CACHED_STATE_AVGS[state][stype] = {
                k: round(sum(v) / len(v), 2) if len(v) > 0 else GLOBAL_SOIL_MEDIANS[k]
                for k, v in vals_dict.items()
            }

    for stype, vals_dict in type_aggregates.items():
        _CACHED_TYPE_AVGS[stype] = {
            k: round(sum(v) / len(v), 2) if len(v) > 0 else GLOBAL_SOIL_MEDIANS[k]
            for k, v in vals_dict.items()
        }


def map_soil_type_to_model(soil_type: str) -> str:
    """
    Maps any user-facing soil type to the 5 baseline classes expected by the trained ML pipeline:
    Black, Clayey, Loamy, Red, Sandy.
    """
    if not soil_type:
        return "Loamy"
    clean = str(soil_type).strip()
    return SOIL_TYPE_TO_MODEL_MAP.get(clean, SOIL_TYPE_TO_MODEL_MAP.get(f"{clean} Soil", "Loamy"))


def get_regional_soil_defaults(
    state: Optional[str],
    district: Optional[str],
    soil_type: Optional[str]
) -> Tuple[Dict[str, float], str, bool]:
    """
    Executes the 4-tier scientific fallback strategy:
    Priority 1: District + Soil Type -> District values
    Priority 2: State + Soil Type -> State average
    Priority 3: Soil Type -> Nationwide Soil Type average
    Priority 4: Global -> Dataset medians

    Returns:
        (parameters_dict, source_level, fallback_used)
    """
    kb = load_regional_soil_kb()
    s_clean = (state or "").strip()
    d_clean = (district or "").strip()
    t_clean = (soil_type or "").strip()

    # Normalize soil keys to check both full name ('Black Soil') and short name ('Black')
    candidate_types = [t_clean]
    if t_clean.endswith(" Soil"):
        candidate_types.append(t_clean[:-5].strip())
    else:
        candidate_types.append(f"{t_clean} Soil")

    # Priority 1: District + Soil Type
    if s_clean in kb and d_clean in kb[s_clean]:
        dist_soils = kb[s_clean][d_clean]
        for c_type in candidate_types:
            if c_type in dist_soils:
                res = {k: float(dist_soils[c_type].get(k, GLOBAL_SOIL_MEDIANS[k])) for k in GLOBAL_SOIL_MEDIANS.keys()}
                return res, "District", False

    # Priority 2: State + Soil Type average
    if _CACHED_STATE_AVGS and s_clean in _CACHED_STATE_AVGS:
        state_soils = _CACHED_STATE_AVGS[s_clean]
        for c_type in candidate_types:
            if c_type in state_soils:
                return dict(state_soils[c_type]), "State Average", True

    # Priority 3: Nationwide Soil Type average
    if _CACHED_TYPE_AVGS:
        for c_type in candidate_types:
            if c_type in _CACHED_TYPE_AVGS:
                return dict(_CACHED_TYPE_AVGS[c_type]), "Soil Type Average", True

    # Priority 4: Global dataset medians
    return dict(GLOBAL_SOIL_MEDIANS), "Global Median", True


def inject_soil_parameters(
    raw_data: Dict[str, Any],
    weather_source: str = "Live Weather Telemetry"
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Seamlessly injects regional soil chemistry parameters into the input dictionary.
    Ensures model receives exact required features while keeping UI farmer-friendly.
    """
    enriched = dict(raw_data)
    state = enriched.get("State", "")
    district = enriched.get("District", "")
    raw_soil_type = enriched.get("Soil_Type", "")

    # Retrieve parameters using 4-tier fallback
    params, source_level, fallback_used = get_regional_soil_defaults(state, district, raw_soil_type)

    # Populate Nitrogen, Phosphorus, Potassium, Soil_Moisture, Soil_pH, Organic_Carbon
    for k, v in params.items():
        # Inject if missing or None
        if k not in enriched or enriched[k] is None:
            enriched[k] = v

    # Internal logging per Step 13
    logger.info(
        f"SOIL_INJECTION | District={district} | State={state} | Soil_Type={raw_soil_type} | "
        f"Weather_Source={weather_source} | Regional_Soil_Source={source_level} | "
        f"Fallback_Used={'Yes' if fallback_used else 'No'}"
    )

    metadata = {
        "state": state,
        "district": district,
        "user_soil_type": raw_soil_type,
        "model_soil_type": map_soil_type_to_model(raw_soil_type),
        "soil_parameters": params,
        "source_level": source_level,
        "fallback_used": fallback_used,
        "weather_source": weather_source
    }

    return enriched, metadata
