"""
SQLAlchemy 2.x Declarative Models for AgriAI Database Layer.
Supports PostgreSQL (Production) and SQLite (Development).
"""
from typing import Dict, Any
from sqlalchemy import (
    Column, Integer, String, Float, Text, ForeignKey,
    Index
)
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy 2.x models."""
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance columns to a python dictionary."""
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False, default="bcrypt")
    role = Column(String(50), nullable=False, default="farmer")
    created_at = Column(String(50), nullable=False)
    last_login = Column(String(50), nullable=True)
    phone = Column(String(50), nullable=True)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    preferred_crop = Column(String(100), nullable=True)
    avatar_path = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="Active")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role_status", "role", "status"),
    )

class PredictionHistory(Base):
    __tablename__ = "prediction_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email = Column(String(255), nullable=True)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    crop = Column(String(100), nullable=True)
    crop_category = Column(String(100), nullable=True)
    sowing_season = Column(String(50), nullable=True)
    weather_season = Column(String(50), nullable=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    rainfall = Column(Float, nullable=True)
    thi = Column(Float, nullable=True)
    rf_hum_ratio = Column(Float, nullable=True)
    predicted_pest = Column(String(100), nullable=True)
    pest_prob = Column(Float, nullable=True)
    predicted_risk = Column(String(50), nullable=True)
    risk_prob = Column(Float, nullable=True)
    model_notes = Column(Text, nullable=True)
    pesticide = Column(Text, nullable=True)
    dosage = Column(Text, nullable=True)
    organic_control = Column(Text, nullable=True)
    safety_notes = Column(Text, nullable=True)
    prevention_methods = Column(Text, nullable=True)
    pdf_path = Column(String(255), nullable=True)
    created_at = Column(String(50), nullable=False)

    __table_args__ = (
        Index("idx_preds_user_id", "user_id"),
        Index("idx_preds_created_at", "created_at"),
        Index("idx_preds_crop", "crop"),
        Index("idx_preds_state_district", "state", "district"),
    )

class ContactQuery(Base):
    __tablename__ = "contact_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    created_date = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="Pending")

    __table_args__ = (
        Index("idx_contact_status", "status"),
    )

class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    dark_mode = Column(Integer, nullable=False, default=0)
    language = Column(String(50), nullable=False, default="English")
    notifications = Column(Integer, nullable=False, default=1)
    theme_mode = Column(String(50), nullable=False, default="auto")
    notify_prediction = Column(Integer, nullable=False, default=1)
    notify_weather = Column(Integer, nullable=False, default=1)
    notify_system = Column(Integer, nullable=False, default=1)
    privacy_history = Column(Integer, nullable=False, default=1)
    privacy_email = Column(Integer, nullable=False, default=1)
    privacy_profile = Column(Integer, nullable=False, default=1)

class AccountActivity(Base):
    __tablename__ = "account_activity"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    activity_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(10), nullable=False, default="⚡")
    created_at = Column(String(50), nullable=False)

    __table_args__ = (
        Index("idx_activity_user_id", "user_id"),
    )

class UserSession(Base):
    __tablename__ = "user_sessions"

    token = Column(String(255), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(String(50), nullable=False)
    expires_at = Column(String(50), nullable=False)

    __table_args__ = (
        Index("idx_sessions_token", "token"),
    )

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token = Column(String(255), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(String(50), nullable=False)
    used = Column(Integer, nullable=False, default=0)
    created_at = Column(String(50), nullable=False)

    __table_args__ = (
        Index("idx_reset_token", "token"),
    )
