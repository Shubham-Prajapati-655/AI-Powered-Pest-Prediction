import unittest
import os
import sys
import io
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from database import (
    init_db, create_user, verify_user, get_user_by_id, get_user_by_email,
    update_user_full_profile, change_user_password, save_user_avatar, remove_user_avatar,
    save_user_preferences, get_user_preferences,
    log_account_activity, get_user_account_activities, get_user_profile_stats,
    create_session_token, delete_all_user_sessions, delete_user_account,
    get_connection, hash_password_bcrypt, verify_password_bcrypt
)

class TestAccountSettingsSuite(unittest.TestCase):
    def setUp(self):
        init_db()
        # Seed a dedicated test user
        self.test_email = "test_farmer_settings@agriai.org"
        self.test_pw = "FarmerSecret@2026"
        self.test_name = "Rajesh Sharma"
        
        ok, user = verify_user(self.test_email, self.test_pw)
        if not ok:
            create_user(self.test_name, self.test_email, self.test_pw, role="farmer")
            ok, user = verify_user(self.test_email, self.test_pw)
        self.assertTrue(ok)
        self.user = user
        self.user_id = user["id"]

    def test_01_update_full_profile_fields(self):
        """Test updating profile name, phone, state, district, and preferred crop."""
        ok, msg = update_user_full_profile(
            user_id=self.user_id,
            name="Rajesh K. Sharma",
            phone="9876543210",
            state="Maharashtra",
            district="Nagpur",
            preferred_crop="Cotton"
        )
        self.assertTrue(ok)
        self.assertIn("successfully", msg.lower())

        updated = get_user_by_id(self.user_id)
        self.assertEqual(updated["name"], "Rajesh K. Sharma")
        self.assertEqual(updated["phone"], "9876543210")
        self.assertEqual(updated["state"], "Maharashtra")
        self.assertEqual(updated["district"], "Nagpur")
        self.assertEqual(updated["preferred_crop"], "Cotton")

    def test_02_update_profile_validation(self):
        """Test validation on empty name and invalid phone numbers."""
        # Empty name
        ok, err = update_user_full_profile(self.user_id, name="   ")
        self.assertFalse(ok)
        self.assertIn("name is required", err.lower())

        # Invalid phone
        ok2, err2 = update_user_full_profile(self.user_id, name="Valid Name", phone="123")
        self.assertFalse(ok2)
        self.assertIn("valid phone number", err2.lower())

    def test_03_avatar_upload_compression_and_removal(self):
        """Test processing, square center-cropping, 256x256 compression and removal."""
        # Generate dummy 500x300 image in memory
        img = Image.new("RGB", (500, 300), color=(34, 139, 34))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        ok, path = save_user_avatar(self.user_id, img_bytes)
        self.assertTrue(ok)
        self.assertIn("avatars", path)

        full_disk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", path))
        self.assertTrue(os.path.exists(full_disk_path))

        # Check image dimensions on disk
        saved_img = Image.open(full_disk_path)
        self.assertEqual(saved_img.size, (256, 256))

        # Remove avatar
        rem_ok = remove_user_avatar(self.user_id)
        self.assertTrue(rem_ok)
        user_after = get_user_by_id(self.user_id)
        self.assertIsNone(user_after["avatar_path"])

    def test_04_change_password_verification_and_bcrypt(self):
        """Test changing password with bcrypt verification and complexity checks."""
        # Wrong current password
        ok, err = change_user_password(
            user_id=self.user_id,
            current_password="WrongPassword!123",
            new_password="NewFarmerSecret@99"
        )
        self.assertFalse(ok)
        self.assertIn("current password is incorrect", err.lower())

        # Weak new password
        ok_weak, err_weak = change_user_password(
            user_id=self.user_id,
            current_password=self.test_pw,
            new_password="weak"
        )
        self.assertFalse(ok_weak)
        self.assertIn("at least 8 characters", err_weak.lower())

        # Valid password change
        new_secret = "NewKisanPower@2026"
        ok_succ, msg = change_user_password(
            user_id=self.user_id,
            current_password=self.test_pw,
            new_password=new_secret,
            confirm_password=new_secret
        )
        self.assertTrue(ok_succ)

        # Verify old password fails
        old_auth, _ = verify_user(self.test_email, self.test_pw)
        self.assertFalse(old_auth)

        # Verify new password succeeds with bcrypt
        new_auth, authed_user = verify_user(self.test_email, new_secret)
        self.assertTrue(new_auth)
        self.assertTrue(authed_user["password_hash"].startswith("$2b$") or authed_user["password_hash"].startswith("$2a$"))

        # Restore password for consistency
        change_user_password(self.user_id, new_secret, self.test_pw, self.test_pw)

    def test_05_application_settings_and_privacy_persistence(self):
        """Test saving and retrieving granular settings, theme modes, notifications and privacy toggles."""
        ok = save_user_preferences(
            user_id=self.user_id,
            dark_mode=True,
            language="Gujarati (ગુજરાતી)",
            notifications=True,
            theme_mode="dark",
            notify_prediction=True,
            notify_weather=False,
            notify_system=True,
            privacy_history=False,
            privacy_email=True,
            privacy_profile=False
        )
        self.assertTrue(ok)

        prefs = get_user_preferences(self.user_id)
        self.assertTrue(prefs["dark_mode"])
        self.assertEqual(prefs["language"], "Gujarati (ગુજરાતી)")
        self.assertEqual(prefs["theme_mode"], "dark")
        self.assertTrue(prefs["notify_prediction"])
        self.assertFalse(prefs["notify_weather"])
        self.assertTrue(prefs["notify_system"])
        self.assertFalse(prefs["privacy_history"])
        self.assertTrue(prefs["privacy_email"])
        self.assertFalse(prefs["privacy_profile"])

    def test_06_activity_logging_and_retrieval(self):
        """Test recording account activities and chronological retrieval."""
        log_account_activity(self.user_id, "Test Action", "Verified account settings activity feed.", "🧪")
        acts = get_user_account_activities(self.user_id, limit=5)
        self.assertGreater(len(acts), 0)
        types = [a["activity_type"] for a in acts]
        self.assertIn("Test Action", types)

    def test_07_logout_all_devices_session_invalidation(self):
        """Test invalidating all active persistent session tokens."""
        t1 = create_session_token(self.user_id, days_valid=10)
        t2 = create_session_token(self.user_id, days_valid=10)
        self.assertIsNotNone(t1)
        self.assertIsNotNone(t2)

        # Logout from all devices
        ok = delete_all_user_sessions(self.user_id)
        self.assertTrue(ok)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM user_sessions WHERE user_id = ?", (self.user_id,))
        count = cur.fetchone()[0]
        conn.close()
        self.assertEqual(count, 0)

    def test_08_user_profile_stats_aggregation(self):
        """Test aggregating user stats: total predictions, favorite crop, last prediction date."""
        stats = get_user_profile_stats(self.user_id)
        self.assertIn("total_predictions", stats)
        self.assertIn("reports_downloaded", stats)
        self.assertIn("favorite_crop", stats)
        self.assertIn("last_prediction_date", stats)

    def test_09_delete_account_lifecycle(self):
        """Test permanently deleting an account and cleaning related tables."""
        temp_email = "temp_del_user@agriai.org"
        create_user("Temporary Farmer", temp_email, "TempSecret@123", role="farmer")
        _, temp_user = verify_user(temp_email, "TempSecret@123")
        temp_id = temp_user["id"]

        create_session_token(temp_id, 10)
        save_user_preferences(temp_id, dark_mode=False)
        log_account_activity(temp_id, "Signup", "New account registered", "🎉")

        # Delete user account
        deleted = delete_user_account(temp_id)
        self.assertTrue(deleted)

        self.assertIsNone(get_user_by_id(temp_id))
        self.assertIsNone(get_user_by_email(temp_email))

if __name__ == "__main__":
    unittest.main()
