import unittest
import os
import sys
import time

# Ensure app directory is on path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from database import (
    init_db, create_user, verify_user, reset_password,
    get_user_by_email, validate_email_format, validate_password_complexity,
    hash_password_bcrypt, verify_password_bcrypt,
    create_session_token, get_user_by_session_token, delete_session_token
)

class TestAuthGateway(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_bcrypt_hashing_and_verification(self):
        """Test that passwords are hashed using standard bcrypt and verify correctly."""
        raw_pw = "Kisan@Agri2026"
        hashed = hash_password_bcrypt(raw_pw)
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))
        self.assertTrue(verify_password_bcrypt(raw_pw, hashed))
        self.assertFalse(verify_password_bcrypt("WrongPassword@1", hashed))

    def test_02_password_complexity_validator(self):
        """Test strict password complexity rules: min 8, uppercase, lowercase, number, special char."""
        # Valid passwords
        ok, _ = validate_password_complexity("Valid@123")
        self.assertTrue(ok)
        ok, _ = validate_password_complexity("Strong#Pass99")
        self.assertTrue(ok)

        # Less than 8 chars
        ok, msg = validate_password_complexity("Ab1!")
        self.assertFalse(ok)
        self.assertIn("at least 8 characters", msg)

        # Missing uppercase
        ok, msg = validate_password_complexity("kisan@12345")
        self.assertFalse(ok)
        self.assertIn("uppercase", msg)

        # Missing lowercase
        ok, msg = validate_password_complexity("KISAN@12345")
        self.assertFalse(ok)
        self.assertIn("lowercase", msg)

        # Missing number
        ok, msg = validate_password_complexity("KisanSpecial@")
        self.assertFalse(ok)
        self.assertIn("number", msg)

        # Missing special char
        ok, msg = validate_password_complexity("KisanPass123")
        self.assertFalse(ok)
        self.assertIn("special character", msg)

    def test_03_email_format_validator(self):
        """Test email address regex validation."""
        valid_emails = ["farmer@agriai.org", "test.user+farm@example.co.in", "admin@sub.domain.com"]
        for e in valid_emails:
            ok, _ = validate_email_format(e)
            self.assertTrue(ok, f"Expected {e} to be valid")

        invalid_emails = ["invalid-email", "user@", "@domain.com", "user@domain", ""]
        for e in invalid_emails:
            ok, msg = validate_email_format(e)
            self.assertFalse(ok, f"Expected {e} to be invalid: {msg}")

    def test_04_user_registration_farmer_default(self):
        """Test registration creates farmer account with bcrypt hash."""
        email = f"farmer_test_{int(time.time()*1000)}@agriai.org"
        ok, user = create_user("Ramesh Kisan", email, "Kisan@Secure2026", role="farmer")
        self.assertTrue(ok)
        self.assertEqual(user["role"], "farmer")
        self.assertEqual(user["email"], email)

        # Verify login
        v_ok, v_user = verify_user(email, "Kisan@Secure2026")
        self.assertTrue(v_ok)
        self.assertEqual(v_user["role"], "farmer")

    def test_05_duplicate_email_prevention(self):
        """Test duplicate registration prevention with case-insensitivity."""
        email = f"duplicate_{int(time.time()*1000)}@agriai.org"
        ok1, _ = create_user("User One", email, "Secret@12345", role="farmer")
        self.assertTrue(ok1)

        # Attempt same email with different casing
        ok2, err_msg = create_user("User Two", email.upper(), "Secret@12345", role="farmer")
        self.assertFalse(ok2)
        self.assertIn("already exists", err_msg.lower())

    def test_06_admin_credentials_and_role(self):
        """Test admin account authentication and role verification."""
        ok, admin_user = verify_user("admin@agriai.org", "Admin@12345")
        self.assertTrue(ok)
        self.assertEqual(admin_user["role"], "admin")

    def test_07_invalid_credentials_handling(self):
        """Test that invalid passwords or non-existent emails return proper errors."""
        ok, msg = verify_user("nonexistent_farmer@agriai.org", "AnyPassword@123")
        self.assertTrue("no account found" in msg.lower() or "invalid" in msg.lower())

        ok, msg = verify_user("admin@agriai.org", "WrongPassword@123")
        self.assertFalse(ok)
        self.assertIn("invalid", msg.lower())

    def test_08_forgot_password_flow(self):
        """Test password reset flow with complexity verification and login."""
        email = f"reset_test_{int(time.time()*1000)}@agriai.org"
        create_user("Reset User", email, "Initial@Pass123", role="farmer")

        # Nonexistent email reset fails
        ok, msg = reset_password("nonexistent@agriai.org", "NewPass@2026")
        self.assertFalse(ok)

        # Reset with weak password fails
        ok, msg = reset_password(email, "weak")
        self.assertFalse(ok)

        # Valid reset succeeds
        ok, msg = reset_password(email, "NewBrand@2026")
        self.assertTrue(ok)

        # Old password fails
        v_old, _ = verify_user(email, "Initial@Pass123")
        self.assertFalse(v_old)

        # New password succeeds
        v_new, user = verify_user(email, "NewBrand@2026")
        self.assertTrue(v_new)

    def test_09_remember_me_session_persistence(self):
        """Test persistent session token creation, lookup, and deletion."""
        email = f"session_test_{int(time.time()*1000)}@agriai.org"
        ok, user = create_user("Session User", email, "Session@Pass123", role="farmer")
        self.assertTrue(ok)

        # Generate persistent token
        token = create_session_token(user["id"], days_valid=15)
        self.assertIsNotNone(token)
        self.assertGreater(len(token), 20)

        # Retrieve user by token
        retrieved = get_user_by_session_token(token)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["id"], user["id"])
        self.assertEqual(retrieved["email"], email)

        # Delete token on logout
        delete_session_token(token)
        retrieved_after_logout = get_user_by_session_token(token)
        self.assertIsNone(retrieved_after_logout)

if __name__ == "__main__":
    unittest.main()
