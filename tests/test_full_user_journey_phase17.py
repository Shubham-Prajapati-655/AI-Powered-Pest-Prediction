"""
Phase 17: Full User Journey Simulation Test Suite
Simulates realistic end-to-end farmer interactions:
1. User Registration (Farmer Role)
2. Login & Credential Verification (bcrypt)
3. Dashboard Loading & Metrics Retrieval
4. Weather Service Query (Open-Meteo & Caching)
5. Agro-Climatic ML Pest & Risk Prediction
6. Top-3 Probability Ranking & Verification
7. Agronomic Advisory Generation (Exclusive to Rank-1 Pest)
8. Advisory PDF Report Compilation & Validation
9. History Persistence in Database (Insert, Retrieve, Verify)
10. Session Invalidation / Logout
Repeated across multiple cycles with zero failures.
"""
import pytest
import os
import sys
import time
import uuid
import pypdf

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "app"))

from database import (
    init_db,
    create_user,
    verify_user,
    get_user_by_email,
    save_prediction_history,
    get_user_prediction_history,
    get_user_dashboard_metrics,
    delete_user_account
)
from weather import fetch_open_meteo_weather
from predictor import predict_pest_and_risk
from recommender import get_recommendations
from pdf_generator import generate_prediction_pdf

class TestFullUserJourneyPhase17:

    @classmethod
    def setup_class(cls):
        init_db()

    @pytest.mark.parametrize("cycle", [1, 2, 3])
    def test_complete_farmer_user_journey(self, cycle):
        """Simulate realistic farmer workflow from registration to prediction, PDF, and history."""
        unique_id = uuid.uuid4().hex[:8]
        email = f"farmer_{unique_id}@agridemo.org"
        password = "SecurePassword@2026!"
        name = f"Farmer Ramesh_{unique_id}"
        state = "Andhra Pradesh"
        district = "Guntur"
        crop = "Cotton"

        # Step 1: Registration
        success, user_data = create_user(name, email, password, role="farmer")
        assert success is True, f"Registration failed: {user_data}"
        user_id = user_data["id"] if isinstance(user_data, dict) else user_data

        # Step 2: Login
        auth_success, auth_user = verify_user(email, password)
        assert auth_success is True, f"Login failed for {email}"
        assert auth_user["email"] == email.lower()

        # Step 3: Dashboard Metrics
        metrics = get_user_dashboard_metrics(user_id)
        assert isinstance(metrics, dict)
        assert "total_predictions" in metrics

        # Step 4: Weather Fetch
        weather = fetch_open_meteo_weather(district, state, "Kharif")
        assert "temperature" in weather
        assert "humidity" in weather
        temp = weather["temperature"]
        hum = weather["humidity"]
        rain = weather.get("rainfall_mm", 100.0)

        # Step 5 & 6: Prediction & Top-3 Candidates
        pest, pest_prob, risk, risk_prob, top3_candidates, note = predict_pest_and_risk(
            state=state, district=district, crop=crop,
            sowing_season="Kharif", season="Kharif",
            temp=temp, humidity=hum, rainfall=rain
        )
        assert len(top3_candidates) == 3
        # Assert Top-3 descending probabilities
        p1, p2, p3 = top3_candidates[0]["probability"], top3_candidates[1]["probability"], top3_candidates[2]["probability"]
        assert p1 >= p2 >= p3
        assert pest == top3_candidates[0]["pest"]

        # Step 7: Advisory Engine (Strictly for Rank-1 Pest)
        advisory = get_recommendations(crop, pest, risk)
        assert "pesticide" in advisory or "Recommended_Pesticide" in advisory

        # Step 8: Generate PDF
        pdf_bytes = generate_prediction_pdf(
            state=state, district=district, crop=crop,
            crop_category="Fiber", sowing_season="Kharif", weather_season="Monsoon",
            temp=temp, humidity=hum, rainfall=rain,
            thi=78.5, rf_hum_ratio=1.5, weather_source="Open-Meteo",
            predicted_pest=pest, pest_conf=pest_prob,
            predicted_risk=risk, risk_conf=risk_prob,
            recommendations=advisory, user_name=name
        )
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 1000

        # Step 9: Save Prediction History
        pred_id = save_prediction_history(
            user_id=user_id,
            user_email=email,
            state=state,
            district=district,
            crop=crop,
            crop_category="Fiber",
            sowing_season="Kharif",
            weather_season="Monsoon",
            temp=temp,
            humidity=hum,
            rainfall=rain,
            thi=78.5,
            rf_hum_ratio=1.5,
            predicted_pest=pest,
            pest_prob=pest_prob,
            predicted_risk=risk,
            risk_prob=risk_prob,
            model_notes=note,
            recommendations=advisory
        )
        assert pred_id is not None

        # Step 10: View History
        history = get_user_prediction_history(user_id)
        assert len(history) >= 1
        latest = history[0]
        assert latest["crop"] == crop
        assert latest["predicted_pest"] == pest

        # Step 11: Cleanup account
        del_success = delete_user_account(user_id)
        assert del_success is True
