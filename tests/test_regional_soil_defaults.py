"""
Unit and Integration Test Suite: Regional Soil Defaults & Automatic Parameter Injection
========================================================================================
Validates:
- JSON structure and presence across datasets/ and artifacts/
- 4-tier scientific fallback strategy (District -> State -> Soil Type -> Global Median)
- Model-compatible soil type mapping (10 user-facing types -> 5 trained classes)
- Transparent parameter injection during inference (no manual NPK required)
- Sub-millisecond lookup latency (< 1 ms requirement)
- End-to-end model compatibility without retraining
"""
import os
import sys
import json
import time
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.regional_soil import (
    load_regional_soil_kb,
    get_regional_soil_defaults,
    map_soil_type_to_model,
    inject_soil_parameters,
    SUPPORTED_SOIL_TYPES,
    GLOBAL_SOIL_MEDIANS
)
from src.predict import predict, prepare_features, build_input_dataframe
from src.production_pipeline import RAW_INPUT_FEATURES


class TestRegionalSoilDefaults:

    def test_01_knowledge_base_json_exists_and_valid(self):
        """Verifies JSON existence, schema, and required chemical metrics."""
        paths = [
            os.path.join(ROOT_DIR, "datasets", "regional_soil_defaults.json"),
            os.path.join(ROOT_DIR, "artifacts", "regional_soil_defaults.json")
        ]
        for p in paths:
            assert os.path.exists(p), f"Missing configuration file: {p}"
            with open(p, "r", encoding="utf-8") as f:
                kb = json.load(f)
            assert isinstance(kb, dict)
            assert len(kb) >= 10, "Should contain at least 10 states"
            assert "Andhra Pradesh" in kb
            assert "Guntur" in kb["Andhra Pradesh"]
            assert "Black Soil" in kb["Andhra Pradesh"]["Guntur"]

            guntur_black = kb["Andhra Pradesh"]["Guntur"]["Black Soil"]
            required_keys = ["Nitrogen", "Phosphorus", "Potassium", "Soil_pH", "Organic_Carbon", "Soil_Moisture"]
            for k in required_keys:
                assert k in guntur_black, f"Missing key {k} in Guntur Black Soil"
                assert isinstance(guntur_black[k], (int, float))

    def test_02_priority_1_district_level_lookup(self):
        """Priority 1: District + Soil Type returns district-specific values without fallback."""
        params, source, fallback_used = get_regional_soil_defaults("Andhra Pradesh", "Guntur", "Black Soil")
        assert source == "District"
        assert not fallback_used
        assert params["Nitrogen"] == 34.0
        assert params["Phosphorus"] == 21.0
        assert params["Potassium"] == 24.0
        assert params["Soil_pH"] == 6.9
        assert params["Organic_Carbon"] == 0.82
        assert params["Soil_Moisture"] == 61.0

    def test_03_priority_2_state_level_fallback(self):
        """Priority 2: If district is unavailable, returns State + Soil Type average."""
        params, source, fallback_used = get_regional_soil_defaults("Andhra Pradesh", "NonExistentDistrictXYZ", "Black Soil")
        assert source == "State Average"
        assert fallback_used
        assert "Nitrogen" in params
        assert params["Nitrogen"] > 0

    def test_04_priority_3_soil_type_level_fallback(self):
        """Priority 3: If state is unavailable, returns nationwide Soil Type average."""
        params, source, fallback_used = get_regional_soil_defaults("AtlantisState", "UnknownDistrict", "Peaty Soil")
        assert source == "Soil Type Average"
        assert fallback_used
        assert params["Soil_pH"] < 7.0 # Peaty soil is acidic

    def test_05_priority_4_global_median_fallback(self):
        """Priority 4: If soil type is unknown, returns dataset global median values."""
        params, source, fallback_used = get_regional_soil_defaults("UnknownState", "UnknownDistrict", "CosmicDustSoil")
        assert source == "Global Median"
        assert fallback_used
        for k in GLOBAL_SOIL_MEDIANS:
            assert params[k] == GLOBAL_SOIL_MEDIANS[k]

    def test_06_supported_soil_types_and_model_mapping(self):
        """Verifies all 10 user-facing soil types map to trained model classes."""
        assert len(SUPPORTED_SOIL_TYPES) == 10
        valid_classes = {"Black", "Clayey", "Loamy", "Red", "Sandy"}

        for stype in SUPPORTED_SOIL_TYPES:
            mapped = map_soil_type_to_model(stype)
            assert mapped in valid_classes, f"Soil type {stype} mapped to invalid class {mapped}"

    def test_07_end_to_end_predict_transparent_injection(self):
        """Verifies prediction succeeds with ONLY farmer inputs (District, Crop, Season, Soil Type)."""
        farmer_input = {
            "District": "Guntur",
            "State": "Andhra Pradesh",
            "Crop_Name": "Cotton",
            "Season": "Kharif",
            "Soil_Type": "Black Soil",
            "Temperature": 31.0,
            "Humidity": 72.0,
            "Rainfall": 110.0,
            "Wind_Speed": 9.5
        }
        res = predict(farmer_input)
        assert isinstance(res, dict)
        assert "recommended_prediction" in res
        assert "top_predictions" in res
        assert len(res["top_predictions"]) == 3
        assert "soil_summary" in res

        # Soil parameters should be automatically injected without exception
        soil_summary = res["soil_summary"]
        assert soil_summary["regional_source"] == "District"
        assert not soil_summary["fallback_used"]
        assert soil_summary["nitrogen_kgha"] == 34.0
        assert soil_summary["phosphorus_kgha"] == 21.0
        assert soil_summary["potassium_kgha"] == 24.0

    def test_08_sub_millisecond_caching_performance(self):
        """Verifies lookup time is well below 1 millisecond target."""
        # Warmup
        get_regional_soil_defaults("Gujarat", "Rajkot", "Black Soil")

        iterations = 500
        t0 = time.perf_counter()
        for _ in range(iterations):
            get_regional_soil_defaults("Maharashtra", "Pune", "Loamy Soil")
        avg_latency_ms = ((time.perf_counter() - t0) / iterations) * 1000.0

        assert avg_latency_ms < 1.0, f"Lookup too slow: {avg_latency_ms:.4f} ms (must be < 1.0 ms)"

    def test_09_model_feature_compatibility_unaltered(self):
        """Verifies constructed DataFrame has exact RAW_INPUT_FEATURES in correct order."""
        farmer_input = {
            "District": "Rajkot",
            "State": "Gujarat",
            "Crop_Name": "Groundnut",
            "Season": "Kharif",
            "Soil_Type": "Black Soil"
        }
        df_input = build_input_dataframe(farmer_input)
        assert list(df_input.columns) == RAW_INPUT_FEATURES
        assert df_input["Soil_Type"].iloc[0] == "Black" # Mapped for model
        assert df_input["Nitrogen"].iloc[0] > 0
        assert df_input["Phosphorus"].iloc[0] > 0
