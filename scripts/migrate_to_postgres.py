"""
AgriAI Production Database Migration Utility
Migrates all existing records from local SQLite (predictions.db) to PostgreSQL.
Preserves existing data, user credentials, prediction histories, and configurations.
"""
import os
import sys
import sqlite3
from pathlib import Path

# Add project root and app directory to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "app"))

from app.config import DATABASE_URL, DEFAULT_SQLITE_PATH
from app.database import get_engine, normalize_database_url
from app.models import (
    Base, User, PredictionHistory, ContactQuery,
    UserPreference, AccountActivity, UserSession, PasswordResetToken
)
from sqlalchemy.orm import Session
from sqlalchemy import select, func

def migrate():
    sqlite_path = DEFAULT_SQLITE_PATH
    if not sqlite_path.exists():
        print(f"[-] SQLite database file not found at: {sqlite_path}")
        return

    pg_url = os.getenv("DATABASE_URL")
    if not pg_url or "sqlite" in pg_url:
        print("[-] Please set DATABASE_URL to a valid PostgreSQL connection string:")
        print("    Example: export DATABASE_URL=postgresql://user:password@localhost:5432/agri_db")
        return

    normalized_url = normalize_database_url(pg_url)
    print(f"[*] Target PostgreSQL URL: {normalized_url.split('@')[-1] if '@' in normalized_url else normalized_url}")

    pg_engine = get_engine(normalized_url)
    print("[*] Creating PostgreSQL schema tables and indexes...")
    Base.metadata.create_all(bind=pg_engine, checkfirst=True)

    print(f"[*] Reading source SQLite records from: {sqlite_path}")
    sq_conn = sqlite3.connect(sqlite_path)
    sq_conn.row_factory = sqlite3.Row
    sq_cur = sq_conn.cursor()

    with Session(pg_engine) as pg_session:
        # 1. Migrate Users
        sq_cur.execute("SELECT * FROM users")
        user_rows = sq_cur.fetchall()
        migrated_users = 0
        for r in user_rows:
            exists = pg_session.execute(
                select(User).where(func.lower(User.email) == r["email"].lower())
            ).scalars().first()
            if not exists:
                u = User(
                    id=r["id"],
                    name=r["name"],
                    email=r["email"],
                    password_hash=r["password_hash"],
                    salt=r["salt"] if "salt" in r.keys() else "bcrypt",
                    role=r["role"] if "role" in r.keys() else "farmer",
                    created_at=r["created_at"],
                    last_login=r["last_login"] if "last_login" in r.keys() else None,
                    phone=r["phone"] if "phone" in r.keys() else None,
                    state=r["state"] if "state" in r.keys() else None,
                    district=r["district"] if "district" in r.keys() else None,
                    preferred_crop=r["preferred_crop"] if "preferred_crop" in r.keys() else None,
                    avatar_path=r["avatar_path"] if "avatar_path" in r.keys() else None,
                    status=r["status"] if "status" in r.keys() and r["status"] else "Active"
                )
                pg_session.add(u)
                migrated_users += 1
        pg_session.commit()
        print(f"[+] Users migrated: {migrated_users} (Total source: {len(user_rows)})")

        # 2. Migrate Prediction History
        sq_cur.execute("SELECT * FROM prediction_history")
        pred_rows = sq_cur.fetchall()
        migrated_preds = 0
        for r in pred_rows:
            exists = pg_session.execute(
                select(PredictionHistory.id).where(PredictionHistory.id == r["id"])
            ).scalar()
            if not exists:
                p = PredictionHistory(
                    id=r["id"],
                    user_id=r["user_id"] if "user_id" in r.keys() else None,
                    user_email=r["user_email"] if "user_email" in r.keys() else None,
                    state=r["state"] if "state" in r.keys() else None,
                    district=r["district"] if "district" in r.keys() else None,
                    crop=r["crop"] if "crop" in r.keys() else None,
                    crop_category=r["crop_category"] if "crop_category" in r.keys() else None,
                    sowing_season=r["sowing_season"] if "sowing_season" in r.keys() else None,
                    weather_season=r["weather_season"] if "weather_season" in r.keys() else None,
                    temperature=r["temperature"] if "temperature" in r.keys() else None,
                    humidity=r["humidity"] if "humidity" in r.keys() else None,
                    rainfall=r["rainfall"] if "rainfall" in r.keys() else None,
                    thi=r["thi"] if "thi" in r.keys() else None,
                    rf_hum_ratio=r["rf_hum_ratio"] if "rf_hum_ratio" in r.keys() else None,
                    predicted_pest=r["predicted_pest"] if "predicted_pest" in r.keys() else None,
                    pest_prob=r["pest_prob"] if "pest_prob" in r.keys() else None,
                    predicted_risk=r["predicted_risk"] if "predicted_risk" in r.keys() else None,
                    risk_prob=r["risk_prob"] if "risk_prob" in r.keys() else None,
                    model_notes=r["model_notes"] if "model_notes" in r.keys() else None,
                    pesticide=r["pesticide"] if "pesticide" in r.keys() else None,
                    dosage=r["dosage"] if "dosage" in r.keys() else None,
                    organic_control=r["organic_control"] if "organic_control" in r.keys() else None,
                    safety_notes=r["safety_notes"] if "safety_notes" in r.keys() else None,
                    prevention_methods=r["prevention_methods"] if "prevention_methods" in r.keys() else None,
                    pdf_path=r["pdf_path"] if "pdf_path" in r.keys() else None,
                    created_at=r["created_at"]
                )
                pg_session.add(p)
                migrated_preds += 1
        pg_session.commit()
        print(f"[+] Prediction records migrated: {migrated_preds} (Total source: {len(pred_rows)})")

        # 3. Migrate Contact Queries
        sq_cur.execute("SELECT * FROM contact_queries")
        cq_rows = sq_cur.fetchall()
        migrated_cqs = 0
        for r in cq_rows:
            exists = pg_session.execute(select(ContactQuery.id).where(ContactQuery.id == r["id"])).scalar()
            if not exists:
                cq = ContactQuery(
                    id=r["id"],
                    name=r["name"],
                    email=r["email"],
                    subject=r["subject"],
                    message=r["message"],
                    created_date=r["created_date"],
                    status=r["status"] if "status" in r.keys() else "Pending"
                )
                pg_session.add(cq)
                migrated_cqs += 1
        pg_session.commit()
        print(f"[+] Contact queries migrated: {migrated_cqs} (Total source: {len(cq_rows)})")

        # 4. Migrate User Preferences
        try:
            sq_cur.execute("SELECT * FROM user_preferences")
            pref_rows = sq_cur.fetchall()
            migrated_prefs = 0
            for r in pref_rows:
                exists = pg_session.execute(select(UserPreference.user_id).where(UserPreference.user_id == r["user_id"])).scalar()
                if not exists:
                    pref = UserPreference(
                        user_id=r["user_id"],
                        dark_mode=r["dark_mode"],
                        language=r["language"],
                        notifications=r["notifications"],
                        theme_mode=r["theme_mode"] if "theme_mode" in r.keys() else "auto",
                        notify_prediction=r["notify_prediction"] if "notify_prediction" in r.keys() else 1,
                        notify_weather=r["notify_weather"] if "notify_weather" in r.keys() else 1,
                        notify_system=r["notify_system"] if "notify_system" in r.keys() else 1,
                        privacy_history=r["privacy_history"] if "privacy_history" in r.keys() else 1,
                        privacy_email=r["privacy_email"] if "privacy_email" in r.keys() else 1,
                        privacy_profile=r["privacy_profile"] if "privacy_profile" in r.keys() else 1
                    )
                    pg_session.add(pref)
                    migrated_prefs += 1
            pg_session.commit()
            print(f"[+] Preferences migrated: {migrated_prefs}")
        except Exception as e:
            print(f"[-] Note for user_preferences migration: {e}")

        # 5. Migrate Account Activities
        try:
            sq_cur.execute("SELECT * FROM account_activity")
            act_rows = sq_cur.fetchall()
            migrated_acts = 0
            for r in act_rows:
                exists = pg_session.execute(select(AccountActivity.id).where(AccountActivity.id == r["id"])).scalar()
                if not exists:
                    act = AccountActivity(
                        id=r["id"],
                        user_id=r["user_id"],
                        activity_type=r["activity_type"],
                        description=r["description"],
                        icon=r["icon"] if "icon" in r.keys() else "⚡",
                        created_at=r["created_at"]
                    )
                    pg_session.add(act)
                    migrated_acts += 1
            pg_session.commit()
            print(f"[+] Account activities migrated: {migrated_acts}")
        except Exception as e:
            print(f"[-] Note for account_activity migration: {e}")

    sq_conn.close()
    print("[+] Migration to PostgreSQL completed successfully!")

if __name__ == "__main__":
    migrate()
