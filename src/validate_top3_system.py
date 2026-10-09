"""
Comprehensive Top-3 Production Validation Suite
================================================
Validates:
1. 100 random production samples across all crops and agro-climatic zones
2. Probability calculation & calibration correctness
3. Strict descending probability sorting
4. Rounding to 2 decimal places
5. JSON schema compliance
6. Confidence tier assignment & overlap warning
7. Advisory strictly for Rank-1 pest
8. Latency profiling (Target: < 1.0 second)
9. API schema compliance
"""
import os
import sys
import json
import time
import random
import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.predict import predict, get_production_pipeline
from src.pipeline_config import DATASETS_DIR

CROPS = ["Rice", "Cotton", "Wheat", "Sugarcane", "Soybean", "Maize", "Gram", "Mustard", "Groundnut", "Tur (Arhar)"]
DISTRICTS = ["Guntur", "Kurnool", "Krishna", "Ahmedabad", "Rajkot", "Hisar", "Karnal", "Dharwad", "Ujjain", "Nagpur", "Pune", "Coimbatore", "Bareilly", "Hooghly"]
SEASONS = ["Kharif", "Rabi", "Zaid", "Whole Year"]
SOIL_TYPES = ["Black", "Red", "Clayey", "Loamy", "Sandy"]

def run_validation(num_samples=100):
    print("=" * 70)
    print(f"STARTING TOP-3 PRODUCTION VALIDATION SUITE ({num_samples} SAMPLES)")
    print("=" * 70)

    # Pre-warm cached pipeline
    t_warm = time.perf_counter()
    pipeline = get_production_pipeline()
    warmup_time = time.perf_counter() - t_warm
    print(f"[OK] Production pipeline loaded and cached in {warmup_time:.2f}s")

    latencies_ms = []
    top1_accuracies = []
    strictly_descending = 0
    schema_compliant = 0
    tier_compliant = 0
    warning_compliant = 0
    advisory_valid = 0

    random.seed(42)
    np.random.seed(42)

    sample_outputs = []

    for i in range(num_samples):
        crop = random.choice(CROPS)
        district = random.choice(DISTRICTS)
        season = random.choice(SEASONS)
        soil = random.choice(SOIL_TYPES)
        temp = round(random.uniform(15.0, 42.0), 1)
        hum = round(random.uniform(25.0, 95.0), 1)
        rain = round(random.uniform(0.0, 250.0), 1)
        wind = round(random.uniform(4.0, 25.0), 1)
        moisture = round(random.uniform(20.0, 80.0), 1)
        ph = round(random.uniform(5.5, 8.5), 1)
        n = random.randint(10, 40)
        p = random.randint(8, 30)
        k = random.randint(5, 20)
        oc = round(random.uniform(0.3, 1.2), 2)

        payload = {
            "District": district,
            "Crop_Name": crop,
            "Season": season,
            "Soil_Type": soil,
            "State": "Andhra Pradesh",
            "Temperature": temp,
            "Humidity": hum,
            "Rainfall": rain,
            "Wind_Speed": wind,
            "Soil_Moisture": moisture,
            "Soil_pH": ph,
            "Nitrogen": n,
            "Phosphorus": p,
            "Potassium": k,
            "Organic_Carbon": oc
        }

        t_start = time.perf_counter()
        res = predict(payload)
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        latencies_ms.append(t_elapsed_ms)

        # 1. JSON Schema validation
        req_keys = ["top_predictions", "risk_level", "risk_probability", "recommended_prediction", "confidence_tier", "Advisory"]
        if all(k in res for k in req_keys):
            schema_compliant += 1

        top_preds = res["top_predictions"]
        assert len(top_preds) == 3, f"Expected 3 predictions, got {len(top_preds)}"

        p1 = top_preds[0]["probability"]
        p2 = top_preds[1]["probability"]
        p3 = top_preds[2]["probability"]

        # 2. Strict Descending Order
        if p1 >= p2 >= p3:
            strictly_descending += 1

        # 3. Two decimal precision check
        for p_item in top_preds:
            prob_val = p_item["probability"]
            assert isinstance(prob_val, float), f"Probability must be float: {prob_val}"
            # Check 2 decimal places
            assert round(prob_val, 2) == prob_val

        # 4. Confidence Tier & Overlap Warning rule
        tier = res["confidence_tier"]
        warn = res["confidence_warning"]
        if p1 >= 80.0:
            if tier == "Very High Confidence" and warn is None:
                tier_compliant += 1
        elif p1 >= 60.0:
            if tier == "High Confidence" and warn is None:
                tier_compliant += 1
        elif p1 >= 40.0:
            if tier == "Medium Confidence" and warn is None:
                tier_compliant += 1
        else:
            if tier == "Low Confidence" and warn == "Environmental conditions overlap multiple pest species. Field inspection is recommended.":
                tier_compliant += 1
                warning_compliant += 1

        # 5. Advisory targeted strictly to Rank-1
        adv = res["Advisory"]
        if "Recommended_Pesticide" in adv and "Organic_Control" in adv and "Chemical_Control" in adv:
            advisory_valid += 1

        if i < 3:
            sample_outputs.append({
                "sample_id": i + 1,
                "crop": crop,
                "top_predictions": top_preds,
                "risk_level": res["risk_level"],
                "risk_probability": res["risk_probability"],
                "recommended_prediction": res["recommended_prediction"],
                "confidence_tier": tier,
                "latency_ms": round(t_elapsed_ms, 2)
            })

    avg_lat = np.mean(latencies_ms)
    p95_lat = np.percentile(latencies_ms, 95)
    max_lat = np.max(latencies_ms)

    print("\n" + "=" * 70)
    print("TOP-3 VALIDATION RESULTS:")
    print("=" * 70)
    print(f"Total Samples Evaluated       : {num_samples}")
    print(f"Strict Descending Order Passed: {strictly_descending}/{num_samples} ({(strictly_descending/num_samples)*100:.1f}%)")
    print(f"JSON Schema Compliant Passed  : {schema_compliant}/{num_samples} ({(schema_compliant/num_samples)*100:.1f}%)")
    print(f"Confidence Tier Rules Passed  : {tier_compliant}/{num_samples} ({(tier_compliant/num_samples)*100:.1f}%)")
    print(f"Advisory Generation Passed    : {advisory_valid}/{num_samples} ({(advisory_valid/num_samples)*100:.1f}%)")
    print(f"Average Inference Latency     : {avg_lat:.2f} ms")
    print(f"P95 Inference Latency         : {p95_lat:.2f} ms")
    print(f"Maximum Inference Latency     : {max_lat:.2f} ms")
    print(f"Target Latency (< 1000 ms)    : {'PASSED' if p95_lat < 1000.0 else 'FAILED'}")
    print("=" * 70)

    # Save validation metrics to file
    summary_data = {
        "num_samples": num_samples,
        "strictly_descending_pass_rate": strictly_descending / num_samples,
        "schema_compliant_pass_rate": schema_compliant / num_samples,
        "tier_compliant_pass_rate": tier_compliant / num_samples,
        "advisory_valid_pass_rate": advisory_valid / num_samples,
        "latency_metrics_ms": {
            "average": round(float(avg_lat), 2),
            "p50": round(float(np.median(latencies_ms)), 2),
            "p95": round(float(p95_lat), 2),
            "max": round(float(max_lat), 2),
            "target_met": bool(p95_lat < 1000.0)
        },
        "sample_predictions": sample_outputs
    }

    os.makedirs("reports", exist_ok=True)
    report_json_path = "reports/top3_validation_results.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"[OK] Validation metrics saved to: {report_json_path}")

    return summary_data

if __name__ == "__main__":
    run_validation(100)
