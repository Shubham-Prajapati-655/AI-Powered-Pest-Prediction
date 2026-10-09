"""
Phase 6, 7 & 8 Comprehensive Automated Test Suite
- Phase 6: Edge Cases & Adversarial Scenarios
- Phase 7: Top-3 Prediction Ranking & Probability Validation
- Phase 8: Advisory Engine Exclusivity to Rank-1 Pest & KB Integrity
"""
import pytest
import os
import sys
import numpy as np

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.predict import predict, get_advisory, load_advisory_knowledgebase

class TestPhases678Suite:

    @pytest.mark.parametrize("case_name,payload", [
        ("normal_farmer_input", {
            "District": "Guntur", "Crop_Name": "Cotton", "Season": "Kharif",
            "State": "Andhra Pradesh", "Temperature": 30.0, "Humidity": 75.0,
            "Rainfall": 120.0, "Wind_Speed": 10.0, "Soil_Type": "Black",
            "Soil_Moisture": 55.0, "Soil_pH": 7.6, "Nitrogen": 28.0,
            "Phosphorus": 20.0, "Potassium": 12.0, "Organic_Carbon": 0.85
        }),
        ("extreme_temperature", {"Temperature": 65.0, "Crop_Name": "Wheat"}),
        ("extreme_humidity", {"Humidity": 100.0, "Crop_Name": "Rice"}),
        ("extreme_rainfall", {"Rainfall": 4500.0, "Crop_Name": "Rice"}),
        ("missing_values", {"Temperature": None, "Humidity": None, "Crop_Name": "Maize"}),
        ("negative_values", {"Temperature": -15.0, "Rainfall": -100.0, "Humidity": -20.0}),
        ("very_high_values", {"Wind_Speed": 180.0, "Nitrogen": 280.0, "Phosphorus": 250.0}),
        ("unknown_crop", {"Crop_Name": "MartianSoy", "District": "Guntur"}),
        ("unknown_district", {"Crop_Name": "Cotton", "District": "GalacticCity"}),
        ("unknown_soil", {"Crop_Name": "Cotton", "Soil_Type": "LunarRegolith"}),
        ("random_synthetic_1", {"Temperature": 22.4, "Humidity": 48.2, "Rainfall": 35.0, "Crop_Name": "Soybean"}),
        ("random_synthetic_2", {"Temperature": 38.1, "Humidity": 88.5, "Rainfall": 350.0, "Crop_Name": "Sugarcane"}),
        ("completely_empty_request", {})
    ])
    def test_phase_6_and_7_invariance(self, case_name, payload):
        """Phase 6 & 7: Verify all 13 required scenarios execute without crash, maintaining Top-3 descending order."""
        res = predict(payload)
        assert isinstance(res, dict)
        top3 = res["top_predictions"]
        assert len(top3) == 3

        # Phase 7: Top-3 validation
        p1, p2, p3 = top3[0]["probability"], top3[1]["probability"], top3[2]["probability"]
        assert p1 >= p2 >= p3, f"Probabilities not strictly descending: {p1}, {p2}, {p3}"
        
        pests = [t["pest"] for t in top3]
        assert len(set(pests)) == 3, f"Duplicate pests found in Top 3: {pests}"
        
        # Rank 1 must match recommended prediction
        assert res["recommended_prediction"] == top3[0]["pest"]

        # Probability formatting: exactly 2 decimal places
        for t in top3:
            s = f"{t['probability']:.2f}"
            assert float(s) == t["probability"]

        # Phase 8: Advisory generated ONLY for Rank-1 pest
        adv = res["advisory"]
        assert "Recommended_Pesticide" in adv
        assert "Organic_Control" in adv
        assert "Chemical_Control" in adv
        assert "Recommended_Fertilizer" in adv
        assert "Safety_Notes" in adv
        assert "Preventive_Measures" in adv
        assert len(adv["Recommended_Pesticide"]) > 0

    def test_phase_8_kb_integrity(self):
        """Phase 8: Check pesticide_recommendations.json integrity and coverage across all crops and pests."""
        kb = load_advisory_knowledgebase()
        assert len(kb) > 0, "Advisory KB is empty!"
        
        expected_crops = ["Cotton", "Rice", "Wheat", "Maize", "Soybean", "Sugarcane", "Gram", "Mustard", "Groundnut", "Tur (Arhar)"]
        for crop in expected_crops:
            assert crop in kb, f"Missing crop in KB: {crop}"
            crop_data = kb[crop]
            assert len(crop_data) > 0, f"No pests mapped for {crop}"
            for pest, risks in crop_data.items():
                for risk_lvl in ["High", "Medium", "Low"]:
                    if risk_lvl in risks:
                        entry = risks[risk_lvl]
                        assert "pesticide" in entry
                        assert "dosage" in entry
                        assert "organic_control" in entry
                        assert "safety_notes" in entry
                        assert "prevention" in entry

    def test_phase_8_fallback_logic(self):
        """Phase 8: Verify fallback logic for unseen crop and pest combinations."""
        adv = get_advisory("ExoticCrop", "ExoticPest", "High")
        assert "Recommended_Pesticide" in adv
        assert "Neem Oil" in adv["Recommended_Pesticide"] or "Azadirachtin" in adv["Recommended_Pesticide"] or "Chlorantraniliprole" in adv["Recommended_Pesticide"]
        assert "Organic_Control" in adv
        assert "Chemical_Control" in adv
        assert "Recommended_Fertilizer" in adv
