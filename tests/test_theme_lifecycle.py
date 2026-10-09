import unittest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from database import init_db, create_user, verify_user, save_user_preferences, get_user_preferences
import auth

class TestThemePreferenceLifecycle(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_theme_flow(self):
        # 1. Verify user authentication
        ok, user = verify_user("vikas@agriai.org", "KisanSecret@123")
        if not ok:
            # Create user if needed
            create_user("Vikas Patel", "vikas@agriai.org", "KisanSecret@123", role="farmer")
            ok, user = verify_user("vikas@agriai.org", "KisanSecret@123")
        self.assertTrue(ok)
        uid = user["id"]

        # 2. Set Dark Mode and Save Preferences
        save_user_preferences(uid, dark_mode=True, language="English", notifications=True)
        prefs = get_user_preferences(uid)
        self.assertTrue(prefs["dark_mode"])

        # 3. Simulate Login and verify Dark Mode is loaded
        import streamlit as st
        # Simulate auth.login_user
        saved_prefs = get_user_preferences(uid)
        self.assertTrue(saved_prefs["dark_mode"])
        
        # 4. Set Light Mode and Save Preferences
        save_user_preferences(uid, dark_mode=False, language="English", notifications=True)
        prefs_light = get_user_preferences(uid)
        self.assertFalse(prefs_light["dark_mode"])

if __name__ == "__main__":
    unittest.main()
