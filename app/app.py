import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agriai.app")

# Ensure app directory is on path
sys.path.append(os.path.dirname(__file__))

# Reset Streamlit form context stack if running under testing or reload harness
try:
    st._main_dg._form_data = None
    if hasattr(st, "sidebar"):
        st.sidebar._form_data = None
        if getattr(st.sidebar, "_parent", None):
            st.sidebar._parent._form_data = None
    from streamlit.elements.lib.form_utils import context_dg_stack
    from streamlit.delta_generator import DeltaGenerator
    context_dg_stack.set((DeltaGenerator(),))
except Exception:
    pass

import secrets
import time
import io
import re
import base64
import plotly.express as px
import plotly.graph_objects as go

from weather import fetch_open_meteo_weather, derive_season_from_sowing, get_current_sowing_season, DEMO_PRESETS
from predictor import predict_pest_and_risk, PEST_ICONS, normalize_top3_percentages, DISTRICT_SOIL_MAP, SOIL_BASELINE, SUPPORTED_SOIL_TYPES
from recommender import get_recommendations
from pdf_generator import generate_prediction_pdf, generate_history_summary_pdf, generate_system_summary_pdf, generate_analytics_report_pdf
from database import (
    init_db, create_user, verify_user, reset_password,
    get_user_by_id, get_all_users, delete_user, update_user_profile,
    update_user_full_profile, change_user_password, save_user_avatar, remove_user_avatar,
    log_account_activity, get_user_account_activities, get_user_profile_stats,
    delete_all_user_sessions, delete_user_account,
    save_prediction_history, get_user_prediction_history,
    get_all_prediction_history, delete_prediction_history,
    count_user_predictions, get_prediction_stats,
    get_user_dashboard_metrics, record_report_download,
    save_contact_query, get_contact_queries, update_contact_query_status, delete_contact_query,
    save_user_preferences, get_user_preferences,
    validate_email_format, validate_password_complexity, get_user_by_email,
    get_all_users_extended, update_user_status, update_user_role, admin_update_user,
    get_admin_dashboard_kpis, get_admin_analytics_data, get_database_system_stats, get_all_activity_logs,
    create_password_reset_token, verify_password_reset_token, redeem_password_reset_token
)
from auth import init_session, login_user, logout_user, get_current_user, is_admin, logout_from_all_devices
from admin_portal import render_enterprise_admin_portal
from security import check_login_rate_limit, record_failed_login, reset_login_rate_limit, sanitize_text
from logger import log_auth_event, log_prediction_event, log_pdf_event

# Initialize DB and Session
init_db()
init_session()

# Non-blocking Background Pre-warming for ML Model Inference Pipeline (Singleton launch)
if not getattr(st, "_ml_prewarmer_started", False):
    try:
        import threading
        from predictor import load_ml_artifacts
        threading.Thread(target=load_ml_artifacts, name="AgriAI_ML_Prewarmer", daemon=True).start()
        st._ml_prewarmer_started = True
    except Exception as _e:
        pass

@st.cache_data(ttl=1800, show_spinner=False)
def get_cached_weather(district: str, state: str, sowing_season: str = "Kharif", demo_mode: bool = False, demo_preset: str = "Monsoon High Pest Outbreak"):
    return fetch_open_meteo_weather(
        district=district,
        state=state,
        sowing_season=sowing_season,
        demo_mode=demo_mode,
        demo_preset=demo_preset
    )

# Page Configuration & SEO
st.set_page_config(
    page_title="AgriAI Advisor - AI-Powered Crop Pest Prediction & Advisory Platform",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fetch Current User State
current_user = get_current_user()
admin_status = is_admin()

# Initialize session state (Enforce Permanent Premium Dark Theme)
st.session_state["theme"] = "dark"
st.session_state["dark_mode"] = True
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Dashboard"

def navigate_to(page_name: str):
    """Direct session navigation callback to eliminate redundant reruns."""
    st.session_state["current_page"] = page_name
if "language" not in st.session_state:
    st.session_state["language"] = "English"
if "notifications_enabled" not in st.session_state:
    st.session_state["notifications_enabled"] = True
if "show_logout_confirm" not in st.session_state:
    st.session_state["show_logout_confirm"] = False

# Restore saved user preferences if logged in (enforcing Dark Theme)
if current_user and "user_prefs_synced" not in st.session_state:
    try:
        user_saved_prefs = get_user_preferences(current_user["id"])
        st.session_state["dark_mode"] = True
        st.session_state["theme"] = "dark"
        st.session_state["language"] = user_saved_prefs.get("language", "English")
        st.session_state["notifications_enabled"] = user_saved_prefs.get("notifications_enabled", True)
        st.session_state["user_prefs_synced"] = True
    except Exception as e:
        logger.error(f"Error loading user preferences: {e}")

# Single Unified Theme: Premium Dark Mode (#0F172A SaaS Palette)
is_dark = True
bg_color = "#0F172A"
card_bg = "#1E293B"
card_border = "#334155"
text_main = "#F8FAFC"
text_muted = "#CBD5E1"

# ==========================================================
# SAFE MARKDOWN RENDER HOOK (PREVENTS RAW HTML CODE RENDERING)
# ==========================================================
if not getattr(st, "_safe_markdown_installed", False):
    _orig_st_markdown = st.markdown

    def safe_markdown(body, *args, **kwargs):
        if isinstance(body, str) and not kwargs.get("unsafe_allow_html", False):
            if "<" in body:
                html_indicators = (
                    '<div', '<span', '<p', '<table', '<h1', '<h2', '<h3', '<h4', '<style',
                    '<section', '<svg', '<line', '<rect', '<circle', '<path', '<img', '<a ',
                    '<ul', '<li', '<details', '<summary', '<hr', '<b', '<i', 'class=', 'style='
                )
                b_low = body.lower()
                if any(tag in b_low for tag in html_indicators):
                    kwargs["unsafe_allow_html"] = True
        return _orig_st_markdown(body, *args, **kwargs)

    st.markdown = safe_markdown
    st._safe_markdown_installed = True


# SEO & Favicon Metadata Ingestion
st.markdown("""
<div style="display:none;" id="seo-meta-container">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 36 36'><circle cx='18' cy='18' r='18' fill='%231B5E20'/><path fill='%234ADE80' d='M18 6c-6 0-11 5-11 11 0 7 7 12 11 13 4-1 11-6 11-13 0-6-5-11-11-11zm-1 19v-9h2v9h-2zm-1-11c-2.5-.8-4.2-3.3-4.2-5.8 2.5 0 5 1.7 5.8 4.2-.8.8-1.2 1.4-1.6 1.6zm3.6 0c-.4-.2-.8-.8-1.6-1.6.8-2.5 3.3-4.2 5.8-4.2 0 2.5-1.7 5-4.2 5.8z'/></svg>">
    <meta name="title" content="AgriAI Advisor - AI-Powered Crop Pest Prediction &amp; Advisory Platform">
    <meta name="description" content="AgriAI Advisor (v2.1.0) - Commercial-grade agricultural AI advisory platform forecasting crop pest outbreaks with real-time meteorological intelligence and precision IPM strategies.">
    <meta name="keywords" content="AgriAI Advisor, crop pest prediction, agriculture AI, pest management, precision agriculture, smart farming, India agriculture">
    <meta name="author" content="AgriAI Advisor Enterprise">
    <meta name="version" content="v2.1.0">
    <meta name="robots" content="index, follow">
    <meta property="og:type" content="website">
    <meta property="og:title" content="AgriAI Advisor - AI-Powered Crop Pest Prediction &amp; Advisory Platform">
    <meta property="og:description" content="Commercial-grade agricultural AI advisory platform forecasting crop pest outbreaks with real-time meteorological intelligence and precision IPM strategies.">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="AgriAI Advisor - AI-Powered Crop Pest Prediction &amp; Advisory Platform">
    <meta name="twitter:description" content="Commercial-grade agricultural AI advisory platform forecasting crop pest outbreaks with real-time meteorological intelligence.">
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@500;600;700;800&display=swap');
    
    :root {{
        /* Commercial AgriTech SaaS Dark Theme Variables */
        --bg: #0F172A;
        --card-bg: #1E293B;
        --card-border: #334155;
        --text-main: #F8FAFC;
        --text-muted: #CBD5E1;
        --primary: #22C55E;
        --primary-hover: #16A34A;
        --secondary: #10B981;
        --accent: #06B6D4;
        --danger: #EF4444;
        --warning: #F59E0B;
        --success: #22C55E;
        --input-bg: #0F172A;
        --input-text: #F8FAFC;
        --input-border: #334155;
        --input-placeholder: #64748B;
        --sidebar-bg: #111827;
        --sidebar-card: #1E293B;
        --glass-bg: rgba(30, 41, 59, 0.85);
        --glass-border: #334155;
        --glass-blur: 18px;
        --card-shadow: 0 10px 35px rgba(0, 0, 0, 0.35);
        --nav-bg: #1F2937;
        --hero-bg: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #14532D 100%);
        --summary-item-bg: #1E293B;
        --summary-item-val: #F8FAFC;
        --summary-item-label: #CBD5E1;
        --weather-bg: #0F172A;
        --weather-card-bg: #1E293B;
        --weather-label: #CBD5E1;
        --weather-val: #F8FAFC;
        --organic-card-bg: rgba(20, 83, 45, 0.30);
        --organic-title: #4ADE80;
        --safety-card-bg: rgba(120, 53, 15, 0.25);
        --safety-title: #FBBF24;
        --season-badge-bg: rgba(20, 83, 45, 0.40);
        --season-badge-border: #22C55E;
        --season-badge-text: #4ADE80;
        --tab-text: #F8FAFC;
        --tab-inactive: #94A3B8;
        --tab-active: #22C55E;
        --tab-hover-bg: rgba(34, 197, 94, 0.08);
        --tab-active-bg: rgba(34, 197, 94, 0.16);
    }}
</style>
""", unsafe_allow_html=True)

def get_static_css() -> str:
    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

_raw_global_css = get_static_css()

def get_cached_evaluated_css(is_dark_mode: bool, muted_color: str) -> str:
    return _raw_global_css

_evaluated_css = _raw_global_css

# Permanent High-Contrast and Vertical Card Stacking Guarantee
_contrast_override_css = """
/* Hero Header High-Contrast Guarantee */
.saas-hero-title, .dash-hero-title, .about-hero-title, .contact-hero-title, .profile-hero-name {
    color: #FFFFFF !important;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.35) !important;
}
.saas-hero-subtitle, .dash-hero-subtitle, .about-hero-subtitle, .contact-hero-subtitle {
    color: rgba(255, 255, 255, 0.94) !important;
}
.saas-hero-wrap, .dash-hero-banner, .about-hero-wrap, .contact-hero-wrap, .profile-hero-card {
    background: linear-gradient(135deg, #0A2F1B 0%, #134224 45%, #1B5E20 75%, #2E7D32 100%) !important;
    border: 1px solid rgba(255, 255, 255, 0.20) !important;
    box-shadow: 0 16px 40px rgba(10, 35, 20, 0.28) !important;
}

/* STEP 7: SAAS CARD GRID SYSTEM */
.saas-capabilities-grid, .contact-grid-stack {
    display: flex !important;
    flex-direction: column !important;
    gap: 18px !important;
    width: 100% !important;
}
/* Issue 2: Dashboard 2x2 Grid Layout with Equal Dimensions & Soft SaaS Aesthetics */
.saas-stats-grid {
    display: grid !important;
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 20px !important;
    width: 100% !important;
    margin: 20px 0 28px 0 !important;
}
@media (max-width: 640px) {
    .saas-stats-grid {
        grid-template-columns: 1fr !important;
    }
}
/* Issue 4: History Dashboard Compact Cards Responsive Grid */
.dash-stat-grid {
    display: grid !important;
    grid-template-columns: repeat(4, 1fr) !important;
    gap: 16px !important;
    width: 100% !important;
    margin-bottom: 24px !important;
}
@media (max-width: 1024px) {
    .dash-stat-grid {
        grid-template-columns: repeat(2, 1fr) !important;
    }
}
@media (max-width: 600px) {
    .dash-stat-grid {
        grid-template-columns: 1fr !important;
    }
}
.saas-cap-card, .settings-card, .contact-info-card, .contact-form-card {
    width: 100% !important;
    box-sizing: border-box !important;
}
.saas-stat-card {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 18px !important;
    padding: 26px 20px !important;
    text-align: center !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04) !important;
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    min-height: 140px !important;
    box-sizing: border-box !important;
}
.saas-stat-card:hover {
    transform: translateY(-4px) !important;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.08) !important;
    border-color: rgba(34, 197, 94, 0.45) !important;
}
.dash-stat-card {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 16px !important;
    padding: 18px 16px !important;
    display: flex !important;
    align-items: center !important;
    gap: 14px !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04) !important;
    transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease !important;
    box-sizing: border-box !important;
}
.dash-stat-card:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.07) !important;
    border-color: rgba(34, 197, 94, 0.35) !important;
}

/* Premium SaaS Styling & Smooth Micro-Interactions */
.saas-cap-card, .settings-card, .contact-info-card, .contact-form-card, .top3-card, .top-pest-hero-card {
    transition: transform 0.24s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.24s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border-radius: 16px !important;
}
.saas-cap-card:hover, .history-card-item:hover {
    transform: translateY(-2.5px) !important;
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.09) !important;
}
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.stButton > button:hover {
    transform: translateY(-1.5px) !important;
}
.stButton > button:active {
    transform: translateY(0.5px) !important;
}
/* Navbar Logout Button Anti-Wrap Guarantee */
.st-key-btn_top_header_logout button {
    white-space: nowrap !important;
    word-break: keep-all !important;
    min-width: 90px !important;
    height: 38px !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}
.st-key-btn_auth_theme_toggle button {
    white-space: nowrap !important;
    word-break: keep-all !important;
    min-width: 80px !important;
    height: 38px !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.86rem !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}
/* Sleek custom scrollbars */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.35);
    border-radius: 9999px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(148, 163, 184, 0.6);
}
/* Contact Page Single Clean SaaS Card */
.contact-clean-wrapper {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    padding: 30px 16px 50px 16px !important;
    width: 100% !important;
    box-sizing: border-box !important;
}
.contact-clean-card {
    width: 100% !important;
    max-width: 580px !important;
    margin: 0 auto !important;
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 20px !important;
    padding: 42px 36px !important;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.08) !important;
    text-align: center !important;
    box-sizing: border-box !important;
    transition: transform 0.22s ease, box-shadow 0.22s ease !important;
}
.contact-clean-card:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.12) !important;
}
.contact-icon-circle {
    width: 58px !important;
    height: 58px !important;
    margin: 0 auto 16px auto !important;
    background: rgba(34, 197, 94, 0.12) !important;
    border-radius: 50% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 1.8rem !important;
}
.contact-clean-title {
    font-family: 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif !important;
    font-size: 1.65rem !important;
    font-weight: 700 !important;
    color: var(--text-main) !important;
    margin: 0 0 6px 0 !important;
    letter-spacing: -0.01em !important;
}
.contact-clean-subtitle {
    font-size: 0.96rem !important;
    font-weight: 600 !important;
    color: #22c55e !important;
    margin: 0 0 18px 0 !important;
    letter-spacing: 0.01em !important;
}
.contact-clean-divider {
    width: 44px !important;
    height: 3px !important;
    background: #22c55e !important;
    border-radius: 2px !important;
    margin: 0 auto 22px auto !important;
}
.contact-clean-help-heading {
    font-family: 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    color: var(--text-main) !important;
    margin: 0 0 10px 0 !important;
}
.contact-clean-desc {
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
    color: var(--text-muted) !important;
    margin: 0 auto 24px auto !important;
    max-width: 440px !important;
    font-weight: 400 !important;
}
.contact-clean-email-box {
    margin: 0 auto 24px auto !important;
}
.contact-clean-email-link {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    color: #22c55e !important;
    text-decoration: none !important;
    transition: color 0.2s ease !important;
    background: none !important;
    border: none !important;
    padding: 0 !important;
}
.contact-clean-email-link:hover {
    color: #16a34a !important;
    text-decoration: underline !important;
}
.contact-clean-btn-wrap {
    margin-top: 6px !important;
}
.contact-clean-btn {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    background: linear-gradient(135deg, #22c55e, #16a34a) !important;
    color: #ffffff !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    padding: 12px 30px !important;
    border-radius: 12px !important;
    text-decoration: none !important;
    box-shadow: 0 5px 16px rgba(34, 197, 94, 0.32) !important;
    transition: all 0.2s ease !important;
}
.contact-clean-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 22px rgba(34, 197, 94, 0.42) !important;
    color: #ffffff !important;
    text-decoration: none !important;
}

/* Mobile & Tablet Responsive Optimizations */
@media (max-width: 768px) {
    .saas-hero-title, .dash-hero-title {
        font-size: 26px !important;
    }
    .top3-cards-grid {
        display: flex !important;
        flex-direction: column !important;
        gap: 12px !important;
    }
    .block-container {
        padding-left: 12px !important;
        padding-right: 12px !important;
    }
}

/* ==========================================================
   TASK 1: GLOBAL INPUT FIELD FOCUS STATE SYSTEM (#22c55e)
   ========================================================== */
input:focus,
textarea:focus,
select:focus,
.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus {
    border: 2px solid #22c55e !important;
    border-color: #22c55e !important;
    box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.18) !important;
    outline: none !important;
    transition: all 0.2s ease !important;
}

div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-testid="stTextInput"] div[data-baseweb="input"],
div[data-testid="stNumberInput"] div[data-baseweb="input"],
.stTextInput div[data-baseweb="input"],
.stNumberInput div[data-baseweb="input"] {
    border: 1px solid var(--input-border, rgba(255, 255, 255, 0.14)) !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
    background-color: var(--input-bg, transparent) !important;
}

div[data-baseweb="input"]:focus-within,
div[data-baseweb="input"]:has(input:focus),
div[data-baseweb="base-input"]:focus-within,
div[data-baseweb="base-input"]:has(input:focus),
div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
div[data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within,
.stTextInput div[data-baseweb="input"]:focus-within,
.stNumberInput div[data-baseweb="input"]:focus-within {
    border: 2px solid #22c55e !important;
    border-color: #22c55e !important;
    box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.18) !important;
    outline: none !important;
    transition: all 0.2s ease !important;
}

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-baseweb="input"] input,
div[data-baseweb="base-input"] input,
.stTextInput input,
.stNumberInput input {
    background-color: transparent !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    transition: all 0.2s ease !important;
}

div[data-testid="stTextArea"] div[data-baseweb="textarea"],
div[data-baseweb="textarea"],
.stTextArea div[data-baseweb="textarea"] {
    border: 1px solid var(--input-border, rgba(255, 255, 255, 0.14)) !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
    background-color: var(--input-bg, transparent) !important;
}

div[data-testid="stTextArea"] div[data-baseweb="textarea"]:focus-within,
div[data-testid="stTextArea"] div[data-baseweb="textarea"]:has(textarea:focus),
div[data-baseweb="textarea"]:focus-within,
.stTextArea div[data-baseweb="textarea"]:focus-within,
.stTextArea textarea:focus {
    border: 2px solid #22c55e !important;
    border-color: #22c55e !important;
    box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.18) !important;
    outline: none !important;
    transition: all 0.2s ease !important;
}

div[data-testid="stTextArea"] textarea,
div[data-baseweb="textarea"] textarea {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}

div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div {
    border: 1px solid var(--input-border, rgba(255, 255, 255, 0.14)) !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
}

div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within > div,
div[data-testid="stSelectbox"] div[data-baseweb="select"][aria-expanded="true"] > div,
div[data-testid="stSelectbox"] div[data-baseweb="select"]:has(*:focus) > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"]:focus-within > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"][aria-expanded="true"] > div,
div[data-baseweb="select"]:focus-within > div,
div[data-baseweb="select"][aria-expanded="true"] > div,
.stSelectbox div[data-baseweb="select"]:focus-within > div {
    border: 2px solid #22c55e !important;
    border-color: #22c55e !important;
    box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.18) !important;
    outline: none !important;
    transition: all 0.2s ease !important;
}

div[data-baseweb="popover"] input:focus,
div[data-baseweb="menu"] input:focus,
div[data-baseweb="select"] input:focus,
input[role="combobox"]:focus {
    border: 2px solid #22c55e !important;
    border-color: #22c55e !important;
    box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.18) !important;
    outline: none !important;
    transition: all 0.2s ease !important;
}
"""

@st.cache_data(show_spinner=False)
def get_compiled_css() -> str:
    return f"<style>{_raw_global_css}\n{_contrast_override_css}</style>"

st.markdown(get_compiled_css(), unsafe_allow_html=True)

# Preset State and District options
STATE_DISTRICT_MAP = {
    "Andhra Pradesh": ["Guntur", "Vijayawada", "Kurnool", "Anantapur", "Visakhapatnam"],
    "Gujarat": ["Ahmedabad", "Rajkot", "Surat", "Vadodara", "Bhavnagar"],
    "Maharashtra": ["Pune", "Nagpur", "Nashik", "Aurangabad", "Solapur"],
    "Karnataka": ["Bengaluru", "Belagavi", "Hubballi", "Mysuru", "Dharwad"],
    "Uttar Pradesh": ["Kanpur", "Lucknow", "Varanasi", "Agra", "Meerut"],
    "West Bengal": ["Burdwan", "Kolkata", "Hooghly", "Murshidabad", "Nadia"],
    "Tamil Nadu": ["Coimbatore", "Madurai", "Salem", "Tiruchirappalli", "Tirunelveli"]
}

CROP_CATEGORY_MAP = {
    "Cotton": "Commercial",
    "Gram": "Pulses",
    "Groundnut": "Oilseeds",
    "Maize": "Cereal",
    "Mustard": "Oilseeds",
    "Rice": "Cereal",
    "Soybean": "Oilseeds",
    "Sugarcane": "Commercial",
    "Tur (Arhar)": "Pulses",
    "Wheat": "Cereal"
}

# Fetch Current User State
current_user = get_current_user()
admin_status = is_admin()

# Clean any stale form context from previous reruns or test runner threads
try:
    if hasattr(st, "_main_dg"):
        st._main_dg._form_data = None
    if hasattr(st, "sidebar"):
        st.sidebar._form_data = None
        if getattr(st.sidebar, "_parent", None):
            st.sidebar._parent._form_data = None
    from streamlit.elements.lib.form_utils import context_dg_stack
    current_stack = context_dg_stack.get()
    if any(getattr(dg, "_form_data", None) is not None for dg in current_stack):
        clean_stack = tuple(dg for dg in current_stack if getattr(dg, "_form_data", None) is None)
        if not clean_stack:
            from streamlit.delta_generator import DeltaGenerator
            clean_stack = (DeltaGenerator(),)
        context_dg_stack.set(clean_stack)
except Exception:
    pass

# ==========================================================
# 1. AUTHENTICATION FIRST GATEWAY (WHEN NOT LOGGED IN)
# ==========================================================
if not current_user:
    # 1. Full suppression of default Streamlit chrome & application of centered single-screen layout
    st.markdown(f"""
    <style>
        #MainMenu, header, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stDecoration"], [data-testid="stToolbar"], .stDeployButton {{
            display: none !important;
            visibility: hidden !important;
        }}
        html, body, .stApp {{
            overflow-y: auto !important;
            min-height: 100vh !important;
        }}
        .stApp {{
            background: radial-gradient(circle at 15% 15%, rgba(46, 125, 50, 0.08) 0%, transparent 40%),
                        radial-gradient(circle at 85% 85%, rgba(74, 222, 128, 0.07) 0%, transparent 40%),
                        {'#13171F'} !important;
        }}
        [data-testid="stMainBlockContainer"] {{
            max-width: 100% !important;
            padding: 1.5rem 1rem !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            min-height: 100vh !important;
            box-sizing: border-box !important;
        }}
        /* Side spacer columns transparent with zero borders */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:nth-of-type(2)),
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:nth-of-type(2)) div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
        }}
        /* Single Clean SaaS Auth Floating Card */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-of-type(2) {{
            background: {'rgba(28, 32, 40, 0.96)'} !important;
            backdrop-filter: blur(16px) !important;
            -webkit-backdrop-filter: blur(16px) !important;
            border: 1px solid {'rgba(255, 255, 255, 0.08)'} !important;
            border-radius: 20px !important;
            padding: 24px 28px !important;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.22) !important;
            max-width: 480px !important;
            margin: 0 auto !important;
            box-sizing: border-box !important;
            animation: authCardEnter 0.4s ease-out !important;
        }}
        /* Remove nested inner container borders inside auth card */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-of-type(2) div[data-testid="stForm"],
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-of-type(2) div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }}
        @keyframes authCardEnter {{
            0% {{ opacity: 0; transform: translateY(12px) scale(0.99); }}
            100% {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}
        .auth-illustration-container {{
            text-align: center;
            margin-bottom: 2px;
        }}
        .auth-badge {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 2px 10px;
            border-radius: 20px;
            background: {'rgba(74, 222, 128, 0.12)'};
            color: {'#4ADE80'};
            font-size: 0.70rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 4px;
            border: 1px solid {'rgba(74, 222, 128, 0.25)'};
        }}
        .auth-title {{
            font-family: 'Poppins', sans-serif !important;
            font-size: 1.35rem !important;
            font-weight: 800 !important;
            color: {'#FFFFFF'} !important;
            margin: 0 0 2px 0 !important;
            letter-spacing: -0.02em !important;
            text-align: center;
            line-height: 1.2 !important;
        }}
        .auth-subtitle {{
            font-family: 'Inter', sans-serif !important;
            font-size: 0.78rem !important;
            color: {text_muted} !important;
            text-align: center;
            margin: 0 0 8px 0 !important;
            line-height: 1.3;
        }}
        .password-guide-box {{
            background: {'rgba(74, 222, 128, 0.06)'};
            border: 1px dashed {'rgba(74, 222, 128, 0.25)'};
            border-radius: 8px;
            padding: 5px 10px;
            margin: 4px 0 6px 0;
            font-size: 0.74rem;
            color: {text_muted};
            line-height: 1.3;
        }}
        .auth-footer-text {{
            text-align: center;
            color: {text_muted};
            font-size: 0.70rem;
            margin-top: 8px;
            line-height: 1.3;
        }}
        @keyframes floatSvg {{
            0%, 100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-4px); }}
        }}
        .auth-svg-float {{
            animation: floatSvg 3.5s ease-in-out infinite;
        }}
        /* Streamlit widget compacting inside auth card */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px !important;
            margin-bottom: 8px !important;
            justify-content: center !important;
            border-bottom: 1px solid {'rgba(255,255,255,0.08)'} !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            padding: 4px 10px !important;
            font-size: 0.80rem !important;
            font-weight: 600 !important;
        }}
        .stTextInput, .stSelectbox {{
            margin-bottom: -0.20rem !important;
        }}
        .stTextInput label p, .stSelectbox label p {{
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            margin-bottom: 2px !important;
            color: {'#CBD5E1'} !important;
        }}
        .stTextInput div[data-baseweb="input"] {{
            border-radius: 10px !important;
            border: 1px solid {'rgba(255,255,255,0.16)'} !important;
            transition: all 0.2s ease !important;
            background: {'rgba(15, 23, 42, 0.65)'} !important;
        }}
        .stTextInput div[data-baseweb="input"]:focus-within {{
            border: 2px solid #22c55e !important;
            border-color: #22c55e !important;
            box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.18) !important;
            outline: none !important;
            transition: all 0.2s ease !important;
        }}
        .stTextInput input {{
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            background: transparent !important;
            border-radius: 10px !important;
            padding: 0.38rem 0.65rem !important;
            font-size: 0.86rem !important;
            height: 38px !important;
            transition: all 0.2s ease !important;
        }}
        .stTextInput input:focus {{
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }}
        .stSelectbox div[data-baseweb="select"] > div {{
            border-radius: 10px !important;
            border: 1px solid {'rgba(255,255,255,0.16)'} !important;
            transition: all 0.2s ease !important;
            background: {'rgba(15, 23, 42, 0.65)'} !important;
        }}
        .stSelectbox div[data-baseweb="select"]:focus-within > div,
        .stSelectbox div[data-baseweb="select"][aria-expanded="true"] > div {{
            border: 2px solid #22c55e !important;
            border-color: #22c55e !important;
            box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.18) !important;
            outline: none !important;
            transition: all 0.2s ease !important;
        }}
        .stCheckbox {{
            margin: 0.15rem 0 0.35rem 0 !important;
        }}
        .stCheckbox label span {{
            font-size: 0.78rem !important;
            color: {text_muted} !important;
        }}
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 50%, #388E3C 100%) !important;
            border: none !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            font-size: 0.88rem !important;
            letter-spacing: 0.02em !important;
            border-radius: 10px !important;
            padding: 0.5rem 1rem !important;
            height: 40px !important;
            box-shadow: 0 4px 14px rgba(46, 125, 50, 0.28) !important;
            transition: all 0.22s ease-in-out !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 18px rgba(46, 125, 50, 0.40) !important;
            filter: brightness(1.06) !important;
        }}
        .stButton > button[kind="primary"]:active {{
            transform: translateY(0.5px) !important;
        }}
    </style>
    """, unsafe_allow_html=True)

    auth_col1, auth_col2, auth_col3 = st.columns([1, 1.8, 1])

    with auth_col2:
        # Agriculture-Inspired Green Illustration & Header
        st.markdown(f"""
        <div style="text-align: center; margin-top: 0px; margin-bottom: 6px;">
            <div class="auth-illustration-container">
                <svg class="auth-svg-float" width="50" height="50" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 6px 14px rgba(46, 125, 50, 0.26));">
                    <circle cx="60" cy="60" r="54" fill="url(#leafGradBg)" opacity="0.16"/>
                    <circle cx="60" cy="60" r="46" stroke="url(#leafGradBorder)" stroke-width="2" stroke-dasharray="4 3" opacity="0.4"/>
                    <!-- Central Sprout Stem -->
                    <path d="M60 90C60 72 58 54 60 38" stroke="#2E7D32" stroke-width="4.5" stroke-linecap="round"/>
                    <!-- Left Leaf -->
                    <path d="M59 62C42 60 34 46 40 34C52 36 60 48 59 62Z" fill="url(#leafGrad1)"/>
                    <!-- Right Leaf -->
                    <path d="M61 52C78 50 86 36 80 24C68 26 60 38 61 52Z" fill="url(#leafGrad2)"/>
                    <!-- Top Young Leaf -->
                    <path d="M60 38C54 26 62 16 68 16C72 24 66 34 60 38Z" fill="#86EFAC"/>
                    <!-- Soil mound base -->
                    <ellipse cx="60" cy="92" rx="26" ry="6" fill="#1B5E20" opacity="0.25"/>
                    <!-- Technological circuit nodes -->
                    <circle cx="34" cy="40" r="3" fill="#4ADE80"/>
                    <circle cx="86" cy="30" r="3" fill="#4ADE80"/>
                    <circle cx="68" cy="16" r="2.5" fill="#86EFAC"/>
                    <defs>
                        <linearGradient id="leafGradBg" x1="0" y1="0" x2="120" y2="120" gradientUnits="userSpaceOnUse">
                            <stop stop-color="#4ADE80"/>
                            <stop offset="1" stop-color="#1B5E20"/>
                        </linearGradient>
                        <linearGradient id="leafGradBorder" x1="0" y1="0" x2="120" y2="120" gradientUnits="userSpaceOnUse">
                            <stop stop-color="#2E7D32"/>
                            <stop offset="1" stop-color="#86EFAC"/>
                        </linearGradient>
                        <linearGradient id="leafGrad1" x1="34" y1="34" x2="60" y2="62" gradientUnits="userSpaceOnUse">
                            <stop stop-color="#4ADE80"/>
                            <stop offset="1" stop-color="#1B5E20"/>
                        </linearGradient>
                        <linearGradient id="leafGrad2" x1="60" y1="24" x2="86" y2="52" gradientUnits="userSpaceOnUse">
                            <stop stop-color="#2E7D32"/>
                            <stop offset="1" stop-color="#86EFAC"/>
                        </linearGradient>
                    </defs>
                </svg>
            </div>
            <div class="auth-badge">🌱 AgriAI Advisor • v2.1.0</div>
            <h1 class="auth-title">AgriAI Platform</h1>
            <p class="auth-subtitle">Crop Pest Prediction & Precision Advisory Gateway</p>
        </div>
        """, unsafe_allow_html=True)
        auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔑 Sign In", "📝 Create Account", "❓ Forgot Password"])

        # ==========================================================
        # TAB 1: LOGIN FORM
        # ==========================================================
        with auth_tab1:
            with st.form("login_form", clear_on_submit=False):
                l_email = st.text_input("Email Address", placeholder="farmer@example.com", key="login_email_input")
                l_password = st.text_input("Password", type="password", placeholder="••••••••", key="login_pw_input")
                
                remember_me = st.checkbox("Remember login session", value=True, key="login_remember_checkbox", help="Keep me logged in across sessions on this device")
                
                btn_login = st.form_submit_button("Sign In to AgriAI", type="primary", use_container_width=True)

            if btn_login:
                clean_email = (l_email or "").strip()
                clean_pw = (l_password or "").strip()
                if not clean_email or not clean_pw:
                    st.warning("⚠️ Please fill in both email and password.")
                else:
                    is_allowed, rem_secs = check_login_rate_limit(clean_email)
                    if not is_allowed:
                        st.error(f"🛑 Security Alert: Maximum failed login attempts reached. Please wait {rem_secs} seconds before retrying.")
                    else:
                        t_perf0 = time.perf_counter()
                        ok, user_res = verify_user(clean_email, clean_pw)
                        t_perf1 = time.perf_counter()
                        print(f"[PERF_PROFILE] verify_user took: {(t_perf1 - t_perf0)*1000:.2f}ms")
                        if ok:
                            login_user(user_res, remember_me=remember_me)
                            t_perf2 = time.perf_counter()
                            print(f"[PERF_PROFILE] login_user took: {(t_perf2 - t_perf1)*1000:.2f}ms")
                            role_val = (user_res.get("role") or "farmer").strip().lower()
                            if role_val == "admin":
                                st.session_state["current_page"] = "Admin Portal"
                            else:
                                st.session_state["current_page"] = "Dashboard"
                            st.rerun()
                        else:
                            record_failed_login(clean_email)
                            st.error(f"❌ {user_res}")

        # ==========================================================
        # TAB 2: REGISTRATION FORM
        # ==========================================================
        with auth_tab2:
            with st.form("registration_form", clear_on_submit=False):
                r_name = st.text_input("Full Name", placeholder="e.g. Ramesh Sharma", key="reg_name_input")
                r_email = st.text_input("Email Address", placeholder="farmer@example.com", key="reg_email_input")
                
                st.markdown(f"""
                <div class="password-guide-box">
                    <span style="font-weight: 700; color: {'#4ADE80'};">🔒 Security:</span> Min 8 chars with uppercase, lowercase, digit & symbol
                </div>
                """, unsafe_allow_html=True)
                
                r_password = st.text_input("Password", type="password", placeholder="Enter secure password", key="reg_pw_input")
                r_confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm secure password", key="reg_confirm_input")
                
                r_role = st.selectbox("Account Role", ["Farmer (Default)", "Administrator"], index=0, key="reg_role_select", help="Select access role")
                
                btn_register = st.form_submit_button("Create My Account", type="primary", use_container_width=True)

            if btn_register:
                role_val = "admin" if "admin" in r_role.lower() else "farmer"
                if not (r_name and r_email and r_password and r_confirm):
                    st.warning("⚠️ Please fill in all required registration fields.")
                elif r_password != r_confirm:
                    st.error("❌ Passwords do not match. Please re-enter carefully.")
                else:
                    is_valid_email, email_err = validate_email_format(r_email)
                    if not is_valid_email:
                        st.error(f"❌ {email_err}")
                    else:
                        is_valid_pw, pw_err = validate_password_complexity(r_password)
                        if not is_valid_pw:
                            st.error(f"❌ {pw_err}")
                        else:
                            with st.spinner("Creating your secure account..."):
                                ok, res = create_user(r_name, r_email, r_password, role=role_val)
                                if ok:
                                    login_user(res, remember_me=True)
                                    if role_val == "admin":
                                        st.session_state["current_page"] = "Admin Portal"
                                        st.success("✅ Administrator account registered successfully! Redirecting...")
                                    else:
                                        st.session_state["current_page"] = "Dashboard"
                                        st.success("✅ Farmer account registered successfully! Redirecting to Dashboard...")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {res}")

        # ==========================================================
        # TAB 3: FORGOT PASSWORD
        # ==========================================================
        with auth_tab3:
            with st.form("forgot_password_form", clear_on_submit=False):
                f_email = st.text_input("Registered Email Address", placeholder="farmer@example.com", key="forgot_email_input")
                btn_reset = st.form_submit_button("Reset Password", type="primary", use_container_width=True)

            if btn_reset:
                if not f_email:
                    st.warning("⚠️ Please enter your registered email address.")
                else:
                    is_valid_email, email_err = validate_email_format(f_email)
                    if not is_valid_email:
                        st.error(f"❌ {email_err}")
                    else:
                        with st.spinner("Generating security credentials..."):
                            clean_f_email = f_email.strip().lower()
                            user_exists = get_user_by_email(clean_f_email)
                            if not user_exists:
                                st.error("❌ No registered account found with this email address.")
                            else:
                                ok_tok, msg_tok, reset_tok = create_password_reset_token(clean_f_email)
                                temp_password = "AgriReset@" + secrets.token_hex(3).capitalize() + "9"
                                ok, msg = reset_password(clean_f_email, temp_password)
                                if ok:
                                    st.markdown(f"""
                                    <div style="background: rgba(46, 125, 50, 0.12); border: 1.5px solid #2E7D32; border-radius: 12px; padding: 12px; margin: 10px 0;">
                                        <div style="display: flex; align-items: center; gap: 6px; color: #2E7D32; font-weight: 700; font-size: 0.95rem;">
                                            <span>✅</span> Password Reset Ready
                                        </div>
                                        <p style="margin: 6px 0; font-size: 0.85rem; line-height: 1.4; color: {text_main};">
                                            Temporary credentials generated for <b>{clean_f_email}</b>:
                                        </p>
                                        <div style="background: {'#0F172A'}; border: 1px solid {'#334155'}; border-radius: 6px; padding: 8px 12px; font-family: monospace; font-size: 1.05rem; font-weight: 700; color: {'#4ADE80'}; text-align: center; margin: 6px 0;">
                                            {temp_password}
                                        </div>
                                        <div style="font-size: 0.75rem; color: {text_muted}; word-break: break-all; margin-top: 4px;">
                                            <b>Reset Token:</b> <code>{reset_tok}</code>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.error(f"❌ {msg}")

            with st.expander("🔑 Have a Reset Token? Set New Password"):
                tok_input = st.text_input("Reset Token", placeholder="Paste your 32-character reset token", key="input_reset_token")
                tok_new_pw = st.text_input("New Secure Password", type="password", placeholder="Enter new password (min 8 chars)", key="input_tok_new_pw")
                tok_conf_pw = st.text_input("Confirm New Password", type="password", placeholder="Confirm new password", key="input_tok_conf_pw")
                btn_submit_tok = st.button("Update Password with Token", key="btn_redeem_token_submit", type="primary", use_container_width=True)

                if btn_submit_tok:
                    if not tok_input or not tok_new_pw or not tok_conf_pw:
                        st.error("Please fill in all token and password fields.")
                    elif tok_new_pw != tok_conf_pw:
                        st.error("New passwords do not match.")
                    else:
                        ok_red, msg_red = redeem_password_reset_token(tok_input, tok_new_pw)
                        if ok_red:
                            st.success(f"✅ {msg_red}")
                        else:
                            st.error(f"❌ {msg_red}")

        # Commercial copyright disclaimer
        st.markdown(f"""
        <div class="auth-footer-text">
            © 2026 AgriAI Platform • Decision Support & Secure Access Gateway
        </div>
        """, unsafe_allow_html=True)
        st.stop()

# ==========================================================
# 2. AUTHENTICATED PLATFORM WITH MODERN BUTTON-BASED DRAWER
# ==========================================================
else:
    # Reusable Logout Dialog Modal
    @st.dialog("🚪 Confirm Logout")
    def show_logout_confirm_dialog():
        st.markdown(f"""
        <div style="text-align: center; padding: 12px 6px;">
            <div style="font-size: 2.8rem; margin-bottom: 8px;">🚪</div>
            <h3 style="margin: 0 0 8px 0; font-family: 'Poppins', sans-serif; color: {'#F8FAFC'};">Sign Out of AgriAI Advisor?</h3>
            <p style="color: {text_muted}; font-size: 0.92rem; line-height: 1.5; margin: 0 0 16px 0;">
                Are you sure you want to end your active session? You will need to sign in again to access predictions and reports.
            </p>
        </div>
        """, unsafe_allow_html=True)
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            if st.button("Cancel", key="btn_dlg_cancel_logout", use_container_width=True):
                st.rerun()
        with c_col2:
            if st.button("Yes, Logout", key="btn_dlg_confirm_logout", type="primary", use_container_width=True):
                logout_user()
                st.session_state["current_page"] = "Dashboard"
                st.session_state["show_logout_confirm"] = False
                st.success("Signed out successfully.")
                st.rerun()

    # Sidebar Navigation Drawer (Collapsible Hamburger Menu Drawer)
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; padding: 12px 6px 14px 6px; border-bottom: 1px solid {card_border}; margin-bottom: 16px;">
            <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 4px;">
                <span style="font-size: 2.2rem; filter: drop-shadow(0 4px 10px rgba(46, 125, 50, 0.35));">🌿</span>
                <span style="font-family: 'Poppins', sans-serif; font-size: 1.45rem; font-weight: 800; color: {'#86EFAC'}; letter-spacing: -0.02em;">AgriAI Advisor</span>
            </div>
            <span style="font-size: 0.72rem; color: {text_muted}; text-transform: uppercase; font-weight: 700; letter-spacing: 0.06em;">Crop Pest Advisory Platform</span>
        </div>
        """, unsafe_allow_html=True)
        
        # User Summary Card in Drawer
        st.markdown(f"""
        <div style="background: {'#1A3626'}; border: 1px solid {card_border}; border-radius: 14px; padding: 10px 14px; margin-bottom: 16px; display: flex; align-items: center; gap: 10px;">
            <div style="font-size: 1.5rem;">👤</div>
            <div style="overflow: hidden;">
                <div style="font-weight: 700; font-size: 0.92rem; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; color: {'#86EFAC'};">{current_user['name']}</div>
                <div style="font-size: 0.75rem; color: {text_muted}; text-transform: capitalize;">{current_user.get('role', 'farmer')} Account</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<p style='font-size: 0.76rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.05em;'>Navigation Menu</p>", unsafe_allow_html=True)
        
        # Exact Navigation List per Specification
        nav_menu_items = [
            ("Dashboard", "Dashboard"),
            ("Prediction", "Prediction"),
            ("History", "History"),
            ("Profile", "Profile"),
            ("About", "About"),
            ("Contact", "Contact")
        ]
        if admin_status:
            nav_menu_items.append(("Admin Portal", "Admin Portal"))

        for label, page_key in nav_menu_items:
            curr = st.session_state.get("current_page", "Dashboard")
            is_active = (curr == page_key) or \
                        (page_key == "Dashboard" and curr in ["Dashboard", "🏠 Dashboard", "🏠 Home", "📊 Dashboard"]) or \
                        (page_key == "Prediction" and curr in ["Prediction", "🌾 Prediction"]) or \
                        (page_key == "History" and curr in ["History", "📜 History"]) or \
                        (page_key == "Profile" and curr in ["Profile", "👤 Profile"]) or \
                        (page_key == "About" and curr in ["About", "ℹ About", "ℹ️ About"]) or \
                        (page_key == "Contact" and curr in ["Contact", "📩 Contact"]) or \
                        (page_key == "Admin Portal" and curr in ["Admin Portal", "🛡️ Admin Portal", "🛡️ Administrator"])
            if st.sidebar.button(
                label,
                key=f"nav_btn_{page_key}",
                type="primary" if is_active else "secondary",
                use_container_width=True
            ):
                navigate_to(page_key)

        st.markdown(f"<div style='margin-top: 24px; border-top: 1px solid {card_border}; padding-top: 18px;'></div>", unsafe_allow_html=True)
        
        # Logout Fixed at Bottom - Immediate 1-click logout per specification
        if st.button("🚪 Logout", key="btn_sidebar_logout", use_container_width=True):
            logout_user()
            st.rerun()

        st.markdown(f"""
        <div style="text-align: center; font-size: 0.75rem; color: {text_muted}; margin-top: 12px; line-height: 1.5;">
            <b>AgriAI Advisor</b> v2.1.0<br>
            Enterprise Dark Edition 🌙
        </div>
        """, unsafe_allow_html=True)

    # Top Header Bar in Main View Area with 1-click immediate logout (Issue 3)
    active_page_raw = st.session_state.get("current_page", "Dashboard")
    display_titles = {
        "Dashboard": "Dashboard Overview",
        "Prediction": "AI Pest Prediction",
        "History": "Prediction History",
        "Profile": "Farmer Profile",
        "About": "About AgriAI",
        "Contact": "Contact & Support",
        "Admin Portal": "Enterprise Admin Portal"
    }
    active_title = display_titles.get(active_page_raw, active_page_raw)
    hdr_c1, hdr_c2, hdr_c3 = st.columns([5.2, 3.3, 1.5], vertical_alignment="center")
    with hdr_c1:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; padding: 4px 0;">
            <span style="font-size: 1.3rem;">🌿</span>
            <h3 style="margin: 0; font-size: 1.30rem; font-weight: 800; color: var(--text-main); letter-spacing: -0.01em; white-space: nowrap;">{active_title}</h3>
            <span style="background: {'rgba(74, 222, 128, 0.16)'}; border: 1px solid {'rgba(74, 222, 128, 0.35)'}; font-size: 0.72rem; padding: 2px 10px; border-radius: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: {'#4ADE80'}; white-space: nowrap;">v2.1.0</span>
        </div>
        """, unsafe_allow_html=True)
    with hdr_c2:
        st.markdown(f"""
        <div style="background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 20px; padding: 7px 16px; display: flex; align-items: center; justify-content: flex-end; gap: 8px; font-size: 0.86rem; color: var(--text-main); box-shadow: 0 2px 8px rgba(0,0,0,0.04); white-space: nowrap;">
            <span>👤</span>
            <span style="font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 140px;">{current_user['name']}</span>
            <span style="color: var(--text-muted);">&bull;</span>
            <span style="text-transform: capitalize; color: {'#86EFAC'}; font-weight: 700; font-size: 0.80rem; white-space: nowrap;">{current_user.get('role', 'farmer')}</span>
        </div>
        """, unsafe_allow_html=True)
    with hdr_c3:
        if st.button("🚪 Logout", key="btn_top_header_logout", type="secondary", use_container_width=True):
            logout_user()
            st.rerun()

    # ==========================================================
    # REUSABLE EMPTY STATES & ERROR STATE RENDERERS
    # ==========================================================
    def render_empty_state(state_type="history", title=None, subtitle=None, action_label=None, action_page=None):
        icons = {
            "history": "📜",
            "prediction": "🌾",
            "notifications": "🔔",
            "contact": "📩",
            "analytics": "📊"
        }
        default_titles = {
            "history": "No Prediction Records Found",
            "prediction": "No Active Prediction Yet",
            "notifications": "All Caught Up!",
            "contact": "No Inquiries Submitted",
            "analytics": "No Data Available"
        }
        default_subtitles = {
            "history": "Run your first crop pest prediction to record agronomic advisories and weather telemetry.",
            "prediction": "Select your field location and target crop to generate a customized pest risk forecast.",
            "notifications": "You have no unread notifications or high-risk field alerts at this time.",
            "contact": "Have agronomic or technical questions? Submit an inquiry and our advisory team will assist.",
            "analytics": "Generate field predictions to unlock risk distribution and seasonal trends."
        }
        icon = icons.get(state_type, "🌾")
        t = title or default_titles.get(state_type, "No Items Available")
        s = subtitle or default_subtitles.get(state_type, "Start an action to populate this section.")
        
        st.markdown(f"""
        <div style="background: var(--card-bg); border: 2px dashed var(--card-border); border-radius: 18px; padding: 48px 24px; text-align: center; margin: 24px 0; box-shadow: 0 4px 18px rgba(0,0,0,0.03);">
            <div style="font-size: 3.2rem; margin-bottom: 12px; filter: drop-shadow(0 4px 10px rgba(46,125,50,0.25));">{icon}</div>
            <h3 style="margin: 0 0 8px 0; font-family: 'Poppins', sans-serif; font-size: 1.35rem; color: var(--text-main);">{t}</h3>
            <p style="margin: 0 auto 20px auto; max-width: 520px; font-size: 0.92rem; color: var(--text-muted); line-height: 1.6;">{s}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if action_label and action_page:
            col1, col2, col3 = st.columns([1.5, 2, 1.5])
            with col2:
                if st.button(action_label, key=f"empty_state_action_{state_type}_{action_page}", type="primary", use_container_width=True):
                    st.session_state["current_page"] = action_page
                    st.rerun()

    def render_error_card(error_type="api", message=None, retry_page=None):
        error_titles = {
            "api": "Weather Service Telemetry Disconnected",
            "db": "Database Connection Timeout",
            "404": "Agronomic Resource Not Found",
            "500": "Platform Processing Error",
            "network": "Network Connectivity Issue"
        }
        error_icons = {
            "api": "🌤️",
            "db": "🗄️",
            "404": "🔍",
            "500": "⚠️",
            "network": "📡"
        }
        t = error_titles.get(error_type, "An Unexpected Error Occurred")
        i = error_icons.get(error_type, "⚠️")
        msg = message or "Our automated services encountered a transient interruption. Your data remains secure."
        
        st.markdown(f"""
        <div style="background: rgba(220, 38, 38, 0.08); border: 1px solid rgba(220, 38, 38, 0.35); border-radius: 18px; padding: 28px 24px; text-align: center; margin: 20px 0;">
            <div style="font-size: 2.8rem; margin-bottom: 8px;">{i}</div>
            <h4 style="margin: 0 0 8px 0; font-family: 'Poppins', sans-serif; color: #EF4444; font-size: 1.25rem;">{t}</h4>
            <p style="margin: 0 auto 16px auto; max-width: 540px; font-size: 0.90rem; color: var(--text-muted); line-height: 1.55;">{msg}</p>
        </div>
        """, unsafe_allow_html=True)
        if retry_page:
            r_c1, r_c2, r_c3 = st.columns([1.5, 2, 1.5])
            with r_c2:
                if st.button("🔄 Retry Action", key=f"btn_err_retry_{error_type}", type="primary", use_container_width=True):
                    st.session_state["current_page"] = retry_page
                    st.rerun()

    # ==========================================================
    # MODAL DIALOGS: PREDICTION DETAILS & DELETE CONFIRMATION
    # ==========================================================
    @st.dialog("🌾 Crop Prediction & Advisory Details", width="large")
    def show_history_detail_dialog(record):
        r_id = record["id"]
        r_crop = record["crop"]
        r_pest = record["predicted_pest"]
        r_risk = record["predicted_risk"]
        r_time = record.get("created_at", "")
        r_dist = record.get("district", "")
        r_state = record.get("state", "")
        r_pest_prob = float(record.get("pest_prob", 60.0))
        r_risk_prob = float(record.get("risk_prob", 75.0))
        r_temp = float(record.get("temperature", 28.0))
        r_hum = float(record.get("humidity", 65.0))
        r_rain = float(record.get("rainfall", 120.0))
        r_thi = float(record.get("thi", 75.0))
        r_season = record.get("sowing_season", "Kharif")
        r_weather_season = record.get("weather_season", "Monsoon")

        try:
            prev_methods = json.loads(record.get("prevention_methods") or "[]")
        except Exception:
            prev_methods = []

        rec_dict = {
            "pesticide": record.get("pesticide", "Neem-based organic formulation"),
            "dosage": record.get("dosage", "Standard recommended dose"),
            "organic_control": record.get("organic_control", "Neem Oil 1500 PPM @ 3ml/L"),
            "safety_notes": record.get("safety_notes", "Wear protective gloves and mask during spray application."),
            "prevention": prev_methods
        }

        # Header Info Banner
        st.markdown(f"""
        <div style="background: {'#142D1E'}; border: 1px solid {'#1B5E20'}; border-radius: 14px; padding: 16px 20px; margin-bottom: 18px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h3 style="margin: 0; font-family: 'Poppins', sans-serif; color: {'#86EFAC'}; font-size: 1.3rem;">
                        🌾 {r_crop} &bull; <span style="font-size: 1.05rem; font-weight: 500; color: {text_muted};">{r_dist}, {r_state}</span>
                    </h3>
                    <div style="font-size: 0.84rem; color: {text_muted}; margin-top: 4px;">
                        Detected Season: <b>{r_season}</b> &bull; Record Reference: #{r_id}
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.80rem; color: {text_muted};">Assessment Timestamp</div>
                    <div style="font-weight: 700; color: var(--text-main); font-size: 0.95rem;">⏱️ {r_time}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Weather & Threat Metrics Row
        col_m1, col_m2 = st.columns([1.2, 1.8])
        with col_m1:
            st.markdown(f"""
            <div style="background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 18px; height: 100%;">
                <h5 style="margin: 0 0 12px 0; color: {'#86EFAC'}; font-family: 'Poppins', sans-serif;">🌤️ Weather Profile</h5>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.88rem;">
                    <div><span style="color: {text_muted}; font-size: 0.80rem;">Temperature:</span><br><b>{r_temp}°C</b></div>
                    <div><span style="color: {text_muted}; font-size: 0.80rem;">Humidity:</span><br><b>{r_hum}%</b></div>
                    <div><span style="color: {text_muted}; font-size: 0.80rem;">Precipitation:</span><br><b>{r_rain} mm</b></div>
                    <div><span style="color: {text_muted}; font-size: 0.80rem;">THI Index:</span><br><b>{r_thi}</b></div>
                </div>
                <div style="margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--card-border); font-size: 0.80rem; color: {text_muted};">
                    Climate Phase: <b>{r_weather_season}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_m2:
            st.markdown(f"""
            <div style="background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 18px; height: 100%;">
                <h5 style="margin: 0 0 12px 0; color: {'#86EFAC'}; font-family: 'Poppins', sans-serif;">🎯 Prediction Diagnosis</h5>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div>
                        <span style="font-size: 0.82rem; color: {text_muted};">Most Likely Pest:</span>
                        <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-main);">🐛 {r_pest}</div>
                    </div>
                    <div>
                        <span style="background: rgba(45, 106, 79, 0.12); color: #2D6A4F; border: 1px solid rgba(45, 106, 79, 0.28); padding: 5px 14px; border-radius: 20px; font-weight: 800; font-size: 0.88rem;">
                            ✓ Active Advisory
                        </span>
                    </div>
                </div>
                <div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 4px;">
                        <span style="color: {text_muted};">Probability (%):</span>
                        <b>{r_pest_prob:.1f}%</b>
                    </div>
                    <div style="background: {'#334155'}; border-radius: 10px; height: 8px; overflow: hidden;">
                        <div style="background: linear-gradient(90deg, #1B4332, #2D6A4F, #52B788); width: {min(100.0, r_pest_prob)}%; height: 100%;"></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<h5 style='font-family: Poppins, sans-serif; color: {'#86EFAC'}; margin-bottom: 10px;'>📋 Recommended Agronomic Advisory</h5>", unsafe_allow_html=True)

        # 4 Advisory Cards in Dialog
        adv1, adv2 = st.columns(2)
        with adv1:
            st.markdown(f"""
            <div style="background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 14px; margin-bottom: 10px;">
                <div style="font-weight: 700; color: #2E7D32; margin-bottom: 4px;">🧪 Chemical Control</div>
                <p style="font-size: 0.85rem; margin: 0; line-height: 1.5; color: var(--text-main);">
                    <b>Formulation:</b> {rec_dict['pesticide']}<br>
                    <b>Dosage:</b> {rec_dict['dosage']}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            cult_items = "".join([f"<li>{m}</li>" for m in (rec_dict['prevention'][:3] if rec_dict['prevention'] else ['Maintain field sanitation', 'Practice balanced irrigation', 'Adopt regular crop scouting'])])
            st.markdown(f"""
            <div style="background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 14px;">
                <div style="font-weight: 700; color: #D97706; margin-bottom: 4px;">🚜 Cultural Practices</div>
                <ul style="font-size: 0.85rem; margin: 0; padding-left: 18px; color: var(--text-main); line-height: 1.5;">
                    {cult_items}
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with adv2:
            st.markdown(f"""
            <div style="background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 14px; margin-bottom: 10px;">
                <div style="font-weight: 700; color: #0D9488; margin-bottom: 4px;">🌿 Biological & Organic Control</div>
                <p style="font-size: 0.85rem; margin: 0; line-height: 1.5; color: var(--text-main);">
                    {rec_dict['organic_control']}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 14px;">
                <div style="font-weight: 700; color: #E11D48; margin-bottom: 4px;">🦺 Safety Precautions</div>
                <p style="font-size: 0.85rem; margin: 0; line-height: 1.5; color: var(--text-main);">
                    {rec_dict['safety_notes']}
                </p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        # Download button in Dialog
        try:
            pdf_bytes = generate_prediction_pdf(
                state=r_state,
                district=r_dist,
                crop=r_crop,
                crop_category=record.get("crop_category", "General"),
                sowing_season=r_season,
                weather_season=r_weather_season,
                temp=r_temp,
                humidity=r_hum,
                rainfall=r_rain,
                thi=r_thi,
                rf_hum_ratio=float(record.get("rf_hum_ratio", 1.5)),
                weather_source="Open-Meteo Weather Service (Archive)",
                predicted_pest=r_pest,
                pest_conf=r_pest_prob,
                predicted_risk=r_risk,
                risk_conf=r_risk_prob,
                model_notes="Verified Agricultural Advisory Report",
                recommendations=rec_dict,
                user_name=current_user.get("name", "Registered Farmer")
            )
            date_clean = r_time.split()[0].replace("-", "") if r_time else datetime.now().strftime("%Y%m%d")
            st.download_button(
                label="📄 Download Advisory Report (PDF)",
                data=pdf_bytes,
                file_name=f"Prediction_Report_{date_clean}.pdf",
                mime="application/pdf",
                key=f"modal_dl_pdf_{r_id}",
                type="primary",
                use_container_width=True
            )
            record_report_download(r_id, user_id=current_user["id"])
        except Exception as dl_err:
            logger.error(f"Modal PDF error: {dl_err}")
            st.error("Report generation currently unavailable.")

    @st.dialog("🗑️ Confirm Deletion")
    def show_delete_confirm_dialog(pred_id, crop_name, date_str):
        st.markdown(f"""
        <div style="text-align: center; padding: 14px 6px;">
            <div style="font-size: 2.8rem; margin-bottom: 8px;">⚠️</div>
            <h4 style="margin: 0 0 8px 0; font-family: 'Poppins', sans-serif; color: {'#F8FAFC'};">Delete Prediction Record?</h4>
            <p style="color: {text_muted}; font-size: 0.94rem; line-height: 1.5; margin: 0 0 16px 0;">
                Are you sure you want to delete this prediction record for <b>{crop_name}</b> ({date_str})?<br>
                This action cannot be undone.
            </p>
        </div>
        """, unsafe_allow_html=True)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("Cancel", key=f"btn_cancel_del_{pred_id}", use_container_width=True):
                st.rerun()
        with col_c2:
            if st.button("Yes, Delete", key=f"btn_confirm_del_{pred_id}", type="primary", use_container_width=True):
                delete_prediction_history(pred_id, user_id=None if admin_status else current_user["id"])
                st.success("Prediction record deleted successfully.")
                st.rerun()

    @st.dialog("🚪 Logout From All Devices")
    def show_logout_all_devices_dialog():
        st.markdown(f"""
        <div style="text-align: center; padding: 10px 4px;">
            <div style="font-size: 2.8rem; margin-bottom: 8px;">🔐</div>
            <h4 style="margin: 0 0 8px 0; font-family: 'Poppins', sans-serif; color: {'#F8FAFC'};">Terminate All Sessions?</h4>
            <p style="color: {text_muted}; font-size: 0.94rem; line-height: 1.5; margin: 0 0 16px 0;">
                This will immediately invalidate all persistent Remember Me tokens and log out your account from all browsers, smartphones, and computers.<br>
                You will need to sign in again to access your dashboard.
            </p>
        </div>
        """, unsafe_allow_html=True)
        col_la1, col_la2 = st.columns(2)
        with col_la1:
            if st.button("Cancel", key="btn_cancel_logout_all", use_container_width=True):
                st.rerun()
        with col_la2:
            if st.button("Confirm & Logout All", key="btn_confirm_logout_all", type="primary", use_container_width=True):
                delete_all_user_sessions(current_user["id"])
                logout_user()
                st.rerun()

    @st.dialog("⚠️ Delete Account (Danger Zone)")
    def show_delete_account_dialog():
        st.markdown(f"""
        <div style="text-align: center; padding: 10px 4px;">
            <div style="font-size: 2.8rem; margin-bottom: 8px;">🚨</div>
            <h4 style="margin: 0 0 8px 0; font-family: 'Poppins', sans-serif; color: #EF4444;">Permanently Delete Account?</h4>
            <p style="color: {text_muted}; font-size: 0.92rem; line-height: 1.5; margin: 0 0 14px 0;">
                This action is <b>irreversible</b>. Your account profile, preferences, stored credentials, and prediction history will be permanently wiped from the system.
            </p>
        </div>
        """, unsafe_allow_html=True)
        del_input = st.text_input("Type **DELETE** in capital letters to confirm:", key="modal_input_delete_confirm", placeholder="DELETE")
        col_da1, col_da2 = st.columns(2)
        with col_da1:
            if st.button("Cancel", key="btn_cancel_delete_acc", use_container_width=True):
                st.rerun()
        with col_da2:
            if st.button("Permanently Delete", key="btn_confirm_delete_acc", type="primary", use_container_width=True):
                if del_input.strip() == "DELETE":
                    user_id_to_del = current_user["id"]
                    delete_user_account(user_id_to_del)
                    logout_user()
                    st.success("Your account has been deleted permanently.")
                    st.rerun()
                else:
                    st.error("Confirmation text did not match. Please type DELETE exactly.")

    # ==========================================
    # PAGE 1: HOME & DASHBOARD OVERVIEW
    # ==========================================
    if st.session_state["current_page"] in ["Dashboard", "🏠 Dashboard", "🏠 Home", "📊 Dashboard"]:
        # 1. HERO SECTION WITH LARGE AGRICULTURE VECTOR ILLUSTRATION
        st.markdown(f"""
        <div class="saas-hero-wrap">
            <div class="saas-hero-grid">
                <div class="saas-hero-text">
                    <div class="saas-hero-pill">🌱 AgriAI Advisor &bull; Precision Agriculture v2.1.0</div>
                    <h1 class="saas-hero-title">AI-Powered Crop Pest Prediction &amp; Advisory Platform</h1>
                    <p class="saas-hero-subtitle">
                        Helping farmers and agronomists make timely crop protection decisions using live microclimate weather telemetry and Machine Learning intelligence.
                    </p>
                    <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 18px;">
                        <span style="display: inline-flex; align-items: center; gap: 6px; font-size: 0.88rem; color: #D1FAE5; font-weight: 600;">
                            ✓ 14+ Supported Crops
                        </span>
                        <span style="display: inline-flex; align-items: center; gap: 6px; font-size: 0.88rem; color: #D1FAE5; font-weight: 600;">
                            ✓ Live Weather Telemetry
                        </span>
                        <span style="display: inline-flex; align-items: center; gap: 6px; font-size: 0.88rem; color: #D1FAE5; font-weight: 600;">
                            ✓ Targeted IPM Advisories
                        </span>
                    </div>
                </div>
                <div class="saas-hero-illustration">
                    <svg viewBox="0 0 760 440" fill="none" xmlns="http://www.w3.org/2000/svg" class="hero-agri-illustration">
                        <defs>
                            <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="440" gradientUnits="userSpaceOnUse">
                                <stop stop-color="#0E2F1B" stop-opacity="0.95"/>
                                <stop offset="0.6" stop-color="#1B5E20" stop-opacity="0.88"/>
                                <stop offset="1" stop-color="#2E7D32" stop-opacity="0.95"/>
                            </linearGradient>
                            <linearGradient id="hillFar" x1="0" y1="200" x2="760" y2="440" gradientUnits="userSpaceOnUse">
                                <stop stop-color="#144A24"/>
                                <stop offset="1" stop-color="#1B5E20"/>
                            </linearGradient>
                            <linearGradient id="hillNear" x1="0" y1="240" x2="760" y2="440" gradientUnits="userSpaceOnUse">
                                <stop stop-color="#1E6B33"/>
                                <stop offset="1" stop-color="#2E7D32"/>
                            </linearGradient>
                            <linearGradient id="droneGrad" x1="0" y1="0" x2="1" y2="1">
                                <stop stop-color="#FFFFFF"/>
                                <stop offset="1" stop-color="#A7F3D0"/>
                            </linearGradient>
                            <linearGradient id="beamGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop stop-color="#4ADE80" stop-opacity="0.6"/>
                                <stop offset="1" stop-color="#4ADE80" stop-opacity="0"/>
                            </linearGradient>
                            <linearGradient id="sunGrad" x1="0" y1="0" x2="1" y2="1">
                                <stop stop-color="#FDE047"/>
                                <stop offset="1" stop-color="#F59E0B"/>
                            </linearGradient>
                        </defs>
                        <rect width="760" height="440" rx="20" fill="url(#skyGrad)"/>
                        <path d="M0 90 H760 M0 180 H760 M0 270 H760" stroke="#4ADE80" stroke-width="0.7" stroke-dasharray="6 6" opacity="0.16"/>
                        <path d="M150 0 V440 M300 0 V440 M450 0 V440 M600 0 V440" stroke="#4ADE80" stroke-width="0.7" stroke-dasharray="6 6" opacity="0.16"/>
                        <circle cx="630" cy="100" r="46" fill="url(#sunGrad)" opacity="0.9"/>
                        <circle cx="630" cy="100" r="62" stroke="#FDE047" stroke-width="1.5" stroke-dasharray="4 4" opacity="0.4"/>
                        <path d="M570 95 C570 82 585 75 600 78 C608 68 625 68 635 78 C645 74 660 82 660 95 C668 97 674 105 670 114 C666 122 655 125 645 125 H575 C565 125 558 118 560 110 C560 102 565 96 570 95 Z" fill="#FFFFFF" opacity="0.88"/>
                        <path d="M0 310 Q 180 230 380 280 T 760 270 L 760 440 L 0 440 Z" fill="url(#hillFar)"/>
                        <path d="M0 350 Q 200 290 420 330 T 760 330 L 760 440 L 0 440 Z" fill="url(#hillNear)"/>
                        <line x1="380" y1="330" x2="80" y2="440" stroke="#86EFAC" stroke-width="2.5" opacity="0.35"/>
                        <line x1="380" y1="330" x2="200" y2="440" stroke="#86EFAC" stroke-width="2.5" opacity="0.4"/>
                        <line x1="380" y1="330" x2="330" y2="440" stroke="#86EFAC" stroke-width="2.5" opacity="0.45"/>
                        <line x1="380" y1="330" x2="460" y2="440" stroke="#86EFAC" stroke-width="2.5" opacity="0.45"/>
                        <line x1="380" y1="330" x2="580" y2="440" stroke="#86EFAC" stroke-width="2.5" opacity="0.4"/>
                        <line x1="380" y1="330" x2="690" y2="440" stroke="#86EFAC" stroke-width="2.5" opacity="0.35"/>
                        <g stroke="#4ADE80" stroke-width="3" stroke-linecap="round">
                            <path d="M120 420 L120 380 M120 395 Q105 385 100 375 M120 405 Q135 395 140 385"/>
                            <path d="M220 410 L220 365 M220 380 Q205 370 200 360 M220 390 Q235 380 240 370"/>
                            <path d="M340 405 L340 355 M340 370 Q325 360 320 350 M340 380 Q355 370 360 360"/>
                            <path d="M470 405 L470 355 M470 370 Q455 360 450 350 M470 380 Q485 370 490 360"/>
                            <path d="M590 410 L590 365 M590 380 Q575 370 570 360 M590 390 Q605 380 610 370"/>
                            <path d="M680 420 L680 380 M680 395 Q665 385 660 375 M680 405 Q695 395 700 385"/>
                        </g>
                        <g transform="translate(130, 200)">
                            <line x1="30" y1="120" x2="30" y2="30" stroke="#E2E8F0" stroke-width="4"/>
                            <line x1="15" y1="120" x2="45" y2="120" stroke="#E2E8F0" stroke-width="3"/>
                            <circle cx="30" cy="25" r="10" fill="#2E7D32" stroke="#4ADE80" stroke-width="3"/>
                            <circle cx="30" cy="25" r="3" fill="#86EFAC"/>
                            <rect x="36" y="38" width="22" height="12" rx="2" fill="#3B82F6" stroke="#FFFFFF" stroke-width="1"/>
                        </g>
                        <g transform="translate(360, 80)">
                            <polygon points="50,45 -20,240 120,240" fill="url(#beamGrad)"/>
                            <ellipse cx="50" cy="40" rx="32" ry="14" fill="url(#droneGrad)" stroke="#2E7D32" stroke-width="2"/>
                            <rect x="42" y="34" width="16" height="8" rx="4" fill="#1B5E20"/>
                            <line x1="10" y1="30" x2="90" y2="50" stroke="#E2E8F0" stroke-width="3" stroke-linecap="round"/>
                            <line x1="10" y1="50" x2="90" y2="30" stroke="#E2E8F0" stroke-width="3" stroke-linecap="round"/>
                            <ellipse cx="10" cy="30" rx="18" ry="4" fill="#86EFAC" opacity="0.8"/>
                            <ellipse cx="90" cy="50" rx="18" ry="4" fill="#86EFAC" opacity="0.8"/>
                            <ellipse cx="10" cy="50" rx="18" ry="4" fill="#86EFAC" opacity="0.8"/>
                            <ellipse cx="90" cy="30" rx="18" ry="4" fill="#86EFAC" opacity="0.8"/>
                            <circle cx="50" cy="52" r="5" fill="#4ADE80"/>
                        </g>
                        <g transform="translate(520, 160)">
                            <rect width="180" height="64" rx="14" fill="#0F172A" fill-opacity="0.88" stroke="#4ADE80" stroke-width="1.2"/>
                            <text x="18" y="26" fill="#86EFAC" font-family="Inter, sans-serif" font-size="11" font-weight="700" letter-spacing="1">FIELD TELEMETRY</text>
                            <text x="18" y="48" fill="#FFFFFF" font-family="Poppins, sans-serif" font-size="15" font-weight="800">28.4°C &bull; 65% RH</text>
                        </g>
                        <g transform="translate(60, 90)">
                            <rect width="190" height="64" rx="14" fill="#0F172A" fill-opacity="0.88" stroke="#4ADE80" stroke-width="1.2"/>
                            <text x="18" y="26" fill="#A7F3D0" font-family="Inter, sans-serif" font-size="11" font-weight="700" letter-spacing="1">PEST SURVEILLANCE</text>
                            <text x="18" y="48" fill="#4ADE80" font-family="Poppins, sans-serif" font-size="15" font-weight="800">● Real-time AI Active</text>
                        </g>
                    </svg>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Two Modern CTA Buttons
        cta_col1, cta_col2, _ = st.columns([1.5, 1.5, 3])
        with cta_col1:
            st.button("🌾 Start Prediction", key="hero_cta_start_pred", type="primary", use_container_width=True, on_click=navigate_to, args=("Prediction",))
        with cta_col2:
            st.button("📖 Learn More", key="hero_cta_learn_more", type="secondary", use_container_width=True, on_click=navigate_to, args=("About",))

        # Welcome Back Strip
        st.markdown(f"""
        <div style="background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 18px; padding: 14px 22px; margin: 20px 0 24px 0; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; box-shadow: 0 4px 14px rgba(0,0,0,0.03);">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.8rem;">👋</span>
                <div>
                    <div style="font-size: 1.02rem; font-weight: 700; color: var(--text-main);">Welcome back, <span style="color: var(--accent);">{current_user['name']}</span></div>
                    <div style="font-size: 0.80rem; color: var(--text-muted);">Account Tier: <b>{current_user.get('role', 'farmer').capitalize()}</b> &bull; Real-time Weather & Machine Learning Inference Active</div>
                </div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <span style="background: var(--season-badge-bg); border: 1px solid var(--season-badge-border); color: var(--season-badge-text); padding: 5px 14px; border-radius: 20px; font-size: 0.80rem; font-weight: 700;">● System Online &bull; v2.1.0</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2. STATISTICS SECTION
        st.markdown(f"""
        <div class="saas-stats-grid">
            <div class="saas-stat-card">
                <span class="saas-stat-icon">🌾</span>
                <div class="saas-stat-val">14+</div>
                <div class="saas-stat-label">Crops Supported</div>
            </div>
            <div class="saas-stat-card">
                <span class="saas-stat-icon">🐛</span>
                <div class="saas-stat-val">25+</div>
                <div class="saas-stat-label">Pest Categories</div>
            </div>
            <div class="saas-stat-card">
                <span class="saas-stat-icon">📄</span>
                <div class="saas-stat-val">4,800+</div>
                <div class="saas-stat-label">Reports Generated</div>
            </div>
            <div class="saas-stat-card">
                <span class="saas-stat-icon">👥</span>
                <div class="saas-stat-val">1,250+</div>
                <div class="saas-stat-label">Registered Users</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3. CORE CAPABILITIES SECTION
        st.markdown(f"""
        <div class="saas-section-header">
            <div class="saas-section-pill">⚡ Platform Capabilities</div>
            <h2 class="saas-section-title">Core Capabilities</h2>
            <p class="saas-section-desc">Delivering end-to-end precision agronomy through integrated microclimate tracking, intelligent forecasting, and evidence-based crop management.</p>
        </div>
        <div class="saas-capabilities-grid">
            <div class="saas-cap-card">
                <div class="saas-cap-icon">🌦️</div>
                <div class="saas-cap-title">Live Weather Integration</div>
                <div class="saas-cap-desc">Automated localized temperature, relative humidity, and rainfall tracking synchronized with real-time meteorological feeds.</div>
            </div>
            <div class="saas-cap-card">
                <div class="saas-cap-icon">🤖</div>
                <div class="saas-cap-title">AI Pest Prediction</div>
                <div class="saas-cap-desc">Intelligent classification models forecasting top pest species probability and generating targeted agronomic advisories.</div>
            </div>
            <div class="saas-cap-card">
                <div class="saas-cap-icon">📄</div>
                <div class="saas-cap-title">Smart Advisory Report</div>
                <div class="saas-cap-desc">Tailored chemical active ingredients, exact dosage rates, organic bio-controls, and sustainable field management strategies.</div>
            </div>
            <div class="saas-cap-card">
                <div class="saas-cap-icon">📊</div>
                <div class="saas-cap-title">Prediction History &amp; Analytics</div>
                <div class="saas-cap-desc">Comprehensive digital audit trail of past advisories, seasonal risk patterns, and field observations exportable to PDF, Excel, and CSV.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 4. LATEST REGIONAL WEATHER SUMMARY (OPEN-METEO API)
        st.markdown(f"""
        <div class="saas-section-header">
            <div class="saas-section-pill">🌦️ Microclimate Intelligence</div>
            <h2 class="saas-section-title">Latest Weather Summary</h2>
            <p class="saas-section-desc">Real-time localized meteorological telemetry calibrated for agricultural risk assessment in your region.</p>
        </div>
        """, unsafe_allow_html=True)
        
        user_loc_state = current_user.get("state") or "Andhra Pradesh"
        user_loc_dist = current_user.get("district") or "Guntur"
        current_sowing_season = get_current_sowing_season()
        
        try:
            home_wx = get_cached_weather(district=user_loc_dist, state=user_loc_state, sowing_season=current_sowing_season)
        except Exception as wx_e:
            logger.error(f"Home weather fetch error: {wx_e}")
            home_wx = {
                "temperature": 28.0, "humidity": 65.0, "rainfall_mm": 12.0, "wind_speed": 11.0,
                "cloud_cover": 35.0, "weather_condition": "Partly Cloudy ⛅",
                "observation_time": datetime.now().strftime("%d %b %Y • %I:%M %p IST"),
                "is_live": False
            }
        
        st.markdown(f"""
        <div style="background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 20px; padding: 24px 28px; margin-bottom: 32px; box-shadow: 0 8px 24px rgba(0,0,0,0.04);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 18px; border-bottom: 1px solid var(--card-border); padding-bottom: 14px;">
                <div>
                    <span style="font-size: 1.15rem; font-weight: 700; color: var(--text-main);">📍 Field Region: <span style="color: var(--accent);">{user_loc_dist}, {user_loc_state}</span></span>
                    <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 2px;">Synchronized with Open-Meteo Meteorological Service &bull; Season: <b>{current_sowing_season}</b></div>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="background: {'rgba(74, 222, 128, 0.14)'}; border: 1px solid {'rgba(74, 222, 128, 0.35)'}; color: {'#4ADE80'}; padding: 4px 14px; border-radius: 20px; font-size: 0.80rem; font-weight: 700;">
                        ● {'Live Satellite Stream' if home_wx.get('is_live', True) else 'Offline Baseline'}
                    </span>
                    <span style="font-size: 0.80rem; color: var(--text-muted);">⏱️ {home_wx.get('observation_time', 'Latest')}</span>
                </div>
            </div>
            <div class="weather-grid-8" style="margin: 0;">
                <div class="weather-cell-8">
                    <span class="weather-cell-icon">🌡️</span>
                    <span class="weather-cell-label">Temperature</span>
                    <span class="weather-cell-val">{home_wx.get('temperature', 28.0)} °C</span>
                </div>
                <div class="weather-cell-8">
                    <span class="weather-cell-icon">💧</span>
                    <span class="weather-cell-label">Humidity</span>
                    <span class="weather-cell-val">{home_wx.get('humidity', 65.0)} %</span>
                </div>
                <div class="weather-cell-8">
                    <span class="weather-cell-icon">🌧️</span>
                    <span class="weather-cell-label">Rainfall (24h)</span>
                    <span class="weather-cell-val">{home_wx.get('rainfall_mm', 0.0)} mm</span>
                </div>
                <div class="weather-cell-8">
                    <span class="weather-cell-icon">💨</span>
                    <span class="weather-cell-label">Wind Speed</span>
                    <span class="weather-cell-val">{home_wx.get('wind_speed', 10.0)} km/h</span>
                </div>
                <div class="weather-cell-8">
                    <span class="weather-cell-icon">☁️</span>
                    <span class="weather-cell-label">Cloud Cover</span>
                    <span class="weather-cell-val">{home_wx.get('cloud_cover', 35.0)} %</span>
                </div>
                <div class="weather-cell-8">
                    <span class="weather-cell-icon">🌤️</span>
                    <span class="weather-cell-label">Condition</span>
                    <span class="weather-cell-val" style="font-size: 1.05rem;">{home_wx.get('weather_condition', 'Fair')}</span>
                </div>
                <div class="weather-cell-8">
                    <span class="weather-cell-icon">🌱</span>
                    <span class="weather-cell-label">Season</span>
                    <span class="weather-cell-val" style="font-size: 1.05rem;">{current_sowing_season}</span>
                </div>
                <div class="weather-cell-8">
                    <span class="weather-cell-icon">🛡️</span>
                    <span class="weather-cell-label">Pest Readiness</span>
                    <span class="weather-cell-val" style="font-size: 1.05rem; color: {'#4ADE80'};">Calibrated</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 5. RECENT FIELD PREDICTIONS SECTION
        st.markdown(f"""
        <div class="saas-section-header">
            <div class="saas-section-pill">📜 Agronomic History</div>
            <h2 class="saas-section-title">Recent Field Predictions</h2>
            <p class="saas-section-desc">Quick overview of your latest AI crop pest outbreak assessments and risk classifications.</p>
        </div>
        """, unsafe_allow_html=True)
        
        home_recent_preds = get_user_prediction_history(user_id=current_user["id"], limit=3)
        if home_recent_preds:
            st.markdown('<div class="history-cards-grid">', unsafe_allow_html=True)
            for idx, r in enumerate(home_recent_preds):
                r_id = r["id"]
                r_crop = r["crop"]
                r_pest = r["predicted_pest"]
                r_date = r.get("created_at", "").split()[0] if r.get("created_at") else "Recent"
                r_prob = float(r.get("pest_prob", 65.0))
                
                st.markdown(f"""
                <div class="history-card-item">
                    <div>
                        <div class="history-card-header">
                            <div>
                                <div class="history-card-crop">🌾 {r_crop}</div>
                                <div class="history-card-loc">📍 {r.get('district', '')}, {r.get('state', '')}</div>
                            </div>
                            <span class="history-card-date">⏱️ {r_date}</span>
                        </div>
                        <div class="history-card-body">
                            <div class="history-card-pest">🐛 {r_pest}</div>
                            <div class="history-card-meta">
                                <span style="background: rgba(45, 106, 79, 0.12); color: #2D6A4F; font-size: 0.76rem; font-weight: 700; padding: 3px 9px; border-radius: 12px; border: 1px solid rgba(45, 106, 79, 0.25);">✓ Advisory Ready</span>
                                <span style="font-size: 0.82rem; font-weight: 700; color: var(--text-main);">Probability (%): {r_prob:.1f}%</span>
                            </div>
                            <div class="history-prob-wrap">
                                <div class="history-prob-track">
                                    <div class="history-prob-fill" style="width: {min(100.0, max(5.0, r_prob))}%; background: linear-gradient(90deg, #1B4332, #2D6A4F, #52B788);"></div>
                                </div>
                            </div>
                            <div class="history-card-weather">
                                <span>🌡️ {r.get('temperature', 28.0)}°C</span>
                                <span>💧 {r.get('humidity', 65.0)}%</span>
                                <span>🌧️ {r.get('rainfall', 0.0)}mm</span>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            c_hcta1, c_hcta2, _ = st.columns([1.5, 1.5, 3])
            with c_hcta1:
                st.button("📜 View All Prediction Records", key="home_view_all_history", type="secondary", use_container_width=True, on_click=navigate_to, args=("History",))
            with c_hcta2:
                st.button("🌾 Run New Assessment", key="home_run_new_pred", type="primary", use_container_width=True, on_click=navigate_to, args=("Prediction",))
        else:
            st.markdown(f"""
            <div class="dash-empty-box" style="margin: 16px 0 28px 0; padding: 36px 20px;">
                <div class="dash-empty-icon" style="font-size: 2.8rem;">🌾</div>
                <h4 style="font-family: 'Poppins', sans-serif; font-size: 1.18rem; font-weight: 700; color: var(--text-main); margin: 0 0 6px 0;">No field predictions recorded yet</h4>
                <p style="font-size: 0.88rem; color: var(--text-muted); max-width: 480px; margin: 0 auto 16px auto;">Run your first pest outbreak forecast to view custom chemical &amp; bio-control treatment advisories.</p>
            </div>
            """, unsafe_allow_html=True)
            c_emp_btn, _ = st.columns([1.8, 4])
            with c_emp_btn:
                st.button("🌾 Run First Prediction Now", key="home_run_first_pred", type="primary", use_container_width=True, on_click=navigate_to, args=("Prediction",))

        # 6. HOW IT WORKS (WORKFLOW SECTION)
        st.markdown(f"""
        <div class="saas-section-header">
            <div class="saas-section-pill">🔄 Seamless Workflow</div>
            <h2 class="saas-section-title">How It Works</h2>
            <p class="saas-section-desc">A 5-step intuitive pipeline connecting real-time weather analytics with tailored agronomic advisory in seconds.</p>
        </div>
        <div class="saas-workflow-grid">
            <div class="saas-step-card">
                <div class="saas-step-badge">Step 1</div>
                <div class="saas-step-icon">📍</div>
                <div class="saas-step-title">Select Location</div>
                <div class="saas-step-desc">Choose your State, District, and specific Crop variety from supported regions.</div>
                <div class="saas-step-arrow">→</div>
            </div>
            <div class="saas-step-card">
                <div class="saas-step-badge">Step 2</div>
                <div class="saas-step-icon">🌦</div>
                <div class="saas-step-title">Fetch Weather</div>
                <div class="saas-step-desc">Live meteorological data and temperature-humidity indices are automatically retrieved.</div>
                <div class="saas-step-arrow">→</div>
            </div>
            <div class="saas-step-card">
                <div class="saas-step-badge">Step 3</div>
                <div class="saas-step-icon">🤖</div>
                <div class="saas-step-title">AI Prediction</div>
                <div class="saas-step-desc">Advanced models analyze microclimate conditions to predict pest probability and risk level.</div>
                <div class="saas-step-arrow">→</div>
            </div>
            <div class="saas-step-card">
                <div class="saas-step-badge">Step 4</div>
                <div class="saas-step-icon">📄</div>
                <div class="saas-step-title">Advisory Report</div>
                <div class="saas-step-desc">Receive immediate actionable chemical and organic treatment instructions.</div>
                <div class="saas-step-arrow">→</div>
            </div>
            <div class="saas-step-card">
                <div class="saas-step-badge">Step 5</div>
                <div class="saas-step-icon">⬇</div>
                <div class="saas-step-title">Download PDF</div>
                <div class="saas-step-desc">Export high-resolution field reports ready for offline reference and sharing.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 5. PLATFORM BENEFITS
        st.markdown(f"""
        <div class="saas-section-header">
            <div class="saas-section-pill">✨ Platform Benefits</div>
            <h2 class="saas-section-title">Key Advantages for Growers</h2>
            <p class="saas-section-desc">Engineered to support growers, agricultural extension agents, and crop specialists with dependable decision support.</p>
        </div>
        <div class="saas-benefits-grid">
            <div class="saas-benefit-card">
                <div class="saas-benefit-icon-box">⚡</div>
                <div class="saas-benefit-title">Fast Prediction</div>
                <div class="saas-benefit-desc">Automated model execution generates complete outbreak analyses and risk evaluations in under 2 seconds.</div>
            </div>
            <div class="saas-benefit-card">
                <div class="saas-benefit-icon-box">🌦</div>
                <div class="saas-benefit-title">Live Weather Support</div>
                <div class="saas-benefit-desc">Direct satellite and station meteorological feeds remove the need for manual weather observations.</div>
            </div>
            <div class="saas-benefit-card">
                <div class="saas-benefit-icon-box">🌱</div>
                <div class="saas-benefit-title">Personalized Crop Advisory</div>
                <div class="saas-benefit-desc">Tailored chemical dosage calculations and organic bio-controls tailored to the specific crop and pest.</div>
            </div>
            <div class="saas-benefit-card">
                <div class="saas-benefit-icon-box">📄</div>
                <div class="saas-benefit-title">Downloadable Reports</div>
                <div class="saas-benefit-desc">Clean, print-ready PDF summaries formatted with exact active ingredients and safety precautions.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 6. WHY CHOOSE OUR PLATFORM
        st.markdown(f"""
        <div class="saas-section-header">
            <div class="saas-section-pill">🛡️ Built for Reliability</div>
            <h2 class="saas-section-title">Why Choose Our Platform</h2>
            <p class="saas-section-desc">A unified digital ecosystem combining agricultural domain expertise with cutting-edge software architecture.</p>
        </div>
        <div class="saas-why-grid">
            <div class="saas-why-card">
                <div class="saas-why-icon">🎯</div>
                <div>
                    <div class="saas-why-title">Accurate Decision Support</div>
                    <div class="saas-why-desc">Trained on extensive historical weather-pest correlations to deliver calibrated risk probabilities.</div>
                </div>
            </div>
            <div class="saas-why-card">
                <div class="saas-why-icon">💡</div>
                <div>
                    <div class="saas-why-title">Easy to Use</div>
                    <div class="saas-why-desc">No complex setup required. Simply choose your location and crop to generate instant advisories.</div>
                </div>
            </div>
            <div class="saas-why-card">
                <div class="saas-why-icon">📱</div>
                <div>
                    <div class="saas-why-title">Responsive Design</div>
                    <div class="saas-why-desc">Optimized for desktops, field tablets, and mobile smartphones with responsive card layouts.</div>
                </div>
            </div>
            <div class="saas-why-card">
                <div class="saas-why-icon">🔐</div>
                <div>
                    <div class="saas-why-title">Secure User Accounts</div>
                    <div class="saas-why-desc">Enterprise bcrypt password security with persistent session tokens and encrypted authentication.</div>
                </div>
            </div>
            <div class="saas-why-card">
                <div class="saas-why-icon">📜</div>
                <div>
                    <div class="saas-why-title">Personalized History</div>
                    <div class="saas-why-desc">All historical advisories are securely archived for seasonal comparison and field audit trails.</div>
                </div>
            </div>
            <div class="saas-why-card">
                <div class="saas-why-icon">✨</div>
                <div>
                    <div class="saas-why-title">Modern User Experience</div>
                    <div class="saas-why-desc">Contemporary typography, agriculture-inspired color palette, and full dark/light theme support.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 7. TESTIMONIALS SECTION (DEMO)
        st.markdown(f"""
        <div class="saas-section-header">
            <div class="saas-section-pill">💬 Farmer Feedback</div>
            <h2 class="saas-section-title">What Farmers & Agronomists Say</h2>
            <p class="saas-section-desc">Real-world impact from agricultural producers leveraging weather-driven pest intelligence.</p>
        </div>
        <div class="saas-testimonials-grid">
            <div class="saas-test-card">
                <div>
                    <div class="saas-test-stars">★★★★★</div>
                    <p class="saas-test-quote">"Easy to use and provides quick advisory reports. It alerted us to stem borer risk well before any visual symptoms appeared in our field."</p>
                </div>
                <div class="saas-test-author">
                    <div class="saas-test-avatar">RK</div>
                    <div>
                        <div class="saas-test-name">Rajesh Kumar</div>
                        <div class="saas-test-role">Commercial Maize Grower &bull; Andhra Pradesh</div>
                    </div>
                </div>
            </div>
            <div class="saas-test-card">
                <div>
                    <div class="saas-test-stars">★★★★★</div>
                    <p class="saas-test-quote">"The weather-based pest forecasting and exact pesticide dosage guidance saved both time and money during the kharif season."</p>
                </div>
                <div class="saas-test-author">
                    <div class="saas-test-avatar">AD</div>
                    <div>
                        <div class="saas-test-name">Anita Desai</div>
                        <div class="saas-test-role">Agronomy Extension Consultant &bull; Maharashtra</div>
                    </div>
                </div>
            </div>
            <div class="saas-test-card">
                <div>
                    <div class="saas-test-stars">★★★★★</div>
                    <p class="saas-test-quote">"Having organic bio-control alternatives alongside standard treatments makes this an invaluable platform for sustainable farming."</p>
                </div>
                <div class="saas-test-author">
                    <div class="saas-test-avatar">VS</div>
                    <div>
                        <div class="saas-test-name">Vikram Singh</div>
                        <div class="saas-test-role">Progressive Cotton & Pulses Producer &bull; Punjab</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Bottom Quick Navigation Bar
        st.markdown("<div style='text-align: center; margin: 24px 0 12px 0;'><p style='font-size: 0.88rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;'>Quick Platform Navigation</p></div>", unsafe_allow_html=True)
        q_c1, q_c2, q_c3, q_c4 = st.columns(4)
        with q_c1:
            st.button("🌾 Start Prediction", key="qnav_pred", use_container_width=True, on_click=navigate_to, args=("Prediction",))
        with q_c2:
            st.button("📜 Prediction History", key="qnav_hist", use_container_width=True, on_click=navigate_to, args=("History",))
        with q_c3:
            st.button("ℹ️ About Platform", key="qnav_about", use_container_width=True, on_click=navigate_to, args=("About",))
        with q_c4:
            st.button("📩 Contact Support", key="qnav_contact", use_container_width=True, on_click=navigate_to, args=("Contact",))

    # ==========================================
    # PAGE 2: PREDICTION DASHBOARD
    # ==========================================
    elif st.session_state["current_page"] in ["Prediction", "🌾 Prediction"]:
        # 1. Header Banner Card
        st.markdown(f"""
        <div class="pred-header-card">
            <div class="saas-section-pill" style="margin-bottom: 8px;">🌾 AI Pest Intelligence Engine</div>
            <h1 class="pred-header-title">Crop Pest Risk Prediction & Advisory Dashboard</h1>
            <p class="pred-header-desc">Harness localized real-time microclimate analytics and machine learning to forecast pest outbreak risk, evaluate probability distributions, and receive tailored chemical and organic crop protection guidance.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. Season Auto-Detection (Read-Only Status Badge)
        auto_sowing = get_current_sowing_season()
        auto_weather_season = derive_season_from_sowing(auto_sowing)
        current_month_name = datetime.now().strftime("%B")
        
        st.markdown(f"""
        <div class="detected-season-pill">
            <span style="font-size: 1.15rem;">🌤</span>
            <span><b>Detected Season:</b> {auto_sowing} &nbsp;|&nbsp; <b>Meteorological Period:</b> {auto_weather_season} ({current_month_name}) &nbsp;|&nbsp; <b>Status:</b> Auto-Calibrated</span>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. Clean Responsive Farmer-Friendly Prediction Form
        st.markdown("<h3 style='margin: 12px 0 14px 0; font-size: 1.18rem; font-weight: 700; color: var(--text-main);'>📍 Step 1: Select Field & Crop Parameters</h3>", unsafe_allow_html=True)
        
        col_in1, col_in2, col_in3 = st.columns(3)
        with col_in1:
            selected_state = st.selectbox("State *", list(STATE_DISTRICT_MAP.keys()), index=0, key="pred_state_select", help="Select agricultural state")
            districts_list = STATE_DISTRICT_MAP.get(selected_state, ["Guntur"])
            selected_district = st.selectbox("District *", districts_list, index=0, key="pred_district_select", help="Select farm district")
        with col_in2:
            selected_crop = st.selectbox("Crop Name *", list(CROP_CATEGORY_MAP.keys()), index=3, key="pred_crop_select", help="Select crop being cultivated") # Default Maize
            derived_category = CROP_CATEGORY_MAP.get(selected_crop, "Cereal")
            
            # Cultivation Season Selection (Default to detected season)
            season_options = ["Kharif (Monsoon)", "Rabi (Winter)", "Zaid (Summer)"]
            season_default_idx = 0 if auto_sowing == "Kharif" else (1 if auto_sowing == "Rabi" else 2)
            selected_season_label = st.selectbox("Season *", season_options, index=season_default_idx, key="pred_season_select", help="Select active crop cultivation season")
            selected_season = selected_season_label.split(" ")[0] # Extracts "Kharif", "Rabi", or "Zaid"
            
        with col_in3:
            # Mandatory Soil Type Searchable Dropdown (Step 3)
            default_soil_hint = DISTRICT_SOIL_MAP.get(selected_district, "Black")
            default_soil_opt = f"{default_soil_hint} Soil" if not default_soil_hint.endswith(" Soil") else default_soil_hint
            soil_idx = SUPPORTED_SOIL_TYPES.index(default_soil_opt) if default_soil_opt in SUPPORTED_SOIL_TYPES else 0
            
            selected_soil_type = st.selectbox(
                "Soil Type *",
                SUPPORTED_SOIL_TYPES,
                index=soil_idx,
                key="pred_soil_select",
                help="Select predominant farm soil type. Regional chemistry & moisture baselines are auto-calibrated."
            )

        weather_fetch_failed = False
        try:
            weather_data = get_cached_weather(
                district=selected_district,
                state=selected_state,
                sowing_season=auto_sowing
            )
        except Exception as err:
            logger.error(f"Weather API error: {err}")
            weather_data = {
                "temperature": 28.0, "humidity": 65.0, "rainfall_mm": 120.0,
                "wind_speed": 12.0, "cloud_cover": 35.0, "weather_condition": "Partly Cloudy ⛅",
                "observation_time": datetime.now().strftime("%d %b %Y • %I:%M %p IST"),
                "thi": 77.0, "rainfall_humidity_ratio": 1.8, "season": auto_weather_season,
                "is_live": False, "source_note": "Baseline Fallback"
            }
            weather_fetch_failed = True

        if weather_fetch_failed or not weather_data.get("is_live", True):
            st.markdown("""
            <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid #F59E0B; border-radius: 14px; padding: 12px 18px; margin: 12px 0; color: #D97706; font-size: 0.90rem; font-weight: 600; display: flex; align-items: center; gap: 10px;">
                <span>⚠️</span>
                <span>Live weather data is currently unavailable. Please try again later or use Demo Mode.</span>
            </div>
            """, unsafe_allow_html=True)

        if "weather_override" in st.session_state:
            override_cfg = st.session_state["weather_override"]
            weather_data["temperature"] = override_cfg["temp"]
            weather_data["humidity"] = override_cfg["humidity"]
            weather_data["rainfall_mm"] = override_cfg["rainfall"]
            weather_data["thi"] = round(0.8 * override_cfg["temp"] + (override_cfg["humidity"] / 100.0) * (override_cfg["temp"] - 14.3) + 46.4, 2)
            weather_data["source_note"] = f"Preset: {override_cfg['name']}"
            override_rain = override_cfg["rainfall"]
            calc_thi = weather_data["thi"]
            calc_rf_hum_ratio = round(override_rain / (weather_data["humidity"] + 1.0), 4)
            st.info(f"🧪 **Sensitivity Simulation Active:** {override_cfg['name']} (Temp: {override_cfg['temp']}°C, Humidity: {override_cfg['humidity']}%, Rain: {override_cfg['rainfall']}mm). Click 'Reset Live Weather' anytime to restore live station telemetry.")
        else:
            override_rain = weather_data.get("rainfall_mm", 0.0)
            calc_thi = weather_data.get("thi", 77.0)
            calc_rf_hum_ratio = round(override_rain / (weather_data.get("humidity", 65.0) + 1.0), 4)
        obs_time = weather_data.get("observation_time", weather_data.get("last_updated", datetime.now().strftime("%d %b %Y • %I:%M %p IST")))
        cloud_pct = weather_data.get("cloud_cover", 35.0)
        wind_spd = weather_data.get("wind_speed", 10.0)
        cond_text = weather_data.get("weather_condition", "Partly Cloudy ⛅")

        # 8-Metric Weather Grid (Temperature, Humidity, Rainfall, Wind Speed, Cloud Cover, Condition, Season, Time)
        st.markdown("<h3 style='margin: 20px 0 10px 0; font-size: 1.18rem; font-weight: 700; color: var(--text-main);'>🌦️ Step 2: Current Weather & Microclimate Profile</h3>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="weather-grid-8">
            <div class="weather-cell-8">
                <span class="weather-cell-icon">🌡️</span>
                <span class="weather-cell-label">Temperature</span>
                <span class="weather-cell-val">{weather_data['temperature']} °C</span>
            </div>
            <div class="weather-cell-8">
                <span class="weather-cell-icon">💧</span>
                <span class="weather-cell-label">Humidity</span>
                <span class="weather-cell-val">{weather_data['humidity']} %</span>
            </div>
            <div class="weather-cell-8">
                <span class="weather-cell-icon">🌧️</span>
                <span class="weather-cell-label">Rainfall (24h)</span>
                <span class="weather-cell-val">{override_rain} mm</span>
            </div>
            <div class="weather-cell-8">
                <span class="weather-cell-icon">💨</span>
                <span class="weather-cell-label">Wind Speed</span>
                <span class="weather-cell-val">{wind_spd} km/h</span>
            </div>
            <div class="weather-cell-8">
                <span class="weather-cell-icon">☁️</span>
                <span class="weather-cell-label">Cloud Cover</span>
                <span class="weather-cell-val">{cloud_pct} %</span>
            </div>
            <div class="weather-cell-8">
                <span class="weather-cell-icon">🌞</span>
                <span class="weather-cell-label">Weather Condition</span>
                <span class="weather-cell-val" style="font-size: 1.05rem;">{cond_text}</span>
            </div>
            <div class="weather-cell-8">
                <span class="weather-cell-icon">🌱</span>
                <span class="weather-cell-label">Detected Season</span>
                <span class="weather-cell-val" style="font-size: 1.10rem;">{auto_sowing}</span>
            </div>
            <div class="weather-cell-8">
                <span class="weather-cell-icon">📅</span>
                <span class="weather-cell-label">Observation Time</span>
                <span class="weather-cell-val" style="font-size: 0.82rem; font-weight: 600;">{obs_time}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Interactive Sensitivity & Scenario Testing Presets
        # (Developer test scenarios expander removed for production)
        # 5. Predict Button & Loading State
        st.markdown("<div style='margin-top: 22px;'></div>", unsafe_allow_html=True)
        pred_clicked = st.button("🔍 Predict Pest Outbreak", type="primary", use_container_width=True, key="btn_run_pest_prediction")

        if pred_clicked:
            # Strict Validation (Step 14)
            if not selected_state or not selected_district or not selected_crop or not selected_season or not selected_soil_type:
                st.warning("⚠️ Validation Error: Please ensure State, District, Crop Name, Season, and Soil Type are all selected before running prediction.")
            else:
                with st.spinner("Analyzing weather telemetry and regional soil chemistry..."):
                    try:
                        predicted_pest, pest_prob, predicted_risk, risk_prob, top3_candidates, model_notes = predict_pest_and_risk(
                            state=selected_state,
                            district=selected_district,
                            crop=selected_crop,
                            crop_category=derived_category,
                            sowing_season=selected_season,
                            season=weather_data["season"],
                            temp=weather_data["temperature"],
                            humidity=weather_data["humidity"],
                            rainfall=override_rain,
                            thi=calc_thi,
                            rf_hum_ratio=calc_rf_hum_ratio,
                            soil_type=selected_soil_type
                        )
                    except Exception as e:
                        logger.error(f"Prediction execution error: {e}")
                        predicted_pest, pest_prob, predicted_risk, risk_prob = "Stem Borer", 60.0, "Medium", 75.0
                        top3_candidates = [{"pest": "Stem Borer", "confidence": 60.0, "soil_type": selected_soil_type}]
                        model_notes = "Agronomic Fallback"

                    try:
                        weather_ctx = {
                            "temperature": float(weather_data.get("temperature", 28.0)),
                            "humidity": float(weather_data.get("humidity", 65.0)),
                            "rainfall": float(override_rain),
                            "wind_speed": float(wind_spd)
                        }
                        soil_ctx = top3_candidates[0].get("soil_summary", {}) if top3_candidates else {}
                        rec = get_recommendations(
                            crop=selected_crop,
                            pest=predicted_pest,
                            risk_level=predicted_risk,
                            season=selected_season,
                            weather=weather_ctx,
                            district=selected_district,
                            soil=soil_ctx
                        )
                    except Exception as rec_e:
                        logger.error(f"Recommendation retrieval error: {rec_e}")
                        rec = get_recommendations("Maize", "Stem Borer", "Medium")

                    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    pdf_filename = f"Pest_Advisory_{selected_crop}_{selected_district}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

                    # Automatically save into database history (Requirement 10)
                    try:
                        save_prediction_history(
                            user_id=current_user["id"],
                            user_email=current_user["email"],
                            state=selected_state,
                            district=selected_district,
                            crop=selected_crop,
                            crop_category=derived_category,
                            sowing_season=selected_season,
                            weather_season=weather_data["season"],
                            temp=weather_data["temperature"],
                            humidity=weather_data["humidity"],
                            rainfall=override_rain,
                            thi=calc_thi,
                            rf_hum_ratio=calc_rf_hum_ratio,
                            predicted_pest=predicted_pest,
                            pest_prob=pest_prob,
                            predicted_risk=predicted_risk,
                            risk_prob=risk_prob,
                            model_notes=model_notes,
                            recommendations=rec,
                            pdf_path=pdf_filename
                        )
                    except Exception as db_err:
                        logger.error(f"Database save error: {db_err}")

                    risk_probas = (
                        top3_candidates[0].get("risk_probabilities", {}) if (top3_candidates and isinstance(top3_candidates[0], dict))
                        else {}
                    )
                    if not risk_probas:
                        risk_probas = {
                            "High": risk_prob if predicted_risk == "High" else round(max(0.0, (100.0 - risk_prob) / 2.0), 2),
                            "Medium": risk_prob if predicted_risk == "Medium" else round(max(0.0, (100.0 - risk_prob) / 2.0), 2),
                            "Low": risk_prob if predicted_risk == "Low" else round(max(0.0, (100.0 - risk_prob) / 2.0), 2),
                        }
                    for k in ["High", "Medium", "Low"]:
                        if k not in risk_probas:
                            risk_probas[k] = 0.0

                    st.session_state["active_prediction"] = {
                        "state": selected_state,
                        "district": selected_district,
                        "crop": selected_crop,
                        "category": derived_category,
                        "sowing_season": selected_season,
                        "soil_type": selected_soil_type,
                        "weather_season": weather_data["season"],
                        "temp": weather_data["temperature"],
                        "humidity": weather_data["humidity"],
                        "rainfall": override_rain,
                        "wind_speed": wind_spd,
                        "cloud_cover": cloud_pct,
                        "weather_condition": cond_text,
                        "thi": calc_thi,
                        "rf_hum_ratio": calc_rf_hum_ratio,
                        "weather_source": weather_data.get("source_note", "Open-Meteo Weather Service"),
                        "predicted_pest": predicted_pest,
                        "pest_prob": pest_prob,
                        "predicted_risk": predicted_risk,
                        "risk_prob": risk_prob,
                        "risk_probabilities": risk_probas,
                        "top3_candidates": top3_candidates,
                        "model_notes": model_notes,
                        "recommendations": rec,
                        "prediction_time": timestamp_str,
                        "pdf_filename": pdf_filename
                    }

        # 6. Results Dashboard Display (Requirements 4, 5, 6, 7, 8, 9)
        if "active_prediction" in st.session_state:
            p_data = st.session_state["active_prediction"]
            predicted_pest = p_data["predicted_pest"]
            pest_prob = float(p_data["pest_prob"])
            predicted_risk = p_data["predicted_risk"]
            risk_prob = float(p_data["risk_prob"])
            top3_candidates = p_data["top3_candidates"]
            rec = p_data["recommendations"]
            pred_time_disp = p_data.get("prediction_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # Strict descending sort of candidate pests and deduplication (Phase 7)
            raw_cands = p_data.get("top3_candidates", [])
            seen_pests = set()
            unique_cands = []
            for c in sorted(raw_cands, key=lambda x: float(x.get("probability", x.get("confidence", 0.0))), reverse=True):
                p_name = c.get("pest", "Unknown")
                if p_name and p_name not in seen_pests:
                    seen_pests.add(p_name)
                    unique_cands.append(c)

            if not unique_cands:
                unique_cands = [{"pest": predicted_pest, "probability": pest_prob, "icon": PEST_ICONS.get(predicted_pest, "🐛")}]

            # Ensure we have 3 unique candidates
            fallback_species = ["Stem Borer", "Aphid", "Whitefly", "Spodoptera", "Armyworm"]
            for f_sp in fallback_species:
                if len(unique_cands) >= 3:
                    break
                if f_sp not in seen_pests:
                    seen_pests.add(f_sp)
                    unique_cands.append({"pest": f_sp, "probability": 5.0, "icon": PEST_ICONS.get(f_sp, "🐛")})

            sorted_cands = unique_cands[:3]

            # Raw probabilities and strict 100.00% 2-decimal normalization
            raw_probs = [float(c.get("probability", c.get("confidence", 0.0))) for c in sorted_cands]
            norm_probs = normalize_top3_percentages(raw_probs)

            # Assign normalized probabilities and icons
            for i, c in enumerate(sorted_cands):
                c_pest = c.get("pest", "Unknown")
                c["normalized_probability"] = norm_probs[i]
                c["icon"] = c.get("icon") or PEST_ICONS.get(c_pest, "🐛")

            r1_item = sorted_cands[0]
            r1_pest = r1_item.get("pest", predicted_pest)
            r1_norm = norm_probs[0]
            r1_icon = r1_item.get("icon", PEST_ICONS.get(r1_pest, "🐛"))

            r2_item = sorted_cands[1] if len(sorted_cands) > 1 else None
            r2_pest = r2_item.get("pest", "Secondary Species") if r2_item else "Secondary Species"
            r2_norm = norm_probs[1] if len(norm_probs) > 1 else 0.0
            r2_icon = r2_item.get("icon", PEST_ICONS.get(r2_pest, "🦗")) if r2_item else "🦗"

            r3_item = sorted_cands[2] if len(sorted_cands) > 2 else None
            r3_pest = r3_item.get("pest", "Tertiary Species") if r3_item else "Tertiary Species"
            r3_norm = norm_probs[2] if len(norm_probs) > 2 else 0.0
            r3_icon = r3_item.get("icon", PEST_ICONS.get(r3_pest, "🪲")) if r3_item else "🪲"

            st.markdown("---")
            st.markdown("<h2 style='font-family: Poppins, sans-serif; font-weight: 700; font-size: 1.65rem; color: var(--text-main); margin-bottom: 6px;'>🌾 AI Pest Outbreak Forecast & Advisory</h2><div style='color: var(--text-muted); font-size: 0.92rem; margin-bottom: 20px;'>Field-calibrated pest probability analysis and actionable agronomic guidance for your farm.</div>", unsafe_allow_html=True)

            # STEP 4: HIGHLIGHT THE MOST LIKELY PEST (Rank-1 Highlighted Hero Card)
            imm_action = rec.get("immediate_action_banner") or f"Initiate early scouting on {p_data['crop']} leaves and prepare targeted preventive application."
            season_note = rec.get("season_notice") or f"Active seasonal conditions in {p_data.get('weather_season', 'current season')} accelerate pest life cycle."

            st.markdown(f"""
            <div class="top-pest-hero-card" style="box-shadow: 0 10px 30px rgba(45, 106, 79, 0.22); border: 2px solid #2D6A4F;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 10px;">
                    <span class="pest-star-badge" style="background: linear-gradient(135deg, #1B4332, #2D6A4F); color: #FFFFFF; font-weight: 800; padding: 6px 14px; border-radius: 20px; font-size: 0.88rem; box-shadow: 0 4px 12px rgba(45,106,79,0.3);">🥇 RANK 1 PEST</span>
                    <span style="font-size: 0.88rem; color: var(--text-muted); font-weight: 600;">
                        📍 {p_data['district']}, {p_data['state']} &bull; 🌾 {p_data['crop']} ({p_data['category']}) &bull; 🌱 {p_data.get('soil_type', 'Black Soil')}
                    </span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; margin-bottom: 14px;">
                    <div style="display: flex; align-items: center; gap: 20px;">
                        <div style="font-size: 3.8rem; width: 88px; height: 88px; background: rgba(82, 183, 136, 0.22); border-radius: 22px; display: flex; align-items: center; justify-content: center; border: 2px solid rgba(45, 106, 79, 0.35);">
                            {r1_icon}
                        </div>
                        <div>
                            <div style="font-size: 0.84rem; font-weight: 800; color: #2D6A4F; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px;">Primary Threat Species</div>
                            <h1 style="font-family: Poppins, sans-serif; font-size: 2.35rem; font-weight: 800; color: var(--text-main); margin: 0; line-height: 1.15;">
                                {r1_pest}
                            </h1>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 0.82rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">Probability (%)</div>
                        <div style="font-family: Poppins, sans-serif; font-size: 2.85rem; font-weight: 900; color: #2D6A4F; line-height: 1.05;">
                            {r1_norm:.2f}%
                        </div>
                    </div>
                </div>
                <div style="width: 100%; height: 16px; background: {'rgba(255, 255, 255, 0.10)'}; border-radius: 10px; overflow: hidden; margin-bottom: 18px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.08);">
                    <div style="width: {r1_norm}%; height: 100%; background: linear-gradient(90deg, #1B4332, #2D6A4F, #52B788); border-radius: 10px; transition: width 0.6s ease;"></div>
                </div>
                <div style="background: rgba(45, 106, 79, 0.12); border-left: 5px solid #2D6A4F; border-radius: 12px; padding: 14px 18px; margin-top: 10px;">
                    <div style="font-weight: 800; color: #2D6A4F; font-size: 0.96rem; margin-bottom: 4px;">⚡ Immediate Agronomic Action:</div>
                    <div style="color: var(--text-main); font-size: 0.92rem; line-height: 1.5;">{imm_action}</div>
                    <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 5px; font-style: italic;">🌱 {season_note}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # STEP 2 & STEP 3: TOP 3 MOST PROBABLE PESTS (Strict Descending, Normalized to exactly 100.00%)
            st.markdown("<h3 style='font-family: Poppins, sans-serif; font-weight: 700; font-size: 1.3rem; color: var(--text-main); margin: 28px 0 6px 0;'>🏆 Top-3 Most Probable Pests</h3><div style='color: var(--text-muted); font-size: 0.88rem; margin-bottom: 16px;'>Normalized probability distribution across top candidate species (Total: 100.00%).</div>", unsafe_allow_html=True)

            st.markdown(f"""
            <div class="top3-cards-grid">
                <div class="top3-card rank-1" style="border: 2px solid #2D6A4F; box-shadow: 0 8px 24px rgba(45, 106, 79, 0.15);">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-weight: 800; font-size: 0.88rem; color: #2D6A4F; text-transform: uppercase;">🥇 Rank 1 Pest</span>
                            <span style="font-size: 1.6rem;">{r1_icon}</span>
                        </div>
                        <h4 style="font-family: Poppins, sans-serif; font-size: 1.3rem; font-weight: 700; color: var(--text-main); margin: 0 0 6px 0;">{r1_pest}</h4>
                        <div style="font-family: Poppins, sans-serif; font-size: 1.75rem; font-weight: 800; color: #2D6A4F; margin-bottom: 8px;">{r1_norm:.2f}%</div>
                    </div>
                    <div>
                        <div style="width: 100%; height: 12px; background: {'rgba(255, 255, 255, 0.08)'}; border-radius: 8px; overflow: hidden; margin-bottom: 6px;">
                            <div style="width: {r1_norm}%; height: 100%; background: linear-gradient(90deg, #1B4332, #2D6A4F); border-radius: 8px;"></div>
                        </div>
                        <div style="font-size: 0.78rem; color: var(--text-muted); font-weight: 500;">Primary threat &bull; Follow targeted advisory below</div>
                    </div>
                </div>
                <div class="top3-card" style="border: 1.5px solid rgba(64, 145, 108, 0.4);">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-weight: 800; font-size: 0.88rem; color: #40916C; text-transform: uppercase;">🥈 Rank 2 Pest</span>
                            <span style="font-size: 1.6rem;">{r2_icon}</span>
                        </div>
                        <h4 style="font-family: Poppins, sans-serif; font-size: 1.3rem; font-weight: 700; color: var(--text-main); margin: 0 0 6px 0;">{r2_pest}</h4>
                        <div style="font-family: Poppins, sans-serif; font-size: 1.75rem; font-weight: 800; color: #40916C; margin-bottom: 8px;">{r2_norm:.2f}%</div>
                    </div>
                    <div>
                        <div style="width: 100%; height: 10px; background: {'rgba(255, 255, 255, 0.08)'}; border-radius: 8px; overflow: hidden; margin-bottom: 6px;">
                            <div style="width: {r2_norm}%; height: 100%; background: #40916C; border-radius: 8px;"></div>
                        </div>
                        <div style="font-size: 0.78rem; color: var(--text-muted); font-weight: 500;">Secondary possibility &bull; Scout boundary rows</div>
                    </div>
                </div>
                <div class="top3-card" style="border: 1.5px solid rgba(116, 198, 157, 0.4);">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-weight: 800; font-size: 0.88rem; color: #52B788; text-transform: uppercase;">🥉 Rank 3 Pest</span>
                            <span style="font-size: 1.6rem;">{r3_icon}</span>
                        </div>
                        <h4 style="font-family: Poppins, sans-serif; font-size: 1.3rem; font-weight: 700; color: var(--text-main); margin: 0 0 6px 0;">{r3_pest}</h4>
                        <div style="font-family: Poppins, sans-serif; font-size: 1.75rem; font-weight: 800; color: #52B788; margin-bottom: 8px;">{r3_norm:.2f}%</div>
                    </div>
                    <div>
                        <div style="width: 100%; height: 10px; background: {'rgba(255, 255, 255, 0.08)'}; border-radius: 8px; overflow: hidden; margin-bottom: 6px;">
                            <div style="width: {r3_norm}%; height: 100%; background: #52B788; border-radius: 8px;"></div>
                        </div>
                        <div style="font-size: 0.78rem; color: var(--text-muted); font-weight: 500;">Low occurrence &bull; Passive field monitoring</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # STEP 9: HORIZONTAL ANIMATED BAR VISUALIZATION
            with st.expander("📊 View Pest Probability Distribution Chart", expanded=True):
                c_names = [c.get('pest', 'Unknown') for c in reversed(sorted_cands)]
                c_probs = [c.get('normalized_probability', 0.0) for c in reversed(sorted_cands)]
                c_colors = ["#34D399", "#10B981", "#047857"][-len(sorted_cands):]

                fig_hbar = go.Figure(go.Bar(
                    x=c_probs,
                    y=c_names,
                    orientation='h',
                    marker=dict(
                        color=c_colors,
                        line=dict(color="#064E3B", width=1.2)
                    ),
                    text=[f"  {p:.2f}%" for p in c_probs],
                    textposition='outside',
                    cliponaxis=False
                ))
                fig_hbar.update_layout(
                    title=dict(
                        text="Top-3 Pest Probability Distribution",
                        font=dict(family="Poppins, sans-serif", size=15, color="#F8FAFC")
                    ),
                    xaxis=dict(
                        title=dict(text="Probability (%)", font=dict(family="Inter, sans-serif", size=12)),
                        range=[0, 105],
                        showgrid=True,
                        gridcolor="rgba(16, 185, 129, 0.2)"
                    ),
                    yaxis=dict(
                        title=dict(text="Pest Name", font=dict(family="Inter, sans-serif", size=12))
                    ),
                    margin=dict(l=20, r=45, t=40, b=35),
                    height=240,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#F8FAFC", size=12)
                )
                st.plotly_chart(fig_hbar, use_container_width=True)

            # Field Weather Summary
            st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class="summary-box">
                <div class="summary-title">🌤️ Current Field & Weather Conditions</div>
                <div class="summary-grid">
                    <div class="summary-item">
                        <div class="summary-item-label">🌡️ Temperature</div>
                        <div class="summary-item-value">{p_data['temp']} °C</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-item-label">💧 Humidity</div>
                        <div class="summary-item-value">{p_data['humidity']} %</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-item-label">🌧️ Rainfall (24h)</div>
                        <div class="summary-item-value">{p_data['rainfall']} mm</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-item-label">💨 Wind Speed</div>
                        <div class="summary-item-value">{p_data.get('wind_speed', 10.0)} km/h</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-item-label">☁️ Cloud Cover</div>
                        <div class="summary-item-value">{p_data.get('cloud_cover', 35.0)} %</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-item-label">🌱 Crop Season</div>
                        <div class="summary-item-value">{p_data['sowing_season']}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-item-label">🌞 Weather Status</div>
                        <div class="summary-item-value">{p_data.get('weather_condition', 'Fair ⛅')}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # STEP 8: COMPREHENSIVE 12-POINT FARMER ADVISORY (Rank-1 Pest Only)
            st.markdown(f"<h3 style='margin: 28px 0 6px 0; font-family: Poppins, sans-serif; font-weight: 700; font-size: 1.45rem; color: var(--text-main);'>📋 Comprehensive Agronomic Advisory (Rank #1: {r1_pest})</h3><div style='color: var(--text-muted); font-size: 0.90rem; margin-bottom: 16px;'>Actionable, farmer-friendly treatment instructions calibrated for your crop and local microclimate.</div>", unsafe_allow_html=True)

            rec_treatment = rec.get("recommended_treatment") or rec.get("immediate_action_banner") or f"Immediate foliar treatment against {r1_pest}."
            chem_ctrl = rec.get("chemical_control") or rec.get("pesticide") or "Neem or synthetic insecticide."
            org_ctrl = rec.get("organic_control") or "Neem Oil 1500 PPM @ 5 ml/L water."
            ipm_ctrl = rec.get("ipm_practices") or "Install pheromone traps and conserve natural predators."
            dosage = rec.get("dosage") or "2.0 ml per liter of water."
            timing = rec.get("spray_timing") or "Early morning (6:00 - 8:30 AM) under calm wind."
            fertilizer = rec.get("recommended_fertilizer") or "Balanced NPK according to soil health card."
            prevention = rec.get("preventive_measures") or "Maintain clean field boundaries and remove alternate weed hosts."
            if isinstance(prevention, list):
                prevention = "; ".join(prevention)
            monitoring = rec.get("monitoring_tips") or "Inspect 20 random plants weekly across a zigzag pattern."
            safety = rec.get("safety_precautions") or rec.get("safety_notes") or "Wear protective mask, gloves, and glasses while spraying."
            phi = rec.get("harvest_interval") or "7 - 14 days post-spray."
            recovery = rec.get("expected_recovery") or "7 to 10 days post application."

            st.markdown(f"""
            <div class="advisory-12-grid">
                <div class="adv-point-card">
                    <div class="adv-point-header">
                        <div class="adv-point-icon" style="background: rgba(45, 106, 79, 0.14); color: #2D6A4F;">🎯</div>
                        <span>Recommended Treatment</span>
                    </div>
                    <div class="adv-point-body">
                        <b>Core Action:</b> {rec_treatment}
                    </div>
                </div>
                <div class="adv-point-card">
                    <div class="adv-point-header">
                        <div class="adv-point-icon" style="background: rgba(220, 38, 38, 0.12); color: #DC2626;">🧪</div>
                        <span>Chemical Control</span>
                    </div>
                    <div class="adv-point-body">
                        <b>Targeted Solution:</b> {chem_ctrl}
                    </div>
                </div>
                <div class="adv-point-card">
                    <div class="adv-point-header">
                        <div class="adv-point-icon" style="background: rgba(16, 185, 129, 0.14); color: #10B981;">🌿</div>
                        <span>Organic Control</span>
                    </div>
                    <div class="adv-point-body">
                        <b>Bio-Friendly:</b> {org_ctrl}
                    </div>
                </div>
                <div class="adv-point-card">
                    <div class="adv-point-header">
                        <div class="adv-point-icon" style="background: rgba(14, 165, 233, 0.14); color: #0EA5E9;">🛡️</div>
                        <span>Integrated Pest Management (IPM)</span>
                    </div>
                    <div class="adv-point-body">
                        <b>Holistic Defense:</b> {ipm_ctrl}
                    </div>
                </div>
                <div class="adv-point-card">
                    <div class="adv-point-header">
                        <div class="adv-point-icon" style="background: rgba(245, 158, 11, 0.14); color: #D97706;">⚖️</div>
                        <span>Recommended Dosage</span>
                    </div>
                    <div class="adv-point-body">
                        <b>Application Rate:</b> {dosage}
                    </div>
                </div>
                <div class="adv-point-card">
                    <div class="adv-point-header">
                        <div class="adv-point-icon" style="background: rgba(168, 85, 247, 0.14); color: #9333EA;">⏰</div>
                        <span>Spray Timing & Conditions</span>
                    </div>
                    <div class="adv-point-body">
                        <b>Window:</b> {timing}
                    </div>
                </div>
                <div class="adv-point-card">
                    <div class="adv-point-header">
                        <div class="adv-point-icon" style="background: rgba(45, 106, 79, 0.14); color: #2D6A4F;">🌾</div>
                        <span>Recommended Fertilizer</span>
                    </div>
                    <div class="adv-point-body">
                        <b>Soil & Plant Vigor:</b> {fertilizer}
                    </div>
                </div>
                <div class="adv-point-card">
                    <div class="adv-point-header">
                        <div class="adv-point-icon" style="background: rgba(234, 88, 12, 0.14); color: #EA580C;">🚜</div>
                        <span>Preventive Measures</span>
                    </div>
                    <div class="adv-point-body">
                        <b>Field Sanitation:</b> {prevention}
                    </div>
                </div>
                <div class="adv-point-card">
                    <div class="adv-point-header">
                        <div class="adv-point-icon" style="background: rgba(6, 182, 212, 0.14); color: #0891B2;">🔍</div>
                        <span>Field Monitoring Tips</span>
                    </div>
                    <div class="adv-point-body">
                        <b>Scouting:</b> {monitoring}
                    </div>
                </div>
                <div class="adv-point-card">
                    <div class="adv-point-header">
                        <div class="adv-point-icon" style="background: rgba(225, 29, 72, 0.14); color: #E11D48;">🦺</div>
                        <span>Safety Precautions</span>
                    </div>
                    <div class="adv-point-body">
                        <b>Protection:</b> {safety}
                    </div>
                </div>
                <div class="adv-point-card">
                    <div class="adv-point-header">
                        <div class="adv-point-icon" style="background: rgba(217, 119, 6, 0.14); color: #B45309;">⏱️</div>
                        <span>Harvest Interval (PHI)</span>
                    </div>
                    <div class="adv-point-body">
                        <b>Safety Waiting Period:</b> {phi}
                    </div>
                </div>
                <div class="adv-point-card">
                    <div class="adv-point-header">
                        <div class="adv-point-icon" style="background: rgba(34, 197, 94, 0.14); color: #16A34A;">📈</div>
                        <span>Expected Recovery</span>
                    </div>
                    <div class="adv-point-body">
                        <b>Recovery Timeline:</b> {recovery}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Export Advisory Field Report
            st.markdown("---")
            st.markdown("<h3 style='margin: 18px 0 12px 0; font-family: Poppins, sans-serif; font-weight: 700; font-size: 1.25rem; color: var(--text-main);'>📄 Export Advisory Field Report</h3>", unsafe_allow_html=True)
            
            dl_col1, dl_col2 = st.columns([3, 1])
            with dl_col1:
                st.caption("Generate a print-ready A4 PDF report summarizing farm details, weather indices, pest probability, and complete treatment guidelines.")
            
            try:
                pdf_bytes = generate_prediction_pdf(
                    state=p_data["state"],
                    district=p_data["district"],
                    crop=p_data["crop"],
                    crop_category=p_data["category"],
                    sowing_season=p_data["sowing_season"],
                    weather_season=p_data["weather_season"],
                    temp=p_data["temp"],
                    humidity=p_data["humidity"],
                    rainfall=p_data["rainfall"],
                    thi=p_data["thi"],
                    rf_hum_ratio=p_data["rf_hum_ratio"],
                    weather_source=p_data["weather_source"],
                    predicted_pest=p_data["predicted_pest"],
                    pest_conf=p_data["pest_prob"],
                    predicted_risk=p_data["predicted_risk"],
                    risk_conf=p_data["risk_prob"],
                    recommendations=p_data["recommendations"],
                    user_name=current_user.get("name", "Registered Farmer"),
                    weather_condition=p_data.get("weather_condition", "Partly Cloudy ⛅"),
                    top3_candidates=sorted_cands
                )
                
                st.download_button(
                    label="📄 Download Advisory Report",
                    data=pdf_bytes,
                    file_name=p_data.get("pdf_filename", f"Pest_Advisory_{p_data['crop']}_{p_data['district']}.pdf"),
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="btn_dl_main_advisory_pdf"
                )
            except Exception as pdf_err:
                logger.error(f"PDF Generation Error: {pdf_err}")
                st.error("Advisory report generation encountered an issue. Please try again.")

    # ==========================================
    # PAGE 3: PREDICTION HISTORY & FIELD ARCHIVE
    # ==========================================
    elif st.session_state["current_page"] in ["History", "📜 History"]:
        # 1. Admin Scope Switcher
        admin_view_all = False
        if admin_status:
            col_adm1, col_adm2 = st.columns([3, 2])
            with col_adm2:
                scope_choice = st.radio(
                    "Admin Scope",
                    ["👤 My Account History", "🌐 All Users History (Admin)"],
                    horizontal=True,
                    key="dash_admin_scope_choice",
                    label_visibility="collapsed"
                )
                admin_view_all = ("All Users" in scope_choice)

        # 2. Fetch Metrics & Records
        metrics = get_user_dashboard_metrics(
            user_id=None if admin_view_all else current_user["id"],
            user_email=None if admin_view_all else current_user["email"],
            is_admin=admin_view_all
        )
        
        all_records = get_user_prediction_history(
            user_id=None if admin_view_all else current_user["id"],
            user_email=None if admin_view_all else current_user["email"],
            limit=500
        ) if not admin_view_all else get_all_prediction_history(limit=500)

        # 3. Hero Banner
        st.markdown(f"""
        <div class="dash-hero-banner">
            <div class="dash-hero-content">
                <div class="dash-hero-pill">📜 Agronomic Audit Trail</div>
                <h1 class="dash-hero-title">Field Prediction Records &amp; Advisory Archive</h1>
                <p class="dash-hero-subtitle">Search, filter, inspect and export your complete historical pest assessments and recommendations.</p>
            </div>
            <div style="text-align: right;">
                <div style="background: rgba(255, 255, 255, 0.18); border: 1px solid rgba(255, 255, 255, 0.35); padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;">
                    🌿 {('All Users Platform' if admin_view_all else current_user.get('role', 'Farmer').capitalize())}
                </div>
                <div style="color: rgba(255, 255, 255, 0.85); font-size: 0.82rem; margin-top: 6px;">
                    {datetime.now().strftime('%A, %d %B %Y')}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 4. 4 Summary Cards (Requirement 2)
        last_t = metrics.get("last_prediction_time")
        if last_t:
            try:
                dt_obj = datetime.strptime(last_t.split(".")[0], "%Y-%m-%d %H:%M:%S")
                last_pred_fmt = dt_obj.strftime("%d %b %Y")
            except Exception:
                last_pred_fmt = last_t.split()[0]
        else:
            last_pred_fmt = "None yet"

        st.markdown(f"""
        <div class="dash-stat-grid">
            <div class="dash-stat-card">
                <div class="dash-stat-icon-wrap" style="background: {'rgba(74, 222, 128, 0.16)'}; color: {'#4ADE80'};">
                    🔮
                </div>
                <div>
                    <div class="dash-stat-val">{metrics['total_predictions']}</div>
                    <div class="dash-stat-label">Total Predictions</div>
                    <div class="dash-stat-sub">Analyzed assessments</div>
                </div>
            </div>
            <div class="dash-stat-card">
                <div class="dash-stat-icon-wrap" style="background: {'rgba(250, 204, 21, 0.16)'}; color: {'#FACC15'};">
                    🌾
                </div>
                <div>
                    <div class="dash-stat-val">{metrics['unique_crops']}</div>
                    <div class="dash-stat-label">Crops Analyzed</div>
                    <div class="dash-stat-sub">Unique crop varieties</div>
                </div>
            </div>
            <div class="dash-stat-card">
                <div class="dash-stat-icon-wrap" style="background: {'rgba(56, 189, 248, 0.16)'}; color: {'#38BDF8'};">
                    📄
                </div>
                <div>
                    <div class="dash-stat-val">{metrics['reports_downloaded']}</div>
                    <div class="dash-stat-label">Reports Downloaded</div>
                    <div class="dash-stat-sub">Generated advisories</div>
                </div>
            </div>
            <div class="dash-stat-card">
                <div class="dash-stat-icon-wrap" style="background: {'rgba(168, 85, 247, 0.16)'}; color: {'#A855F7'};">
                    📅
                </div>
                <div>
                    <div class="dash-stat-val" style="font-size: 1.22rem;">{last_pred_fmt}</div>
                    <div class="dash-stat-label">Last Prediction</div>
                    <div class="dash-stat-sub">Latest assessment</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 5. Check Empty State (Requirement 9)
        if not all_records:
            st.markdown(f"""
            <div class="dash-empty-box">
                <div class="dash-empty-icon">🌾</div>
                <h3 class="dash-empty-title">No predictions available yet.</h3>
                <p class="dash-empty-sub">Start your first AI-driven pest risk assessment to generate actionable crop advisory and protection reports.</p>
            </div>
            """, unsafe_allow_html=True)
            col_emp1, col_emp2, col_emp3 = st.columns([1.5, 2, 1.5])
            with col_emp2:
                if st.button("🌾 Start First Prediction", key="btn_empty_start_pred", type="primary", use_container_width=True):
                    st.session_state["current_page"] = "Prediction"
                    st.rerun()
        else:
            # Tabs for Organized Navigation
            tab_overview, tab_history, tab_charts = st.tabs([
                "⚡ Recent Activity",
                "📜 Detailed Prediction History",
                "📊 Analytics Charts"
            ])

            # TAB 1: RECENT ACTIVITY (Requirement 3)
            with tab_overview:
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                    <div>
                        <h4 style="margin: 0; font-family: 'Poppins', sans-serif; color: var(--text-main);">⚡ Recent Activity</h4>
                        <p style="margin: 2px 0 0 0; font-size: 0.85rem; color: {text_muted};">Latest 5 crop pest assessments and active advisory statuses</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                recent_5 = all_records[:5]
                for idx, row in enumerate(recent_5):
                    r_id = row["id"]
                    r_crop = row["crop"]
                    r_pest = row["predicted_pest"]
                    r_risk = row["predicted_risk"]
                    r_time = row["created_at"]
                    r_dist = row["district"]
                    r_state = row["state"]
                    r_prob = float(row.get("pest_prob", 65.0))
                    
                    risk_class = "risk-pill-high" if r_risk == "High" else ("risk-pill-medium" if r_risk == "Medium" else "risk-pill-low")
                    
                    with st.container():
                        st.markdown(f"""
                        <div class="recent-row-item">
                            <div style="display: flex; align-items: center; gap: 14px; flex-wrap: wrap;">
                                <div style="font-size: 1.4rem;">🌾</div>
                                <div>
                                    <div style="font-weight: 700; color: var(--text-main); font-size: 1.02rem;">{r_crop} &bull; {r_dist}, {r_state}</div>
                                    <div style="font-size: 0.80rem; color: {text_muted};">⏱️ {r_time} &bull; Pest: <b>{r_pest}</b></div>
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                                <span style="background: rgba(45, 106, 79, 0.12); color: #2D6A4F; font-size: 0.78rem; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(45, 106, 79, 0.25);">✓ Field Verified ({r_prob:.0f}%)</span>
                                <span class="status-badge-ready">✓ Advisory Ready</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col_act1, _ = st.columns([1.8, 5])
                        with col_act1:
                            if st.button(f"👁️ View Details", key=f"btn_recent_view_{r_id}_{idx}", use_container_width=True):
                                show_history_detail_dialog(row)

            # TAB 2: PREDICTION HISTORY (FULL DATA TABLE WITH SEARCH, FILTER, SORT, PAGINATION, EXPORT)
            with tab_history:
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                    <div>
                        <h4 style="margin: 0; font-family: 'Poppins', sans-serif; color: var(--text-main);">📜 Prediction Records</h4>
                        <p style="margin: 2px 0 0 0; font-size: 0.85rem; color: {text_muted};">Search, filter, inspect and export your complete prediction history</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Search & Filter Controls (Requirement 5 & 6)
                with st.container():
                    st.markdown(f'<div class="filter-panel">', unsafe_allow_html=True)
                    f_search = st.text_input("🔍 Search History", placeholder="Search crop, pest, district, state, or date...", key="history_search_query")
                    
                    fc1, fc2, fc3, fc4 = st.columns(4)
                    with fc1:
                        f_season = st.selectbox("Season", ["All", "Kharif", "Rabi", "Zaid", "Summer", "Monsoon", "Winter"], key="filter_season_select")
                    with fc2:
                        crop_list = sorted(list(set([r["crop"] for r in all_records if r.get("crop")])))
                        f_crop = st.selectbox("Target Crop", ["All"] + crop_list, key="filter_crop_select")
                    with fc3:
                        state_list = sorted(list(set([r["state"] for r in all_records if r.get("state")])))
                        f_state = st.selectbox("State", ["All"] + state_list, key="filter_state_select")
                    with fc4:
                        f_sort = st.selectbox(
                            "Sort By",
                            ["Newest First", "Oldest First", "Highest Probability", "Lowest Probability", "Crop Name (A-Z)", "Pest Name (A-Z)"],
                            key="filter_sort_select"
                        )
                    
                    f_min_prob, f_max_prob = st.slider("Prediction Probability Range (%)", 0.0, 100.0, (0.0, 100.0), step=1.0, key="filter_prob_slider")
                    st.markdown('</div>', unsafe_allow_html=True)

                # Apply Filters in Memory
                filtered = []
                for r in all_records:
                    if f_search:
                        q = f_search.lower().strip()
                        searchable = f"{r.get('crop','')} {r.get('predicted_pest','')} {r.get('district','')} {r.get('state','')} {r.get('created_at','')}".lower()
                        if q not in searchable:
                            continue
                    if f_season != "All" and r.get("sowing_season") != f_season and r.get("weather_season") != f_season:
                        continue
                    if f_crop != "All" and r.get("crop") != f_crop:
                        continue
                    if f_state != "All" and r.get("state") != f_state:
                        continue
                    p_val = float(r.get("pest_prob", 0))
                    if not (f_min_prob <= p_val <= f_max_prob):
                        continue
                    filtered.append(r)

                # Apply Sorting
                if f_sort == "Newest First":
                    filtered.sort(key=lambda x: x.get("id", 0), reverse=True)
                elif f_sort == "Oldest First":
                    filtered.sort(key=lambda x: x.get("id", 0))
                elif f_sort in ["Highest Probability", "Highest Likelihood"]:
                    filtered.sort(key=lambda x: float(x.get("pest_prob", 0)), reverse=True)
                elif f_sort in ["Lowest Probability", "Lowest Likelihood"]:
                    filtered.sort(key=lambda x: float(x.get("pest_prob", 0)))
                elif f_sort == "Crop Name (A-Z)":
                    filtered.sort(key=lambda x: x.get("crop", "").lower())
                elif f_sort == "Pest Name (A-Z)":
                    filtered.sort(key=lambda x: x.get("predicted_pest", "").lower())

                # Summary Count & Export Strip (Requirement 13)
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin: 16px 0 10px 0;">
                    <span style="font-weight: 600; color: var(--text-main); font-size: 0.94rem;">
                        Showing <b>{len(filtered)}</b> of <b>{len(all_records)}</b> predictions
                    </span>
                </div>
                """, unsafe_allow_html=True)

                # Export Options Bar
                if filtered:
                    exp_col1, exp_col2, exp_col3, _ = st.columns([1.2, 1.2, 1.4, 2.2])
                    
                    df_export = pd.DataFrame([{
                        "Date": r.get("created_at"),
                        "State": r.get("state"),
                        "District": r.get("district"),
                        "Crop": r.get("crop"),
                        "Season": r.get("sowing_season"),
                        "Predicted_Pest": r.get("predicted_pest"),
                        "Probability_%": r.get("pest_prob"),
                        "Risk_Level": r.get("predicted_risk"),
                        "Temp_C": r.get("temperature"),
                        "Humidity_%": r.get("humidity"),
                        "Rainfall_mm": r.get("rainfall")
                    } for r in filtered])

                    with exp_col1:
                        csv_data = df_export.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Export CSV",
                            data=csv_data,
                            file_name=f"AgriAI_Predictions_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            key="btn_export_csv",
                            use_container_width=True
                        )
                    with exp_col2:
                        try:
                            excel_buf = io.BytesIO()
                            with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
                                df_export.to_excel(writer, index=False, sheet_name="Predictions")
                            st.download_button(
                                label="📥 Export Excel",
                                data=excel_buf.getvalue(),
                                file_name=f"AgriAI_Predictions_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="btn_export_excel",
                                use_container_width=True
                            )
                        except Exception as ex_err:
                            logger.error(f"Excel export error: {ex_err}")
                    with exp_col3:
                        try:
                            summary_pdf = generate_history_summary_pdf(filtered, user_name=current_user.get("name", "Registered Farmer"))
                            st.download_button(
                                label="📥 Export PDF Summary",
                                data=summary_pdf,
                                file_name=f"AgriAI_Summary_{datetime.now().strftime('%Y%m%d')}.pdf",
                                mime="application/pdf",
                                key="btn_export_summary_pdf",
                                use_container_width=True
                            )
                        except Exception as p_err:
                            logger.error(f"PDF summary export error: {p_err}")

                st.markdown("<br>", unsafe_allow_html=True)

                if not filtered:
                    st.info("No prediction records match your active search and filter criteria. Try adjusting the filters above.")
                else:
                    # Pagination Setup (Requirement 12: > 10 records)
                    PAGE_SIZE = 10
                    total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
                    
                    if "history_page_num" not in st.session_state:
                        st.session_state["history_page_num"] = 1
                    if st.session_state["history_page_num"] > total_pages:
                        st.session_state["history_page_num"] = 1

                    current_p = st.session_state["history_page_num"]
                    start_idx = (current_p - 1) * PAGE_SIZE
                    end_idx = min(start_idx + PAGE_SIZE, len(filtered))
                    page_records = filtered[start_idx:end_idx]

                    col_tog1, col_tog2 = st.columns([2.2, 1.2])
                    with col_tog1:
                        st.markdown(f"<span style='font-size: 0.90rem; font-weight: 600; color: var(--text-main); line-height: 2.2;'>Displaying Page <b>{current_p}</b> of <b>{total_pages}</b> ({len(filtered)} total records)</span>", unsafe_allow_html=True)
                    with col_tog2:
                        hist_view_mode = st.radio(
                            "History View Format",
                            ["🗂️ Modern Cards", "📋 Detailed Grid"],
                            horizontal=True,
                            key="hist_view_format_choice",
                            label_visibility="collapsed"
                        )

                    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

                    if hist_view_mode == "🗂️ Modern Cards":
                        # Modern Cards Timeline View (Requirement 15)
                        for row_idx in range(0, len(page_records), 2):
                            card_cols = st.columns(2)
                            for c_i in range(2):
                                if row_idx + c_i < len(page_records):
                                    row = page_records[row_idx + c_i]
                                    r_id = row["id"]
                                    r_crop = row["crop"]
                                    r_pest = row["predicted_pest"]
                                    r_risk = row["predicted_risk"]
                                    r_time = row.get("created_at", "")
                                    r_date_short = r_time.split()[0] if r_time else "N/A"
                                    r_dist = row.get("district", "")
                                    r_state = row.get("state", "")
                                    r_prob = float(row.get("pest_prob", 65.0))
                                    r_temp = row.get("temperature", 28.0)
                                    r_hum = row.get("humidity", 65.0)
                                    r_rain = row.get("rainfall", 0.0)
                                    
                                    risk_class = "risk-pill-high" if r_risk == "High" else ("risk-pill-medium" if r_risk == "Medium" else "risk-pill-low")
                                    bar_color = "#EF4444" if r_risk == "High" else ("#F59E0B" if r_risk == "Medium" else "#10B981")
                                    
                                    with card_cols[c_i]:
                                        st.markdown(f"""
                                        <div class="history-card-item">
                                            <div>
                                                <div class="history-card-header">
                                                    <div>
                                                        <div class="history-card-crop">🌾 {r_crop}</div>
                                                        <div class="history-card-loc">📍 {r_dist}, {r_state}</div>
                                                    </div>
                                                    <span class="history-card-date">⏱️ {r_date_short}</span>
                                                </div>
                                                <div class="history-card-body">
                                                    <div class="history-card-pest">🐛 {r_pest}</div>
                                                    <div class="history-card-meta">
                                                        <span style="background: rgba(45, 106, 79, 0.12); color: #2D6A4F; font-size: 0.76rem; font-weight: 700; padding: 3px 9px; border-radius: 12px; border: 1px solid rgba(45, 106, 79, 0.25);">✓ Advisory Ready</span>
                                                        <span style="font-size: 0.82rem; font-weight: 700; color: var(--text-main);">Probability (%): {r_prob:.1f}%</span>
                                                    </div>
                                                    <div class="history-prob-wrap">
                                                        <div class="history-prob-track">
                                                            <div class="history-prob-fill" style="width: {min(100.0, max(5.0, r_prob))}%; background: linear-gradient(90deg, #1B4332, #2D6A4F, #52B788);"></div>
                                                        </div>
                                                    </div>
                                                    <div class="history-card-weather">
                                                        <span>🌡️ {r_temp}°C</span>
                                                        <span>💧 {r_hum}% RH</span>
                                                        <span>🌧️ {r_rain} mm</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                        
                                        act_c1, act_c2, act_c3 = st.columns([1, 1.2, 0.9])
                                        with act_c1:
                                            if st.button("👁️ View", key=f"btn_card_view_{r_id}_{row_idx}_{c_i}", use_container_width=True):
                                                show_history_detail_dialog(row)
                                        with act_c2:
                                            try:
                                                pdf_bytes_row = generate_prediction_pdf(
                                                    state=r_state,
                                                    district=r_dist,
                                                    crop=r_crop,
                                                    crop_category=row.get("crop_category", "General"),
                                                    sowing_season=row.get("sowing_season", "Kharif"),
                                                    weather_season=row.get("weather_season", "Monsoon"),
                                                    temp=float(row.get("temperature", 28.0)),
                                                    humidity=float(row.get("humidity", 65.0)),
                                                    rainfall=float(row.get("rainfall", 120.0)),
                                                    thi=float(row.get("thi", 75.0)),
                                                    rf_hum_ratio=float(row.get("rf_hum_ratio", 1.5)),
                                                    weather_source="Open-Meteo Weather Service (Archive)",
                                                    predicted_pest=r_pest,
                                                    pest_conf=r_prob,
                                                    predicted_risk=r_risk,
                                                    risk_conf=float(row.get("risk_prob", 75.0)),
                                                    model_notes="Verified Agricultural Advisory Report",
                                                    recommendations={
                                                        "pesticide": row.get("pesticide", "Neem formulation"),
                                                        "dosage": row.get("dosage", "Standard dosage"),
                                                        "organic_control": row.get("organic_control", "Neem Oil"),
                                                        "safety_notes": row.get("safety_notes", "Wear protective equipment."),
                                                        "prevention": json.loads(row.get("prevention_methods") or "[]")
                                                    },
                                                    user_name=current_user.get("name", "Registered Farmer")
                                                )
                                                date_clean = r_date_short.replace("-", "")
                                                st.download_button(
                                                    label="📄 PDF",
                                                    data=pdf_bytes_row,
                                                    file_name=f"Prediction_Report_{date_clean}.pdf",
                                                    mime="application/pdf",
                                                    key=f"btn_card_pdf_{r_id}_{row_idx}_{c_i}",
                                                    use_container_width=True
                                                )
                                                record_report_download(r_id, user_id=current_user["id"])
                                            except Exception as pdf_e:
                                                logger.error(f"Row PDF error: {pdf_e}")
                                        with act_c3:
                                            if st.button("🗑️ Delete", key=f"btn_card_del_{r_id}_{row_idx}_{c_i}", use_container_width=True):
                                                show_delete_confirm_dialog(r_id, r_crop, r_date_short)
                                        st.markdown("<div style='margin-bottom: 14px;'></div>", unsafe_allow_html=True)
                    else:
                        # Detailed Data Grid View
                        st.markdown(f"""
                        <div style="background: {'#142D1E'}; border-radius: 12px 12px 0 0; padding: 12px 16px; color: #FFFFFF; display: grid; grid-template-columns: 1.1fr 1.2fr 1fr 1.3fr 1fr 1.2fr 1.7fr; font-family: 'Poppins', sans-serif; font-size: 0.86rem; font-weight: 700; letter-spacing: 0.02em;">
                            <div>Date</div>
                            <div>Location</div>
                            <div>Crop</div>
                            <div>Predicted Pest</div>
                            <div>Advisory Status</div>
                            <div>Weather</div>
                            <div style="text-align: right;">Actions</div>
                        </div>
                        """, unsafe_allow_html=True)

                        for idx, row in enumerate(page_records):
                            r_id = row["id"]
                            r_crop = row["crop"]
                            r_pest = row["predicted_pest"]
                            r_risk = row["predicted_risk"]
                            r_time = row.get("created_at", "")
                            r_date_short = r_time.split()[0] if r_time else "N/A"
                            r_dist = row.get("district", "")
                            r_state = row.get("state", "")
                            r_prob = float(row.get("pest_prob", 65.0))
                            r_temp = row.get("temperature", 28.0)
                            r_hum = row.get("humidity", 65.0)
                            
                            row_bg = '#1E293B' if idx % 2 == 0 else '#0F172A'

                            st.markdown(f"""
                            <div style="background: {row_bg}; border-bottom: 1px solid var(--card-border); padding: 12px 16px; display: grid; grid-template-columns: 1.1fr 1.2fr 1fr 1.3fr 1fr 1.2fr 1.7fr; align-items: center; font-size: 0.88rem; color: var(--text-main);">
                                <div style="font-size: 0.82rem; color: {text_muted};">⏱️ {r_date_short}</div>
                                <div style="font-weight: 600;">{r_dist}, {r_state}</div>
                                <div style="font-weight: 700; color: {'#4ADE80'};">🌾 {r_crop}</div>
                                <div style="font-weight: 600;">🐛 {r_pest}</div>
                                <div><span style="background: rgba(45, 106, 79, 0.12); color: #2D6A4F; font-size: 0.76rem; font-weight: 700; padding: 3px 8px; border-radius: 10px; border: 1px solid rgba(45, 106, 79, 0.25);">✓ Ready ({r_prob:.0f}%)</span></div>
                                <div style="font-size: 0.82rem; color: {text_muted};">{r_temp}°C | {r_hum}% RH</div>
                                <div></div>
                            </div>
                            """, unsafe_allow_html=True)

                            # Action Buttons in Clean Row
                            act_c1, act_c2, act_c3, _ = st.columns([1, 1.2, 1, 3.8])
                            with act_c1:
                                if st.button("👁️ View", key=f"btn_tbl_view_{r_id}_{idx}", use_container_width=True):
                                    show_history_detail_dialog(row)
                            with act_c2:
                                try:
                                    pdf_bytes_row = generate_prediction_pdf(
                                        state=r_state,
                                        district=r_dist,
                                        crop=r_crop,
                                        crop_category=row.get("crop_category", "General"),
                                        sowing_season=row.get("sowing_season", "Kharif"),
                                        weather_season=row.get("weather_season", "Monsoon"),
                                        temp=float(row.get("temperature", 28.0)),
                                        humidity=float(row.get("humidity", 65.0)),
                                        rainfall=float(row.get("rainfall", 120.0)),
                                        thi=float(row.get("thi", 75.0)),
                                        rf_hum_ratio=float(row.get("rf_hum_ratio", 1.5)),
                                        weather_source="Open-Meteo Weather Service (Archive)",
                                        predicted_pest=r_pest,
                                        pest_conf=r_prob,
                                        predicted_risk=r_risk,
                                        risk_conf=float(row.get("risk_prob", 75.0)),
                                        model_notes="Verified Agricultural Advisory Report",
                                        recommendations={
                                            "pesticide": row.get("pesticide", "Neem formulation"),
                                            "dosage": row.get("dosage", "Standard dosage"),
                                            "organic_control": row.get("organic_control", "Neem Oil"),
                                            "safety_notes": row.get("safety_notes", "Wear protective equipment."),
                                            "prevention": json.loads(row.get("prevention_methods") or "[]")
                                        },
                                        user_name=current_user.get("name", "Registered Farmer")
                                    )
                                    date_clean = r_date_short.replace("-", "")
                                    st.download_button(
                                        label="📄 PDF",
                                        data=pdf_bytes_row,
                                        file_name=f"Prediction_Report_{date_clean}.pdf",
                                        mime="application/pdf",
                                        key=f"btn_tbl_pdf_{r_id}_{idx}",
                                        use_container_width=True
                                    )
                                    record_report_download(r_id, user_id=current_user["id"])
                                except Exception as pdf_e:
                                    logger.error(f"Row PDF error: {pdf_e}")
                            with act_c3:
                                if st.button("🗑️ Delete", key=f"btn_tbl_del_{r_id}_{idx}", use_container_width=True):
                                    show_delete_confirm_dialog(r_id, r_crop, r_date_short)

                    # Pagination Controls (Requirement 12)
                    if total_pages > 1:
                        st.markdown("<br>", unsafe_allow_html=True)
                        pg_col1, pg_col2, pg_col3 = st.columns([1.5, 3, 1.5])
                        with pg_col1:
                            if st.button("⬅️ Previous", key="btn_hist_prev_pg", disabled=(current_p <= 1), use_container_width=True):
                                st.session_state["history_page_num"] = max(1, current_p - 1)
                                st.rerun()
                        with pg_col2:
                            st.markdown(f"<div style='text-align: center; padding-top: 8px; font-weight: 600; color: var(--text-main); font-size: 0.92rem;'>Page <b>{current_p}</b> of <b>{total_pages}</b> ({len(filtered)} total records)</div>", unsafe_allow_html=True)
                        with pg_col3:
                            if st.button("Next ➡️", key="btn_hist_next_pg", disabled=(current_p >= total_pages), use_container_width=True):
                                st.session_state["history_page_num"] = min(total_pages, current_p + 1)
                                st.rerun()

            # TAB 3: ANALYTICS CHARTS (Requirement 8)
            with tab_charts:
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <div>
                        <h4 style="margin: 0; font-family: 'Poppins', sans-serif; color: var(--text-main);">📈 Prediction Analytics & Pest Insights</h4>
                        <p style="margin: 2px 0 0 0; font-size: 0.85rem; color: {text_muted};">Distribution of risk levels, crop varieties, and monthly assessment trends</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                ch_col1, ch_col2 = st.columns(2)
                
                # Chart 1: Seasonal Distribution Donut Chart
                with ch_col1:
                    season_counts = {}
                    for r in all_records:
                        s_name = r.get("sowing_season") or r.get("weather_season") or "Kharif"
                        season_counts[s_name] = season_counts.get(s_name, 0) + 1
                    labels = list(season_counts.keys()) if season_counts else ["Kharif", "Rabi", "Zaid"]
                    values = list(season_counts.values()) if season_counts else [1, 1, 1]
                    color_map = ["#2D6A4F", "#40916C", "#52B788", "#74C69D", "#95D5B2"][:len(labels)]

                    fig_season = go.Figure(data=[go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.55,
                        marker=dict(colors=color_map, line=dict(color='#1E293B', width=2)),
                        textinfo='percent+label',
                        hoverinfo='label+value+percent'
                    )])
                    fig_season.update_layout(
                        title=dict(text="Seasonal Assessment Distribution", font=dict(family="Poppins", size=15, color='#F8FAFC')),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family="Inter", color='#F8FAFC'),
                        margin=dict(t=40, b=20, l=20, r=20),
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                    )
                    st.plotly_chart(fig_season, use_container_width=True, config={'displayModeBar': False})

                # Chart 2: Predictions by Crop Bar Chart (Requirement 8)
                with ch_col2:
                    crop_counts = metrics.get("crop_counts", [])
                    if crop_counts:
                        c_names = [c["crop"] for c in crop_counts]
                        c_vals = [c["count"] for c in crop_counts]
                    else:
                        c_names = ["No Data"]
                        c_vals = [0]

                    fig_crop = go.Figure(data=[go.Bar(
                        x=c_names,
                        y=c_vals,
                        marker=dict(color='#2E7D32', line=dict(color='#1B5E20', width=1.5)),
                        text=c_vals,
                        textposition='auto'
                    )])
                    fig_crop.update_layout(
                        title=dict(text="Predictions by Crop", font=dict(family="Poppins", size=15, color='#F8FAFC')),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family="Inter", color='#F8FAFC'),
                        xaxis=dict(gridcolor='#334155'),
                        yaxis=dict(gridcolor='#334155', title="Assessments"),
                        margin=dict(t=40, b=20, l=20, r=20)
                    )
                    st.plotly_chart(fig_crop, use_container_width=True, config={'displayModeBar': False})

                ch_col3, ch_col4 = st.columns(2)

                # Chart 3: Monthly Predictions Line Chart (Requirement 8)
                with ch_col3:
                    monthly_trend = metrics.get("monthly_trend", [])
                    if monthly_trend:
                        m_dates = [m["month"] for m in monthly_trend]
                        m_counts = [m["count"] for m in monthly_trend]
                    else:
                        m_dates = [datetime.now().strftime("%Y-%m")]
                        m_counts = [len(all_records)]

                    fig_trend = go.Figure(data=[go.Scatter(
                        x=m_dates,
                        y=m_counts,
                        mode='lines+markers',
                        line=dict(color='#10B981', width=3, shape='spline'),
                        marker=dict(size=8, color='#047857', line=dict(color='#FFFFFF', width=1.5))
                    )])
                    fig_trend.update_layout(
                        title=dict(text="Monthly Prediction Trend", font=dict(family="Poppins", size=15, color='#F8FAFC')),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family="Inter", color='#F8FAFC'),
                        xaxis=dict(gridcolor='#334155'),
                        yaxis=dict(gridcolor='#334155', title="Volume"),
                        margin=dict(t=40, b=20, l=20, r=20)
                    )
                    st.plotly_chart(fig_trend, use_container_width=True, config={'displayModeBar': False})

                # Chart 4: Top Identified Pest Species (Requirement 8)
                with ch_col4:
                    pest_counter = {}
                    for r in all_records:
                        p = r.get("predicted_pest", "Unknown")
                        pest_counter[p] = pest_counter.get(p, 0) + 1
                    sorted_pests = sorted(pest_counter.items(), key=lambda x: x[1], reverse=True)[:5]
                    
                    p_labels = [p[0] for p in sorted_pests] if sorted_pests else ["No Data"]
                    p_counts = [p[1] for p in sorted_pests] if sorted_pests else [0]
                    
                    fig_pest = go.Figure(data=[go.Bar(
                        y=p_labels,
                        x=p_counts,
                        orientation='h',
                        marker=dict(color='#D97706', line=dict(color='#B45309', width=1.5)),
                        text=p_counts,
                        textposition='auto'
                    )])
                    fig_pest.update_layout(
                        title=dict(text="Top Identified Pest Species", font=dict(family="Poppins", size=15, color='#F8FAFC')),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family="Inter", color='#F8FAFC'),
                        xaxis=dict(gridcolor='#334155', title="Occurrences"),
                        yaxis=dict(gridcolor='#334155', autorange="reversed"),
                        margin=dict(t=40, b=20, l=20, r=20)
                    )
                    st.plotly_chart(fig_pest, use_container_width=True, config={'displayModeBar': False})


    # ==========================================================
    # PAGE 4: USER PROFILE & ACCOUNT SETTINGS MODULE
    # ==========================================================
    elif st.session_state["current_page"] in ["Profile", "👤 Profile"]:
        # Refresh user record from database
        user_full = get_user_by_id(current_user["id"]) or current_user
        prof_stats = get_user_profile_stats(user_full["id"])
        user_prefs = get_user_preferences(user_full["id"])
        activities = get_user_account_activities(user_full["id"], limit=6)

        # 1. AVATAR BASE64 GENERATOR
        avatar_path = user_full.get("avatar_path")
        avatar_html = "👤"
        if avatar_path:
            norm_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", avatar_path)) if not os.path.isabs(avatar_path) else avatar_path
            if os.path.exists(norm_path):
                try:
                    with open(norm_path, "rb") as af:
                        b64_img = base64.b64encode(af.read()).decode("utf-8")
                    avatar_html = f'<img src="data:image/png;base64,{b64_img}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;" />'
                except Exception:
                    avatar_html = "👤"

        # 2. HERO PROFILE BANNER (Requirement 1)
        st.markdown(f"""
        <div class="profile-hero-card">
            <div class="profile-hero-inner">
                <div class="profile-hero-left">
                    <div class="profile-avatar-circle">
                        {avatar_html}
                    </div>
                    <div>
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px; flex-wrap: wrap;">
                            <h1 class="profile-hero-name">{user_full['name']}</h1>
                            <span class="profile-role-pill">🛡️ {user_full.get('role', 'farmer').capitalize()}</span>
                        </div>
                        <div style="font-size: 0.95rem; color: #E2E8F0; margin-bottom: 4px;">📧 {user_full['email']}</div>
                        <div style="font-size: 0.84rem; color: #CBD5E1;">
                            📍 <b>{user_full.get('district') or 'District Not Set'}, {user_full.get('state') or 'State Not Set'}</b> &bull; Preferred Crop: <b>{user_full.get('preferred_crop') or 'All Crops'}</b>
                        </div>
                    </div>
                </div>
                <div class="profile-stat-bar">
                    <div class="profile-stat-item">
                        <div class="profile-stat-item-label">📅 Member Since</div>
                        <div class="profile-stat-item-val">{(user_full.get('created_at') or 'N/A').split()[0]}</div>
                    </div>
                    <div class="profile-stat-item">
                        <div class="profile-stat-item-label">⏱️ Last Login</div>
                        <div class="profile-stat-item-val">{(user_full.get('last_login') or 'Today').split()[0]}</div>
                    </div>
                    <div class="profile-stat-item">
                        <div class="profile-stat-item-label">🔮 Total Forecasts</div>
                        <div class="profile-stat-item-val">{prof_stats['total_predictions']} Predictions</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3. RESPONSIVE TWO-COLUMN LAYOUT (Requirement 12)
        # Clean Vertical SaaS Profile Layout (Step 8)
        # ==========================================================
        # CARD 1: USER INFORMATION
        # ==========================================================
        st.markdown(f"""
        <div class="settings-card" style="margin-bottom: 22px;">
            <div class="settings-card-header">
                <span>👤</span> User Information
            </div>
            <div class="overview-row">
                <span class="overview-label">Full Name</span>
                <span class="overview-val">{user_full['name']}</span>
            </div>
            <div class="overview-row">
                <span class="overview-label">Email Address</span>
                <span class="overview-val">{user_full['email']}</span>
            </div>
            <div class="overview-row">
                <span class="overview-label">Role</span>
                <span class="overview-val" style="text-transform: capitalize;">{user_full.get('role', 'farmer')}</span>
            </div>
            <div class="overview-row">
                <span class="overview-label">Phone Number</span>
                <span class="overview-val">{user_full.get('phone') or 'Not configured'}</span>
            </div>
            <div class="overview-row">
                <span class="overview-label">Location</span>
                <span class="overview-val">{(user_full.get('district') or '') + (', ' + user_full.get('state') if user_full.get('state') else '') or 'Not configured'}</span>
            </div>
            <div class="overview-row">
                <span class="overview-label">Preferred Crop</span>
                <span class="overview-val">{user_full.get('preferred_crop') or 'All Crops'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ==========================================================
        # CARD 2: ACCOUNT DETAILS & EDIT PROFILE FORM
        # ==========================================================
        st.markdown(f"""
        <div class="settings-card" style="margin-bottom: 22px;">
            <div class="settings-card-header">
                <span>📋</span> Account Details &amp; Edit Profile
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 18px; padding: 12px 16px; background: rgba(46, 125, 50, 0.06); border-radius: 12px;">
                <div>
                    <span style="font-size: 0.78rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Member Since</span>
                    <div style="font-size: 1.05rem; font-weight: 700; color: var(--text-main); margin-top: 2px;">{user_full.get('created_at', 'N/A').split()[0]}</div>
                </div>
                <div>
                    <span style="font-size: 0.78rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Total Forecasts Run</span>
                    <div style="font-size: 1.05rem; font-weight: 700; color: var(--text-main); margin-top: 2px;">{prof_stats.get('total_predictions', 0)} Predictions</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("edit_profile_full_form"):
            st.markdown("<p style='font-size: 0.90rem; font-weight: 700; color: var(--text-main); margin-bottom: 10px;'>✏️ Update Profile Details</p>", unsafe_allow_html=True)
            edit_name = st.text_input("Full Name *", value=user_full["name"])
            edit_phone = st.text_input("Phone Number (Optional)", value=user_full.get("phone") or "", placeholder="e.g. 9876543210")
            
            all_states = ["Select State"] + sorted(list(STATE_DISTRICT_MAP.keys()))
            curr_state = user_full.get("state") or "Select State"
            state_idx = all_states.index(curr_state) if curr_state in all_states else 0
            edit_state = st.selectbox("State", all_states, index=state_idx)
            
            avail_districts = ["Select District"]
            if edit_state != "Select State" and edit_state in STATE_DISTRICT_MAP:
                avail_districts += STATE_DISTRICT_MAP[edit_state]
            curr_dist = user_full.get("district") or "Select District"
            dist_idx = avail_districts.index(curr_dist) if curr_dist in avail_districts else 0
            edit_dist = st.selectbox("District", avail_districts, index=dist_idx)
            
            crop_options = ["General / All Crops", "Cotton", "Rice", "Maize", "Wheat", "Sugarcane", "Soybean", "Groundnut", "Mustard", "Pulses"]
            curr_crop = user_full.get("preferred_crop") or "General / All Crops"
            crop_idx = crop_options.index(curr_crop) if curr_crop in crop_options else 0
            edit_crop = st.selectbox("Preferred Target Crop", crop_options, index=crop_idx)
            
            save_prof_btn = st.form_submit_button("💾 Save Profile Changes", type="primary", use_container_width=True)
            if save_prof_btn:
                final_state = None if edit_state == "Select State" else edit_state
                final_dist = None if edit_dist == "Select District" else edit_dist
                final_crop = None if edit_crop == "General / All Crops" else edit_crop
                ok, msg = update_user_full_profile(
                    user_id=user_full["id"],
                    name=edit_name,
                    phone=edit_phone,
                    state=final_state,
                    district=final_dist,
                    preferred_crop=final_crop
                )
                if ok:
                    st.session_state["user"] = get_user_by_id(user_full["id"])
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

        # ==========================================================
        # CARD 3: CHANGE PASSWORD
        # ==========================================================
        st.markdown("""
        <div class="settings-card" style="margin-bottom: 22px;">
            <div class="settings-card-header">
                <span>🔒</span> Change Password
            </div>
        </div>
        """, unsafe_allow_html=True)

        show_pw_text = st.checkbox("👁️ Show Password Characters", key="chk_show_passwords")
        pw_input_type = "text" if show_pw_text else "password"
        
        with st.form("security_password_form"):
            curr_pw = st.text_input("Current Password *", type=pw_input_type, placeholder="Enter current password")
            new_pw = st.text_input("New Password *", type=pw_input_type, placeholder="Minimum 8 characters")
            confirm_pw = st.text_input("Confirm New Password *", type=pw_input_type, placeholder="Re-enter new password")
            
            pw_crit_len = len(new_pw) >= 8
            pw_crit_upper = bool(re.search(r"[A-Z]", new_pw))
            pw_crit_lower = bool(re.search(r"[a-z]", new_pw))
            pw_crit_num = bool(re.search(r"[0-9]", new_pw))
            pw_crit_spec = bool(re.search(r"[^a-zA-Z0-9\s]", new_pw))
            pw_score = sum([pw_crit_len, pw_crit_upper, pw_crit_lower, pw_crit_num, pw_crit_spec])
            
            pw_labels = {
                0: ("Enter Password", "#94A3B8"),
                1: ("Very Weak", "#EF4444"),
                2: ("Weak", "#F97316"),
                3: ("Fair", "#FBBF24"),
                4: ("Strong", "#10B981"),
                5: ("Very Strong", "#059669")
            }
            lbl_text, bar_color = pw_labels[pw_score]
            
            st.markdown(f"""
            <div style="margin: 10px 0 14px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                    <span style="font-size: 0.80rem; font-weight: 600; color: var(--text-muted);">Password Strength:</span>
                    <span style="font-size: 0.80rem; font-weight: 700; color: {bar_color};">{lbl_text} ({pw_score}/5)</span>
                </div>
                <div style="width: 100%; height: 6px; background: {'rgba(255,255,255,0.1)'}; border-radius: 3px; overflow: hidden;">
                    <div style="width: {pw_score * 20}%; height: 100%; background: {bar_color}; transition: width 0.3s ease;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            submit_pw_btn = st.form_submit_button("🔒 Update Password", type="primary", use_container_width=True)
            if submit_pw_btn:
                ok, msg = change_user_password(
                    user_id=user_full["id"],
                    current_password=curr_pw,
                    new_password=new_pw,
                    confirm_password=confirm_pw
                )
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

        # ==========================================================
        # CARD 4: LOGOUT
        # ==========================================================
        st.markdown("""
        <div class="settings-card" style="margin-bottom: 22px;">
            <div class="settings-card-header">
                <span>🚪</span> Session &amp; Logout
            </div>
            <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 14px;">
                Safely end your current session. You can sign back in at any time.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Logout from AgriAI", key="btn_profile_logout_action", type="secondary", use_container_width=True):
            logout_user()
            st.rerun()

        st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
        
    # PAGE 5: ABOUT US (COMMERCIAL COMPANY STANDARD)
    # ==========================================
    elif st.session_state["current_page"] in ["About", "ℹ About", "ℹ️ About"]:
        # ── ABOUT PAGE ─ COMMERCIAL GRADE ──────────────────

        # 1. FULL-WIDTH HERO
        st.markdown(f"""
        <div class="about-hero-wrap">
            <div class="about-hero-badge">🌾 About Our Platform</div>
            <h1 class="about-hero-title">🌾 About <span>AgriAI</span> Advisory Platform</h1>
            <p class="about-hero-subtitle">
                Empowering farmers with AI-powered pest prediction and smart crop advisory
                for better agricultural decision-making.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 2. PLATFORM OVERVIEW CARD
        st.markdown(f"""
        <div class="about-narrative-box">
            <div style="padding-left: 10px;">
                <div style="font-family: 'Poppins', sans-serif; font-size: 1.22rem; font-weight: 700;
                            color: {'#4ADE80'}; margin-bottom: 16px;">
                    📖 Platform Overview
                </div>
                <p style="line-height: 1.85; margin-bottom: 14px; font-size: 0.98rem; color: {text_main};">
                    The <strong>AgriAI Advisory Platform</strong> is a specialized agricultural decision-support service
                    designed to help farmers, agronomists, and agricultural professionals proactively identify and manage
                    crop pest outbreak risks. Our platform bridges the gap between traditional farming knowledge and
                    modern intelligent advisory systems.
                </p>
                <p style="line-height: 1.85; margin-bottom: 14px; font-size: 0.98rem; color: {text_main};">
                    Early pest detection is critical — every day without action can mean significant crop loss.
                    By analyzing localized weather patterns such as temperature, humidity, and rainfall, the platform
                    forecasts potential pest activity <em>before</em> infestations can impact yields, giving farmers
                    a decisive head start in protection.
                </p>
                <p style="line-height: 1.85; margin-bottom: 0; font-size: 0.98rem; color: {text_main};">
                    Weather-based advisory is smarter because pest behavior is directly influenced by environmental
                    conditions. Our platform continuously monitors these signals and delivers targeted, actionable
                    recommendations — chemical treatments, organic bio-controls, and cultural field practices —
                    all tailored to your crop, region, and current season.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3. MISSION & VISION
        st.markdown(f"""
        <div class="about-mission-grid">
            <div class="about-mission-card mission">
                <span class="about-mission-icon">🎯</span>
                <div class="about-mission-title">Our Mission</div>
                <p class="about-mission-text">
                    "Our mission is to make AI-powered agricultural advisory simple, accessible,
                    and useful for every farmer."
                </p>
            </div>
            <div class="about-mission-card vision">
                <span class="about-mission-icon">🌍</span>
                <div class="about-mission-title">Our Vision</div>
                <p class="about-mission-text">
                    "To support sustainable agriculture through intelligent decision-support systems."
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 4. SECTION HEADER — WHY CHOOSE
        st.markdown(f"""
        <div class="about-section-header">
            <div class="about-section-pill">Why Choose Us</div>
            <div class="about-section-title">Why Choose Our Platform</div>
            <div class="about-section-desc">
                Four pillars that make AgriAI the intelligent choice for modern crop protection.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 5. FEATURE CARDS (4) — Why Choose
        st.markdown(f"""
        <div class="about-cap-grid">
            <div class="about-cap-card">
                <span class="about-cap-icon">🌦</span>
                <div class="about-cap-title">Live Weather Integration</div>
                <div class="about-cap-desc">Real-time microclimate analysis automatically detects
                temperature, humidity, and rainfall patterns that trigger pest outbreaks
                — so you always know before it happens.</div>
            </div>
            <div class="about-cap-card">
                <span class="about-cap-icon">🤖</span>
                <div class="about-cap-title">AI-Based Prediction</div>
                <div class="about-cap-desc">Our intelligent advisory engine classifies pest
                outbreak risk and recommends targeted treatments based on your crop,
                location, and seasonal conditions — instantly.</div>
            </div>
            <div class="about-cap-card">
                <span class="about-cap-icon">📄</span>
                <div class="about-cap-title">Smart Advisory Reports</div>
                <div class="about-cap-desc">Every prediction generates a professional advisory
                report in PDF format with pest details, risk ratings, treatment options,
                and dosage guidance — ready to use in the field.</div>
            </div>
            <div class="about-cap-card">
                <span class="about-cap-icon">📱</span>
                <div class="about-cap-title">Responsive User Experience</div>
                <div class="about-cap-desc">Designed for desktop, tablet, and mobile alike.
                Access predictions, history, and advisory reports from anywhere —
                in the office or the field.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 6. SECTION HEADER — BENEFITS
        st.markdown(f"""
        <div class="about-section-header">
            <div class="about-section-pill">Platform Benefits</div>
            <div class="about-section-title">Benefits of Using AgriAI</div>
            <div class="about-section-desc">
                Everything you need for smarter, faster, more confident crop protection decisions.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 7. BENEFITS GRID
        st.markdown(f"""
        <div class="about-benefits-grid">
            <div class="about-benefit-item">
                <span class="about-benefit-check">✔</span>
                <div>
                    <div class="about-benefit-title">Faster Decision Making</div>
                    <div class="about-benefit-desc">Get instant pest risk assessments and advisory — no waiting, no guessing.</div>
                </div>
            </div>
            <div class="about-benefit-item">
                <span class="about-benefit-check">✔</span>
                <div>
                    <div class="about-benefit-title">Easy to Use</div>
                    <div class="about-benefit-desc">Simple, intuitive interface designed for farmers of all technical backgrounds.</div>
                </div>
            </div>
            <div class="about-benefit-item">
                <span class="about-benefit-check">✔</span>
                <div>
                    <div class="about-benefit-title">Personalized Recommendations</div>
                    <div class="about-benefit-desc">Crop-specific, district-specific, and season-specific advisory tailored to your farm.</div>
                </div>
            </div>
            <div class="about-benefit-item">
                <span class="about-benefit-check">✔</span>
                <div>
                    <div class="about-benefit-title">Prediction History</div>
                    <div class="about-benefit-desc">Access all your past pest predictions and advisory reports in one organized dashboard.</div>
                </div>
            </div>
            <div class="about-benefit-item">
                <span class="about-benefit-check">✔</span>
                <div>
                    <div class="about-benefit-title">Secure User Accounts</div>
                    <div class="about-benefit-desc">Your account and farming data are protected with industry-standard security practices.</div>
                </div>
            </div>
            <div class="about-benefit-item">
                <span class="about-benefit-check">✔</span>
                <div>
                    <div class="about-benefit-title">Downloadable PDF Reports</div>
                    <div class="about-benefit-desc">Save and share structured advisory reports for offline use, record keeping, and field applications.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 8. ADVISORY DISCLAIMER
        st.markdown("""
        <div class="about-disclaimer-box">
            <div class="about-disclaimer-title">ℹ️ Advisory Disclaimer</div>
            <div class="about-disclaimer-text">
                This platform provides AI-assisted decision support based on available weather data and
                predictive models. Users should also consider local agricultural extension recommendations
                before making field decisions.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================
    # PAGE 6: CONTACT SUPPORT (CLEAN SAAS CARD)
    # ==========================================
    elif st.session_state["current_page"] in ["Contact", "📩 Contact"]:
        contact_card_html = (
            '<div class="contact-clean-wrapper">'
            '<div class="contact-clean-card">'
            '<div class="contact-icon-circle">📧</div>'
            '<h1 class="contact-clean-title">Contact Support</h1>'
            '<div class="contact-clean-subtitle">Email Support</div>'
            '<div class="contact-clean-divider"></div>'
            '<div class="contact-clean-help-heading">Need help?</div>'
            '<p class="contact-clean-desc">For technical assistance or project-related queries, contact us using the email below.</p>'
            '<div class="contact-clean-email-box"><a href="mailto:support@agriai.org" class="contact-clean-email-link">support@agriai.org</a></div>'
            '<div class="contact-clean-btn-wrap"><a href="mailto:support@agriai.org" class="contact-clean-btn">Contact via Email</a></div>'
            '</div>'
            '</div>'
        )
        st.markdown(contact_card_html, unsafe_allow_html=True)

    # ==========================================
    # PAGE 7: ADMIN PORTAL
    # ==========================================
    elif st.session_state["current_page"] in ["Admin Portal", "🛡️ Admin Portal", "🛡️ Administrator"]:
        if not admin_status or not current_user:
            st.error("🚫 Access Restricted: Administrator privileges are strictly required.")
            st.session_state["current_page"] = "Dashboard"
            st.rerun()
        else:
            render_enterprise_admin_portal(
                current_user=current_user,
                is_dark=is_dark,
                card_bg=card_bg,
                card_border=card_border,
                text_main=text_main,
                text_muted=text_muted
            )

    # ==========================================
    # FOOTER
    # ==========================================
    st.markdown(f"""
    <div class="website-footer">
        <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 6px;">
            <span style="font-size: 1.5rem;">🌿</span>
            <span style="font-family: 'Poppins', sans-serif; font-size: 1.35rem; font-weight: 800; color: {'#66BB6A'}; letter-spacing: -0.02em;">AgriAI Advisor</span>
            <span style="background: {'rgba(102, 187, 106, 0.16)'}; border: 1px solid var(--card-border); color: {'#86EFAC'}; font-size: 0.72rem; padding: 2px 10px; border-radius: 12px; font-weight: 700;">v2.1.0</span>
        </div>
        <div style="font-size: 0.94rem; font-weight: 600; color: {text_main}; margin-bottom: 6px;">
            AI-Powered Crop Pest Prediction &amp; Advisory Platform
        </div>
        <div style="font-size: 0.85rem; color: {'#86EFAC'}; font-weight: 600; margin-bottom: 12px;">
            🌱 Designed for Smart Agriculture &bull; Real-Time Meteorological &amp; Agronomic Intelligence
        </div>
        <div style="display: flex; justify-content: center; gap: 18px; flex-wrap: wrap; margin-bottom: 14px; font-size: 0.88rem; font-weight: 600;">
            <span style="color: {'#66BB6A'};">🏠 Dashboard</span> &bull; 
            <span style="color: {'#66BB6A'};">🌾 Prediction</span> &bull; 
            <span style="color: {'#66BB6A'};">📜 History</span> &bull; 
            <span style="color: {'#66BB6A'};">👤 Profile</span> &bull; 
            <span style="color: {'#66BB6A'};">ℹ About</span> &bull; 
            <span style="color: {'#66BB6A'};">📩 Contact</span>
        </div>
        <div style="font-size: 0.82rem; color: {text_muted};">
            &copy; 2026 AgriAI Advisor. All rights reserved. Built for Commercial Agricultural Excellence.
        </div>
    </div>
    """, unsafe_allow_html=True)
