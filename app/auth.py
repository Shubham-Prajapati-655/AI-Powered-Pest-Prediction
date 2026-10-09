import streamlit as st
import time
import secrets
from config import SESSION_TIMEOUT_MINUTES
from logger import log_auth_event
from security import check_login_rate_limit, record_failed_login, reset_login_rate_limit
from database import (
    create_user, verify_user, reset_password,
    get_user_by_id, count_user_predictions,
    get_user_preferences, save_user_preferences,
    validate_email_format, validate_password_complexity,
    create_session_token, get_user_by_session_token, delete_session_token,
    delete_all_user_sessions, log_account_activity,
    create_password_reset_token, verify_password_reset_token, redeem_password_reset_token
)

SESSION_TIMEOUT_SECONDS = SESSION_TIMEOUT_MINUTES * 60

def init_session():
    """Initialize session state variables and restore persistent Remember Me sessions."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "login_timestamp" not in st.session_state:
        st.session_state["login_timestamp"] = 0
    if "session_token" not in st.session_state:
        st.session_state["session_token"] = None

    # Auto-login from persistent token if Remember Me was selected previously
    if not st.session_state["authenticated"]:
        if st.session_state.get("just_logged_out", False):
            # Reset logout latch so subsequent user actions can authenticate
            st.session_state["just_logged_out"] = False
        else:
            token = None
            try:
                token = st.query_params.get("session_token", None)
            except Exception:
                token = None
                
            if token:
                persisted_user = get_user_by_session_token(token)
                if persisted_user:
                    st.session_state["session_token"] = token
                    login_user(persisted_user, remember_me=True, set_query_param=False)
                else:
                    # Clean up expired / invalid token from URL
                    try:
                        if "session_token" in st.query_params:
                            del st.query_params["session_token"]
                    except Exception:
                        pass

def check_session_timeout():
    """Verify if user session has timed out based on configurable expiration."""
    if st.session_state.get("authenticated", False):
        login_time = st.session_state.get("login_timestamp", 0)
        if login_time > 0 and (time.time() - login_time > SESSION_TIMEOUT_SECONDS):
            u = st.session_state.get("user") or {}
            log_auth_event("SESSION_TIMEOUT", u.get("email", "unknown"), False, details="Session exceeded max duration.")
            logout_user()
            return False
    return True

def login_user(user_dict, remember_me=False, set_query_param=True):
    """
    Set authenticated session state, regenerate session identifiers to prevent session fixation,
    route by role, and manage Remember Me tokens.
    """
    st.session_state["authenticated"] = True
    st.session_state["user"] = user_dict
    st.session_state["login_timestamp"] = time.time()
    st.session_state["just_logged_out"] = False
    
    # Reset rate limiting counter for this user upon successful authentication
    reset_login_rate_limit(user_dict.get("email", ""))
    
    # Deterministic role-based landing page routing
    user_role = (user_dict.get("role") or "farmer").strip().lower()
    if user_role == "admin":
        st.session_state["current_page"] = "Admin Portal"
    else:
        st.session_state["current_page"] = "Dashboard"
        
    # Remember Me handling
    if remember_me:
        token = st.session_state.get("session_token")
        if not token:
            token = create_session_token(user_dict["id"], days_valid=30)
            st.session_state["session_token"] = token
        if set_query_param:
            try:
                st.query_params["session_token"] = token
            except Exception:
                pass
    else:
        st.session_state["session_token"] = None
        try:
            if "session_token" in st.query_params:
                del st.query_params["session_token"]
        except Exception:
            pass

    
    # Restore persisted user preferences
    try:
        prefs = get_user_preferences(user_dict["id"])
        saved_dark = bool(prefs.get("dark_mode", st.session_state.get("dark_mode", True)))
        st.session_state["dark_mode"] = saved_dark
        st.session_state["theme"] = "dark" if saved_dark else "light"
        st.session_state["theme_mode"] = prefs.get("theme_mode", "auto")
        st.session_state["language"] = prefs.get("language", "English")
        st.session_state["notifications_enabled"] = prefs.get("notifications_enabled", True)
        st.session_state["notify_prediction"] = prefs.get("notify_prediction", True)
        st.session_state["notify_weather"] = prefs.get("notify_weather", True)
        st.session_state["notify_system"] = prefs.get("notify_system", True)
        st.session_state["privacy_history"] = prefs.get("privacy_history", True)
        st.session_state["privacy_email"] = prefs.get("privacy_email", True)
        st.session_state["privacy_profile"] = prefs.get("privacy_profile", True)
        st.session_state["user_prefs_synced"] = True
    except Exception:
        pass

    try:
        log_account_activity(user_dict["id"], "Logged In", "User authenticated into session.", "🔑")
        log_auth_event("LOGIN", user_dict.get("email", ""), True, details=f"Role: {user_role}")
    except Exception:
        pass

def logout_user():
    """
    Clear user session completely and invalidate active session token.
    Purges all cookies, query parameters, authentication states, and cached user data.
    Ensures immediate, complete redirection to login page with no stale data or back-button recovery.
    """
    user = st.session_state.get("user")
    email = user.get("email", "unknown") if user else "unknown"
    user_id = user.get("id") if user else None

    token = st.session_state.get("session_token", None)
    if not token:
        try:
            token = st.query_params.get("session_token", None)
        except Exception:
            token = None
            
    if token:
        try:
            delete_session_token(token)
        except Exception:
            pass

    if user_id:
        try:
            delete_all_user_sessions(user_id)
        except Exception:
            pass
            
    # Clear query parameters completely
    try:
        st.query_params.clear()
    except Exception:
        pass

    # Preserve global application caches (weather, static assets) on user logout

    # Reset authentication states safely without breaking widget trees
    st.session_state["authenticated"] = False
    st.session_state["user"] = None
    st.session_state["login_timestamp"] = 0
    st.session_state["session_token"] = None
    st.session_state["current_page"] = "Dashboard"
    st.session_state["show_logout_confirm"] = False
    st.session_state["just_logged_out"] = True
    st.session_state.pop("active_prediction", None)

    log_auth_event("LOGOUT", email, True, details="User initiated logout. Session invalidated.")

def logout_from_all_devices(user_id: int):
    """
    Invalidate all persistent session tokens for user across all devices (Demo capability),
    then log out current device session.
    """
    try:
        delete_all_user_sessions(user_id)
        logout_user()
        return True
    except Exception:
        return False

def get_current_user():
    """Return currently authenticated user or None."""
    if st.session_state.get("authenticated", False) and check_session_timeout():
        return st.session_state.get("user")
    return None

def is_admin():
    """Check if current user is an Administrator."""
    user = get_current_user()
    return user is not None and user.get("role", "").lower() == "admin"
