"""
PostgreSQL Migration & API Security Test Suite
Covers:
1. PostgreSQL connection & driver verification.
2. Database schema initialization (idempotency & table/index verification).
3. User registration (role forced to 'farmer', no public admin creation).
4. Duplicate email rejection.
5. Login and JWT generation (sanitized response, no password hash).
6. JWT verification (claims validation & invalid/expired token rejection).
7. Unauthorized profile access (401 on missing token, 403 on accessing other user).
8. Unauthorized history access (401 on missing token, 403 on accessing other user).
9. Prediction history persistence (persistence, retrieval, and deduplication).
10. Admin access control (restricted admin endpoints & cross-user access).
"""
import os
import sys
import uuid
import pytest
from datetime import timedelta
from fastapi.testclient import TestClient

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "app"))

try:
    from app.config import (
        ADMIN_EMAIL, ADMIN_DEFAULT_PASSWORD, validate_production_secrets
    )
    from app.database import (
        init_db, get_engine, normalize_database_url, get_database_health_summary,
        create_user, verify_user, get_user_by_id, get_user_by_email,
        save_prediction_history, get_user_prediction_history, delete_user_account
    )
    from app.models import Base
    from app.security import create_access_token, decode_access_token
except (ImportError, ModuleNotFoundError):
    from config import (
        ADMIN_EMAIL, ADMIN_DEFAULT_PASSWORD, validate_production_secrets
    )
    from database import (
        init_db, get_engine, normalize_database_url, get_database_health_summary,
        create_user, verify_user, get_user_by_id, get_user_by_email,
        save_prediction_history, get_user_prediction_history, delete_user_account
    )
    from models import Base
    from security import create_access_token, decode_access_token
from src.api import app


class TestPostgresMigrationSuite:

    @classmethod
    def setup_class(cls):
        init_db()
        cls.client = TestClient(app)

        # Unique test emails for this run
        uid = uuid.uuid4().hex[:8]
        cls.farmer_email = f"farmer_{uid}@kisan.org"
        cls.farmer_pw = "FarmerSecret@2026!"
        cls.farmer_name = f"Farmer Test_{uid}"

        cls.other_farmer_email = f"other_{uid}@kisan.org"
        cls.other_farmer_pw = "OtherSecret@2026!"
        cls.other_farmer_name = f"Other Farmer_{uid}"

        # Register Farmer 1
        ok, u1 = create_user(cls.farmer_name, cls.farmer_email, cls.farmer_pw, role="farmer")
        assert ok is True
        cls.farmer_id = u1["id"]

        # Register Farmer 2
        ok, u2 = create_user(cls.other_farmer_name, cls.other_farmer_email, cls.other_farmer_pw, role="farmer")
        assert ok is True
        cls.other_farmer_id = u2["id"]

        # Generate tokens
        cls.farmer_token = create_access_token({"sub": str(cls.farmer_id), "email": cls.farmer_email, "role": "farmer"})
        cls.other_farmer_token = create_access_token({"sub": str(cls.other_farmer_id), "email": cls.other_farmer_email, "role": "farmer"})

        # Get Admin ID
        admin_u = get_user_by_email(ADMIN_EMAIL)
        cls.admin_id = admin_u["id"]
        cls.admin_token = create_access_token({"sub": str(cls.admin_id), "email": ADMIN_EMAIL, "role": "admin"})

    @classmethod
    def teardown_class(cls):
        if hasattr(cls, "farmer_id"):
            delete_user_account(cls.farmer_id)
        if hasattr(cls, "other_farmer_id"):
            delete_user_account(cls.other_farmer_id)

    # --------------------------------------------------------------------------
    # 1. PostgreSQL Connection & Driver Verification
    # --------------------------------------------------------------------------
    def test_01_postgresql_connection_and_driver(self):
        """Verify URL normalization, psycopg driver mapping, and no silent SQLite fallback."""
        raw_url = "postgresql://agri_user:secret@localhost:5432/agri_db"
        norm = normalize_database_url(raw_url)
        assert norm.startswith("postgresql+psycopg://") or norm.startswith("postgresql+psycopg2://")
        assert "localhost:5432/agri_db" in norm

        # Test Heroku / Neon 'postgres://' compatibility
        raw_heroku = "postgres://agri_user:secret@ep-cool.us-east-1.aws.neon.tech/agri_db"
        norm_heroku = normalize_database_url(raw_heroku)
        assert norm_heroku.startswith("postgresql+psycopg://") or norm_heroku.startswith("postgresql+psycopg2://")

        # Verify that an unreachable PostgreSQL host NEVER silently falls back to SQLite
        fake_pg_url = "postgresql://invalid_user:bad_password@127.0.0.1:59999/fake_db"
        with pytest.raises(ConnectionError) as exc_info:
            get_engine(fake_pg_url)
        assert "silent fallback to sqlite is strictly forbidden" in str(exc_info.value).lower()

    # --------------------------------------------------------------------------
    # 2. Database Schema Initialization (Idempotent)
    # --------------------------------------------------------------------------
    def test_02_database_schema_initialization(self):
        """Verify idempotent schema initialization, table presence, and index registration."""
        init_db(force=True)
        health = get_database_health_summary()
        assert health["status"] == "Healthy & Online"
        assert "table_counts" in health

        expected_tables = [
            "users", "prediction_history", "contact_queries",
            "user_preferences", "account_activity", "user_sessions",
            "password_reset_tokens"
        ]
        for tbl in expected_tables:
            assert tbl in health["table_counts"], f"Missing table: {tbl}"

        # Verify required indexes
        assert health["indexes_active"] >= 8
        idx_names = [idx.split()[0] for idx in health["index_list"]]
        for req in ["idx_users_email", "idx_preds_user_id", "idx_contact_status", "idx_sessions_token"]:
            assert req in idx_names

        # Verify admin seeding idempotency
        admin_row = get_user_by_email(ADMIN_EMAIL)
        assert admin_row is not None
        assert admin_row["role"] == "admin"

    # --------------------------------------------------------------------------
    # 3. User Registration (Forced 'farmer' Role, Security)
    # --------------------------------------------------------------------------
    def test_03_user_registration(self):
        """Verify public registration forces role to 'farmer', refusing admin escalation."""
        rand_email = f"hack_admin_{uuid.uuid4().hex[:6]}@agriai.org"
        payload = {
            "name": "Malicious Caller",
            "email": rand_email,
            "password": "Password@12345",
            "role": "admin"  # Attempt to create an admin account
        }
        resp = self.client.post("/register", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        registered_user = data["user"]

        # MUST be forced to farmer!
        assert registered_user["role"] == "farmer", "Security flaw: Public registration allowed non-farmer role"

        # Password hash or salt MUST NOT be returned in API response
        assert "password_hash" not in registered_user
        assert "salt" not in registered_user

        # Clean up
        delete_user_account(registered_user["id"])

    # --------------------------------------------------------------------------
    # 4. Duplicate Email Rejection
    # --------------------------------------------------------------------------
    def test_04_duplicate_email_rejection(self):
        """Verify duplicate email registration (case-insensitive) is rejected with 400 Bad Request."""
        payload = {
            "name": "Duplicate Tester",
            "email": self.farmer_email.upper(),  # Test uppercase variation
            "password": "ValidPassword@123",
            "role": "farmer"
        }
        resp = self.client.post("/register", json=payload)
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"].lower()

    # --------------------------------------------------------------------------
    # 5. Login & JWT Generation
    # --------------------------------------------------------------------------
    def test_05_login_and_jwt_generation(self):
        """Verify valid login returns access_token, token_type bearer, and sanitized user data."""
        resp = self.client.post("/login", json={
            "email": self.farmer_email,
            "password": self.farmer_pw
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 30

        user = data["user"]
        assert user["email"] == self.farmer_email.lower()
        assert "password_hash" not in user
        assert "salt" not in user

    # --------------------------------------------------------------------------
    # 6. JWT Verification
    # --------------------------------------------------------------------------
    def test_06_jwt_verification(self):
        """Verify JWT decoding, claim verification, and rejection of invalid/expired tokens."""
        claims = decode_access_token(self.farmer_token)
        assert claims["sub"] == str(self.farmer_id)
        assert claims["email"] == self.farmer_email
        assert claims["role"] == "farmer"
        assert "exp" in claims

        # Tampered / Invalid token rejection
        with pytest.raises(ValueError):
            decode_access_token("tampered.token.here")

        # Expired token rejection
        expired_token = create_access_token(
            {"sub": str(self.farmer_id), "email": self.farmer_email, "role": "farmer"},
            expires_delta=timedelta(seconds=-10)
        )
        with pytest.raises(ValueError) as exc:
            decode_access_token(expired_token)
        assert "expired" in str(exc.value).lower()

    # --------------------------------------------------------------------------
    # 7. Unauthorized Profile Access
    # --------------------------------------------------------------------------
    def test_07_unauthorized_profile_access(self):
        """Verify 401 on missing token and 403 on cross-user profile access."""
        # Unauthenticated access -> 401 Unauthorized
        resp = self.client.get("/profile", headers={})
        assert resp.status_code == 401

        # Farmer 1 viewing their own profile -> 200 OK
        resp = self.client.get("/profile", headers={"Authorization": f"Bearer {self.farmer_token}"})
        assert resp.status_code == 200
        assert resp.json()["profile"]["id"] == self.farmer_id

        # Farmer 1 trying to view Farmer 2's profile -> 403 Forbidden (Data Isolation)
        resp = self.client.get(
            f"/profile?user_id={self.other_farmer_id}",
            headers={"Authorization": f"Bearer {self.farmer_token}"}
        )
        assert resp.status_code == 403
        assert "access denied" in resp.json()["detail"].lower()

    # --------------------------------------------------------------------------
    # 8. Unauthorized History Access
    # --------------------------------------------------------------------------
    def test_08_unauthorized_history_access(self):
        """Verify 401 on missing token and 403 on cross-user prediction history access."""
        # Unauthenticated access -> 401 Unauthorized
        resp = self.client.get("/history", headers={})
        assert resp.status_code == 401

        # Farmer 1 querying their own history -> 200 OK
        resp = self.client.get("/history", headers={"Authorization": f"Bearer {self.farmer_token}"})
        assert resp.status_code == 200
        assert "history" in resp.json()

        # Farmer 1 trying to query Farmer 2's history -> 403 Forbidden
        resp = self.client.get(
            f"/history?user_id={self.other_farmer_id}",
            headers={"Authorization": f"Bearer {self.farmer_token}"}
        )
        assert resp.status_code == 403

    # --------------------------------------------------------------------------
    # 9. Prediction History Persistence
    # --------------------------------------------------------------------------
    def test_09_prediction_history_persistence(self):
        """Verify prediction history insertion, deduplication, and persistence in database."""
        pred_id = save_prediction_history(
            user_id=self.farmer_id,
            user_email=self.farmer_email,
            state="Andhra Pradesh",
            district="Guntur",
            crop="Cotton",
            crop_category="Commercial",
            sowing_season="Kharif",
            weather_season="Monsoon",
            temp=31.5,
            humidity=72.0,
            rainfall=110.0,
            thi=78.2,
            rf_hum_ratio=1.5,
            predicted_pest="Pink Bollworm",
            pest_prob=88.5,
            predicted_risk="High",
            risk_prob=92.0,
            model_notes="ML Advisory Inference",
            recommendations={"pesticide": "Emamectin Benzoate 5% SG", "dosage": "0.4 g/L"}
        )
        assert pred_id is not None
        assert pred_id > 0

        # Retrieve history for farmer
        hist = get_user_prediction_history(user_id=self.farmer_id)
        assert len(hist) >= 1
        record = [h for h in hist if h["id"] == pred_id][0]
        assert record["crop"] == "Cotton"
        assert record["predicted_pest"] == "Pink Bollworm"
        assert record["predicted_risk"] == "High"

        # Verify duplicate prevention (submitting identical record within 30s)
        dup_id = save_prediction_history(
            user_id=self.farmer_id,
            user_email=self.farmer_email,
            state="Andhra Pradesh",
            district="Guntur",
            crop="Cotton",
            crop_category="Commercial",
            sowing_season="Kharif",
            weather_season="Monsoon",
            temp=31.5,
            humidity=72.0,
            rainfall=110.0,
            thi=78.2,
            rf_hum_ratio=1.5,
            predicted_pest="Pink Bollworm",
            pest_prob=88.5,
            predicted_risk="High",
            risk_prob=92.0,
            model_notes="ML Advisory Inference",
            recommendations={"pesticide": "Emamectin Benzoate 5% SG", "dosage": "0.4 g/L"}
        )
        assert dup_id == pred_id, "Deduplication failed to return existing prediction ID"

    # --------------------------------------------------------------------------
    # 10. Admin Access Control
    # --------------------------------------------------------------------------
    def test_10_admin_access_control(self):
        """Verify admin privileges allow cross-user inspection and admin-restricted endpoints."""
        # 1. Farmer attempting to access admin endpoint -> 403 Forbidden
        resp = self.client.get("/admin/users", headers={"Authorization": f"Bearer {self.farmer_token}"})
        assert resp.status_code == 403

        # 2. Admin accessing admin endpoint -> 200 OK
        resp = self.client.get("/admin/users", headers={"Authorization": f"Bearer {self.admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["count"] > 0

        # 3. Admin can view other users' profiles
        resp = self.client.get(
            f"/profile?user_id={self.farmer_id}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["profile"]["email"] == self.farmer_email.lower()

        # 4. Admin can view other users' prediction histories
        resp = self.client.get(
            f"/history?user_id={self.farmer_id}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert resp.status_code == 200
        assert "history" in resp.json()
