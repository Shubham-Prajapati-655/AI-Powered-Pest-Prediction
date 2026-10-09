import unittest
import os
import sys
import time
import io
import pandas as pd

# Add app directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from database import (
    init_db, create_user, verify_user,
    save_prediction_history, get_user_prediction_history,
    get_all_prediction_history, delete_prediction_history,
    get_user_dashboard_metrics, record_report_download
)
from pdf_generator import generate_prediction_pdf, generate_history_summary_pdf

class TestUserDashboard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_user_dashboard_metrics_calculation(self):
        """Test calculation of dashboard summary metrics for a user."""
        email = f"dash_farmer_{int(time.time()*1000)}@agriai.org"
        ok, user = create_user("Dashboard Farmer", email, "Farmer@Secure123", role="farmer")
        self.assertTrue(ok)
        u_id = user["id"]

        # Initial metrics for brand new user
        m_init = get_user_dashboard_metrics(user_id=u_id, user_email=email, is_admin=False)
        self.assertEqual(m_init["total_predictions"], 0)
        self.assertEqual(m_init["unique_crops"], 0)
        self.assertIsNone(m_init["last_prediction_time"])

        # Add 2 predictions
        rec = {
            "pesticide": "Neem Gold", "dosage": "3 ml/L",
            "organic_control": "Neem formulation", "safety_notes": "Wear gloves",
            "prevention": ["Crop rotation", "Clean bunds"]
        }
        pred_id1 = save_prediction_history(
            u_id, email, "Andhra Pradesh", "Guntur", "Rice", "Cereal",
            "Kharif", "Monsoon", 29.0, 78.0, 110.0, 77.0, 1.4,
            "Stem Borer", 82.0, "High", 88.0, "Single Model", rec
        )
        pred_id2 = save_prediction_history(
            u_id, email, "Maharashtra", "Pune", "Maize", "Cereal",
            "Kharif", "Monsoon", 26.0, 65.0, 45.0, 71.0, 0.7,
            "Fall Armyworm", 75.0, "Medium", 80.0, "Single Model", rec
        )
        self.assertGreater(pred_id1, 0)
        self.assertGreater(pred_id2, 0)

        # Updated metrics
        m_updated = get_user_dashboard_metrics(user_id=u_id, user_email=email, is_admin=False)
        self.assertEqual(m_updated["total_predictions"], 2)
        self.assertEqual(m_updated["unique_crops"], 2)
        self.assertEqual(m_updated["risk_counts"]["High"], 1)
        self.assertEqual(m_updated["risk_counts"]["Medium"], 1)
        self.assertIsNotNone(m_updated["last_prediction_time"])

        # Clean up
        delete_prediction_history(pred_id1, user_id=u_id)
        delete_prediction_history(pred_id2, user_id=u_id)

    def test_02_record_report_download(self):
        """Test marking prediction reports as downloaded."""
        email = f"report_dl_{int(time.time()*1000)}@agriai.org"
        ok, user = create_user("Report User", email, "Report@Secure123", role="farmer")
        self.assertTrue(ok)
        u_id = user["id"]

        pred_id = save_prediction_history(
            u_id, email, "Gujarat", "Rajkot", "Cotton", "Commercial",
            "Kharif", "Monsoon", 31.0, 70.0, 60.0, 78.0, 0.85,
            "Whitefly", 72.0, "Medium", 85.0, "Model Notes",
            {"pesticide": "Azadirachtin", "dosage": "2 ml/L", "organic_control": "Yellow sticky traps", "safety_notes": "Mask", "prevention": []}
        )
        self.assertGreater(pred_id, 0)

        ok_dl = record_report_download(pred_id, user_id=u_id)
        self.assertTrue(ok_dl)

        delete_prediction_history(pred_id, user_id=u_id)

    def test_03_history_summary_pdf_generation(self):
        """Test generating a multi-record summary PDF."""
        records = [
            {"created_at": "2026-09-08 10:00:00", "district": "Guntur", "state": "Andhra Pradesh", "crop": "Rice", "predicted_pest": "Stem Borer", "pest_prob": 84.5, "predicted_risk": "High"},
            {"created_at": "2026-09-08 10:05:00", "district": "Pune", "state": "Maharashtra", "crop": "Maize", "predicted_pest": "Fall Armyworm", "pest_prob": 76.0, "predicted_risk": "Medium"}
        ]
        pdf_bytes = generate_history_summary_pdf(records, user_name="Test Farmer")
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_04_user_isolation_security(self):
        """Test that regular users cannot view or delete another user's prediction history."""
        email_a = f"farmer_a_{int(time.time()*1000)}@agriai.org"
        email_b = f"farmer_b_{int(time.time()*1000)}@agriai.org"
        _, user_a = create_user("User A", email_a, "PassA@Secure123", role="farmer")
        _, user_b = create_user("User B", email_b, "PassB@Secure123", role="farmer")

        rec = {"pesticide": "Neem", "dosage": "3ml", "organic_control": "Neem Oil", "safety_notes": "Gloves", "prevention": []}
        p_id_a = save_prediction_history(
            user_a["id"], email_a, "Gujarat", "Surat", "Sugarcane", "Commercial",
            "Kharif", "Monsoon", 30.0, 75.0, 100.0, 76.0, 1.3,
            "Early Shoot Borer", 80.0, "High", 85.0, "Single Model", rec
        )

        # User B queries their history
        history_b = get_user_prediction_history(user_id=user_b["id"], user_email=email_b)
        self.assertFalse(any(r["id"] == p_id_a for r in history_b))

        # User B attempts to delete User A's prediction
        del_attempt = delete_prediction_history(p_id_a, user_id=user_b["id"])
        self.assertFalse(del_attempt)

        # User A successfully deletes their own prediction
        del_success = delete_prediction_history(p_id_a, user_id=user_a["id"])
        self.assertTrue(del_success)

if __name__ == "__main__":
    unittest.main()
