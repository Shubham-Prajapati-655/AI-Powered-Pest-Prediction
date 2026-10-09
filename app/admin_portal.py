import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import io

from config import (
    APP_VERSION, APP_ENV, DEBUG, LOG_FILE, DATABASE_URL,
    LOGS_DIR, BACKUPS_DIR, UPLOADS_DIR, DATABASE_DIR, DEFAULT_SQLITE_PATH
)
from logger import get_recent_logs, log_admin_action, get_logger
from backup_manager import (
    create_manual_backup, list_available_backups, restore_backup,
    get_backup_bytes, trigger_auto_backup_demo, get_backup_storage_stats
)
from database import (
    get_all_users_extended, delete_user, update_user_status, update_user_role,
    admin_update_user, get_admin_dashboard_kpis, get_admin_analytics_data,
    get_database_system_stats, get_all_activity_logs, get_all_prediction_history,
    delete_prediction_history, get_contact_queries, update_contact_query_status,
    delete_contact_query, change_user_password, update_user_full_profile,
    log_account_activity, get_connection, get_database_health_summary
)
from pdf_generator import generate_system_summary_pdf, generate_analytics_report_pdf

# Track application start time for uptime metric
if "app_start_time" not in st.session_state:
    st.session_state["app_start_time"] = datetime.now()

# ==========================================================
# DIALOG MODALS
# ==========================================================

@st.dialog("👤 User Account Profile", width="medium")
def show_user_detail_dialog(user):
    st.markdown(f"""
    <div style="padding: 6px 0 16px 0;">
        <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 16px;">
            <div style="width: 52px; height: 52px; border-radius: 50%; background: #2E7D32; color: #ffffff; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; font-weight: 700;">
                {user['name'][:1].upper()}
            </div>
            <div>
                <h3 style="margin: 0; font-family: 'Poppins', sans-serif;">{user['name']}</h3>
                <span style="font-size: 0.86rem; color: #64748B;">{user['email']}</span>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
            <div style="background: rgba(46, 125, 50, 0.06); padding: 10px 14px; border-radius: 10px; border: 1px solid rgba(46, 125, 50, 0.15);">
                <div style="font-size: 0.76rem; color: #64748B; font-weight: 600; text-transform: uppercase;">User ID</div>
                <div style="font-size: 1.1rem; font-weight: 700;">#{user['id']}</div>
            </div>
            <div style="background: rgba(46, 125, 50, 0.06); padding: 10px 14px; border-radius: 10px; border: 1px solid rgba(46, 125, 50, 0.15);">
                <div style="font-size: 0.76rem; color: #64748B; font-weight: 600; text-transform: uppercase;">Account Role</div>
                <div style="font-size: 1.1rem; font-weight: 700; text-transform: capitalize;">{user.get('role', 'farmer')}</div>
            </div>
            <div style="background: rgba(46, 125, 50, 0.06); padding: 10px 14px; border-radius: 10px; border: 1px solid rgba(46, 125, 50, 0.15);">
                <div style="font-size: 0.76rem; color: #64748B; font-weight: 600; text-transform: uppercase;">Status</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: {'#16A34A' if user.get('status') == 'Active' else '#DC2626'};">{user.get('status', 'Active')}</div>
            </div>
            <div style="background: rgba(46, 125, 50, 0.06); padding: 10px 14px; border-radius: 10px; border: 1px solid rgba(46, 125, 50, 0.15);">
                <div style="font-size: 0.76rem; color: #64748B; font-weight: 600; text-transform: uppercase;">Predictions Generated</div>
                <div style="font-size: 1.1rem; font-weight: 700;">{user.get('prediction_count', 0)}</div>
            </div>
        </div>
        <div style="font-size: 0.88rem; line-height: 1.6; color: #475569;">
            <b>📞 Phone:</b> {user.get('phone') or 'Not Provided'}<br>
            <b>📍 Region:</b> {user.get('district') or 'N/A'}, {user.get('state') or 'N/A'}<br>
            <b>🌾 Primary Crop:</b> {user.get('preferred_crop') or 'General Farming'}<br>
            <b>📅 Member Since:</b> {user.get('created_at', 'N/A')}<br>
            <b>⏱️ Last Login:</b> {user.get('last_login') or 'Never'}
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Close Window", use_container_width=True):
        st.rerun()

@st.dialog("✏️ Edit User Account", width="medium")
def show_user_edit_dialog(user):
    st.markdown(f"#### Edit Account: {user['name']} (ID: #{user['id']})")
    with st.form(f"edit_user_form_{user['id']}"):
        new_name = st.text_input("Full Name", value=user["name"])
        new_email = st.text_input("Email Address", value=user["email"])
        new_role = st.selectbox("Role", ["farmer", "admin"], index=0 if user.get("role") == "farmer" else 1)
        new_status = st.selectbox("Status", ["Active", "Suspended"], index=0 if user.get("status") == "Active" else 1)
        
        submitted = st.form_submit_button("💾 Save Account Changes", use_container_width=True)
        if submitted:
            if not new_name.strip() or not new_email.strip():
                st.error("Name and Email cannot be empty.")
            else:
                admin_update_user(user["id"], new_name, new_email, new_role, new_status)
                st.success("User account updated successfully.")
                st.rerun()

@st.dialog("🌾 Pest Advisory Prediction Details", width="large")
def show_prediction_detail_dialog(record):
    r_id = record.get("id")
    r_crop = record.get("crop", "Unknown")
    r_pest = record.get("predicted_pest", "None")
    r_risk = record.get("predicted_risk", "Low")
    r_time = record.get("created_at", "N/A")
    r_user = record.get("user_email", "Anonymous")
    r_state = record.get("state", "N/A")
    r_district = record.get("district", "N/A")
    r_season = record.get("sowing_season", "Kharif")
    r_weather_season = record.get("weather_season", "Monsoon")
    r_pest_prob = float(record.get("pest_prob", 60.0))
    r_risk_prob = float(record.get("risk_prob", 75.0))
    r_temp = float(record.get("temperature", 28.0))
    r_hum = float(record.get("humidity", 65.0))
    r_rain = float(record.get("rainfall", 120.0))
    r_thi = float(record.get("thi", 75.0))
    
    st.markdown(f"""
    <div style="background: rgba(46, 125, 50, 0.08); border: 1px solid rgba(46, 125, 50, 0.2); border-radius: 14px; padding: 16px 20px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
                <h3 style="margin: 0; font-family: 'Poppins', sans-serif; color: #1B5E20;">
                    🌾 {r_crop} &bull; {r_district}, {r_state}
                </h3>
                <div style="font-size: 0.85rem; color: #475569; margin-top: 4px;">
                    User: <b>{r_user}</b> &bull; Record ID: <b>#{r_id}</b> &bull; Date: {r_time}
                </div>
            </div>
            <div>
                <span style="display: inline-block; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.9rem; background: {'#FEE2E2' if r_risk == 'High' else '#FEF3C7' if r_risk == 'Medium' else '#DCFCE7'}; color: {'#991B1B' if r_risk == 'High' else '#92400E' if r_risk == 'Medium' else '#166534'};">
                    {r_risk} Risk
                </span>
            </div>
        </div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px;">
        <div style="background: var(--card-bg, #f8fafc); border: 1px solid var(--card-border, #e2e8f0); border-radius: 10px; padding: 10px 14px; text-align: center;">
            <div style="font-size: 0.75rem; color: #64748b; font-weight: 600;">PREDICTED PEST</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #1b5e20;">{r_pest}</div>
            <div style="font-size: 0.75rem; color: #64748b;">{r_pest_prob:.1f}% Confidence</div>
        </div>
        <div style="background: var(--card-bg, #f8fafc); border: 1px solid var(--card-border, #e2e8f0); border-radius: 10px; padding: 10px 14px; text-align: center;">
            <div style="font-size: 0.75rem; color: #64748b; font-weight: 600;">TEMPERATURE</div>
            <div style="font-size: 1.05rem; font-weight: 700;">{r_temp:.1f} °C</div>
            <div style="font-size: 0.75rem; color: #64748b;">THI: {r_thi:.1f}</div>
        </div>
        <div style="background: var(--card-bg, #f8fafc); border: 1px solid var(--card-border, #e2e8f0); border-radius: 10px; padding: 10px 14px; text-align: center;">
            <div style="font-size: 0.75rem; color: #64748b; font-weight: 600;">HUMIDITY</div>
            <div style="font-size: 1.05rem; font-weight: 700;">{r_hum:.1f} %</div>
            <div style="font-size: 0.75rem; color: #64748b;">Rain: {r_rain:.1f} mm</div>
        </div>
        <div style="background: var(--card-bg, #f8fafc); border: 1px solid var(--card-border, #e2e8f0); border-radius: 10px; padding: 10px 14px; text-align: center;">
            <div style="font-size: 0.75rem; color: #64748b; font-weight: 600;">SEASONS</div>
            <div style="font-size: 1.05rem; font-weight: 700;">{r_season}</div>
            <div style="font-size: 0.75rem; color: #64748b;">{r_weather_season}</div>
        </div>
    </div>
    <div style="background: var(--card-bg, #f8fafc); border: 1px solid var(--card-border, #e2e8f0); border-radius: 12px; padding: 16px; margin-bottom: 16px;">
        <h4 style="margin: 0 0 10px 0; color: #1B5E20;">🌿 Recommended Treatment & Controls</h4>
        <div style="font-size: 0.90rem; line-height: 1.6;">
            <b>🧪 Chemical Pesticide:</b> {record.get('pesticide', 'Standard Recommended Formulation')}<br>
            <b>⚖️ Dosage:</b> {record.get('dosage', 'Standard field dose according to CIBRC guidelines')}<br>
            <b>🌱 Organic / Biological Control:</b> {record.get('organic_control', 'Neem Seed Kernel Extract (NSKE 5%) or Trichoderma')}<br>
            <b>⚠️ Safety Notes:</b> {record.get('safety_notes', 'Wear protective gloves, eye protection, and mask during handling.')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Close Details", use_container_width=True):
        st.rerun()

@st.dialog("📩 Contact Message Details", width="medium")
def show_contact_detail_dialog(query):
    qid = query.get("id")
    q_name = query.get("name", "Farmer")
    q_email = query.get("email", "N/A")
    q_sub = query.get("subject", "No Subject")
    q_msg = query.get("message", "No message body")
    q_date = query.get("created_date", "N/A")
    q_status = query.get("status", "Pending")
    
    st.markdown(f"""
    <div style="padding: 4px 0 12px 0;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
            <div>
                <h4 style="margin: 0; font-family: 'Poppins', sans-serif;">{q_sub}</h4>
                <div style="font-size: 0.85rem; color: #64748B; margin-top: 4px;">From: <b>{q_name}</b> ({q_email})</div>
                <div style="font-size: 0.80rem; color: #94A3B8;">Submitted: {q_date}</div>
            </div>
            <span style="display: inline-block; padding: 4px 12px; border-radius: 18px; font-weight: 700; font-size: 0.80rem; background: {'#DCFCE7' if q_status == 'Resolved' else '#FEE2E2'}; color: {'#166534' if q_status == 'Resolved' else '#991B1B'};">
                {q_status}
            </span>
        </div>
        <div style="background: rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; padding: 16px; font-size: 0.92rem; line-height: 1.6; margin-bottom: 16px;">
            {q_msg}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        if q_status != "Resolved" and st.button("Mark as Resolved", key=f"dlg_res_{qid}", type="primary", use_container_width=True):
            update_contact_query_status(qid, "Resolved")
            st.success("Marked as Resolved.")
            st.rerun()
        elif q_status == "Resolved" and st.button("Mark as Pending", key=f"dlg_pen_{qid}", use_container_width=True):
            update_contact_query_status(qid, "Pending")
            st.info("Marked as Pending.")
            st.rerun()
    with c2:
        if st.button("Delete Query", key=f"dlg_del_{qid}", use_container_width=True):
            delete_contact_query(qid)
            st.success("Query deleted.")
            st.rerun()

# ==========================================================
# MAIN ENTERPRISE ADMIN PORTAL RENDERER
# ==========================================================

def render_enterprise_admin_portal(current_user, is_dark, card_bg, card_border, text_main, text_muted):
    """
    Renders the modern, enterprise-grade SaaS administrative dashboard.
    Strictly restricted to Admin users.
    """
    # Injected Premium Dark Mode Admin Styling
    st.markdown("""
    <style>
        .admin-hero-banner {
            background: linear-gradient(135deg, #181A1F 0%, #23262F 50%, #1a3822 100%) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 18px !important;
            padding: 28px 32px !important;
            box-shadow: 0 10px 35px rgba(0, 0, 0, 0.12) !important;
            margin-bottom: 24px !important;
        }
        .admin-hero-title {
            font-family: 'Poppins', sans-serif !important;
            font-size: 34px !important;
            font-weight: 800 !important;
            color: #F8FAFC !important;
            margin: 8px 0 6px 0 !important;
        }
        .admin-hero-subtitle {
            font-family: 'Inter', sans-serif !important;
            font-size: 16px !important;
            color: #94A3B8 !important;
            margin: 0 !important;
        }
        .admin-kpi-card {
            background: #23262F !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 18px !important;
            padding: 18px 16px !important;
            box-shadow: 0 10px 35px rgba(0, 0, 0, 0.12) !important;
            transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease !important;
        }
        .admin-kpi-card:hover {
            transform: translateY(-4px) !important;
            box-shadow: 0 14px 40px rgba(0, 0, 0, 0.22) !important;
            border-color: #43A047 !important;
        }
        .admin-kpi-title {
            font-family: 'Inter', sans-serif !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            color: #94A3B8 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.04em !important;
        }
        .admin-kpi-num {
            font-family: 'Poppins', sans-serif !important;
            font-size: 26px !important;
            font-weight: 800 !important;
            color: #F8FAFC !important;
            margin: 6px 0 2px 0 !important;
        }
        .admin-kpi-sub {
            font-family: 'Inter', sans-serif !important;
            font-size: 12px !important;
            color: #94A3B8 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # 1. LANDING HERO HEADER
    st.markdown(f"""
    <div class="admin-hero-banner">
        <div class="admin-hero-badge">
            🛡️ Enterprise Operations Center &bull; Telemetry Active
        </div>
        <h1 class="admin-hero-title">👋 Welcome, {current_user['name']}</h1>
        <p class="admin-hero-subtitle">
            Monitor platform activity, users, predictions, and system health in real-time.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 2. 6 KPI CARDS
    kpis = get_admin_dashboard_kpis()
    
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.markdown(f"""
        <div class="admin-kpi-card">
            <div class="admin-kpi-header">
                <span class="admin-kpi-title">Total Users</span>
                <div class="admin-kpi-icon-wrap">👥</div>
            </div>
            <div class="admin-kpi-num">{kpis['total_users']}</div>
            <div class="admin-kpi-sub"><span>🟢</span> Active Registry</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="admin-kpi-card">
            <div class="admin-kpi-header">
                <span class="admin-kpi-title">Farmers</span>
                <div class="admin-kpi-icon-wrap">🌾</div>
            </div>
            <div class="admin-kpi-num">{kpis['total_farmers']}</div>
            <div class="admin-kpi-sub"><span>🚜</span> Field Producers</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="admin-kpi-card">
            <div class="admin-kpi-header">
                <span class="admin-kpi-title">Predictions</span>
                <div class="admin-kpi-icon-wrap">🔮</div>
            </div>
            <div class="admin-kpi-num">{kpis['total_predictions']}</div>
            <div class="admin-kpi-sub"><span>⚡</span> ML Inferences</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="admin-kpi-card">
            <div class="admin-kpi-header">
                <span class="admin-kpi-title">PDF Reports</span>
                <div class="admin-kpi-icon-wrap">📄</div>
            </div>
            <div class="admin-kpi-num">{kpis['pdf_reports']}</div>
            <div class="admin-kpi-sub"><span>📥</span> Advisory Dossiers</div>
        </div>
        """, unsafe_allow_html=True)
    with k5:
        st.markdown(f"""
        <div class="admin-kpi-card">
            <div class="admin-kpi-header">
                <span class="admin-kpi-title">Queries</span>
                <div class="admin-kpi-icon-wrap">📩</div>
            </div>
            <div class="admin-kpi-num">{kpis['contact_queries']}</div>
            <div class="admin-kpi-sub"><span>💬</span> Help Desk Log</div>
        </div>
        """, unsafe_allow_html=True)
    with k6:
        st.markdown(f"""
        <div class="admin-kpi-card">
            <div class="admin-kpi-header">
                <span class="admin-kpi-title">System Status</span>
                <div class="admin-kpi-icon-wrap">🟢</div>
            </div>
            <div class="admin-kpi-num" style="font-size: 1.35rem; color: #16A34A; margin-top: 4px;">100% OK</div>
            <div class="admin-kpi-sub"><span>🛡️</span> All Nodes Green</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. ENTERPRISE TAB NAVIGATION (LAZY EVALUATION VIA MODERN PILLS)
    admin_tab_options = [
        "👥 User Management",
        "🔮 Prediction Log",
        "📩 Contact Queries",
        "📊 Analytics Dashboard",
        "🗄️ Database & Backups",
        "📤 Export Center",
        "📜 Activity Logs",
        "👤 Admin Profile",
        "⚙️ System Settings",
        "🩺 System Health & Monitoring"
    ]
    selected_tab = st.pills(
        "Operational Modules",
        admin_tab_options,
        default=st.session_state.get("admin_active_nav_tab", admin_tab_options[0]) or admin_tab_options[0],
        key="admin_active_nav_tab",
        label_visibility="collapsed"
    )
    if not selected_tab:
        selected_tab = admin_tab_options[0]

    # ----------------------------------------------------
    # TAB 1: USER MANAGEMENT
    # ----------------------------------------------------
    if selected_tab == "👥 User Management":
        st.markdown("### 👥 User Directory & Access Management")
        st.markdown("<p style='color: var(--text-muted); font-size: 0.9rem;'>Search, monitor, update roles, suspend, or manage platform user accounts.</p>", unsafe_allow_html=True)
        
        # Search & Filter Bar
        f_col1, f_col2, f_col3, f_col4 = st.columns([3, 1.5, 1.5, 1.5])
        with f_col1:
            u_search = st.text_input("🔍 Search Users", placeholder="Search by name or email...", key="admin_u_search")
        with f_col2:
            u_role_filter = st.selectbox("Role Filter", ["All", "farmer", "admin"], key="admin_u_role")
        with f_col3:
            u_status_filter = st.selectbox("Status Filter", ["All", "Active", "Suspended"], key="admin_u_status")
        with f_col4:
            u_sort = st.selectbox("Sort By", ["Newest First", "Oldest First", "Most Predictions", "Name (A-Z)"], key="admin_u_sort")

        all_users = get_all_users_extended(
            search=u_search,
            role_filter=u_role_filter,
            status_filter=u_status_filter
        )

        # Sorting logic
        if u_sort == "Oldest First":
            all_users = sorted(all_users, key=lambda x: x["id"])
        elif u_sort == "Most Predictions":
            all_users = sorted(all_users, key=lambda x: x.get("prediction_count", 0), reverse=True)
        elif u_sort == "Name (A-Z)":
            all_users = sorted(all_users, key=lambda x: x["name"].lower())
        else:
            all_users = sorted(all_users, key=lambda x: x["id"], reverse=True)

        st.caption(f"Showing **{len(all_users)}** user accounts matching filters.")

        if all_users:
            # Pagination
            page_size = 10
            total_pages = max(1, (len(all_users) + page_size - 1) // page_size)
            curr_page = st.number_input("Page", min_value=1, max_value=total_pages, step=1, key="admin_u_page")
            start_idx = (curr_page - 1) * page_size
            page_users = all_users[start_idx : start_idx + page_size]

            # Display Users Table View
            user_table_data = []
            for u in page_users:
                user_table_data.append({
                    "User ID": f"#{u['id']}",
                    "Full Name": u["name"],
                    "Email Address": u["email"],
                    "Role": u.get("role", "farmer").capitalize(),
                    "Status": u.get("status", "Active"),
                    "Predictions": u.get("prediction_count", 0),
                    "Registered Date": u.get("created_at", "N/A"),
                    "Last Login": u.get("last_login") or "Never"
                })
            u_df = pd.DataFrame(user_table_data)
            st.dataframe(u_df, use_container_width=True, hide_index=True)

            # Actions Selector
            st.markdown("##### ⚡ Quick Actions on User Accounts")
            u_action_col1, u_action_col2, u_action_col3, u_action_col4 = st.columns([3, 1.5, 1.5, 1.5])
            with u_action_col1:
                selected_user_id = st.selectbox(
                    "Select User for Action",
                    options=[u["id"] for u in page_users],
                    format_func=lambda uid: f"#{uid} - {next((x['name'] for x in page_users if x['id'] == uid), '')} ({next((x['email'] for x in page_users if x['id'] == uid), '')})",
                    key="admin_u_select"
                )
            
            sel_user = next((u for u in page_users if u["id"] == selected_user_id), None)
            if sel_user:
                with u_action_col2:
                    if st.button("👁 View Profile", key=f"btn_v_{selected_user_id}", use_container_width=True):
                        show_user_detail_dialog(sel_user)
                with u_action_col3:
                    if st.button("✏ Edit User", key=f"btn_e_{selected_user_id}", use_container_width=True):
                        show_user_edit_dialog(sel_user)
                with u_action_col4:
                    curr_st = sel_user.get("status", "Active")
                    new_toggle_st = "Suspended" if curr_st == "Active" else "Active"
                    toggle_label = "🔒 Suspend" if curr_st == "Active" else "🟢 Activate"
                    if st.button(toggle_label, key=f"btn_togg_{selected_user_id}", use_container_width=True):
                        if selected_user_id == current_user["id"]:
                            st.warning("Cannot suspend your own active administrator account.")
                        else:
                            update_user_status(selected_user_id, new_toggle_st)
                            st.success(f"User #{selected_user_id} set to {new_toggle_st}.")
                            st.rerun()

            # Delete Account Section with Confirmation
            with st.expander("🗑️ Delete User Account Permanently"):
                del_c1, del_c2 = st.columns([3, 1])
                with del_c1:
                    st.warning("⚠️ Warning: Deleting a user account will remove their personal profile, activity history, and authentication credentials permanently.")
                with del_c2:
                    if st.button("Confirm Delete", key="btn_del_user_acc", type="primary", use_container_width=True):
                        if sel_user and sel_user["id"] == current_user["id"]:
                            st.error("Cannot delete your own active administrator account.")
                        elif sel_user:
                            delete_user(sel_user["id"])
                            st.success(f"User #{sel_user['id']} has been deleted.")
                            st.rerun()
        else:
            st.info("No user accounts found matching your search criteria.")

    # ----------------------------------------------------
    # TAB 2: PREDICTION MANAGEMENT
    # ----------------------------------------------------
    elif selected_tab == "🔮 Prediction Log":
        st.markdown("### 🔮 Global Advisory Predictions Management")
        st.markdown("<p style='color: var(--text-muted); font-size: 0.9rem;'>Browse, inspect, filter, export, and manage all platform crop health assessments.</p>", unsafe_allow_html=True)
        
        all_preds = get_all_prediction_history(limit=500)
        
        # Filter controls
        p_f1, p_f2, p_f3, p_f4 = st.columns([3, 1.5, 1.5, 1.5])
        with p_f1:
            p_search = st.text_input("🔍 Search Predictions", placeholder="Crop, district, state, or pest...", key="admin_p_search")
        with p_f2:
            p_risk_filter = st.selectbox("Risk Filter", ["All", "High", "Medium", "Low"], key="admin_p_risk")
        with p_f3:
            crops_list = ["All"] + sorted(list(set(r.get("crop", "") for r in all_preds if r.get("crop"))))
            p_crop_filter = st.selectbox("Crop Filter", crops_list, key="admin_p_crop")
        with p_f4:
            p_sort = st.selectbox("Order", ["Newest First", "Highest Risk", "Highest Confidence"], key="admin_p_sort")

        filtered_preds = all_preds
        if p_search:
            s_q = p_search.strip().lower()
            filtered_preds = [
                r for r in filtered_preds if (
                    s_q in str(r.get("crop", "")).lower() or
                    s_q in str(r.get("district", "")).lower() or
                    s_q in str(r.get("state", "")).lower() or
                    s_q in str(r.get("predicted_pest", "")).lower() or
                    s_q in str(r.get("user_email", "")).lower()
                )
            ]
        if p_risk_filter != "All":
            filtered_preds = [r for r in filtered_preds if r.get("predicted_risk") == p_risk_filter]
        if p_crop_filter != "All":
            filtered_preds = [r for r in filtered_preds if r.get("crop") == p_crop_filter]

        if p_sort == "Highest Risk":
            risk_order = {"High": 3, "Medium": 2, "Low": 1}
            filtered_preds = sorted(filtered_preds, key=lambda x: risk_order.get(x.get("predicted_risk"), 0), reverse=True)
        elif p_sort == "Highest Confidence":
            filtered_preds = sorted(filtered_preds, key=lambda x: float(x.get("pest_prob", 0)), reverse=True)
        else:
            filtered_preds = sorted(filtered_preds, key=lambda x: x.get("id", 0), reverse=True)

        st.caption(f"Displaying **{len(filtered_preds)}** prediction records.")

        if filtered_preds:
            p_table = []
            for r in filtered_preds[:100]:
                p_table.append({
                    "ID": f"#{r.get('id')}",
                    "Date": r.get("created_at", "N/A"),
                    "User": r.get("user_email", "N/A"),
                    "State": r.get("state", "N/A"),
                    "District": r.get("district", "N/A"),
                    "Crop": r.get("crop", "N/A"),
                    "Season": r.get("sowing_season", "Kharif"),
                    "Predicted Pest": r.get("predicted_pest", "N/A"),
                    "Probability": f"{float(r.get('pest_prob', 0)):.1f}%",
                    "Risk Level": r.get("predicted_risk", "Medium")
                })
            st.dataframe(pd.DataFrame(p_table), use_container_width=True, hide_index=True)

            # Record Actions
            st.markdown("##### ⚡ Prediction Record Actions")
            pa_col1, pa_col2, pa_col3, pa_col4 = st.columns([3, 1.5, 1.5, 1.5])
            with pa_col1:
                sel_pred_id = st.selectbox(
                    "Select Record",
                    options=[r["id"] for r in filtered_preds[:100]],
                    format_func=lambda pid: f"Record #{pid} - {next((x['crop'] for x in filtered_preds if x['id'] == pid), '')} ({next((x['predicted_pest'] for x in filtered_preds if x['id'] == pid), '')})",
                    key="admin_sel_pred"
                )
            
            sel_pred = next((r for r in filtered_preds if r["id"] == sel_pred_id), None)
            if sel_pred:
                with pa_col2:
                    if st.button("👁 View Details", key="btn_v_pred", use_container_width=True):
                        show_prediction_detail_dialog(sel_pred)
                with pa_col3:
                    if st.button("🗑 Delete Record", key="btn_del_pred", type="primary", use_container_width=True):
                        delete_prediction_history(sel_pred["id"], user_id=None)
                        st.success(f"Record #{sel_pred['id']} deleted.")
                        st.rerun()
                with pa_col4:
                    csv_p = pd.DataFrame(filtered_preds).to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Export CSV",
                        data=csv_p,
                        file_name=f"predictions_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
        else:
            st.info("No prediction records found matching filters.")

    # ----------------------------------------------------
    # TAB 3: CONTACT QUERY MANAGEMENT
    # ----------------------------------------------------
    elif selected_tab == "📩 Contact Queries":
        st.markdown("### 📩 Contact Queries & Farmer Feedback")
        st.markdown("<p style='color: var(--text-muted); font-size: 0.9rem;'>Review incoming inquiries, change ticket statuses, and respond to farmer messages.</p>", unsafe_allow_html=True)
        
        cq_col1, cq_col2, cq_col3 = st.columns([3, 1.5, 1.5])
        with cq_col1:
            cq_search = st.text_input("🔍 Search Messages", placeholder="Search by name, email, or subject...", key="admin_cq_search")
        with cq_col2:
            cq_status_filter = st.selectbox("Status", ["All", "Pending", "Resolved"], key="admin_cq_status")
        with cq_col3:
            st.write("")
            st.write("")
            all_queries = get_contact_queries()
            cq_csv = pd.DataFrame(all_queries).to_csv(index=False).encode('utf-8') if all_queries else b""
            st.download_button(
                "📥 Export Queries CSV",
                data=cq_csv,
                file_name=f"contact_queries_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        queries = get_contact_queries(status_filter=cq_status_filter)
        if cq_search:
            s_q = cq_search.strip().lower()
            queries = [
                q for q in queries if (
                    s_q in q.get("name", "").lower() or
                    s_q in q.get("email", "").lower() or
                    s_q in q.get("subject", "").lower() or
                    s_q in q.get("message", "").lower()
                )
            ]

        if queries:
            for q in queries:
                qid = q["id"]
                q_status = q.get("status", "Pending")
                st.markdown(f"""
                <div style="background: {card_bg}; border: 1px solid {card_border}; border-radius: 14px; padding: 18px; margin-bottom: 14px; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <span style="font-size: 1.05rem; font-weight: 700; color: #1B5E20;">📋 {q['subject']}</span>
                            <div style="font-size: 0.85rem; color: {text_muted}; margin-top: 4px;">
                                👤 <b>{q['name']}</b> &bull; 📧 <a href="mailto:{q['email']}" style="color: #2E7D32; text-decoration: none;">{q['email']}</a>
                            </div>
                        </div>
                        <span style="display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.80rem; background: {'#DCFCE7' if q_status == 'Resolved' else '#FEE2E2'}; color: {'#166534' if q_status == 'Resolved' else '#991B1B'};">
                            {q_status}
                        </span>
                    </div>
                    <p style="margin: 12px 0 8px 0; color: {text_main}; line-height: 1.55; font-size: 0.93rem;">{q['message']}</p>
                    <small style="color: {text_muted};">Submitted on: {q.get('created_date', 'N/A')}</small>
                </div>
                """, unsafe_allow_html=True)
                
                b1, b2, b3, _ = st.columns([1.5, 1.5, 1.5, 3.5])
                with b1:
                    if st.button("👁 View Message", key=f"btn_v_q_{qid}", use_container_width=True):
                        show_contact_detail_dialog(q)
                with b2:
                    if q_status != "Resolved":
                        if st.button("✅ Mark Resolved", key=f"btn_res_q_{qid}", use_container_width=True):
                            update_contact_query_status(qid, "Resolved")
                            st.success("Query resolved.")
                            st.rerun()
                    else:
                        if st.button("⏳ Mark Pending", key=f"btn_pen_q_{qid}", use_container_width=True):
                            update_contact_query_status(qid, "Pending")
                            st.info("Query set to pending.")
                            st.rerun()
                with b3:
                    if st.button("🗑 Delete", key=f"btn_del_q_{qid}", use_container_width=True):
                        delete_contact_query(qid)
                        st.success("Query deleted.")
                        st.rerun()
        else:
            st.info("No contact queries logged.")

    # ----------------------------------------------------
    # TAB 4: ANALYTICS DASHBOARD
    # ----------------------------------------------------
    elif selected_tab == "📊 Analytics Dashboard":
        st.markdown("### 📊 Platform Analytics & Intelligence")
        st.markdown("<p style='color: var(--text-muted); font-size: 0.9rem;'>Real-time metrics, risk severity breakdowns, crop distributions, and platform adoption curves.</p>", unsafe_allow_html=True)
        
        analytics = get_admin_analytics_data()

        chart_theme = "plotly_dark"
        forest_green_palette = ["#22C55E", "#10B981", "#06B6D4", "#F59E0B", "#A855F7", "#3B82F6"]
        
        c_row1_1, c_row1_2 = st.columns(2)
        
        # 1. Pie Chart: Predictions by Risk
        with c_row1_1:
            risk_labels = list(analytics["risk_counts"].keys())
            risk_values = list(analytics["risk_counts"].values())
            fig_risk = px.pie(
                names=risk_labels,
                values=risk_values,
                title="🎯 Predictions by Risk Severity Level",
                color=risk_labels,
                color_discrete_map={
                    "High": "#DC2626",
                    "Medium": "#F59E0B",
                    "Low": "#10B981"
                },
                hole=0.45
            )
            fig_risk.update_layout(
                template=chart_theme,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif"),
                legend=dict(orientation="h", y=-0.1)
            )
            st.plotly_chart(fig_risk, use_container_width=True)

        # 2. Donut Chart: User Distribution
        with c_row1_2:
            u_dist_labels = list(analytics["user_dist"].keys())
            u_dist_values = list(analytics["user_dist"].values())
            fig_users = px.pie(
                names=u_dist_labels,
                values=u_dist_values,
                title="👥 User Distribution by Role",
                color_discrete_sequence=["#1B4332", "#40916C", "#74C69D"],
                hole=0.5
            )
            fig_users.update_layout(
                template=chart_theme,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif"),
                legend=dict(orientation="h", y=-0.1)
            )
            st.plotly_chart(fig_users, use_container_width=True)

        c_row2_1, c_row2_2 = st.columns(2)

        # 3. Bar Chart: Predictions by Crop
        with c_row2_1:
            crops = list(analytics["crop_counts"].keys())
            crop_vals = list(analytics["crop_counts"].values())
            fig_crop = px.bar(
                x=crops,
                y=crop_vals,
                title="🌾 Crop Predictions Distribution",
                labels={"x": "Crop Name", "y": "Predictions Count"},
                color=crop_vals,
                color_continuous_scale=[[0, "#40916C"], [1, "#1B4332"]]
            )
            fig_crop.update_layout(
                template=chart_theme,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif"),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_crop, use_container_width=True)

        # 4. Line Chart: Daily Predictions
        with c_row2_2:
            fig_daily = px.line(
                x=analytics["daily_dates"],
                y=analytics["daily_counts"],
                title="📈 Daily Platform Predictions Trend",
                labels={"x": "Date", "y": "Prediction Volume"},
                markers=True
            )
            fig_daily.update_traces(line_color="#2E7D32", line_width=3, marker=dict(size=8, color="#1B5E20"))
            fig_daily.update_layout(
                template=chart_theme,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif")
            )
            st.plotly_chart(fig_daily, use_container_width=True)

        # 5. Heatmap: Monthly Platform Usage
        st.markdown("#### 🗓️ Monthly Platform Usage Heatmap")
        month_keys = list(analytics["monthly_usage"].keys())
        month_vals = list(analytics["monthly_usage"].values())
        if len(month_keys) > 0:
            grid_z = [month_vals]
            fig_heat = px.imshow(
                grid_z,
                labels=dict(x="Month", y="Metric", color="Predictions"),
                x=month_keys,
                y=["Activity Density"],
                color_continuous_scale=[[0, "#E8F5E9"], [0.5, "#40916C"], [1, "#1B4332"]]
            )
            fig_heat.update_layout(
                template=chart_theme,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=180,
                font=dict(family="Inter, sans-serif")
            )
            st.plotly_chart(fig_heat, use_container_width=True)

    # ----------------------------------------------------
    # TAB 5: DATABASE STATISTICS
    # ----------------------------------------------------
    elif selected_tab == "🗄️ Database & Backups":
        st.markdown("### 🗄️ Database & Infrastructure Overview")
        st.markdown("<p style='color: var(--text-muted); font-size: 0.9rem;'>SQLite storage telemetry, table capacities, and database health metrics.</p>", unsafe_allow_html=True)
        
        db_stats = get_database_system_stats()

        ds1, ds2, ds3, ds4 = st.columns(4)
        with ds1:
            st.markdown(f"""
            <div class="admin-kpi-card">
                <div class="admin-kpi-header">
                    <span class="admin-kpi-title">Storage Used</span>
                    <div class="admin-kpi-icon-wrap">💾</div>
                </div>
                <div class="admin-kpi-num">{db_stats['storage_mb']} MB</div>
                <div class="admin-kpi-sub"><span>🗄️</span> SQLite File Footprint</div>
            </div>
            """, unsafe_allow_html=True)
        with ds2:
            st.markdown(f"""
            <div class="admin-kpi-card">
                <div class="admin-kpi-header">
                    <span class="admin-kpi-title">Database Status</span>
                    <div class="admin-kpi-icon-wrap">🟢</div>
                </div>
                <div class="admin-kpi-num" style="font-size: 1.3rem; color: #16A34A;">Online</div>
                <div class="admin-kpi-sub"><span>⚡</span> WAL Mode Active</div>
            </div>
            """, unsafe_allow_html=True)
        with ds3:
            st.markdown(f"""
            <div class="admin-kpi-card">
                <div class="admin-kpi-header">
                    <span class="admin-kpi-title">Latest User Reg</span>
                    <div class="admin-kpi-icon-wrap">👤</div>
                </div>
                <div class="admin-kpi-num" style="font-size: 1.05rem;">{str(db_stats['latest_user_date']).split()[0]}</div>
                <div class="admin-kpi-sub"><span>⏱️</span> {str(db_stats['latest_user_date']).split()[-1] if ' ' in str(db_stats['latest_user_date']) else ''}</div>
            </div>
            """, unsafe_allow_html=True)
        with ds4:
            st.markdown(f"""
            <div class="admin-kpi-card">
                <div class="admin-kpi-header">
                    <span class="admin-kpi-title">Latest Prediction</span>
                    <div class="admin-kpi-icon-wrap">🔮</div>
                </div>
                <div class="admin-kpi-num" style="font-size: 1.05rem;">{str(db_stats['latest_pred_date']).split()[0]}</div>
                <div class="admin-kpi-sub"><span>⏱️</span> {str(db_stats['latest_pred_date']).split()[-1] if ' ' in str(db_stats['latest_pred_date']) else ''}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Database table summaries
        db_details = [
            {"Table": "users", "Description": "User authentication, profiles, preferences", "Records": str(db_stats["total_users"]), "Status": "Normal"},
            {"Table": "prediction_history", "Description": "Crop advisory assessments & pest logs", "Records": str(db_stats["total_predictions"]), "Status": "Normal"},
            {"Table": "contact_queries", "Description": "Feedback, tickets, contact submissions", "Records": str(db_stats["total_queries"]), "Status": "Normal"},
            {"Table": "user_preferences", "Description": "Farmer & Admin UI settings", "Records": str(db_stats["total_users"]), "Status": "Normal"},
            {"Table": "account_activity", "Description": "Security audit logs & activity history", "Records": "Logged Dynamically", "Status": "Normal"}
        ]
        st.table(pd.DataFrame(db_details))

        # Performance Indexes
        db_health = get_database_health_summary()
        with st.expander(f"⚡ Active Performance Indexes ({db_health['indexes_active']} Configured)"):
            st.markdown("<p style='color: var(--text-muted); font-size: 0.88rem;'>Database indexes ensure instantaneous queries for search, authentication, and regional forecasting.</p>", unsafe_allow_html=True)
            idx_cols = st.columns(2)
            half = (len(db_health['index_list']) + 1) // 2
            with idx_cols[0]:
                for idx in db_health['index_list'][:half]:
                    st.markdown(f"&bull; <code>{idx}</code>", unsafe_allow_html=True)
            with idx_cols[1]:
                for idx in db_health['index_list'][half:]:
                    st.markdown(f"&bull; <code>{idx}</code>", unsafe_allow_html=True)

        # Backup & Disaster Recovery Operations
        st.markdown("#### 💾 Database Backup & Disaster Recovery")
        st.markdown("<p style='color: var(--text-muted); font-size: 0.88rem;'>Create hot backups, download snapshots, or restore previous system checkpoints with rollback protection.</p>", unsafe_allow_html=True)

        bk_action_c1, bk_action_c2, bk_action_c3 = st.columns([2, 2, 2])
        with bk_action_c1:
            if st.button("📦 Create Instant Backup", use_container_width=True, key="btn_create_manual_backup"):
                ok, msg, fname = create_manual_backup(current_user["email"])
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        with bk_action_c2:
            if st.button("⏰ Run Daily Auto-Backup (Demo)", use_container_width=True, key="btn_auto_backup_demo"):
                ok, msg = trigger_auto_backup_demo()
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        with bk_action_c3:
            bk_stats = get_backup_storage_stats()
            st.markdown(f"<div style='text-align: right; font-size: 0.84rem; color: var(--text-muted); padding-top: 8px;'><b>Backups Available:</b> {bk_stats['count']} ({bk_stats['total_size_mb']} MB)</div>", unsafe_allow_html=True)

        # List Existing Backups
        avail_backups = list_available_backups()
        if avail_backups:
            bk_table_data = []
            for b in avail_backups:
                bk_table_data.append({
                    "Backup File": b["filename"],
                    "Size (MB)": b["size_mb"],
                    "Created At": b["created_at"],
                    "Author": b["creator"]
                })
            st.dataframe(pd.DataFrame(bk_table_data), use_container_width=True)

            # Download & Restore Tools
            with st.expander("📥 Download or Restore Backup Snapshot"):
                r_c1, r_c2 = st.columns(2)
                with r_c1:
                    st.markdown("<b>Download Backup File</b>", unsafe_allow_html=True)
                    dl_choice = st.selectbox("Select Backup to Download", [b["filename"] for b in avail_backups], key="sel_dl_bk")
                    dl_bytes = get_backup_bytes(dl_choice)
                    if dl_bytes:
                        st.download_button(
                            label=f"⬇️ Download {dl_choice}",
                            data=dl_bytes,
                            file_name=dl_choice,
                            mime="application/x-sqlite3",
                            use_container_width=True
                        )
                with r_c2:
                    st.markdown("<b>Restore Database from Snapshot</b>", unsafe_allow_html=True)
                    st.caption("Restores database state. Current state is automatically preserved as a rollback safety copy.")
                    res_choice = st.selectbox("Select Backup to Restore", [b["filename"] for b in avail_backups], key="sel_res_bk")
                    if st.button(f"⚠️ Restore Database to {res_choice}", key="btn_confirm_restore"):
                        ok, msg = restore_backup(res_choice, current_user["email"])
                        if ok:
                            st.success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
        else:
            st.info("ℹ️ No backups created yet. Click 'Create Instant Backup' above to generate your first snapshot.")

        # Maintenance Utilities
        with st.expander("🛠️ Low-Level SQLite Maintenance Utilities"):
            m1, m2 = st.columns(2)
            with m1:
                st.markdown("<b>Optimize & Checkpoint SQLite WAL</b>", unsafe_allow_html=True)
                st.caption("Executes PRAGMA wal_checkpoint(TRUNCATE) and PRAGMA optimize to compress data pages.")
                if st.button("Run Maintenance Checkpoint", key="btn_maint_chk"):
                    try:
                        conn = get_connection()
                        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                        conn.execute("PRAGMA optimize")
                        conn.close()
                        st.success("Database checkpoint & optimization executed successfully.")
                    except Exception as e:
                        st.error(f"Maintenance error: {e}")
            with m2:
                st.markdown("<b>Verify DB Integrity</b>", unsafe_allow_html=True)
                st.caption("Executes PRAGMA integrity_check to ensure SQLite consistency.")
                if st.button("Run Integrity Check", key="btn_maint_integ"):
                    try:
                        conn = get_connection()
                        res = conn.execute("PRAGMA integrity_check").fetchone()[0]
                        conn.close()
                        st.success(f"Integrity Check: {res}")
                    except Exception as e:
                        st.error(f"Integrity error: {e}")

    # ----------------------------------------------------
    # TAB 6: EXPORT CENTER
    # ----------------------------------------------------
    elif selected_tab == "📤 Export Center":
        st.markdown("### 📤 Enterprise Data Export Center")
        st.markdown("<p style='color: var(--text-muted); font-size: 0.9rem;'>Download high-resolution CSV datasets and executive PDF audit reports.</p>", unsafe_allow_html=True)
        
        ex_col1, ex_col2 = st.columns(2)

        # 1. Users CSV
        with ex_col1:
            st.markdown("""
            <div class="admin-panel-card">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">👥</div>
                <h4 style="margin: 0 0 6px 0;">User Accounts Registry</h4>
                <p style="color: var(--text-muted); font-size: 0.86rem; margin-bottom: 14px;">
                    Full CSV export of all user accounts including registration dates, roles, status, and prediction volumes.
                </p>
            </div>
            """, unsafe_allow_html=True)
            u_export = get_all_users_extended()
            u_csv = pd.DataFrame(u_export).to_csv(index=False).encode('utf-8')
            if st.download_button(
                "📥 Export Users CSV",
                data=u_csv,
                file_name=f"agriai_users_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_u_csv"
            ):
                st.success("Users CSV successfully generated!")

        # 2. Predictions CSV
        with ex_col2:
            st.markdown("""
            <div class="admin-panel-card">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">🔮</div>
                <h4 style="margin: 0 0 6px 0;">Global Predictions Dataset</h4>
                <p style="color: var(--text-muted); font-size: 0.86rem; margin-bottom: 14px;">
                    Complete CSV records of historical inferences, weather metrics, predicted pests, and risk levels.
                </p>
            </div>
            """, unsafe_allow_html=True)
            p_export = get_all_prediction_history(limit=1000)
            p_csv = pd.DataFrame(p_export).to_csv(index=False).encode('utf-8')
            if st.download_button(
                "📥 Export Predictions CSV",
                data=p_csv,
                file_name=f"agriai_predictions_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_p_csv"
            ):
                st.success("Predictions CSV successfully generated!")

        ex_col3, ex_col4 = st.columns(2)

        # 3. Contact Queries CSV
        with ex_col3:
            st.markdown("""
            <div class="admin-panel-card">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">📩</div>
                <h4 style="margin: 0 0 6px 0;">Help Desk & Queries CSV</h4>
                <p style="color: var(--text-muted); font-size: 0.86rem; margin-bottom: 14px;">
                    Export all farmer inquiries, ticket history, contact details, and resolution timestamps.
                </p>
            </div>
            """, unsafe_allow_html=True)
            q_export = get_contact_queries()
            q_csv = pd.DataFrame(q_export).to_csv(index=False).encode('utf-8')
            if st.download_button(
                "📥 Export Contact Queries CSV",
                data=q_csv,
                file_name=f"agriai_contact_queries_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_q_csv"
            ):
                st.success("Contact Queries CSV exported successfully!")

        # 4. System Summary PDF
        with ex_col4:
            st.markdown("""
            <div class="admin-panel-card">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">📄</div>
                <h4 style="margin: 0 0 6px 0;">Executive System Summary PDF</h4>
                <p style="color: var(--text-muted); font-size: 0.86rem; margin-bottom: 14px;">
                    Professional A4 PDF document summarizing platform KPIs, system status, storage, and audit events.
                </p>
            </div>
            """, unsafe_allow_html=True)
            activity_recent = get_all_activity_logs(limit=15)
            sys_pdf_bytes = generate_system_summary_pdf(kpis, db_stats, activity_recent)
            if st.download_button(
                "📥 Export System Summary PDF",
                data=sys_pdf_bytes,
                file_name=f"AgriAI_System_Summary_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="dl_sys_pdf"
            ):
                st.success("System Summary PDF exported successfully!")

        # 5. Analytics Report PDF
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="admin-panel-card">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div>
                    <div style="font-size: 1.5rem; margin-bottom: 4px;">📊</div>
                    <h4 style="margin: 0 0 4px 0;">Full Platform Analytics & Intelligence PDF</h4>
                    <p style="color: var(--text-muted); font-size: 0.86rem; margin: 0;">
                        Comprehensive agricultural risk distribution, top crops, and monthly utilization report.
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        analytics_data = get_admin_analytics_data()
        analytics_pdf_bytes = generate_analytics_report_pdf(analytics_data)
        if st.download_button(
            "📥 Download Full Analytics PDF Report",
            data=analytics_pdf_bytes,
            file_name=f"AgriAI_Analytics_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="dl_analytics_pdf"
        ):
            st.success("Analytics PDF Report exported successfully!")

    # ----------------------------------------------------
    # TAB 7: ACTIVITY LOGS
    # ----------------------------------------------------
    elif selected_tab == "📜 Activity Logs":
        st.markdown("### 📜 Platform Audit & Activity Logs")
        st.markdown("<p style='color: var(--text-muted); font-size: 0.9rem;'>Real-time platform activity feed arranged in reverse chronological order.</p>", unsafe_allow_html=True)
        
        act_col1, act_col2 = st.columns([3, 1])
        with act_col1:
            act_search = st.text_input("🔍 Search Logs", placeholder="Filter by event type, user, or description...", key="admin_act_search")
        with act_col2:
            st.write("")
            st.write("")
            all_logs = get_all_activity_logs(limit=100, search_query=act_search)
            logs_csv = pd.DataFrame(all_logs).to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Export Activity CSV",
                data=logs_csv,
                file_name=f"activity_logs_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        if all_logs:
            for log in all_logs[:30]:
                icon = log.get("icon", "⚡")
                evt_type = log.get("activity_type", "Event")
                desc = log.get("description", "")
                time_str = log.get("created_at", "N/A")
                u_name = log.get("user_name", "System")
                u_email = log.get("user_email", "")

                st.markdown(f"""
                <div style="background: {card_bg}; border: 1px solid {card_border}; border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; display: flex; align-items: flex-start; gap: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
                    <div style="font-size: 1.6rem; line-height: 1;">{icon}</div>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                            <span style="font-weight: 700; color: #1B5E20; font-size: 0.94rem;">{evt_type}</span>
                            <span style="font-size: 0.78rem; color: {text_muted};">⏱️ {time_str}</span>
                        </div>
                        <p style="margin: 4px 0 2px 0; font-size: 0.88rem; color: {text_main};">{desc}</p>
                        <small style="color: {text_muted};">Actor: <b>{u_name}</b> ({u_email})</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No activity logs found.")

    # ----------------------------------------------------
    # TAB 8: ADMIN PROFILE
    # ----------------------------------------------------
    elif selected_tab == "👤 Admin Profile":
        st.markdown("### 👤 Administrator Profile & Credentials")
        st.markdown("<p style='color: var(--text-muted); font-size: 0.9rem;'>View and manage your administrator security credentials.</p>", unsafe_allow_html=True)
        
        prof_c1, prof_c2 = st.columns([1.5, 2.5])
        
        with prof_c1:
            st.markdown(f"""
            <div class="admin-panel-card" style="text-align: center;">
                <div style="width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, #1B5E20, #2E7D32); color: #ffffff; display: flex; align-items: center; justify-content: center; font-size: 2.8rem; font-weight: 700; margin: 0 auto 14px auto; box-shadow: 0 6px 20px rgba(46, 125, 50, 0.3);">
                    {current_user['name'][:1].upper()}
                </div>
                <h3 style="margin: 0 0 4px 0; font-family: 'Poppins', sans-serif;">{current_user['name']}</h3>
                <span class="admin-badge-role-admin">🛡️ Platform Administrator</span>
                <div style="margin-top: 16px; font-size: 0.88rem; color: {text_muted}; text-align: left; line-height: 1.8;">
                    <b>📧 Email:</b> {current_user['email']}<br>
                    <b>🆔 Admin ID:</b> #{current_user['id']}<br>
                    <b>📅 Join Date:</b> {current_user.get('created_at', 'N/A')}<br>
                    <b>⏱️ Current Login:</b> {current_user.get('last_login', 'Active Session')}<br>
                    <b>🔒 Security Level:</b> Enterprise Superuser
                </div>
            </div>
            """, unsafe_allow_html=True)

        with prof_c2:
            st.markdown("#### 🔒 Change Administrator Password")
            with st.form("admin_change_pw_form"):
                cur_pw = st.text_input("Current Password", type="password", placeholder="Enter current administrator password")
                new_pw = st.text_input("New Password", type="password", placeholder="Enter strong new password (min 8 chars)")
                conf_pw = st.text_input("Confirm New Password", type="password", placeholder="Re-enter new password")
                
                pw_submit = st.form_submit_button("🔑 Update Password", use_container_width=True)
                if pw_submit:
                    if not cur_pw or not new_pw or not conf_pw:
                        st.error("Please fill in all password fields.")
                    elif new_pw != conf_pw:
                        st.error("New password and confirmation do not match.")
                    else:
                        ok, msg = change_user_password(current_user["id"], cur_pw, new_pw, conf_pw)
                        if ok:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ {msg}")

    # ----------------------------------------------------
    # TAB 9: SYSTEM SETTINGS
    # ----------------------------------------------------
    elif selected_tab == "⚙️ System Settings":
        st.markdown("### ⚙️ Platform Global Configuration & Settings")
        st.markdown("<p style='color: var(--text-muted); font-size: 0.9rem;'>Customize administrator environment preferences, themes, language, and operational controls.</p>", unsafe_allow_html=True)
        
        with st.form("admin_system_settings_form"):
            s_c1, s_c2 = st.columns(2)
            
            with s_c1:
                st.markdown("##### 🎨 Visual & Localization")
                st.text_input(
                    "Active System Theme",
                    value="🌙 Enterprise Dark Edition (#0F172A)",
                    disabled=True,
                    help="Platform operates strictly in high-contrast Enterprise Dark Mode."
                )
                admin_lang = st.selectbox(
                    "Platform Language",
                    ["English (Default)", "Hindi (हिंदी)", "Marathi (मराठी)", "Telugu (తెలుగు)", "Tamil (தமிழ்)", "Gujarati (ગુજરાતી)"],
                    index=0,
                    help="Sets platform localization language for advisory and administrative alerts."
                )
                session_timeout = st.selectbox(
                    "Session Security Timeout",
                    ["15 Minutes", "30 Minutes (Recommended)", "1 Hour", "4 Hours", "Persistent"],
                    index=1,
                    help="Automatic session logout duration for inactivity."
                )

            with s_c2:
                st.markdown("##### 🛡️ Platform Controls & Alerts")
                maint_mode = st.toggle(
                    "Maintenance Mode (Demo)",
                    value=st.session_state.get("admin_demo_maintenance", False),
                    help="Displays a platform maintenance banner for testing operational announcements."
                )
                notify_new_user = st.checkbox("Notify on New Farmer Registration", value=True)
                notify_high_risk = st.checkbox("Immediate Alert on High Pest Risk Outbreaks", value=True)
                notify_daily_digest = st.checkbox("Generate Daily System Health Digest", value=True)

            save_settings = st.form_submit_button("💾 Save System Preferences", use_container_width=True)
            if save_settings:
                st.session_state["admin_demo_maintenance"] = maint_mode
                log_account_activity(
                    current_user["id"],
                    "Settings Updated",
                    f"Admin updated system configuration (Theme: {admin_theme}, Lang: {admin_lang}).",
                    "⚙️"
                )
                st.success("✅ System preferences saved successfully.")
                st.rerun()

        if st.session_state.get("admin_demo_maintenance", False):
            st.warning("⚠️ Notice: Maintenance Mode (Demo) is currently active. Standard advisory requests will show operational notice banner.")

    # ----------------------------------------------------
    # TAB 10: SYSTEM HEALTH & MONITORING
    # ----------------------------------------------------
    elif selected_tab == "🩺 System Health & Monitoring":
        st.markdown("### 🩺 Platform Telemetry & System Health Monitoring")
        st.markdown("<p style='color: var(--text-muted); font-size: 0.9rem;'>Real-time operational health, API statuses, storage consumption, uptime, and secure audit logs.</p>", unsafe_allow_html=True)

        # Uptime Calculation
        uptime_delta = datetime.now() - st.session_state.get("app_start_time", datetime.now())
        hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # Storage Metrics
        db_health = get_database_health_summary()
        bk_stats = get_backup_storage_stats()
        
        log_size_mb = 0.0
        if LOG_FILE.exists():
            log_size_mb = round(os.path.getsize(LOG_FILE) / (1024 * 1024), 2)
            
        uploads_size_mb = 0.0
        if UPLOADS_DIR.exists():
            uploads_size = sum(f.stat().st_size for f in UPLOADS_DIR.glob('**/*') if f.is_file())
            uploads_size_mb = round(uploads_size / (1024 * 1024), 2)

        total_system_storage_mb = round(
            (db_health['size_bytes'] / (1024 * 1024)) + bk_stats['total_size_mb'] + log_size_mb + uploads_size_mb, 2
        )

        # 6 Telemetry Cards
        t1, t2, t3, t4, t5, t6 = st.columns(6)
        with t1:
            st.markdown(f"""
            <div class="admin-kpi-card">
                <div class="admin-kpi-header">
                    <span class="admin-kpi-title">DB Status</span>
                    <div class="admin-kpi-icon-wrap">🟢</div>
                </div>
                <div class="admin-kpi-num" style="font-size: 1.25rem; color: #16A34A;">Online</div>
                <div class="admin-kpi-sub"><span>⚡</span> {db_health['latency_ms']} ms ping</div>
            </div>
            """, unsafe_allow_html=True)
        with t2:
            st.markdown(f"""
            <div class="admin-kpi-card">
                <div class="admin-kpi-header">
                    <span class="admin-kpi-title">Weather API</span>
                    <div class="admin-kpi-icon-wrap">🌤️</div>
                </div>
                <div class="admin-kpi-num" style="font-size: 1.25rem; color: #16A34A;">Operational</div>
                <div class="admin-kpi-sub"><span>🌐</span> Open-Meteo v1</div>
            </div>
            """, unsafe_allow_html=True)
        with t3:
            st.markdown(f"""
            <div class="admin-kpi-card">
                <div class="admin-kpi-header">
                    <span class="admin-kpi-title">Total Storage</span>
                    <div class="admin-kpi-icon-wrap">💾</div>
                </div>
                <div class="admin-kpi-num">{total_system_storage_mb} MB</div>
                <div class="admin-kpi-sub"><span>📦</span> Disk footprint</div>
            </div>
            """, unsafe_allow_html=True)
        with t4:
            st.markdown(f"""
            <div class="admin-kpi-card">
                <div class="admin-kpi-header">
                    <span class="admin-kpi-title">Version</span>
                    <div class="admin-kpi-icon-wrap">🚀</div>
                </div>
                <div class="admin-kpi-num" style="font-size: 1.1rem;">{APP_VERSION}</div>
                <div class="admin-kpi-sub"><span>🏷️</span> Env: {APP_ENV.upper()}</div>
            </div>
            """, unsafe_allow_html=True)
        with t5:
            st.markdown(f"""
            <div class="admin-kpi-card">
                <div class="admin-kpi-header">
                    <span class="admin-kpi-title">Last Backup</span>
                    <div class="admin-kpi-icon-wrap">🛡️</div>
                </div>
                <div class="admin-kpi-num" style="font-size: 1.0rem;">{bk_stats['last_backup_date'].split()[0] if ' ' in bk_stats['last_backup_date'] else bk_stats['last_backup_date']}</div>
                <div class="admin-kpi-sub"><span>📦</span> {bk_stats['count']} snapshots</div>
            </div>
            """, unsafe_allow_html=True)
        with t6:
            st.markdown(f"""
            <div class="admin-kpi-card">
                <div class="admin-kpi-header">
                    <span class="admin-kpi-title">System Uptime</span>
                    <div class="admin-kpi-icon-wrap">⏱️</div>
                </div>
                <div class="admin-kpi-num" style="font-size: 1.05rem; color: #16A34A;">{uptime_str}</div>
                <div class="admin-kpi-sub"><span>🔄</span> Demo Uptime</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Storage Consumption Breakdown
        st.markdown("#### 📁 Storage & Asset Footprint Breakdown")
        storage_breakdown = [
            {"Asset Component": "Database File (predictions.db)", "Path": str(DEFAULT_SQLITE_PATH), "Size (MB)": round(db_health['size_bytes'] / (1024 * 1024), 2), "Status": "Active"},
            {"Asset Component": "Snapshot Backups", "Path": str(BACKUPS_DIR), "Size (MB)": bk_stats['total_size_mb'], "Status": f"{bk_stats['count']} Snapshots"},
            {"Asset Component": "Rotating System Logs", "Path": str(LOG_FILE), "Size (MB)": log_size_mb, "Status": "Rotating (5MB Max)"},
            {"Asset Component": "User Uploads & Avatars", "Path": str(UPLOADS_DIR), "Size (MB)": uploads_size_mb, "Status": "UUID Storage"}
        ]
        st.table(pd.DataFrame(storage_breakdown))

        # Real-time System Log Viewer
        st.markdown("#### 📜 Dedicated Enterprise System Log Viewer")
        st.markdown("<p style='color: var(--text-muted); font-size: 0.88rem;'>Structured system events, authentication audits, and error logs recorded securely in <code>logs/agriai.log</code>. Never exposed to regular users.</p>", unsafe_allow_html=True)

        log_ctrl_c1, log_ctrl_c2, log_ctrl_c3 = st.columns([2, 2, 2])
        with log_ctrl_c1:
            log_level_filter = st.selectbox("Filter by Severity", ["ALL", "INFO", "WARNING", "ERROR"], key="admin_log_lvl_filter")
        with log_ctrl_c2:
            st.write("")
            st.write("")
            if st.button("🔄 Refresh System Logs", use_container_width=True, key="btn_refresh_logs"):
                st.rerun()
        with log_ctrl_c3:
            st.write("")
            st.write("")
            if LOG_FILE.exists():
                with open(LOG_FILE, "rb") as lf:
                    st.download_button(
                        label="⬇️ Download Full Log File",
                        data=lf.read(),
                        file_name="agriai_system.log",
                        mime="text/plain",
                        use_container_width=True,
                        key="btn_dl_logs"
                    )

        recent_logs = get_recent_logs(limit=100, level_filter=log_level_filter)
        if recent_logs:
            log_df = pd.DataFrame(recent_logs)
            st.dataframe(log_df, use_container_width=True, height=350)
        else:
            st.info(f"No log records found matching severity '{log_level_filter}'.")
