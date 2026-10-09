"""
Phase 13 Comprehensive REST API Test Suite
Tests:
- GET /health
- POST /predict
- POST /advisory
- POST invalid JSON
- POST missing values
- POST unknown crop
- POST large payload
- HTTP codes and Response schema validation
- Latency benchmarks (API < 700 ms target)
- Concurrent requests and thread safety
"""
import pytest
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.api import app

class TestRestAPIPhase13:

    @classmethod
    def setup_class(cls):
        assert app is not None, "FastAPI app failed to initialize"
        from src.predict import get_production_pipeline, load_advisory_knowledgebase
        get_production_pipeline()
        load_advisory_knowledgebase()
        cls._cm = TestClient(app)
        cls.client = cls._cm.__enter__()
        # Pre-warm predict endpoint so subsequent timed assertions measure steady-state latency
        cls.client.post("/predict", json={
            "District": "Guntur", "Crop_Name": "Cotton", "Season": "Kharif",
            "State": "Andhra Pradesh", "Temperature": 32.0, "Humidity": 75.0,
            "Rainfall": 120.0, "Wind_Speed": 10.0, "Soil_Type": "Black"
        })

    @classmethod
    def teardown_class(cls):
        if hasattr(cls, "_cm"):
            cls._cm.__exit__(None, None, None)

    def test_01_get_health(self):
        """Verify GET /health returns 200 and healthy status."""
        resp = self.client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is True
        assert "2.1.0" in data["version"]

    def test_02_post_predict_normal(self):
        """Verify POST /predict with standard farmer input returns 200 and full schema."""
        payload = {
            "District": "Guntur",
            "Crop_Name": "Cotton",
            "Season": "Kharif",
            "State": "Andhra Pradesh",
            "Temperature": 32.0,
            "Humidity": 75.0,
            "Rainfall": 120.0,
            "Wind_Speed": 10.0,
            "Soil_Type": "Black"
        }
        t0 = time.perf_counter()
        resp = self.client.post("/predict", json=payload)
        latency_ms = (time.perf_counter() - t0) * 1000
        assert resp.status_code == 200
        data = resp.json()
        assert "recommended_prediction" in data
        assert "top_predictions" in data
        assert len(data["top_predictions"]) == 3
        assert "advisory" in data
        assert "risk_level" in data
        assert latency_ms < 700.0, f"API latency {latency_ms:.2f} ms exceeded 700 ms target"

    def test_03_post_advisory(self):
        """Verify POST /advisory returns decoupled agronomic recommendations."""
        payload = {
            "Crop_Name": "Cotton",
            "Predicted_Pest": "Pink Bollworm",
            "Predicted_Risk": "High",
            "Nitrogen": 25.0
        }
        resp = self.client.post("/advisory", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "Recommended_Pesticide" in data
        assert "Chemical_Control" in data
        assert "Organic_Control" in data

    def test_04_post_invalid_json(self):
        """Verify POST /predict with invalid JSON payload returns 422 Unprocessable Entity."""
        resp = self.client.post(
            "/predict",
            content="INVALID_JSON_CONTENT{{{",
            headers={"Content-Type": "application/json"}
        )
        assert resp.status_code in [400, 422]

    def test_05_post_missing_values(self):
        """Verify POST /predict with missing / empty fields utilizes defaults cleanly."""
        resp = self.client.post("/predict", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "recommended_prediction" in data
        assert len(data["top_predictions"]) == 3

    def test_06_post_unknown_crop(self):
        """Verify POST /predict with unknown agricultural crop returns 200 without crashing."""
        payload = {
            "District": "Guntur",
            "Crop_Name": "ExtraterrestrialSoy",
            "Season": "Kharif",
            "Temperature": 28.0,
            "Humidity": 70.0
        }
        resp = self.client.post("/predict", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "recommended_prediction" in data

    def test_07_post_large_payload(self):
        """Verify POST /predict handles large payloads with extra unrecognized fields gracefully."""
        payload = {
            "District": "Pune",
            "Crop_Name": "Soybean",
            "Season": "Kharif",
            "Temperature": 29.5,
            "Humidity": 68.0,
            "Rainfall": 80.0,
            "extra_field_1": "x" * 10000,
            "extra_field_2": [i for i in range(1000)]
        }
        resp = self.client.post("/predict", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "recommended_prediction" in data

    def test_08_concurrency_and_thread_safety(self):
        """Verify concurrent parallel requests execute safely without state corruption."""
        payload = {
            "District": "Guntur",
            "Crop_Name": "Cotton",
            "Season": "Kharif",
            "Temperature": 32.0,
            "Humidity": 75.0
        }
        def send_request():
            r = self.client.post("/predict", json=payload)
            return r.status_code, r.json()["recommended_prediction"]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_request) for _ in range(15)]
            results = [f.result() for f in futures]

        for status_code, pest in results:
            assert status_code == 200
            assert len(pest) > 0

    def test_09_get_weather(self):
        """Verify GET /weather returns valid meteorological telemetry."""
        resp = self.client.get("/weather?district=Guntur&state=Andhra+Pradesh&demo_mode=true")
        assert resp.status_code == 200
        data = resp.json()
        assert "temperature" in data
        assert "humidity" in data
        assert "rainfall_mm" in data

    def test_10_post_weather(self):
        """Verify POST /weather returns valid telemetry for requested location."""
        resp = self.client.post("/weather", json={"district": "Pune", "state": "Maharashtra", "demo_mode": True})
        assert resp.status_code == 200
        data = resp.json()
        assert "temperature" in data
        assert "humidity" in data

    def test_11_post_history(self):
        """Verify POST /history returns historical predictions list."""
        resp = self.client.post("/history", json={"user_id": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "history" in data

    def test_12_post_report(self):
        """Verify POST /report generates valid downloadable PDF payload."""
        payload = {
            "crop": "Cotton",
            "state": "Andhra Pradesh",
            "district": "Guntur",
            "temperature": 30.0,
            "humidity": 70.0,
            "rainfall": 50.0,
            "predicted_pest": "Whitefly",
            "pest_conf": 80.0,
            "predicted_risk": "Medium",
            "risk_conf": 75.0,
            "user_name": "Test Farmer"
        }
        resp = self.client.post("/report", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["pdf_size_bytes"] > 500
        assert "pdf_base64" in data
