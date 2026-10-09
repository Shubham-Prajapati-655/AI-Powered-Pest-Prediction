"""
Architecture & Technical Diagrams Generator
AI-Powered Crop Pest Prediction & Agricultural Advisory System
Generates high-resolution PNG (300 DPI) and scalable vector SVG diagrams for:
1. System Architecture
2. ML Pipeline Architecture
3. Data Flow Diagram (DFD Level 1)
4. Entity Relationship (ER) Diagram
5. End-to-End Sequence Diagram
6. Production Deployment Architecture
7. Component Architecture Diagram
8. Comprehensive User & Inference Workflow Diagram
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch

DIAGRAMS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "diagrams"))
os.makedirs(DIAGRAMS_DIR, exist_ok=True)

# Modern Agricultural SaaS Theme Palette
PALETTE = {
    "bg": "#0D1117",
    "card_bg": "#161B22",
    "card_border": "#30363D",
    "primary": "#2EA043",
    "primary_light": "#3FB950",
    "primary_dark": "#238636",
    "accent_blue": "#58A6FF",
    "accent_cyan": "#39C5CF",
    "accent_amber": "#D29922",
    "accent_red": "#F85149",
    "accent_purple": "#BC8CFF",
    "text_main": "#F0F6FC",
    "text_sub": "#8B949E",
    "box_header": "#21262D"
}

def setup_canvas(width=16, height=10, title=""):
    fig, ax = plt.subplots(figsize=(width, height), facecolor=PALETTE["bg"])
    ax.set_facecolor(PALETTE["bg"])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    if title:
        fig.text(0.5, 0.95, title, ha="center", va="top", fontsize=18, fontweight="bold",
                 color=PALETTE["text_main"], family="sans-serif")
    return fig, ax

def draw_card(ax, x, y, w, h, title, subtitle="", items=None, border_color=None, bg_color=None, header_color=None):
    border = border_color or PALETTE["card_border"]
    bg = bg_color or PALETTE["card_bg"]
    hdr = header_color or PALETTE["box_header"]
    
    # Outer box
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.2",
                         edgecolor=border, facecolor=bg, linewidth=1.5, zorder=2)
    ax.add_patch(box)
    
    # Header strip
    hdr_h = min(2.5, h * 0.28)
    hdr_box = FancyBboxPatch((x, y + h - hdr_h), w, hdr_h, boxstyle="round,pad=0.2,rounding_size=0.8",
                            edgecolor="none", facecolor=hdr, zorder=3)
    ax.add_patch(hdr_box)
    
    # Header text
    ax.text(x + w/2, y + h - hdr_h/2, title, ha="center", va="center",
            fontsize=11, fontweight="bold", color=border if border != PALETTE["card_border"] else PALETTE["text_main"],
            zorder=4)
    
    # Subtitle
    cur_y = y + h - hdr_h - 1.2
    if subtitle:
        ax.text(x + 1.2, cur_y, subtitle, ha="left", va="top",
                fontsize=9, fontstyle="italic", color=PALETTE["accent_cyan"], zorder=4)
        cur_y -= 1.8
        
    # Items
    if items:
        for itm in items:
            ax.text(x + 1.5, cur_y, f"• {itm}", ha="left", va="top",
                    fontsize=8.5, color=PALETTE["text_main"], zorder=4)
            cur_y -= 1.4

def draw_arrow(ax, x1, y1, x2, y2, label="", color=None, style="->"):
    col = color or PALETTE["text_sub"]
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=col, lw=1.8, shrinkA=3, shrinkB=3),
                zorder=5)
    if label:
        mx, my = (x1 + x2)/2, (y1 + y2)/2
        ax.text(mx, my + 0.8, label, ha="center", va="bottom", fontsize=8,
                color=col, fontweight="semibold", bbox=dict(boxstyle="round,pad=0.2", fc=PALETTE["bg"], ec="none", alpha=0.85), zorder=6)

def save_diagram(fig, base_name):
    png_path = os.path.join(DIAGRAMS_DIR, f"{base_name}.png")
    svg_path = os.path.join(DIAGRAMS_DIR, f"{base_name}.svg")
    fig.savefig(png_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    fig.savefig(svg_path, format="svg", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"Generated: {base_name}.png & {base_name}.svg")

# =====================================================================
# 1. SYSTEM ARCHITECTURE
# =====================================================================
def generate_system_architecture():
    fig, ax = setup_canvas(16, 10, "AI-Powered Crop Pest Prediction & Advisory System - Architecture")
    
    # Layers
    draw_card(ax, 5, 68, 90, 20, "1. PRESENTATION LAYER (USER INTERACTION)", "Responsive Web UI & Microservices",
              border_color=PALETTE["accent_blue"])
    draw_card(ax, 8, 70, 40, 15, "Streamlit SaaS Frontend (Port 8501)", "Modern Reactive Architecture",
              ["Dark/Light Theme Toggle & Glassmorphism UI", "Dynamic Agro-Climatic Input Form & Validation", "Live Interactive Prediction Dashboards & Charts", "Farmer Profile & Prediction History Explorer"])
    draw_card(ax, 52, 70, 40, 15, "FastAPI RESTful Service (Port 8000)", "High-Throughput Microservice",
              ["GET /health (Liveness & Pipeline Readiness)", "POST /predict (Top-3 Pest & Risk Inference)", "POST /advisory (Decoupled Agronomic Lookup)", "POST /report (Automated PDF Generation)"])

    draw_card(ax, 5, 38, 90, 24, "2. CORE APPLICATION & SERVICE LAYER", "Business Logic, Security & Integrations",
              border_color=PALETTE["primary_light"])
    draw_card(ax, 8, 40, 26, 19, "Security & Auth Engine", "Zero-Trust Principles",
              ["Bcrypt Password Hashing (Cost 12)", "256-bit Hex Session Management", "Brute-Force Rate Limiter (5 tries/15m)", "Strict XSS & SQLi Sanitization"])
    draw_card(ax, 37, 40, 26, 19, "Live Weather Engine", "Open-Meteo Integration",
              ["4-Tier Resilience & Fallback Hierarchy", "10-Minute Regional Coordinate Cache", "Live REST API Sync with Exponential Retry", "Seasonal Agro-Climatic Defaults"])
    draw_card(ax, 66, 40, 26, 19, "Advisory & PDF Reporter", "Agronomic Knowledgebase",
              ["Decoupled Advisory Lookup for Rank-1", "ReportLab High-Res Vector Engine", "Farmer Advisory & Analytics PDFs", "Automated Point-in-Time Delivery"])

    draw_card(ax, 5, 8, 90, 24, "3. MACHINE LEARNING & STORAGE LAYER", "Pipelines, Predictive Models & Database",
              border_color=PALETTE["accent_purple"])
    draw_card(ax, 8, 10, 40, 19, "ML Inference Pipeline", "best_model.pkl & preprocessor.pkl",
              ["Continuous Feature Scaling (StandardScaler)", "Categorical Encoding (OrdinalEncoder)", "Agro-Climatic Feature Eng. (THI, Ratio)", "Multi-Output Classifier (CatBoost/LightGBM)"])
    draw_card(ax, 52, 10, 40, 19, "Persistence & DR Storage", "SQLite WAL Mode & Automated Backups",
              ["10 Strategic B-Tree Performance Indexes", "Atomic ACID Transactions & Foreign Keys", "Automated Timestamped Snapshot Engine", "Point-in-Time Backup & Disaster Recovery"])

    # Inter-layer connections
    draw_arrow(ax, 28, 70, 28, 59, "User Queries / State", PALETTE["accent_blue"])
    draw_arrow(ax, 72, 70, 72, 59, "REST API Endpoints", PALETTE["accent_blue"])
    draw_arrow(ax, 28, 40, 28, 29, "Inference Calls", PALETTE["primary_light"])
    draw_arrow(ax, 72, 40, 72, 29, "DB Queries / Logs", PALETTE["accent_purple"])

    save_diagram(fig, "system_architecture")

# =====================================================================
# 2. ML PIPELINE
# =====================================================================
def generate_ml_pipeline():
    fig, ax = setup_canvas(16, 10, "End-to-End Production ML Pipeline Architecture")
    
    stages = [
        (4, 52, 20, 36, "1. RAW AGRO DATA", "Data Source Layer",
         ["Master Dataset (249,700 rows)", "21 Agronomic Features", "Zero Missing / Corrupted Rows", "Zero Target/Advisory Leakage", "Strict Input Boundary Validation"]),
        (28, 52, 20, 36, "2. PREPROCESSING", "Feature Engineering",
         ["THI = 0.8T + H*(T-14.3)/100 + 46.4", "Rainfall/Humidity Ratio", "StandardScaler (Numerical)", "OrdinalEncoder (Categorical)", "Unknown Token Imputation"]),
        (52, 52, 20, 36, "3. MODEL ENSEMBLE", "Gradient Boosting",
         ["CatBoost / LightGBM / XGBoost", "Multi-Output Classification", "Output 1: Target Pest (12 Classes)", "Output 2: Crop Risk (3 Classes)", "Hyperparameter Optimization"]),
        (76, 52, 20, 36, "4. TOP-3 INFERENCE", "Probability Ranking",
         ["predict_proba() Computation", "Strict Monotonic Sorting", "Rank 1 Prob >= Rank 2 >= Rank 3", "Dynamic Confidence Tiering", "Sub-150ms Low Latency SLA"])
    ]
    
    colors = [PALETTE["accent_blue"], PALETTE["accent_cyan"], PALETTE["primary_light"], PALETTE["accent_amber"]]
    for i, (x, y, w, h, title, sub, itms) in enumerate(stages):
        draw_card(ax, x, y, w, h, title, sub, itms, border_color=colors[i])
        if i < len(stages) - 1:
            draw_arrow(ax, x + w, y + h/2, stages[i+1][0], y + h/2, "Transform", colors[i])
            
    # Bottom Advisory Engine Integration
    draw_card(ax, 28, 8, 44, 32, "5. DECOUPLED ADVISORY ENGINE", "Automated Decision Support",
              ["Knowledgebase Lookup strictly for Rank-1 Pest", "Chemical Pesticide Name & Recommended Dosage", "Organic Biological Controls & Preventive Cultural Practices", "Mandatory Farmer PPE & Field Application Safety Guidelines", "Automated Multilingual PDF Generation"],
              border_color=PALETTE["accent_red"])
              
    draw_card(ax, 76, 8, 20, 32, "6. VALIDATION & DRIFT", "Quality Gates",
              ["100% Deterministic Bitwise Match", "Zero Feature Drift Guarantee", "Automated Pytest Suite (91 Tests)", "1,000 Query Stress Benchmark"],
              border_color=PALETTE["accent_purple"])

    draw_arrow(ax, 86, 52, 86, 40, "Rank-1 Pest", PALETTE["accent_amber"])
    draw_arrow(ax, 72, 24, 76, 24, "Verified", PALETTE["primary_light"])

    save_diagram(fig, "ml_pipeline")

# =====================================================================
# 3. DATA FLOW DIAGRAM (DFD LEVEL 1)
# =====================================================================
def generate_data_flow():
    fig, ax = setup_canvas(16, 10, "Data Flow Diagram (DFD Level 1) - Pest Advisory System")
    
    # Entities
    draw_card(ax, 4, 75, 18, 16, "FARMER / CLIENT", "External Entity",
              ["Inputs Crop & Location", "Requests Weather Sync", "Views Top-3 & Advisory", "Downloads PDF Report"],
              border_color=PALETTE["accent_blue"])
              
    draw_card(ax, 78, 75, 18, 16, "WEATHER API", "External Service",
              ["Open-Meteo REST API", "Geocoded Coordinates", "Hourly / Current Forecast", "Automatic Retry Handler"],
              border_color=PALETTE["accent_cyan"])
              
    # Processes
    draw_card(ax, 41, 75, 20, 16, "1.0 AUTH & INPUT", "Process 1",
              ["Validate User Session", "Sanitize Agro Inputs", "Determine Weather Season"],
              border_color=PALETTE["primary_light"])
              
    draw_card(ax, 41, 44, 20, 18, "2.0 ML PREDICTION", "Process 2",
              ["Calculate THI & Ratio", "Execute ColumnTransformer", "Run MultiOutput Classifier", "Rank Top-3 Probabilities"],
              border_color=PALETTE["accent_amber"])
              
    draw_card(ax, 41, 10, 20, 20, "3.0 ADVISORY & PDF", "Process 3",
              ["Extract Rank-1 Pest", "Lookup Advisory KB", "Format Dosage & Safety", "Generate Vector PDF"],
              border_color=PALETTE["accent_red"])

    # Data Stores
    draw_card(ax, 4, 18, 22, 18, "D1: USERS & HISTORY", "Data Store (SQLite)",
              ["User Credentials & Roles", "Prediction Audit Records", "Session State Tokens"],
              border_color=PALETTE["accent_purple"])
              
    draw_card(ax, 74, 18, 22, 18, "D2: ADVISORY KB", "Data Store (JSON)",
              ["Pest Control Protocols", "Chemical & Organic Recs", "Safety Bulletins"],
              border_color=PALETTE["accent_purple"])

    # Data Flows
    draw_arrow(ax, 22, 83, 41, 83, "Credentials / Agro Input", PALETTE["text_main"])
    draw_arrow(ax, 78, 83, 61, 83, "Live Weather JSON", PALETTE["accent_cyan"])
    draw_arrow(ax, 51, 75, 51, 62, "Sanitized Payload", PALETTE["primary_light"])
    draw_arrow(ax, 51, 44, 51, 30, "Top-3 Pest Ranks", PALETTE["accent_amber"])
    draw_arrow(ax, 61, 20, 74, 20, "Query Pest", PALETTE["accent_purple"], style="<->")
    draw_arrow(ax, 41, 20, 26, 20, "Store Record", PALETTE["accent_purple"])
    draw_arrow(ax, 41, 15, 14, 75, "PDF / Advisory Response", PALETTE["accent_blue"])

    save_diagram(fig, "data_flow_diagram")

# =====================================================================
# 4. ENTITY RELATIONSHIP (ER) DIAGRAM
# =====================================================================
def generate_er_diagram():
    fig, ax = setup_canvas(16, 10, "Database Entity Relationship (ER) Diagram - SQLite Schema")
    
    # Tables
    draw_card(ax, 5, 55, 26, 36, "TABLE: users", "Authentication & Profiles",
              ["id (INTEGER PK AUTOINCREMENT)", "name (VARCHAR(120))", "email (VARCHAR(190) UNIQUE)", "password_hash (VARCHAR(255))", "role (VARCHAR(30))", "state (VARCHAR(100))", "district (VARCHAR(100))", "preferred_crop (VARCHAR(100))", "created_at (DATETIME)", "status (VARCHAR(30))"],
              border_color=PALETTE["primary_light"])
              
    draw_card(ax, 37, 55, 28, 36, "TABLE: prediction_history", "Agronomic Audit Records",
              ["id (INTEGER PK AUTOINCREMENT)", "user_id (INTEGER FK -> users.id)", "crop (VARCHAR(100))", "district (VARCHAR(100))", "state (VARCHAR(100))", "temperature (FLOAT)", "humidity (FLOAT)", "rainfall (FLOAT)", "predicted_pest (VARCHAR(120))", "pest_confidence (FLOAT)", "predicted_risk (VARCHAR(50))", "risk_confidence (FLOAT)", "created_at (DATETIME)"],
              border_color=PALETTE["accent_amber"])

    draw_card(ax, 69, 55, 26, 36, "TABLE: user_preferences", "UI & Custom Settings",
              ["id (INTEGER PK AUTOINCREMENT)", "user_id (INTEGER FK -> users.id)", "theme (VARCHAR(30))", "language (VARCHAR(10))", "email_alerts (BOOLEAN)", "sms_alerts (BOOLEAN)", "two_factor_auth (BOOLEAN)", "updated_at (DATETIME)"],
              border_color=PALETTE["accent_blue"])

    draw_card(ax, 5, 10, 26, 34, "TABLE: user_sessions", "Active Login Tokens",
              ["id (INTEGER PK AUTOINCREMENT)", "user_id (INTEGER FK -> users.id)", "session_token (VARCHAR(64) UNIQUE)", "device_info (VARCHAR(255))", "ip_address (VARCHAR(45))", "created_at (DATETIME)", "expires_at (DATETIME)"],
              border_color=PALETTE["accent_cyan"])

    draw_card(ax, 37, 10, 28, 34, "TABLE: account_activity", "Security & System Audit Log",
              ["id (INTEGER PK AUTOINCREMENT)", "user_id (INTEGER FK -> users.id)", "action (VARCHAR(100))", "details (TEXT)", "ip_address (VARCHAR(45))", "created_at (DATETIME)"],
              border_color=PALETTE["accent_purple"])

    draw_card(ax, 69, 10, 26, 34, "TABLE: contact_queries", "User Support & Feedback",
              ["id (INTEGER PK AUTOINCREMENT)", "user_id (INTEGER FK -> users.id NULL)", "name (VARCHAR(120))", "email (VARCHAR(190))", "category (VARCHAR(50))", "message (TEXT)", "status (VARCHAR(30))", "created_at (DATETIME)"],
              border_color=PALETTE["accent_red"])

    # Relationships
    draw_arrow(ax, 31, 73, 37, 73, "1 : N (User History)", PALETTE["text_main"], style="<->")
    draw_arrow(ax, 18, 55, 18, 44, "1 : N (Sessions)", PALETTE["text_main"], style="<->")
    draw_arrow(ax, 31, 65, 37, 35, "1 : N (Audit)", PALETTE["text_main"], style="<->")
    draw_arrow(ax, 31, 80, 69, 80, "1 : 1 (Preferences)", PALETTE["text_main"], style="<->")

    save_diagram(fig, "er_diagram")

# =====================================================================
# 5. SEQUENCE DIAGRAM
# =====================================================================
def generate_sequence_diagram():
    fig, ax = setup_canvas(16, 10, "End-to-End Sequence Diagram - Crop Pest Prediction")
    
    actors = [
        (12, "Farmer / User"),
        (32, "Streamlit UI"),
        (52, "Weather Service"),
        (72, "ML Pipeline"),
        (90, "Database / KB")
    ]
    
    # Draw vertical lifelines
    for x, name in actors:
        ax.plot([x, x], [12, 85], color=PALETTE["card_border"], linestyle="--", lw=1.5, zorder=1)
        ax.text(x, 88, name, ha="center", va="center", fontsize=11, fontweight="bold",
                color=PALETTE["text_main"], bbox=dict(boxstyle="round,pad=0.4", fc=PALETTE["card_bg"], ec=PALETTE["card_border"]))

    steps = [
        (12, 32, 80, "1. Selects Crop & District", PALETTE["accent_blue"]),
        (32, 52, 73, "2. Request Live Weather Sync", PALETTE["accent_cyan"]),
        (52, 32, 66, "3. Return Temp, Hum, Rain JSON", PALETTE["accent_cyan"]),
        (32, 12, 59, "4. Display Weather & Form Populated", PALETTE["accent_blue"]),
        (12, 32, 52, "5. Click 'Predict Pest Risk'", PALETTE["accent_blue"]),
        (32, 72, 45, "6. Forward Sanitized Agro Vector", PALETTE["primary_light"]),
        (72, 72, 38, "7. Pipeline Feature Eng. & Predict", PALETTE["accent_amber"]),
        (72, 32, 31, "8. Return Top-3 Ranks & Probabilities", PALETTE["primary_light"]),
        (32, 90, 24, "9. Lookup Rank-1 Advisory & Save DB", PALETTE["accent_purple"]),
        (90, 32, 17, "10. Advisory Data & Record ID Confirmed", PALETTE["accent_purple"]),
        (32, 12, 10, "11. Render Dashboard, Top-3 Cards & PDF Download", PALETTE["primary_light"])
    ]
    
    for x1, x2, y, label, col in steps:
        if x1 == x2:
            # Self-call
            box = patches.Arc((x1+2, y), 4, 3, angle=0, theta1=-90, theta2=90, color=col, lw=1.8)
            ax.add_patch(box)
            ax.text(x1 + 4.5, y, label, ha="left", va="center", fontsize=8, color=col, fontweight="semibold")
        else:
            draw_arrow(ax, x1, y, x2, y, label, col)

    save_diagram(fig, "sequence_diagram")

# =====================================================================
# 6. DEPLOYMENT ARCHITECTURE
# =====================================================================
def generate_deployment_architecture():
    fig, ax = setup_canvas(16, 10, "Production Deployment Architecture - Container & Cloud Topology")
    
    draw_card(ax, 5, 75, 90, 16, "INTERNET / EDGE GATEWAY", "Client Traffic & Security",
              border_color=PALETTE["accent_blue"])
    draw_card(ax, 8, 77, 26, 11, "Farmer Devices", "Desktop & Mobile Browsers", ["Chrome / Safari / Firefox", "Progressive Responsive UI"])
    draw_card(ax, 37, 77, 26, 11, "Cloudflare / CDN", "DDoS & SSL Termination", ["Global Edge Anycast", "WAF & SSL/TLS 1.3"])
    draw_card(ax, 66, 77, 26, 11, "External APIs", "Third-party Services", ["Open-Meteo Weather API", "Government Agro Feeds"])

    draw_card(ax, 5, 40, 90, 28, "DOCKER CONTAINER ENVIRONMENT (Render / Railway / Cloud)", "Application Pod",
              border_color=PALETTE["primary_light"])
    draw_card(ax, 8, 42, 26, 23, "Nginx / Reverse Proxy", "Port 80/443 Routing",
              ["Reverse Proxy Traffic Routing", "Rate Limiting & Gzip Compress", "Static Asset Caching", "Health Probe Relay"])
    draw_card(ax, 37, 42, 26, 23, "Streamlit SaaS App", "Port 8501 (Web)",
              ["Multi-threaded Session State", "Real-Time Visualization Engine", "ReportLab PDF Generator", "Bcrypt Auth & Rate Limiter"])
    draw_card(ax, 66, 42, 26, 23, "FastAPI Microservice", "Port 8000 (REST)",
              ["Uvicorn ASGI High Concurrency", "Pre-warmed Model Lifespan", "OpenAPI Documentation (/docs)", "CORS & Bearer Security"])

    draw_card(ax, 5, 8, 90, 25, "PERSISTENCE & STORAGE TIER", "High Availability Data",
              border_color=PALETTE["accent_purple"])
    draw_card(ax, 8, 10, 40, 20, "SQLite Enterprise Engine (WAL Mode)", "ACID Local Storage",
              ["users.db with 10 B-Tree Indexes", "Write-Ahead Logging (High Read/Write)", "Zero Deadlock Concurrency", "Integrated Disaster Recovery Engine"])
    draw_card(ax, 52, 10, 40, 20, "Model & Asset Repository", "Versioned Artifacts",
              ["best_model.pkl (Trained Gradient Boosting)", "preprocessing_pipeline.pkl", "advisory_knowledgebase.json", "Automated Hourly Timestamped Backups"])

    # Connectors
    draw_arrow(ax, 21, 77, 21, 65, "HTTPS", PALETTE["accent_blue"])
    draw_arrow(ax, 50, 77, 50, 65, "Proxy", PALETTE["accent_blue"])
    draw_arrow(ax, 79, 77, 79, 65, "REST Fetch", PALETTE["accent_cyan"])
    draw_arrow(ax, 50, 42, 28, 30, "Read/Write DB", PALETTE["accent_purple"])
    draw_arrow(ax, 79, 42, 72, 30, "Load Models", PALETTE["primary_light"])

    save_diagram(fig, "deployment_architecture")

# =====================================================================
# 7. COMPONENT DIAGRAM
# =====================================================================
def generate_component_diagram():
    fig, ax = setup_canvas(16, 10, "Software Component Architecture & Dependency Graph")
    
    components = [
        (6, 68, 26, 22, "UI Components (app/)", "Frontend Modules",
         ["app.py (Main Streamlit Entry)", "auth.py (Login/Register Gateway)", "admin_portal.py (Admin Center)", "user_dashboard.py (Farmer KPIs)"], PALETTE["accent_blue"]),
        (37, 68, 26, 22, "Core Services (app/)", "Business Logic",
         ["predictor.py (Inference Wrapper)", "recommender.py (Advisory Matcher)", "weather.py (Open-Meteo Client)", "pdf_generator.py (ReportLab PDFs)"], PALETTE["primary_light"]),
        (68, 68, 26, 22, "Security & Ops (app/)", "Support Modules",
         ["database.py (SQLite CRUD & Health)", "security.py (Bcrypt, XSS, Limiter)", "logger.py (Masked Audit Logs)", "backup_manager.py (DR Snapshots)"], PALETTE["accent_purple"]),
        (6, 18, 26, 22, "REST Microservice (src/)", "API Endpoints",
         ["api.py (FastAPI App & Lifespan)", "Pydantic Prediction Schemas", "Advisory Query Endpoint", "Token Authentication Router"], PALETTE["accent_cyan"]),
        (37, 18, 26, 22, "ML Pipeline (src/)", "Model Architecture",
         ["predict.py (Clean Inference Engine)", "pipeline_config.py (Config & Paths)", "data_sanitizer.py (Audit & Clean)", "train_production_pipeline.py"], PALETTE["accent_amber"]),
        (68, 18, 26, 22, "Test & QA Suite (tests/)", "Automated Validation",
         ["test_phases_6_7_8.py (ML Invariance)", "test_rest_api_phase13.py (REST API)", "test_saas_ui.py (Streamlit AppTest)", "test_production_readiness.py (Ops)"], PALETTE["accent_red"])
    ]
    
    for x, y, w, h, title, sub, itms, col in components:
        draw_card(ax, x, y, w, h, title, sub, itms, border_color=col)
        
    draw_arrow(ax, 32, 79, 37, 79, "Invokes", PALETTE["text_main"])
    draw_arrow(ax, 63, 79, 68, 79, "Secures", PALETTE["text_main"])
    draw_arrow(ax, 50, 68, 50, 40, "Executes ML", PALETTE["primary_light"])
    draw_arrow(ax, 32, 29, 37, 29, "Imports", PALETTE["text_main"])
    draw_arrow(ax, 68, 29, 63, 29, "Validates", PALETTE["accent_red"])

    save_diagram(fig, "component_diagram")

# =====================================================================
# 8. WORKFLOW DIAGRAM
# =====================================================================
def generate_workflow_diagram():
    fig, ax = setup_canvas(16, 10, "End-to-End User & Inference Workflow Diagram")
    
    steps = [
        (4, 55, 18, 30, "1. USER AUTHENTICATION", "Gateway Phase",
         ["Farmer Registration / Login", "Bcrypt Password Verification", "Brute Force Check (<5 tries)", "Session Token Initialization", "Load Farmer Saved Preferences"]),
        (28, 55, 18, 30, "2. LOCATION & WEATHER", "Telemetry Phase",
         ["Select State, District, Crop", "Trigger Weather Sync", "Check 10-Minute Cache", "Query Open-Meteo REST API", "Fallback to Baseline if Offline"]),
        (52, 55, 18, 30, "3. AGRO DATA AUDIT", "Validation Phase",
         ["Validate Agronomic Bounds", "Clamp Extreme Rainfall/Temp", "Compute Heat Index (THI)", "Compute Rain-to-Humidity", "Construct Model Feature Vector"]),
        (76, 55, 18, 30, "4. MODEL PREDICTION", "Inference Phase",
         ["Apply Preprocessing Pipeline", "Execute Multi-Output Model", "Sort Class Probabilities", "Isolate Top-3 Pest Classes", "Compute Risk Probability"])
    ]
    
    for i, (x, y, w, h, title, sub, itms) in enumerate(steps):
        col = [PALETTE["accent_blue"], PALETTE["accent_cyan"], PALETTE["primary_light"], PALETTE["accent_amber"]][i]
        draw_card(ax, x, y, w, h, title, sub, itms, border_color=col)
        if i < len(steps) - 1:
            draw_arrow(ax, x + w, y + h/2, steps[i+1][0], y + h/2, "Next", col)

    outcomes = [
        (16, 10, 26, 30, "5. RANK-1 ADVISORY GENERATION", "Decision Support",
         ["Extract Highest Probability Pest", "Query Knowledgebase JSON", "Formulate Chemical Pesticide & Dose", "Formulate Organic Bio-Control", "Generate Farmer Safety Guidelines"], PALETTE["accent_red"]),
        (58, 10, 26, 30, "6. PERSISTENCE & PDF EXPORT", "Reporting & Audit",
         ["Save Prediction to SQLite DB", "Log Action to Audit Trail", "Generate High-Res A4 PDF Report", "Render Interactive Plotly Charts", "Enable Instant PDF Download"], PALETTE["accent_purple"])
    ]
    
    for x, y, w, h, title, sub, itms, col in outcomes:
        draw_card(ax, x, y, w, h, title, sub, itms, border_color=col)
        
    draw_arrow(ax, 85, 55, 85, 25, "Rank-1 Only", PALETTE["accent_amber"])
    draw_arrow(ax, 85, 25, 42, 25, "Advisory Payload", PALETTE["accent_red"])
    draw_arrow(ax, 42, 25, 58, 25, "Persist & Export", PALETTE["primary_light"])

    save_diagram(fig, "workflow_diagram")

if __name__ == "__main__":
    print(f"Generating 8 architecture diagrams into: {DIAGRAMS_DIR}")
    generate_system_architecture()
    generate_ml_pipeline()
    generate_data_flow()
    generate_er_diagram()
    generate_sequence_diagram()
    generate_deployment_architecture()
    generate_component_diagram()
    generate_workflow_diagram()
    print("All 8 architecture diagrams generated successfully in both PNG and SVG formats!")
