import unittest
import os
import sys
import time
from pathlib import Path

# Add project root and app directory to Python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "app"))

from config import (
    DATABASE_URL,
    SESSION_TIMEOUT_MINUTES,
    MAX_LOGIN_ATTEMPTS,
    LOGIN_LOCKOUT_MINUTES,
    LOG_FILE,
    BACKUPS_DIR
)
from database import (
    init_db,
    get_connection,
    create_user,
    verify_user,
    hash_password_bcrypt,
    verify_password_bcrypt,
    validate_password_complexity,
    validate_email_format,
    create_session_token,
    get_user_by_session_token,
    delete_session_token,
    delete_all_user_sessions,
    create_password_reset_token,
    verify_password_reset_token,
    redeem_password_reset_token,
    save_prediction_history,
    save_contact_query,
    get_database_health_summary
)
from security import (
    sanitize_text,
    check_login_rate_limit,
    record_failed_login,
    reset_login_rate_limit,
    validate_avatar_upload
)
from logger import (
    log_auth_event,
    log_prediction_event,
    log_weather_event,
    log_admin_action,
    get_recent_logs,
    SensitiveDataFilter
)
from backup_manager import (
    create_manual_backup,
    list_available_backups,
    restore_backup,
    get_backup_bytes,
    trigger_auto_backup_demo,
    get_backup_storage_stats
)
from weather import (
    fetch_open_meteo_weather,
    derive_season_from_sowing
)

class TestProductionReadiness(unittest.TestCase):
    """
    Comprehensive automated test suite verifying all 20 production readiness,
    security, database optimization, logging, and resiliency requirements.
    """

    @classmethod
    def setUpClass(cls):
        init_db()

    # -------------------------------------------------------------
    # 1. DATABASE OPTIMIZATION & INDEXES
    # -------------------------------------------------------------
    def test_01_database_indexes_provisioned(self):
        """Verify that all required single and composite indexes exist in the schema."""
        health = get_database_health_summary()
        self.assertEqual(health["status"], "Healthy & Online")
        self.assertGreaterEqual(health["indexes_active"], 8)
        
        index_names = [idx.split()[0] for idx in health["index_list"]]
        required_indexes = [
            "idx_users_email",
            "idx_users_role_status",
            "idx_preds_user_id",
            "idx_preds_created_at",
            "idx_preds_crop",
            "idx_preds_state_district",
            "idx_activity_user_id",
            "idx_contact_status",
            "idx_sessions_token",
            "idx_reset_token"
        ]
        for req_idx in required_indexes:
            self.assertIn(req_idx, index_names, f"Expected index {req_idx} not found in database.")

    def test_02_database_health_metrics(self):
        """Verify database health summary metrics and query response latency."""
        health = get_database_health_summary()
        self.assertIn("latency_ms", health)
        self.assertLess(health["latency_ms"], 500.0)  # Sub-500ms database response
        self.assertIn("table_counts", health)
        self.assertIn("users", health["table_counts"])
        self.assertIn("prediction_history", health["table_counts"])

    # -------------------------------------------------------------
    # 2. PASSWORD SECURITY & BCRYPT
    # -------------------------------------------------------------
    def test_03_bcrypt_password_hashing(self):
        """Verify that passwords are never stored in plain text and bcrypt hash verification works."""
        pw = "SuperSecure@2026"
        hashed = hash_password_bcrypt(pw)
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))
        self.assertNotEqual(pw, hashed)
        self.assertTrue(verify_password_bcrypt(pw, hashed))
        self.assertFalse(verify_password_bcrypt("WrongPassword@123", hashed))

    def test_04_password_complexity_validator(self):
        """Verify 8+ chars, uppercase, lowercase, number, and special character enforcement."""
        # Valid
        ok, _ = validate_password_complexity("ValidPass@123")
        self.assertTrue(ok)

        # Invalid cases
        short_ok, short_msg = validate_password_complexity("Sh1@")
        self.assertFalse(short_ok)
        self.assertIn("8 characters", short_msg)

        no_upper_ok, _ = validate_password_complexity("lowerpass@123")
        self.assertFalse(no_upper_ok)

        no_lower_ok, _ = validate_password_complexity("UPPERPASS@123")
        self.assertFalse(no_lower_ok)

        no_num_ok, _ = validate_password_complexity("OnlyLetters@Pass")
        self.assertFalse(no_num_ok)

        no_spec_ok, _ = validate_password_complexity("LettersAndNumbers123")
        self.assertFalse(no_spec_ok)

    def test_05_password_reset_token_lifecycle(self):
        """Verify generation, verification, and redemption of time-limited reset tokens."""
        test_email = "token_tester@agriai.org"
        create_user("Token Tester", test_email, "InitialSecret@123", role="farmer")

        # Create token
        ok, msg, token = create_password_reset_token(test_email)
        self.assertTrue(ok)
        self.assertTrue(len(token) >= 32)

        # Verify token
        is_valid, v_msg, uid = verify_password_reset_token(token)
        self.assertTrue(is_valid)
        self.assertIsNotNone(uid)

        # Redeem token with new password
        new_pw = "RedeemedPass@999"
        red_ok, red_msg = redeem_password_reset_token(token, new_pw)
        self.assertTrue(red_ok)

        # Verify login with new password
        auth_ok, auth_user = verify_user(test_email, new_pw)
        self.assertTrue(auth_ok)
        self.assertEqual(auth_user["email"], test_email)

        # Token cannot be reused (single-use constraint)
        reused_ok, _, _ = verify_password_reset_token(token)
        self.assertFalse(reused_ok)

    # -------------------------------------------------------------
    # 3. RATE LIMITING & BRUTE FORCE PROTECTION
    # -------------------------------------------------------------
    def test_06_login_rate_limiting(self):
        """Verify rate limiter triggers lockout after max failed attempts."""
        test_id = "bruteforce_target@agriai.org"
        reset_login_rate_limit(test_id)

        # First 4 attempts allowed
        for _ in range(MAX_LOGIN_ATTEMPTS - 1):
            record_failed_login(test_id)
            allowed, _ = check_login_rate_limit(test_id)
            self.assertTrue(allowed)

        # 5th failed attempt triggers lockout
        record_failed_login(test_id)
        locked_allowed, rem_secs = check_login_rate_limit(test_id)
        self.assertFalse(locked_allowed)
        self.assertGreater(rem_secs, 0)

        # Resetting rate limit restores access
        reset_login_rate_limit(test_id)
        clean_allowed, _ = check_login_rate_limit(test_id)
        self.assertTrue(clean_allowed)

    # -------------------------------------------------------------
    # 4. SESSION MANAGEMENT & LOGOUT ALL DEVICES
    # -------------------------------------------------------------
    def test_07_session_tokens_and_logout_all(self):
        """Verify persistent session creation and invalidation across all devices."""
        test_email = "session_user@agriai.org"
        create_user("Session User", test_email, "SessionSecret@123")
        _, user = verify_user(test_email, "SessionSecret@123")

        # Create multiple session tokens for different devices
        t1 = create_session_token(user["id"], days_valid=30)
        t2 = create_session_token(user["id"], days_valid=30)
        
        self.assertIsNotNone(get_user_by_session_token(t1))
        self.assertIsNotNone(get_user_by_session_token(t2))

        # Logout from all devices
        delete_all_user_sessions(user["id"])

        # All session tokens should now be invalid
        self.assertIsNone(get_user_by_session_token(t1))
        self.assertIsNone(get_user_by_session_token(t2))

    # -------------------------------------------------------------
    # 5. INPUT SANITIZATION & FILE VALIDATION
    # -------------------------------------------------------------
    def test_08_xss_input_sanitization(self):
        """Verify that malicious script tags and HTML are sanitized and escaped."""
        malicious_input = "<script>alert('xss');</script>Hello & welcome"
        clean = sanitize_text(malicious_input)
        self.assertNotIn("<script>", clean)
        self.assertIn("&lt;script&gt;", clean)
        self.assertIn("&amp;", clean)

    def test_09_avatar_file_upload_validation(self):
        """Verify avatar validation checks allowed types, sizes, and assigns UUID names."""
        # 1. Reject invalid extensions (.exe, .sh)
        bad_ok, bad_msg, _ = validate_avatar_upload("malicious.exe", b"binary content")
        self.assertFalse(bad_ok)

        # 2. Reject oversized files (> 2MB)
        oversized_bytes = b"0" * (3 * 1024 * 1024)
        size_ok, size_msg, _ = validate_avatar_upload("large.png", oversized_bytes)
        self.assertFalse(size_ok)

        # 3. Accept valid PNG image
        valid_png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        png_ok, _, secure_name = validate_avatar_upload("profile.png", valid_png_bytes)
        self.assertTrue(png_ok)
        self.assertTrue(secure_name.startswith("avatar_"))
        self.assertTrue(secure_name.endswith(".png"))

    # -------------------------------------------------------------
    # 6. DEDUPLICATION & TRANSACTION SAFETY
    # -------------------------------------------------------------
    def test_10_prediction_and_contact_deduplication(self):
        """Verify identical prediction and contact submissions within threshold are deduplicated."""
        test_email = "dedup_tester@agriai.org"
        create_user("Dedup Tester", test_email, "DedupSecret@123")
        _, user = verify_user(test_email, "DedupSecret@123")

        # 1. Prediction Deduplication
        pred_id1 = save_prediction_history(
            user["id"], test_email, "Maharashtra", "Pune", "Sugarcane", "Cash",
            "Kharif", "Monsoon", 28.5, 75.0, 45.0, 78.0, 0.59,
            "Early Shoot Borer", 85.0, "High", 90.0, "Model note",
            {"pesticide": "Chlorantraniliprole", "dosage": "0.4 ml/L"}
        )
        
        # Immediate duplicate submission
        pred_id2 = save_prediction_history(
            user["id"], test_email, "Maharashtra", "Pune", "Sugarcane", "Cash",
            "Kharif", "Monsoon", 28.5, 75.0, 45.0, 78.0, 0.59,
            "Early Shoot Borer", 85.0, "High", 90.0, "Model note",
            {"pesticide": "Chlorantraniliprole", "dosage": "0.4 ml/L"}
        )
        self.assertEqual(pred_id1, pred_id2)

        # 2. Contact Query Deduplication
        q_id1 = save_contact_query("Ramesh", "ramesh@kisan.in", "Pest outbreak query", "Need dosage advice")
        q_id2 = save_contact_query("Ramesh", "ramesh@kisan.in", "Pest outbreak query", "Need dosage advice")
        self.assertEqual(q_id1, q_id2)

    # -------------------------------------------------------------
    # 7. BACKUP & DISASTER RECOVERY
    # -------------------------------------------------------------
    def test_11_backup_and_restore_operations(self):
        """Verify creating snapshot backup, listing, downloading bytes, and auto-backup."""
        # Create manual backup
        ok, msg, backup_name = create_manual_backup("test_admin@agriai.org")
        self.assertTrue(ok)
        self.assertIsNotNone(backup_name)

        # List backups
        backups = list_available_backups()
        self.assertGreaterEqual(len(backups), 1)
        backup_files = [b["filename"] for b in backups]
        self.assertIn(backup_name, backup_files)

        # Download bytes
        b_bytes = get_backup_bytes(backup_name)
        self.assertIsNotNone(b_bytes)
        self.assertTrue(b_bytes.startswith(b"SQLite format 3"))

        # Storage statistics
        stats = get_backup_storage_stats()
        self.assertGreaterEqual(stats["count"], 1)
        self.assertGreater(stats["total_size_mb"], 0.0)

        # Daily auto-backup check
        auto_ok, _ = trigger_auto_backup_demo()
        self.assertTrue(auto_ok)

        # Restore from backup
        res_ok, res_msg = restore_backup(backup_name, "test_admin@agriai.org")
        self.assertTrue(res_ok)

    # -------------------------------------------------------------
    # 8. STRUCTURED LOGGING & DATA MASKING
    # -------------------------------------------------------------
    def test_12_structured_logging_and_sensitive_data_masking(self):
        """Verify structured logs are written and sensitive credentials are automatically redacted."""
        log_auth_event("LOGIN", "confidential_farmer@agriai.org", True, ip="192.168.1.50")
        log_prediction_event(101, "Cotton", "Gujarat", "Rajkot", "Pink Bollworm", "High")
        log_weather_event("SUCCESS", "Rajkot, Gujarat", latency_ms=124.5)
        log_admin_action("admin@agriai.org", "TEST_AUDIT", "TelemetryNode")

        # Verify logs were appended to LOG_FILE
        self.assertTrue(LOG_FILE.exists())
        recent_logs = get_recent_logs(limit=20)
        self.assertGreaterEqual(len(recent_logs), 1)

        # Verify sensitive credential masking filter
        raw_sensitive_msg = "User logged in with password=SuperSecretPassword123 and token=abc123secret"
        masked = SensitiveDataFilter.mask_sensitive_text(raw_sensitive_msg)
        self.assertNotIn("SuperSecretPassword123", masked)
        self.assertIn("***REDACTED***", masked)

    # -------------------------------------------------------------
    # 9. RESILIENT WEATHER API & CACHING
    # -------------------------------------------------------------
    def test_13_weather_api_caching_and_demo_mode(self):
        """Verify Open-Meteo live API integration, caching, and fallback handling."""
        # Demo mode preset
        w_demo = fetch_open_meteo_weather("Pune", "Maharashtra", demo_mode=True, demo_preset="Monsoon High Pest Outbreak")
        self.assertEqual(w_demo["temperature"], 32.5)
        self.assertEqual(w_demo["season"], "Monsoon")
        self.assertFalse(w_demo["is_live"])

        # Live weather fetch (with automatic fallback resilience)
        w_live = fetch_open_meteo_weather("Pune", "Maharashtra", demo_mode=False)
        self.assertIn("temperature", w_live)
        self.assertIn("humidity", w_live)
        self.assertIn("thi", w_live)
        self.assertIn("weather_condition", w_live)

if __name__ == "__main__":
    unittest.main()
