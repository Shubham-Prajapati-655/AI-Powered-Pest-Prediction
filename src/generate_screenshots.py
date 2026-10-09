"""
High-Fidelity Application Screenshots Generator
AI-Powered Crop Pest Prediction & Agricultural Advisory System
Generates crisp, professional 1920x1080 UI screenshots for:
1. Login (Auth Gateway - Sign In)
2. Register (Auth Gateway - Create Account)
3. Dashboard (Farmer KPI Center & Workflow)
4. Prediction (Agricultural Telemetry & Input Form)
5. Top-3 Prediction (Rank Cards with Probabilities & Tiers)
6. Probability Chart (Plotly-style Confidence Distribution)
7. Weather (Live Open-Meteo Telemetry & Agro Indices)
8. History (Searchable Prediction Records & Audit Logs)
9. PDF Report (A4 Field Advisory Report Preview)
10. Admin (Enterprise Operations & Database Metrics)
11. API Docs (Interactive OpenAPI / Swagger UI Preview)
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch

SCREENSHOTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "screenshots"))
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# SaaS Theme Palette
PAL = {
    "bg": "#0B0F17",
    "surface": "#121824",
    "card": "#182234",
    "card_border": "#243247",
    "sidebar": "#0E1522",
    "primary": "#2EA043",
    "primary_dark": "#1B5E20",
    "accent_blue": "#388BFD",
    "accent_cyan": "#39C5CF",
    "accent_amber": "#D29922",
    "accent_red": "#F85149",
    "accent_purple": "#A371F7",
    "text": "#F0F6FC",
    "text_muted": "#8B949E",
    "nav_active": "#1F2D44"
}

def create_browser_window(title="AgriAI Advisor - Smart Crop Pest Prediction"):
    fig, ax = plt.subplots(figsize=(19.2, 10.8), facecolor=PAL["bg"])
    ax.set_facecolor(PAL["bg"])
    ax.set_xlim(0, 192)
    ax.set_ylim(0, 108)
    ax.axis("off")
    
    # Browser Window Bar
    bar = FancyBboxPatch((0, 102), 192, 6, boxstyle="square,pad=0", facecolor="#090D14", edgecolor="none", zorder=10)
    ax.add_patch(bar)
    
    # Browser Traffic Lights
    ax.add_patch(patches.Circle((4, 105), 0.9, facecolor="#FF5F56", edgecolor="none", zorder=11))
    ax.add_patch(patches.Circle((7, 105), 0.9, facecolor="#FFBD2E", edgecolor="none", zorder=11))
    ax.add_patch(patches.Circle((10, 105), 0.9, facecolor="#27C93F", edgecolor="none", zorder=11))
    
    # URL bar
    url_box = FancyBboxPatch((24, 103), 144, 4, boxstyle="round,pad=0.2,rounding_size=1",
                             facecolor="#161B22", edgecolor="#30363D", zorder=11)
    ax.add_patch(url_box)
    ax.text(96, 105, "🔒 https://agriai-advisor.platform.org • AgriAI Agricultural Intelligence Platform v2.2.0",
            ha="center", va="center", color=PAL["text_muted"], fontsize=9.5, zorder=12)

    return fig, ax

def draw_sidebar(ax, active_item="🏠 Dashboard"):
    # Left Sidebar
    sb = FancyBboxPatch((0, 0), 38, 102, boxstyle="square,pad=0", facecolor=PAL["sidebar"],
                        edgecolor=PAL["card_border"], linewidth=1, zorder=2)
    ax.add_patch(sb)
    
    # Logo & Brand
    ax.text(8, 96, "🌱 AgriAI Advisor", color=PAL["primary"], fontsize=15, fontweight="bold", zorder=3)
    ax.text(8, 93, "Agricultural Intelligence v2.2.0", color=PAL["text_muted"], fontsize=9, zorder=3)
    
    # Nav Items
    items = [
        ("🏠 Dashboard", "Overview & Metrics"),
        ("🌾 Prediction", "Crop Pest Analysis"),
        ("📜 History", "Past Farmer Records"),
        ("👤 Profile", "Account Settings"),
        ("🛡️ Admin Portal", "Enterprise Ops"),
        ("ℹ️ About", "Platform & Mission"),
        ("📩 Contact", "Support & Inquiries")
    ]
    
    y = 85
    for label, desc in items:
        is_act = (label == active_item)
        if is_act:
            btn_bg = FancyBboxPatch((4, y - 2), 30, 5, boxstyle="round,pad=0.3,rounding_size=1",
                                   facecolor=PAL["primary_dark"], edgecolor=PAL["primary"], linewidth=1.2, zorder=3)
            ax.add_patch(btn_bg)
            ax.text(7, y + 0.5, label, color=PAL["text"], fontsize=11, fontweight="bold", zorder=4)
        else:
            btn_bg = FancyBboxPatch((4, y - 2), 30, 5, boxstyle="round,pad=0.3,rounding_size=1",
                                   facecolor=PAL["surface"], edgecolor="none", zorder=3)
            ax.add_patch(btn_bg)
            ax.text(7, y + 0.5, label, color=PAL["text_muted"], fontsize=10.5, zorder=4)
        y -= 7.5

    # User profile badge at bottom
    ub = FancyBboxPatch((4, 4), 30, 8, boxstyle="round,pad=0.3,rounding_size=1",
                        facecolor="#141E2E", edgecolor=PAL["card_border"], zorder=3)
    ax.add_patch(ub)
    ax.add_patch(patches.Circle((8, 8), 2.2, facecolor=PAL["primary"], zorder=4))
    ax.text(8, 8, "TF", color="#FFFFFF", ha="center", va="center", fontsize=8.5, fontweight="bold", zorder=5)
    ax.text(12, 9, "Test Farmer", color=PAL["text"], fontsize=9.5, fontweight="bold", zorder=4)
    ax.text(12, 6.5, "farmer@agriai.org", color=PAL["text_muted"], fontsize=8, zorder=4)

def save_screen(fig, name):
    path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"Generated screenshot: {name}.png")

# 1. LOGIN SCREENSHOT
def make_login_screen():
    fig, ax = create_browser_window()
    card = FancyBboxPatch((66, 16), 60, 74, boxstyle="round,pad=0.5,rounding_size=1.5",
                          facecolor=PAL["card"], edgecolor=PAL["card_border"], linewidth=1.5, zorder=2)
    ax.add_patch(card)
    ax.add_patch(patches.Circle((96, 76), 5, facecolor="#1B5E20", edgecolor=PAL["primary"], linewidth=2, zorder=3))
    ax.text(96, 76, "🌱", ha="center", va="center", fontsize=20, zorder=4)
    ax.text(96, 67, "AgriAI Platform Gateway", ha="center", va="center", color=PAL["text"], fontsize=16, fontweight="bold", zorder=3)
    ax.text(96, 63, "Smart Crop Pest Prediction & Precision Advisory", ha="center", va="center", color=PAL["text_muted"], fontsize=10, zorder=3)
    
    # Inputs
    fields = [("Email Address", "farmer@example.com", 53), ("Password", "••••••••••••", 42)]
    for label, val, y in fields:
        ax.text(72, y + 4.5, label, color=PAL["text"], fontsize=10, fontweight="semibold", zorder=3)
        inp = FancyBboxPatch((72, y - 1), 48, 4.5, boxstyle="round,pad=0.2,rounding_size=0.8",
                             facecolor="#0B1017", edgecolor="#30363D", zorder=3)
        ax.add_patch(inp)
        ax.text(74, y + 1.2, val, color=PAL["text_muted"], fontsize=9.5, zorder=4)
        
    btn = FancyBboxPatch((72, 28), 48, 5.5, boxstyle="round,pad=0.3,rounding_size=0.8",
                         facecolor=PAL["primary"], edgecolor="none", zorder=3)
    ax.add_patch(btn)
    ax.text(96, 30.7, "Sign In to AgriAI", ha="center", va="center", color="#FFFFFF", fontsize=11, fontweight="bold", zorder=4)
    ax.text(96, 21, "New to AgriAI? Register a Farmer Account", ha="center", va="center", color=PAL["accent_blue"], fontsize=9.5, zorder=3)
    save_screen(fig, "login")

# 2. REGISTER SCREENSHOT
def make_register_screen():
    fig, ax = create_browser_window()
    card = FancyBboxPatch((60, 10), 72, 84, boxstyle="round,pad=0.5,rounding_size=1.5",
                          facecolor=PAL["card"], edgecolor=PAL["card_border"], linewidth=1.5, zorder=2)
    ax.add_patch(card)
    ax.text(96, 86, "Create New Farmer Account", ha="center", va="center", color=PAL["text"], fontsize=16, fontweight="bold", zorder=3)
    ax.text(96, 82, "Join thousands of Indian farmers protecting crops with AI", ha="center", va="center", color=PAL["text_muted"], fontsize=10, zorder=3)
    
    fields = [
        ("Full Name", "Shubham Prajapati", 72),
        ("Email Address", "shubham.farmer@agriai.org", 61),
        ("State / Province", "Maharashtra", 50),
        ("Primary Crop", "Cotton", 39),
        ("Password", "••••••••••••", 28)
    ]
    for label, val, y in fields:
        ax.text(66, y + 4.2, label, color=PAL["text"], fontsize=9.5, fontweight="semibold", zorder=3)
        inp = FancyBboxPatch((66, y - 0.5), 60, 4, boxstyle="round,pad=0.2,rounding_size=0.8",
                             facecolor="#0B1017", edgecolor="#30363D", zorder=3)
        ax.add_patch(inp)
        ax.text(68, y + 1.5, val, color=PAL["text_muted"], fontsize=9, zorder=4)
        
    btn = FancyBboxPatch((66, 17), 60, 5, boxstyle="round,pad=0.3,rounding_size=0.8",
                         facecolor=PAL["primary"], edgecolor="none", zorder=3)
    ax.add_patch(btn)
    ax.text(96, 19.5, "Complete Registration", ha="center", va="center", color="#FFFFFF", fontsize=11, fontweight="bold", zorder=4)
    save_screen(fig, "register")

# 3. DASHBOARD SCREENSHOT
def make_dashboard_screen():
    fig, ax = create_browser_window()
    draw_sidebar(ax, "🏠 Dashboard")
    
    # Main Header
    ax.text(44, 94, "🌾 Precision Agricultural Intelligence Dashboard", color=PAL["text"], fontsize=17, fontweight="bold", zorder=3)
    ax.text(44, 90, "Real-time crop telemetry, pest probability rankings, and agronomic management", color=PAL["text_muted"], fontsize=10, zorder=3)
    
    # 4 KPI Cards
    kpis = [
        ("Total Predictions", "249,700", "Master Dataset Trained", PAL["accent_blue"], 44),
        ("Target Pest Classes", "12 Pests", "Multi-Output Taxonomy", PAL["primary"], 79),
        ("Model Accuracy", "94.6%", "CatBoost / LightGBM", PAL["accent_amber"], 114),
        ("API Response SLA", "122 ms", "Sub-200ms Target", PAL["accent_cyan"], 149)
    ]
    for title, val, sub, col, x in kpis:
        box = FancyBboxPatch((x, 70), 32, 16, boxstyle="round,pad=0.4,rounding_size=1",
                             facecolor=PAL["card"], edgecolor=col, linewidth=1.5, zorder=3)
        ax.add_patch(box)
        ax.text(x + 3, 82, title, color=PAL["text_muted"], fontsize=9.5, zorder=4)
        ax.text(x + 3, 76, val, color=col, fontsize=18, fontweight="bold", zorder=4)
        ax.text(x + 3, 72, sub, color=PAL["text_muted"], fontsize=8, zorder=4)

    # Big Visualization Area
    main_box = FancyBboxPatch((44, 8), 137, 58, boxstyle="round,pad=0.5,rounding_size=1.2",
                              facecolor=PAL["card"], edgecolor=PAL["card_border"], zorder=3)
    ax.add_patch(main_box)
    ax.text(48, 62, "Regional Pest Infestation Risk Distribution (Current Season)", color=PAL["text"], fontsize=13, fontweight="bold", zorder=4)
    
    # Fake Mock Bars
    pests = ["Bollworm", "Aphids", "Stem Borer", "Whitefly", "Leafhopper", "Brown Plant Hopper", "Thrips"]
    probs = [0.82, 0.64, 0.58, 0.49, 0.38, 0.31, 0.22]
    colors = [PAL["accent_red"], PAL["accent_amber"], PAL["accent_amber"], PAL["primary"], PAL["primary"], PAL["accent_blue"], PAL["accent_blue"]]
    
    y = 54
    for p, pr, c in zip(pests, probs, colors):
        ax.text(48, y, p, color=PAL["text"], fontsize=9.5, zorder=4)
        bg_bar = FancyBboxPatch((70, y - 0.5), 100, 3, boxstyle="round,pad=0.1,rounding_size=0.5",
                                facecolor="#0B111A", edgecolor="none", zorder=4)
        ax.add_patch(bg_bar)
        fg_bar = FancyBboxPatch((70, y - 0.5), pr * 100, 3, boxstyle="round,pad=0.1,rounding_size=0.5",
                                facecolor=c, edgecolor="none", zorder=5)
        ax.add_patch(fg_bar)
        ax.text(70 + pr * 100 + 2, y + 1, f"{pr*100:.1f}%", color=PAL["text_muted"], fontsize=8.5, zorder=6)
        y -= 6.5

    save_screen(fig, "dashboard")

# 4. PREDICTION SCREENSHOT
def make_prediction_screen():
    fig, ax = create_browser_window()
    draw_sidebar(ax, "🌾 Prediction")
    
    ax.text(44, 94, "🌾 Crop Pest & Disease Diagnostic Engine", color=PAL["text"], fontsize=17, fontweight="bold", zorder=3)
    ax.text(44, 90, "Automated telemetry, atmospheric indexing, and gradient boosted prediction", color=PAL["text_muted"], fontsize=10, zorder=3)
    
    # Form Container
    f_box = FancyBboxPatch((44, 10), 137, 76, boxstyle="round,pad=0.5,rounding_size=1.2",
                           facecolor=PAL["card"], edgecolor=PAL["card_border"], zorder=3)
    ax.add_patch(f_box)
    
    # Form Inputs Grid
    inputs = [
        ("Selected State", "Andhra Pradesh", 48, 70), ("Target District", "Guntur", 94, 70), ("Crop Cultivated", "Cotton", 140, 70),
        ("Sowing Season", "Kharif", 48, 55), ("Soil Classification", "Black Soil", 94, 55), ("Ambient Temp (°C)", "32.5 °C", 140, 55),
        ("Relative Humidity (%)", "78.0 %", 48, 40), ("Accumulated Rain (mm)", "145.0 mm", 94, 40), ("Wind Speed (km/h)", "12.4 km/h", 140, 40)
    ]
    for lbl, val, x, y in inputs:
        ax.text(x, y + 5, lbl, color=PAL["text"], fontsize=9.5, fontweight="semibold", zorder=4)
        ibox = FancyBboxPatch((x, y), 38, 4.5, boxstyle="round,pad=0.2,rounding_size=0.8",
                              facecolor="#0B111A", edgecolor="#30363D", zorder=4)
        ax.add_patch(ibox)
        ax.text(x + 2, y + 2, val, color=PAL["accent_cyan"], fontsize=9.5, zorder=5)
        
    # Weather sync button
    w_btn = FancyBboxPatch((48, 22), 42, 6, boxstyle="round,pad=0.3,rounding_size=0.8",
                           facecolor="#1A3B5C", edgecolor=PAL["accent_blue"], linewidth=1.2, zorder=4)
    ax.add_patch(w_btn)
    ax.text(69, 25, "⛅ Fetch Live Weather Data", ha="center", va="center", color=PAL["accent_blue"], fontsize=10, fontweight="bold", zorder=5)
    
    # Predict button
    p_btn = FancyBboxPatch((96, 22), 82, 6, boxstyle="round,pad=0.3,rounding_size=0.8",
                           facecolor=PAL["primary"], edgecolor="none", zorder=4)
    ax.add_patch(p_btn)
    ax.text(137, 25, "🚀 Execute AI Pest & Risk Inference", ha="center", va="center", color="#FFFFFF", fontsize=11, fontweight="bold", zorder=5)

    save_screen(fig, "prediction")

# 5. TOP-3 PREDICTION SCREENSHOT
def make_top3_screen():
    fig, ax = create_browser_window()
    draw_sidebar(ax, "🌾 Prediction")
    
    ax.text(44, 94, "🎯 Diagnostic Results: Top-3 Potential Pest Threats", color=PAL["text"], fontsize=17, fontweight="bold", zorder=3)
    ax.text(44, 90, "Multi-class probabilistic ranking with dynamic confidence classification", color=PAL["text_muted"], fontsize=10, zorder=3)
    
    ranks = [
        ("RANK 1: PRIMARY THREAT", "Bollworm", "82.45% Probability", "CRITICAL RISK", PAL["accent_red"], 44),
        ("RANK 2: SECONDARY RISK", "Aphids", "11.30% Probability", "MODERATE RISK", PAL["accent_amber"], 91),
        ("RANK 3: TERTIARY WATCH", "Whitefly", "4.25% Probability", "LOW RISK", PAL["primary"], 138)
    ]
    for rtitle, pest, prob, risk, col, x in ranks:
        rcard = FancyBboxPatch((x, 50), 43, 36, boxstyle="round,pad=0.5,rounding_size=1.2",
                               facecolor=PAL["card"], edgecolor=col, linewidth=2, zorder=3)
        ax.add_patch(rcard)
        ax.text(x + 21.5, 81, rtitle, ha="center", va="center", color=col, fontsize=10, fontweight="bold", zorder=4)
        ax.text(x + 21.5, 72, pest, ha="center", va="center", color=PAL["text"], fontsize=18, fontweight="bold", zorder=4)
        ax.text(x + 21.5, 64, prob, ha="center", va="center", color=col, fontsize=13, fontweight="bold", zorder=4)
        badge = FancyBboxPatch((x + 10, 54), 23, 4, boxstyle="round,pad=0.2,rounding_size=0.6",
                               facecolor=col, edgecolor="none", zorder=4)
        ax.add_patch(badge)
        ax.text(x + 21.5, 56, risk, ha="center", va="center", color="#FFFFFF", fontsize=8.5, fontweight="bold", zorder=5)

    # Advisory Section for Rank 1
    adv_box = FancyBboxPatch((44, 8), 137, 38, boxstyle="round,pad=0.5,rounding_size=1.2",
                             facecolor="#1A2433", edgecolor=PAL["accent_red"], linewidth=1.5, zorder=3)
    ax.add_patch(adv_box)
    ax.text(48, 41, "🛡️ Recommended Action Plan (Strictly for Rank-1: Bollworm)", color=PAL["accent_red"], fontsize=12, fontweight="bold", zorder=4)
    ax.text(48, 35, "• Chemical Pesticide: Emamectin Benzoate 5% SG @ 4.0 g / 10L water", color=PAL["text"], fontsize=10, zorder=4)
    ax.text(48, 29, "• Biological Control: Release Trichogramma chilonis egg parasitoids @ 50,000/ha; Neem Seed Kernel Extract (NSKE 5%)", color=PAL["text"], fontsize=10, zorder=4)
    ax.text(48, 23, "• Preventive Measures: Install 5 pheromone traps per acre; avoid excessive nitrogenous fertilizers", color=PAL["text"], fontsize=10, zorder=4)
    ax.text(48, 17, "• Mandatory Safety Notes: Wear chemical-resistant gloves, eye protection, and respirator during spraying", color=PAL["text_muted"], fontsize=9.5, zorder=4)

    save_screen(fig, "top3_prediction")

# 6. PROBABILITY CHART SCREENSHOT
def make_prob_chart_screen():
    fig, ax = create_browser_window()
    draw_sidebar(ax, "🌾 Prediction")
    
    ax.text(44, 94, "📊 Multi-Class Probability Distribution & Feature Explanations", color=PAL["text"], fontsize=17, fontweight="bold", zorder=3)
    ax.text(44, 90, "Detailed model output probabilities across full pest spectrum", color=PAL["text_muted"], fontsize=10, zorder=3)
    
    box = FancyBboxPatch((44, 10), 137, 76, boxstyle="round,pad=0.5,rounding_size=1.2",
                         facecolor=PAL["card"], edgecolor=PAL["card_border"], zorder=3)
    ax.add_patch(box)
    
    pests = ["Bollworm", "Aphids", "Whitefly", "Stem Borer", "Leafhopper", "Brown Plant Hopper", "Thrips", "Armyworm"]
    probs = [0.8245, 0.1130, 0.0425, 0.0110, 0.0050, 0.0025, 0.0010, 0.0005]
    
    y = 74
    for i, (p, pr) in enumerate(zip(pests, probs)):
        ax.text(48, y, f"#{i+1} {p}", color=PAL["text"], fontsize=10, fontweight="bold" if i==0 else "normal", zorder=4)
        bar_bg = FancyBboxPatch((74, y - 0.5), 88, 4, boxstyle="round,pad=0.1,rounding_size=0.5",
                                facecolor="#0B111A", edgecolor="none", zorder=4)
        ax.add_patch(bar_bg)
        c = PAL["accent_red"] if i==0 else (PAL["accent_amber"] if i==1 else PAL["primary"])
        bar_fg = FancyBboxPatch((74, y - 0.5), pr * 88, 4, boxstyle="round,pad=0.1,rounding_size=0.5",
                                facecolor=c, edgecolor="none", zorder=5)
        ax.add_patch(bar_fg)
        ax.text(165, y + 1.5, f"{pr*100:.2f}%", color=c, fontsize=9.5, fontweight="bold", zorder=5)
        y -= 7.5

    save_screen(fig, "probability_chart")

# 7. WEATHER SCREENSHOT
def make_weather_screen():
    fig, ax = create_browser_window()
    draw_sidebar(ax, "🌾 Prediction")
    
    ax.text(44, 94, "⛅ Regional Agro-Climatic Intelligence (Open-Meteo)", color=PAL["text"], fontsize=17, fontweight="bold", zorder=3)
    ax.text(44, 90, "Live telemetry synchronized with 10-minute coordinate cache and 4-tier fallback", color=PAL["text_muted"], fontsize=10, zorder=3)
    
    wcards = [
        ("Ambient Temperature", "32.4 °C", "Normal Kharif Range", PAL["accent_amber"], 44, 52),
        ("Relative Humidity", "76.5 %", "Optimal for Fungal Spores", PAL["accent_cyan"], 91, 52),
        ("Precipitation / Rain", "138.2 mm", "Heavy Monsoon Showers", PAL["accent_blue"], 138, 52),
        ("Wind Velocity", "11.8 km/h", "Favorable Pest Migration", PAL["primary"], 44, 18),
        ("Temperature-Humidity Index", "81.4 THI", "Severe Pest Proliferation", PAL["accent_red"], 91, 18),
        ("Rain-to-Humidity Ratio", "1.78", "High Infestation Vector", PAL["accent_purple"], 138, 18)
    ]
    for t, v, s, col, x, y in wcards:
        b = FancyBboxPatch((x, y), 43, 28, boxstyle="round,pad=0.5,rounding_size=1.2",
                           facecolor=PAL["card"], edgecolor=col, linewidth=1.5, zorder=3)
        ax.add_patch(b)
        ax.text(x + 3, y + 21, t, color=PAL["text_muted"], fontsize=10, zorder=4)
        ax.text(x + 3, y + 13, v, color=col, fontsize=19, fontweight="bold", zorder=4)
        ax.text(x + 3, y + 6, s, color=PAL["text_muted"], fontsize=8.5, zorder=4)

    save_screen(fig, "weather")

# 8. HISTORY SCREENSHOT
def make_history_screen():
    fig, ax = create_browser_window()
    draw_sidebar(ax, "📜 History")
    
    ax.text(44, 94, "📜 Farmer Prediction History & Agronomic Audit Records", color=PAL["text"], fontsize=17, fontweight="bold", zorder=3)
    ax.text(44, 90, "Permanent historical record of all diagnostic assessments with vector PDF download", color=PAL["text_muted"], fontsize=10, zorder=3)
    
    box = FancyBboxPatch((44, 10), 137, 76, boxstyle="round,pad=0.5,rounding_size=1.2",
                         facecolor=PAL["card"], edgecolor=PAL["card_border"], zorder=3)
    ax.add_patch(box)
    
    # Table headers
    headers = [("Date / Time", 48), ("Crop", 72), ("District", 90), ("Predicted Pest", 112), ("Confidence", 138), ("Actions", 158)]
    for h, x in headers:
        ax.text(x, 80, h, color=PAL["accent_cyan"], fontsize=10, fontweight="bold", zorder=4)
        
    records = [
        ("2026-10-02 08:30", "Cotton", "Guntur", "Bollworm", "82.45% (High)", PAL["accent_red"]),
        ("2026-09-28 14:15", "Rice", "Kurnool", "Stem Borer", "79.10% (High)", PAL["accent_amber"]),
        ("2026-09-22 10:45", "Wheat", "Pune", "Aphids", "68.40% (Med)", PAL["primary"]),
        ("2026-09-15 16:20", "Sugarcane", "Nashik", "Whitefly", "74.80% (High)", PAL["accent_amber"]),
        ("2026-09-08 11:10", "Cotton", "Guntur", "Leafhopper", "61.20% (Med)", PAL["primary"])
    ]
    y = 70
    for dt, crp, dist, pest, conf, col in records:
        ax.plot([48, 175], [y - 1.5, y - 1.5], color="#202A3C", lw=1, zorder=4)
        ax.text(48, y, dt, color=PAL["text_muted"], fontsize=9, zorder=4)
        ax.text(72, y, crp, color=PAL["text"], fontsize=9.5, fontweight="semibold", zorder=4)
        ax.text(90, y, dist, color=PAL["text"], fontsize=9.5, zorder=4)
        ax.text(112, y, pest, color=col, fontsize=9.5, fontweight="bold", zorder=4)
        ax.text(138, y, conf, color=col, fontsize=9, zorder=4)
        d_btn = FancyBboxPatch((158, y - 1), 16, 3.5, boxstyle="round,pad=0.1,rounding_size=0.5",
                               facecolor=PAL["primary"], edgecolor="none", zorder=5)
        ax.add_patch(d_btn)
        ax.text(166, y + 0.8, "📥 PDF", ha="center", va="center", color="#FFFFFF", fontsize=8, fontweight="bold", zorder=6)
        y -= 9.5

    save_screen(fig, "history")

# 9. PDF REPORT PREVIEW SCREENSHOT
def make_pdf_report_screen():
    fig, ax = create_browser_window()
    draw_sidebar(ax, "📜 History")
    
    ax.text(44, 94, "📄 Automated Agricultural Advisory Report (A4 PDF Generated)", color=PAL["text"], fontsize=17, fontweight="bold", zorder=3)
    ax.text(44, 90, "Formal decision-support document exported via ReportLab vector rendering engine", color=PAL["text_muted"], fontsize=10, zorder=3)
    
    # A4 Page Mockup
    page = FancyBboxPatch((70, 6), 85, 80, boxstyle="round,pad=0.2,rounding_size=0.8",
                          facecolor="#FFFFFF", edgecolor="#CBD5E1", linewidth=2, zorder=3)
    ax.add_patch(page)
    
    # Green PDF Header
    hdr = FancyBboxPatch((70, 78), 85, 8, boxstyle="square,pad=0",
                         facecolor="#1B4332", edgecolor="none", zorder=4)
    ax.add_patch(hdr)
    ax.text(112.5, 82, "AI CROP PEST ADVISORY REPORT", ha="center", va="center", color="#FFFFFF", fontsize=11, fontweight="bold", zorder=5)
    
    # Document content
    ax.text(75, 73, "Farmer Name: Test Farmer  |  Date: 2026-10-02  |  State: Andhra Pradesh  |  District: Guntur", color="#1F2937", fontsize=6.5, zorder=5)
    ax.plot([75, 150], [71, 71], color="#2EA043", lw=1.5, zorder=5)
    ax.text(75, 67, "1. PRIMARY DIAGNOSIS (RANK-1 THREAT)", color="#1B4332", fontsize=8, fontweight="bold", zorder=5)
    ax.text(75, 62, "Predicted Pest: Bollworm  (Helicoverpa armigera)  •  Confidence: 82.45% (High Risk)", color="#DC2626", fontsize=7.5, fontweight="bold", zorder=5)
    ax.text(75, 56, "2. RECOMMENDED CHEMICAL CONTROLS & DOSAGE", color="#1B4332", fontsize=8, fontweight="bold", zorder=5)
    ax.text(75, 52, "• Apply Emamectin Benzoate 5% SG @ 4.0 g per 10 Liters water via knapsack sprayer.", color="#374151", fontsize=6.5, zorder=5)
    ax.text(75, 48, "• Apply Flubendiamide 39.35% SC @ 2.5 ml per 10 Liters water at egg-hatching phase.", color="#374151", fontsize=6.5, zorder=5)
    ax.text(75, 42, "3. ORGANIC & BIOLOGICAL CONTROL PROTOCOLS", color="#1B4332", fontsize=8, fontweight="bold", zorder=5)
    ax.text(75, 38, "• Release Trichogramma chilonis egg parasitoids @ 50,000 / hectare at weekly intervals.", color="#374151", fontsize=6.5, zorder=5)
    ax.text(75, 34, "• Spray Neem Seed Kernel Extract (NSKE 5%) during early larval instars.", color="#374151", fontsize=6.5, zorder=5)
    ax.text(75, 28, "4. MANDATORY FARMER SAFETY & PPE GUIDELINES", color="#1B4332", fontsize=8, fontweight="bold", zorder=5)
    ax.text(75, 24, "• Always wear chemical-resistant nitrile gloves, eye goggles, and a particulate respirator.", color="#4B5563", fontsize=6.5, zorder=5)
    ax.text(75, 20, "• Avoid spraying against prevailing wind direction; observe a 14-day pre-harvest interval.", color="#4B5563", fontsize=6.5, zorder=5)
    ax.text(112.5, 10, "Page 1 of 1 • Generated by AgriAI Precision Agricultural Intelligence System v2.2.0", ha="center", va="center", color="#9CA3AF", fontsize=5.5, zorder=5)

    save_screen(fig, "pdf_report")

# 10. ADMIN PORTAL SCREENSHOT
def make_admin_screen():
    fig, ax = create_browser_window()
    draw_sidebar(ax, "🛡️ Admin Portal")
    
    ax.text(44, 94, "🛡️ Enterprise Operations & Disaster Recovery Center", color=PAL["text"], fontsize=17, fontweight="bold", zorder=3)
    ax.text(44, 90, "Platform health, SQLite telemetry, audit logs, and automated backup operations", color=PAL["text_muted"], fontsize=10, zorder=3)
    
    # 4 Status Badges
    badges = [
        ("Database Status", "Healthy & Online", "WAL Mode Active", PAL["primary"], 44),
        ("Active B-Tree Indexes", "10 Indexes", "Zero-Scan Lookups", PAL["accent_cyan"], 79),
        ("Registered Farmers", "1,240 Users", "Role-Based Access", PAL["accent_blue"], 114),
        ("Backup System", "Operational", "Hourly Snapshots", PAL["accent_purple"], 149)
    ]
    for t, v, s, col, x in badges:
        b = FancyBboxPatch((x, 70), 32, 16, boxstyle="round,pad=0.4,rounding_size=1",
                           facecolor=PAL["card"], edgecolor=col, linewidth=1.5, zorder=3)
        ax.add_patch(b)
        ax.text(x + 3, 82, t, color=PAL["text_muted"], fontsize=9.5, zorder=4)
        ax.text(x + 3, 76, v, color=col, fontsize=15, fontweight="bold", zorder=4)
        ax.text(x + 3, 72, s, color=PAL["text_muted"], fontsize=8, zorder=4)

    # Database Table Summaries
    tbox = FancyBboxPatch((44, 10), 137, 56, boxstyle="round,pad=0.5,rounding_size=1.2",
                          facecolor=PAL["card"], edgecolor=PAL["card_border"], zorder=3)
    ax.add_patch(tbox)
    ax.text(48, 60, "Database Entity Metrics & Point-in-Time Recovery Controls", color=PAL["text"], fontsize=12, fontweight="bold", zorder=4)
    
    t_headers = [("Table Name", 48), ("Description", 74), ("Record Count", 120), ("Engine Status", 150)]
    for h, x in t_headers:
        ax.text(x, 53, h, color=PAL["accent_cyan"], fontsize=9.5, fontweight="bold", zorder=4)
        
    rows = [
        ("users", "User authentication, profiles, role security", "1,240", "Normal / Indexed"),
        ("prediction_history", "Crop advisory assessments & pest logs", "249,700", "Normal / Indexed"),
        ("contact_queries", "Feedback, support tickets, inquiries", "312", "Normal / Indexed"),
        ("user_preferences", "Farmer & Admin UI settings", "1,240", "Normal / Indexed"),
        ("account_activity", "Security audit logs & activity history", "8,950", "Logged Dynamically")
    ]
    y = 45
    for tn, d, rc, st in rows:
        ax.plot([48, 175], [y - 1.5, y - 1.5], color="#202A3C", lw=1, zorder=4)
        ax.text(48, y, tn, color=PAL["text"], fontsize=9, fontweight="semibold", zorder=4)
        ax.text(74, y, d, color=PAL["text_muted"], fontsize=8.5, zorder=4)
        ax.text(120, y, rc, color=PAL["accent_amber"], fontsize=9, fontweight="bold", zorder=4)
        ax.text(150, y, st, color=PAL["primary"], fontsize=8.5, zorder=4)
        y -= 7

    save_screen(fig, "admin")

# 11. API DOCS SCREENSHOT
def make_api_docs_screen():
    fig, ax = create_browser_window("AgriAI REST API - Swagger UI Documentation")
    
    # Swagger Header Bar
    sb = FancyBboxPatch((0, 92), 192, 10, boxstyle="square,pad=0", facecolor="#1B1B1B", edgecolor="none", zorder=2)
    ax.add_patch(sb)
    ax.text(15, 97, "swagger", color="#89BF04", fontsize=18, fontweight="bold", zorder=3)
    ax.text(32, 97, "supported by FastAPI", color="#888888", fontsize=11, zorder=3)
    ax.text(150, 97, "http://localhost:8000/docs", color="#4990E2", fontsize=10, zorder=3)
    
    # Main Doc Card
    dcard = FancyBboxPatch((15, 10), 162, 78, boxstyle="round,pad=0.5,rounding_size=1",
                           facecolor="#FFFFFF", edgecolor="#E0E0E0", zorder=3)
    ax.add_patch(dcard)
    ax.text(20, 83, "AgriAI Crop Pest Prediction Microservice", color="#3B4151", fontsize=18, fontweight="bold", zorder=4)
    ax.text(20, 78, "Production OpenAPI v3.1.0 • Comprehensive REST API Specification", color="#7D828C", fontsize=10, zorder=4)
    
    endpoints = [
        ("GET", "/health", "Healthcheck & ML model readiness probe", "#61AFFE", 67),
        ("POST", "/predict", "Full Top-3 prediction & advisory inference", "#49CC90", 55),
        ("POST", "/advisory", "Decoupled agronomic advisory lookup", "#49CC90", 43),
        ("POST", "/login", "User authentication & JWT token issuance", "#49CC90", 31),
        ("POST", "/report", "Generate base64 encoded PDF advisory report", "#49CC90", 19)
    ]
    for m, ep, desc, col, y in endpoints:
        box = FancyBboxPatch((20, y - 2), 152, 9, boxstyle="round,pad=0.2,rounding_size=0.6",
                             facecolor="#F7F9FA", edgecolor=col, linewidth=1.5, zorder=4)
        ax.add_patch(box)
        m_tag = FancyBboxPatch((22, y - 0.5), 14, 6, boxstyle="round,pad=0.2,rounding_size=0.4",
                               facecolor=col, edgecolor="none", zorder=5)
        ax.add_patch(m_tag)
        ax.text(29, y + 2.5, m, ha="center", va="center", color="#FFFFFF", fontsize=10, fontweight="bold", zorder=6)
        ax.text(39, y + 2.5, ep, color="#3B4151", fontsize=11, fontweight="bold", zorder=5)
        ax.text(80, y + 2.5, desc, color="#7D828C", fontsize=9.5, zorder=5)

    save_screen(fig, "api_docs")

if __name__ == "__main__":
    print(f"Generating 11 UI screenshots into: {SCREENSHOTS_DIR}")
    make_login_screen()
    make_register_screen()
    make_dashboard_screen()
    make_prediction_screen()
    make_top3_screen()
    make_prob_chart_screen()
    make_weather_screen()
    make_history_screen()
    make_pdf_report_screen()
    make_admin_screen()
    make_api_docs_screen()
    print("All 11 UI screenshots generated successfully!")
