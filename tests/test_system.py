import unittest
import os
import sys
import json

# Add app directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from weather import fetch_open_meteo_weather, derive_season_from_sowing, get_coordinates, DEMO_PRESETS
from predictor import predict_pest_and_risk, load_ml_artifacts
from recommender import get_recommendations, load_recommendations_json
from database import (
    init_db, create_user, verify_user, reset_password,
    save_prediction_history, get_user_prediction_history,
    delete_prediction_history, get_prediction_stats,
    save_contact_query, get_contact_queries, update_contact_query_status,
    log_prediction, fetch_prediction_logs
)
from pdf_generator import generate_prediction_pdf

class TestProductionSaaSSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_weather_api_live_and_fallback(self):
        """1. Test Weather API success & Demo Mode fallback."""
        w = fetch_open_meteo_weather("Guntur", "Andhra Pradesh", "Kharif", demo_mode=False)
        self.assertIn("temperature", w)
        self.assertIn("humidity", w)
        self.assertIn("rainfall_mm", w)
        self.assertIn("thi", w)
        self.assertGreater(w["temperature"], 0)

        w_demo = fetch_open_meteo_weather("Guntur", "Andhra Pradesh", "Kharif", demo_mode=True, demo_preset="Monsoon High Pest Outbreak")
        self.assertEqual(w_demo["temperature"], 32.5)
        self.assertEqual(w_demo["humidity"], 82.0)
        self.assertEqual(w_demo["rainfall_mm"], 165.0)
        self.assertFalse(w_demo["is_live"])

    def test_02_multioutput_model_inference(self):
        """2. Test MultiOutput ML Model inference & Top-3 prediction probabilities."""
        artifacts = load_ml_artifacts()
        self.assertIn("model", artifacts)
        self.assertIn("pipeline", artifacts)
        self.assertIn("pest_encoder", artifacts)
        self.assertIn("risk_encoder", artifacts)

        pest, pest_prob, risk, risk_prob, top3_candidates, note = predict_pest_and_risk(
            state="Andhra Pradesh", district="Guntur", crop="Maize", crop_category="Cereal",
            sowing_season="Kharif", season="Monsoon", temp=32.5, humidity=82.0,
            rainfall=165.0, thi=85.0, rf_hum_ratio=2.0
        )

        self.assertIsInstance(pest, str)
        self.assertGreater(pest_prob, 0.0)
        self.assertIn(risk, ["High", "Medium", "Low"])
        self.assertGreater(risk_prob, 0.0)
        self.assertEqual(len(top3_candidates), 3)

    def test_03_recommendation_engine(self):
        """3. Test Recommendation engine knowledgebase JSON parsing."""
        kb = load_recommendations_json()
        self.assertIn("Maize", kb)
        self.assertIn("Fall Armyworm", kb["Maize"])

        rec = get_recommendations("Maize", "Fall Armyworm", "High")
        self.assertIn("pesticide", rec)
        self.assertIn("dosage", rec)
        self.assertIn("organic_control", rec)
        self.assertIn("safety_notes", rec)
        self.assertGreater(len(rec["prevention"]), 0)

    def test_04_pdf_report_prediction_probability(self):
        """4. Test ReportLab PDF report generation & check for valid byte stream."""
        rec = get_recommendations("Maize", "Fall Armyworm", "High")
        pdf_bytes = generate_prediction_pdf(
            state="Andhra Pradesh", district="Guntur", crop="Maize", crop_category="Cereal",
            sowing_season="Kharif", weather_season="Monsoon", temp=32.5, humidity=82.0,
            rainfall=165.0, thi=85.0, rf_hum_ratio=2.0, weather_source="Live Open-Meteo Weather API",
            predicted_pest="Fall Armyworm", pest_conf=85.5, predicted_risk="High", risk_conf=92.0,
            model_notes="Single MultiOutput RandomForest Model", recommendations=rec
        )
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_05_user_authentication_flow(self):
        """5. Test Registration, Password Hashing, Login, and Password Reset."""
        import time
        test_email = f"testfarmer_{int(time.time()*1000)}@agriai.org"
        
        # Register
        ok, res = create_user("Test Farmer", test_email, "FarmSecret@123", role="farmer")
        self.assertTrue(ok)
            
        # Verify valid login
        ok, user = verify_user(test_email, "FarmSecret@123")
        self.assertTrue(ok)
        self.assertEqual(user["email"], test_email)
        
        # Verify invalid password
        bad_ok, _ = verify_user(test_email, "WrongPassword!")
        self.assertFalse(bad_ok)
        
        # Reset Password
        reset_ok, _ = reset_password(test_email, "NewSecret@456")
        self.assertTrue(reset_ok)
        
        # Verify with new password
        ok2, user2 = verify_user(test_email, "NewSecret@456")
        self.assertTrue(ok2)

    def test_06_prediction_history_crud(self):
        """6. Test Saving, Filtering, and Deleting Prediction History."""
        rec = get_recommendations("Cotton", "Whitefly", "High")
        pred_id = save_prediction_history(
            user_id=1,
            user_email="testfarmer@agriai.org",
            state="Gujarat",
            district="Rajkot",
            crop="Cotton",
            crop_category="Commercial",
            sowing_season="Kharif",
            weather_season="Monsoon",
            temp=30.0,
            humidity=75.0,
            rainfall=90.0,
            thi=79.0,
            rf_hum_ratio=1.2,
            predicted_pest="Whitefly",
            pest_prob=42.5,
            predicted_risk="High",
            risk_prob=95.0,
            model_notes="MultiOutput Inference",
            recommendations=rec
        )
        self.assertIsInstance(pred_id, int)
        self.assertGreater(pred_id, 0)
        
        history = get_user_prediction_history(user_id=1, crop_filter="Cotton")
        self.assertGreater(len(history), 0)
        self.assertEqual(history[0]["crop"], "Cotton")
        
        deleted = delete_prediction_history(pred_id, user_id=1)
        self.assertTrue(deleted)

    def test_07_contact_queries_workflow(self):
        """7. Test Contact queries storage and status workflow."""
        qid = save_contact_query(
            name="Kisan Kumar",
            email="kisan@example.com",
            subject="Pest Advisory in Paddy",
            message="Noticed brown leaves in paddy field."
        )
        self.assertIsInstance(qid, int)
        
        queries = get_contact_queries(status_filter="Pending")
        self.assertTrue(any(q["id"] == qid for q in queries))
        
        updated = update_contact_query_status(qid, "Resolved")
        self.assertTrue(updated)
        
        resolved_queries = get_contact_queries(status_filter="Resolved")
        self.assertTrue(any(q["id"] == qid for q in resolved_queries))

    def test_08_admin_statistics(self):
        """8. Test Platform analytics calculation."""
        stats = get_prediction_stats()
        self.assertIn("total_predictions", stats)
        self.assertIn("total_users", stats)
        self.assertIn("pending_queries", stats)
        self.assertIn("risk_counts", stats)

    def test_09_user_preferences_theme_persistence(self):
        """9. Test User preferences theme storage, update, and retrieval."""
        from database import save_user_preferences, get_user_preferences
        
        # Test saving Dark Mode
        save_ok = save_user_preferences(user_id=1, dark_mode=True, language="Hindi (हिन्दी)", notifications=True)
        self.assertTrue(save_ok)
        
        prefs = get_user_preferences(user_id=1)
        self.assertTrue(prefs["dark_mode"])
        self.assertEqual(prefs["language"], "Hindi (हिन्दी)")
        
        # Test switching back to Light Mode
        save_ok2 = save_user_preferences(user_id=1, dark_mode=False, language="English", notifications=False)
        self.assertTrue(save_ok2)
        
        prefs2 = get_user_preferences(user_id=1)
        self.assertFalse(prefs2["dark_mode"])
        self.assertEqual(prefs2["language"], "English")
        self.assertFalse(prefs2["notifications_enabled"])

if __name__ == "__main__":
    unittest.main()
