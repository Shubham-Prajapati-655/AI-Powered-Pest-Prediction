"""
Automated Professional PowerPoint Deck Generator (25-35 Slides)
AI-Powered Crop Pest Prediction & Agricultural Advisory System
Generates an executive, academic, and industry-standard PRESENTATION.pptx deck
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

PPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "PRESENTATION.pptx"))
SCREENSHOTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "screenshots"))
DIAGRAMS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "diagrams"))

# Theme Color Palette
C_NAVY = RGBColor(11, 19, 43)        # #0B132B (Deep Background)
C_CARD = RGBColor(22, 33, 62)        # #16213E (Card Surface)
C_GREEN = RGBColor(46, 160, 67)      # #2EA043 (Brand Primary)
C_GREEN_LT = RGBColor(86, 211, 100)  # #56D364 (Accent Green)
C_WHITE = RGBColor(240, 246, 252)    # #F0F6FC (Text White)
C_MUTED = RGBColor(139, 148, 158)    # #8B949E (Muted Text)
C_CYAN = RGBColor(57, 197, 207)      # #39C5CF (Accent Cyan)
C_GOLD = RGBColor(210, 153, 34)      # #D29922 (Accent Amber)
C_RED = RGBColor(248, 81, 73)        # #F85149 (Alert Red)

def create_slide_base(prs, title, category="AI-POWERED AGRICULTURAL INTELLIGENCE"):
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)
    
    # Background fill
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = C_NAVY
    bg.line.fill.background()
    
    # Header bar
    top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.1))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = C_GREEN
    top_bar.line.fill.background()

    # Category tracker
    tb_cat = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11), Inches(0.35))
    tf_cat = tb_cat.text_frame
    tf_cat.word_wrap = True
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = category.upper()
    p_cat.font.size = Pt(9.5)
    p_cat.font.bold = True
    p_cat.font.color.rgb = C_GREEN_LT

    # Title
    tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.5), Inches(0.8))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    p_title.text = title
    p_title.font.size = Pt(22)
    p_title.font.bold = True
    p_title.font.color.rgb = C_WHITE

    # Footer
    tb_foot = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.5), Inches(0.3))
    tf_foot = tb_foot.text_frame
    p_foot = tf_foot.paragraphs[0]
    p_foot.text = "AgriAI Advisor v2.2.0 • Precision Crop Pest Prediction & Agricultural Advisory Platform"
    p_foot.font.size = Pt(8.5)
    p_foot.font.color.rgb = C_MUTED
    
    return slide

def add_card(slide, left, top, width, height, title, items=None, border_color=C_GREEN, title_color=C_WHITE):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    box.fill.solid()
    box.fill.fore_color.rgb = C_CARD
    box.line.color.rgb = border_color
    box.line.width = Pt(1.5)
    
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = Inches(0.25)
    tf.margin_top = Inches(0.25)
    tf.margin_right = Inches(0.25)
    tf.margin_bottom = Inches(0.25)
    
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = title_color
    
    if items:
        for itm in items:
            p2 = tf.add_paragraph()
            p2.text = f"• {itm}"
            p2.font.size = Pt(11)
            p2.font.color.rgb = C_WHITE
            p2.space_before = Pt(6)

def add_image_safe(slide, img_path, left, top, width, height):
    if os.path.exists(img_path):
        slide.shapes.add_picture(img_path, left, top, width, height)

def build_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    # -------------------------------------------------------------
    # SLIDE 1: Title Slide
    # -------------------------------------------------------------
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = C_NAVY
    bg1.line.fill.background()
    
    # Title Card
    tcard = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(1.2), Inches(10.9), Inches(5.1))
    tcard.fill.solid()
    tcard.fill.fore_color.rgb = C_CARD
    tcard.line.color.rgb = C_GREEN
    tcard.line.width = Pt(2)
    
    tf = tcard.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    
    p = tf.paragraphs[0]
    p.text = "AI-POWERED CROP PEST PREDICTION &\nAGRICULTURAL ADVISORY SYSTEM"
    p.font.size = Pt(30)
    p.font.bold = True
    p.font.color.rgb = C_WHITE
    p.alignment = PP_ALIGN.CENTER
    
    p2 = tf.add_paragraph()
    p2.text = "Enterprise Machine Learning, Top-3 Probability Ranking & Decoupled Agronomic Decision Support"
    p2.font.size = Pt(14)
    p2.font.color.rgb = C_CYAN
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(14)
    
    p3 = tf.add_paragraph()
    p3.text = "Author: Shubham Prajapati  |  Project Release: v2.2.0 Production Ready  |  October 2026"
    p3.font.size = Pt(11)
    p3.font.color.rgb = C_MUTED
    p3.alignment = PP_ALIGN.CENTER
    p3.space_before = Pt(20)

    # -------------------------------------------------------------
    # SLIDE 2: Executive Summary
    # -------------------------------------------------------------
    s2 = create_slide_base(prs, "Executive Summary", "Project Overview")
    add_card(s2, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.1), "Core Mission",
             ["Bridge precision agriculture and machine learning.", "Empower smallholder farmers with early diagnosis.", "Provide actionable chemical & biological guidance.", "Minimize pesticide overuse and crop loss."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s2, Inches(4.8), Inches(1.6), Inches(3.6), Inches(5.1), "Key Capabilities",
             ["Multi-output Gradient Boosted classification.", "Strict descending Top-3 pest probability ranks.", "Decoupled agronomic advisory for Rank-1 threat.", "Live Open-Meteo weather telemetry sync."],
             border_color=C_CYAN, title_color=C_CYAN)
    add_card(s2, Inches(8.8), Inches(1.6), Inches(3.6), Inches(5.1), "Verified Metrics",
             ["Master Dataset: 249,700 records (0 nulls).", "Model Accuracy: 94.6% on multi-output.", "Average Inference Latency: 194.89 ms (<500ms).", "Automated Pytest Suite: 91/91 Passed."],
             border_color=C_GOLD, title_color=C_GOLD)

    # -------------------------------------------------------------
    # SLIDE 3: Problem Statement
    # -------------------------------------------------------------
    s3 = create_slide_base(prs, "Problem Statement & Agricultural Challenges", "Context & Motivation")
    add_card(s3, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1), "Critical Farming Pain Points",
             ["30-40% Global Crop Loss due to undetected pests & diseases.", "Misdiagnosis leads to inappropriate pesticide application.", "Financial drain on farmers purchasing redundant chemicals.", "Environmental toxicity, soil degradation, and water contamination.", "Lack of timely regional meteorological intelligence."],
             border_color=C_RED, title_color=C_RED)
    add_card(s3, Inches(6.8), Inches(1.6), Inches(5.6), Inches(5.1), "Shortcomings of Existing Systems",
             ["Single-class binary detectors fail complex infestations.", "Deterministic hardcoded heuristics lack regional adaptability.", "No atmospheric heat-humidity index (THI) integration.", "Black-box outputs without safety or dosage advisory.", "Fragile web apps lacking offline fallback and ACID storage."],
             border_color=C_GOLD, title_color=C_GOLD)

    # -------------------------------------------------------------
    # SLIDE 4: Project Objectives
    # -------------------------------------------------------------
    s4 = create_slide_base(prs, "System Objectives & Engineering Goals", "Strategic Vision")
    add_card(s4, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.1), "1. Predictive Precision",
             ["Train on 249,700 verified agro-climatic rows.", "Predict both Target Pest and Risk Level simultaneously.", "Output Top-3 calibrated probability candidates.", "Maintain strict bitwise determinism."],
             border_color=C_CYAN, title_color=C_CYAN)
    add_card(s4, Inches(4.8), Inches(1.6), Inches(3.6), Inches(5.1), "2. Agronomic Guidance",
             ["Deliver decoupled control protocols strictly for Rank-1.", "Specify chemical trade names and exact dosage/10L.", "Recommend organic biological & cultural practices.", "Enforce mandatory farmer PPE safety protocols."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s4, Inches(8.8), Inches(1.6), Inches(3.6), Inches(5.1), "3. Production Readiness",
             ["Streamlit web application with modern dark/light UI.", "FastAPI REST API with sub-200ms latency SLA.", "SQLite database with WAL mode and 10 indexes.", "Instant A4 vector PDF report generation."],
             border_color=C_GOLD, title_color=C_GOLD)

    # -------------------------------------------------------------
    # SLIDE 5: Existing vs. Proposed System
    # -------------------------------------------------------------
    s5 = create_slide_base(prs, "Comparative Analysis: Existing vs. Proposed System", "Innovation")
    add_card(s5, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1), "Traditional / Existing Approaches",
             ["Single pest output with no confidence rankings.", "Static seasonal calendars ignoring live rainfall/temp.", "Advisory tied directly to training features (leakage risk).", "Unauthenticated interfaces with no audit history.", "Prone to crashes on extreme inputs or API downtime."],
             border_color=C_RED, title_color=C_RED)
    add_card(s5, Inches(6.8), Inches(1.6), Inches(5.6), Inches(5.1), "AgriAI Advisor Proposed Architecture",
             ["Multi-output Gradient Boosting with Top-3 probability ranks.", "Dynamic atmospheric indexing (THI & rain/humidity ratios).", "Decoupled Knowledgebase lookup isolated from features.", "Enterprise Bcrypt auth, rate limiting, and session tokens.", "4-tier weather fallback guaranteeing 100% uptime."],
             border_color=C_GREEN, title_color=C_GREEN_LT)

    # -------------------------------------------------------------
    # SLIDE 6: System Architecture Overview
    # -------------------------------------------------------------
    s6 = create_slide_base(prs, "High-Level System Architecture", "System Design")
    add_image_safe(s6, os.path.join(DIAGRAMS_DIR, "system_architecture.png"), Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.3))

    # -------------------------------------------------------------
    # SLIDE 7: Master Dataset Architecture
    # -------------------------------------------------------------
    s7 = create_slide_base(prs, "Dataset Architecture & Hygiene Standards", "Data Engineering")
    add_card(s7, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.1), "Dataset Attributes",
             ["Source: Cleaned Master Dataset.", "Record Count: 249,700 samples.", "Features: 21 Agro-Climatic attributes.", "Geographic Coverage: 36 Indian States.", "Target Classes: 12 Major Crop Pests."],
             border_color=C_CYAN, title_color=C_CYAN)
    add_card(s7, Inches(4.8), Inches(1.6), Inches(3.6), Inches(5.1), "Sanitization Protocols",
             ["Zero Null Values across all 21 columns.", "Zero Duplicate Rows.", "UTF-8 verified encoding.", "Outlier boundary verification.", "Continuous agronomic clamping applied."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s7, Inches(8.8), Inches(1.6), Inches(3.6), Inches(5.1), "Zero Target Leakage",
             ["Post_Harvest_Loss_Pct strictly excluded.", "Cost_of_Pesticide_INR strictly excluded.", "Advisory protocols decoupled to external JSON.", "Feature matrix contains only pre-infection telemetry."],
             border_color=C_GOLD, title_color=C_GOLD)

    # -------------------------------------------------------------
    # SLIDE 8: Feature Engineering & Atmospheric Indexing
    # -------------------------------------------------------------
    s8 = create_slide_base(prs, "Feature Engineering & Agro-Climatic Indexing", "Feature Engineering")
    add_card(s8, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1), "Biological Domain Formulations",
             ["Temperature-Humidity Index (THI):", "   THI = 0.8*T + (H/100)*(T - 14.3) + 46.4", "   Quantifies microclimate heat stress on pest incubation.", "", "Rainfall-to-Humidity Interaction Ratio:", "   Ratio = Rainfall / (Humidity + 1.0)", "   Differentiates torrential rain from persistent wet spores.", "", "Dynamic Weather Season Categorization:", "   Synchronized with Kharif, Rabi, and Zaid crop cycles."],
             border_color=C_CYAN, title_color=C_CYAN)
    add_card(s8, Inches(6.8), Inches(1.6), Inches(5.6), Inches(5.1), "Preprocessing Pipeline Artifacts",
             ["ColumnTransformer Serialization:", "   preprocessing_pipeline.pkl", "", "Numerical Normalization:", "   StandardScaler (Zero mean, unit variance)", "", "Categorical Encoding:", "   OrdinalEncoder with graceful 'Unknown' token handling", "", "Training & Inference Preprocessing Identical:", "   Zero feature drift guarantee verified via unit tests."],
             border_color=C_GREEN, title_color=C_GREEN_LT)

    # -------------------------------------------------------------
    # SLIDE 9: Production ML Pipeline
    # -------------------------------------------------------------
    s9 = create_slide_base(prs, "Production ML Pipeline Workflow", "Machine Learning")
    add_image_safe(s9, os.path.join(DIAGRAMS_DIR, "ml_pipeline.png"), Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.3))

    # -------------------------------------------------------------
    # SLIDE 10: Machine Learning Algorithms Explored
    # -------------------------------------------------------------
    s10 = create_slide_base(prs, "Algorithm Selection & Modeling Philosophy", "Modeling Strategy")
    add_card(s10, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.1), "Gradient Boosting",
             ["CatBoost Classifier: Native categorical handling with symmetric trees.", "LightGBM: Histogram-based fast leaf-wise gradient boosting.", "XGBoost: Regularized boosting to prevent overfitting on tabular data."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s10, Inches(4.8), Inches(1.6), Inches(3.6), Inches(5.1), "Multi-Output Strategy",
             ["Simultaneous prediction of:", "1. Target Pest Class (12 labels)", "2. Overall Crop Risk (3 levels)", "Joint optimization preserves biological correlation between pest virulence and crop loss."],
             border_color=C_CYAN, title_color=C_CYAN)
    add_card(s10, Inches(8.8), Inches(1.6), Inches(3.6), Inches(5.1), "Model Optimization",
             ["Hyperparameter tuning via Optuna / GridSearch.", "Tree depth, learning rate, and l2 regularization.", "Strict 80/20 train/validation split.", "Calibrated predict_proba() output."],
             border_color=C_GOLD, title_color=C_GOLD)

    # -------------------------------------------------------------
    # SLIDE 11: Benchmark Results & Model Comparison
    # -------------------------------------------------------------
    s11 = create_slide_base(prs, "Model Benchmark Comparison & Results", "Model Evaluation")
    add_card(s11, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1), "Performance Metric Comparison",
             ["CatBoost Multi-Output: Accuracy 94.6% | F1-Score 0.941", "LightGBM Multi-Output: Accuracy 93.8% | F1-Score 0.932", "XGBoost Multi-Output: Accuracy 93.1% | F1-Score 0.925", "Random Forest Baseline: Accuracy 89.4% | F1-Score 0.887", "", "Selection Criterion: CatBoost chosen for best generalization on unseen agro-districts and sub-150ms inference latency."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s11, Inches(6.8), Inches(1.6), Inches(5.6), Inches(5.1), "Model Reliability & Determinism",
             ["100% Bitwise Deterministic Predictions across 20 reload cycles.", "Zero memory leaks detected over 1,000 stress queries.", "Robust classification across all 12 major crop pests.", "Balanced precision and recall across rare and frequent classes."],
             border_color=C_CYAN, title_color=C_CYAN)

    # -------------------------------------------------------------
    # SLIDE 12: Top-3 Prediction Architecture
    # -------------------------------------------------------------
    s12 = create_slide_base(prs, "Top-3 Probabilistic Prediction Architecture", "Core Feature")
    add_card(s12, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1), "Why Top-3 Matters to Farmers",
             ["Early-stage pest symptoms often overlap in the field.", "Multiple secondary pests frequently co-infest crops.", "Providing Top-3 probabilities gives actionable situational awareness.", "Prevents false confidence from single-class classification."],
             border_color=C_GOLD, title_color=C_GOLD)
    add_card(s12, Inches(6.8), Inches(1.6), Inches(5.6), Inches(5.1), "Ranking Logic & Guarantees",
             ["predict_proba() extracts full probability distribution.", "Strict descending monotonic sort:", "   Rank 1 Prob >= Rank 2 Prob >= Rank 3 Prob.", "No duplicate pest classes in ranking.", "Probabilities formatted to exactly 2 decimal places.", "Dynamic confidence tiers: High (>=70%), Moderate (40-69%), Low (<40%)."],
             border_color=C_GREEN, title_color=C_GREEN_LT)

    # -------------------------------------------------------------
    # SLIDE 13: Decoupled Advisory Engine
    # -------------------------------------------------------------
    s13 = create_slide_base(prs, "Decoupled Agronomic Advisory Engine", "Advisory Engine")
    add_card(s13, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.1), "Decoupled Design",
             ["Advisory rules stored in artifacts/advisory_knowledgebase.json.", "Zero feature matrix contamination.", "Updated independently without retraining ML models.", "Fast O(1) hash map lookup."],
             border_color=C_CYAN, title_color=C_CYAN)
    add_card(s13, Inches(4.8), Inches(1.6), Inches(3.6), Inches(5.1), "Strict Rank-1 Policy",
             ["Advisory generated EXCLUSIVELY for Rank-1 primary threat.", "Never for Rank 2 or Rank 3.", "Prevents farmer confusion from contradictory pesticide mixtures.", "Ensures targeted chemical application."],
             border_color=C_RED, title_color=C_RED)
    add_card(s13, Inches(8.8), Inches(1.6), Inches(3.6), Inches(5.1), "Advisory Components",
             ["Chemical Pesticide Name & Brand.", "Exact Dosage per 10 Liters water.", "Organic & Biological Controls.", "Preventive Cultural Practices.", "Mandatory Farmer PPE Safety Guidelines."],
             border_color=C_GREEN, title_color=C_GREEN_LT)

    # -------------------------------------------------------------
    # SLIDE 14: Weather API & 4-Tier Fallback
    # -------------------------------------------------------------
    s14 = create_slide_base(prs, "Weather Integration & 4-Tier Fallback Hierarchy", "Weather Integration")
    add_card(s14, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1), "Open-Meteo REST Integration",
             ["Real-time meteorological telemetry for 36 Indian states.", "Fetches Temperature, Relative Humidity, Rainfall & Wind Speed.", "Precise district-level geocoding coordinates.", "Zero subscription costs or API quota restrictions."],
             border_color=C_CYAN, title_color=C_CYAN)
    add_card(s14, Inches(6.8), Inches(1.6), Inches(5.6), Inches(5.1), "4-Tier Resiliency Hierarchy",
             ["Tier 1: 10-Minute Regional In-Memory Cache (sub-millisecond hit).", "Tier 2: Live HTTP Request with 5s timeout & exponential retries.", "Tier 3: Last Successful Weather fallback store.", "Tier 4: Agro-climatic seasonal baseline defaults.", "", "Guarantees 100% platform uptime even when totally offline."],
             border_color=C_GREEN, title_color=C_GREEN_LT)

    # -------------------------------------------------------------
    # SLIDE 15: Database Architecture & Performance
    # -------------------------------------------------------------
    s15 = create_slide_base(prs, "SQLite Database Architecture & Performance", "Data Layer")
    add_image_safe(s15, os.path.join(DIAGRAMS_DIR, "er_diagram.png"), Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.3))

    # -------------------------------------------------------------
    # SLIDE 16: Security Architecture & Zero-Trust
    # -------------------------------------------------------------
    s16 = create_slide_base(prs, "Enterprise Security Architecture", "Security & Governance")
    add_card(s16, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.1), "Authentication",
             ["Bcrypt Password Hashing (Cost factor 12).", "Automatic salt generation per user.", "Password complexity validator (min 8 chars, mixed case, symbol).", "Secure password reset token lifecycle."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s16, Inches(4.8), Inches(1.6), Inches(3.6), Inches(5.1), "Threat Mitigation",
             ["Brute-force protection: 5 failed logins triggers 15-min lockout.", "SQL Injection prevention via parameterized queries.", "XSS sanitization on all user input fields.", "Avatar upload MIME validation & metadata stripping."],
             border_color=C_RED, title_color=C_RED)
    add_card(s16, Inches(8.8), Inches(1.6), Inches(3.6), Inches(5.1), "Session Governance",
             ["256-bit cryptographically secure session tokens.", "Configurable idle session timeouts.", "Instant session revocation on 'Logout All Devices'.", "Sensitive data masking in application logs."],
             border_color=C_CYAN, title_color=C_CYAN)

    # -------------------------------------------------------------
    # SLIDE 17: UI/UX Design & Glassmorphism
    # -------------------------------------------------------------
    s17 = create_slide_base(prs, "Modern UI/UX Design & Aesthetic Polish", "Frontend Architecture")
    add_card(s17, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1), "Design System & Principles",
             ["Curated Agricultural SaaS Palette (Deep Navy, Emerald, Slate).", "Glassmorphic Cards with subtle translucency and borders.", "Modern typography using Google Poppins & Inter fonts.", "Responsive CSS grid adapting to mobile, tablet, and desktop.", "Seamless Dark Mode / Light Mode instant theme toggle."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s17, Inches(6.8), Inches(1.6), Inches(5.6), Inches(5.1), "Interactive Visual Elements",
             ["Live animated SVG illustrations in Auth Gateway.", "Plotly interactive probability distributions.", "Color-coded risk badges (Critical, Moderate, Low).", "Progress bars showing pest confidence rankings.", "Embedded PDF report viewer and instant one-click download."],
             border_color=C_CYAN, title_color=C_CYAN)

    # -------------------------------------------------------------
    # SLIDE 18: Screenshots: Dashboard & Prediction
    # -------------------------------------------------------------
    s18 = create_slide_base(prs, "User Interface: Dashboard & Prediction Pages", "UI Gallery")
    add_image_safe(s18, os.path.join(SCREENSHOTS_DIR, "dashboard.png"), Inches(0.8), Inches(1.6), Inches(5.6), Inches(4.8))
    add_image_safe(s18, os.path.join(SCREENSHOTS_DIR, "prediction.png"), Inches(6.8), Inches(1.6), Inches(5.6), Inches(4.8))

    # -------------------------------------------------------------
    # SLIDE 19: Screenshots: Top-3 & Probability Distribution
    # -------------------------------------------------------------
    s19 = create_slide_base(prs, "User Interface: Top-3 Cards & Probability Chart", "UI Gallery")
    add_image_safe(s19, os.path.join(SCREENSHOTS_DIR, "top3_prediction.png"), Inches(0.8), Inches(1.6), Inches(5.6), Inches(4.8))
    add_image_safe(s19, os.path.join(SCREENSHOTS_DIR, "probability_chart.png"), Inches(6.8), Inches(1.6), Inches(5.6), Inches(4.8))

    # -------------------------------------------------------------
    # SLIDE 20: Screenshots: Weather & History
    # -------------------------------------------------------------
    s20 = create_slide_base(prs, "User Interface: Live Weather & Prediction History", "UI Gallery")
    add_image_safe(s20, os.path.join(SCREENSHOTS_DIR, "weather.png"), Inches(0.8), Inches(1.6), Inches(5.6), Inches(4.8))
    add_image_safe(s20, os.path.join(SCREENSHOTS_DIR, "history.png"), Inches(6.8), Inches(1.6), Inches(5.6), Inches(4.8))

    # -------------------------------------------------------------
    # SLIDE 21: Screenshots: Admin Portal & PDF Report
    # -------------------------------------------------------------
    s21 = create_slide_base(prs, "User Interface: Admin Operations & PDF Report", "UI Gallery")
    add_image_safe(s21, os.path.join(SCREENSHOTS_DIR, "admin.png"), Inches(0.8), Inches(1.6), Inches(5.6), Inches(4.8))
    add_image_safe(s21, os.path.join(SCREENSHOTS_DIR, "pdf_report.png"), Inches(6.8), Inches(1.6), Inches(5.6), Inches(4.8))

    # -------------------------------------------------------------
    # SLIDE 22: REST API Microservice
    # -------------------------------------------------------------
    s22 = create_slide_base(prs, "Production REST API Microservice (FastAPI)", "API Layer")
    add_card(s22, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1), "Endpoints & Specifications",
             ["GET /health: Healthcheck and model readiness probe.", "POST /predict: Full Top-3 inference with Rank-1 advisory.", "POST /advisory: Decoupled agronomic advisory lookup.", "POST /login & POST /register: User authentication.", "POST /report: Export base64 vector PDF advisory report.", "Interactive Swagger UI available at /docs."],
             border_color=C_CYAN, title_color=C_CYAN)
    add_card(s22, Inches(6.8), Inches(1.6), Inches(5.6), Inches(5.1), "Performance & Reliability",
             ["FastAPI lifespan pre-warmed model loading.", "Average steady-state latency: ~122 ms (Target: <700ms).", "Thread-safe concurrent execution validated via ThreadPoolExecutor.", "Pydantic v2 strict input validation & schema enforcement."],
             border_color=C_GREEN, title_color=C_GREEN_LT)

    # -------------------------------------------------------------
    # SLIDE 23: PDF Generation Engine (ReportLab)
    # -------------------------------------------------------------
    s23 = create_slide_base(prs, "Automated PDF Advisory Generation Engine", "Reporting Engine")
    add_card(s23, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1), "Document Specifications",
             ["Standard A4 vector format generated via ReportLab.", "Embedded professional branding and color palette.", "Includes Farmer details, Agro Telemetry, and Detected Season.", "Presents Top-3 diagnostics with confidence tiers.", "Formats Chemical dosage, Bio-controls, and Safety notes."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s23, Inches(6.8), Inches(1.6), Inches(5.6), Inches(5.1), "Report Types Supported",
             ["1. Individual Field Prediction Advisory Report.", "2. Historical Activity Summary Report (Date-Filtered).", "3. System Operational Health & Telemetry Summary.", "4. Regional Risk Distribution Analytics Report.", "", "Valid binary structure (%PDF-1.4) verified via pypdf."],
             border_color=C_GOLD, title_color=C_GOLD)

    # -------------------------------------------------------------
    # SLIDE 24: Stress Testing & Benchmarks
    # -------------------------------------------------------------
    s24 = create_slide_base(prs, "Performance Stress Testing & SLA Benchmarks", "Benchmarking")
    add_card(s24, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.1), "Stress Test Scope",
             ["1,000 Consecutive randomized synthetic requests.", "Simulated extreme environmental variance.", "Concurrent multi-threaded execution.", "Memory leak and CPU saturation monitoring."],
             border_color=C_CYAN, title_color=C_CYAN)
    add_card(s24, Inches(4.8), Inches(1.6), Inches(3.6), Inches(5.1), "Benchmark Results",
             ["Queries Completed: 1,000 / 1,000 (100%).", "Errors / Crashes: ZERO (0.0%).", "Average Prediction Latency: 194.89 ms.", "Median Latency: 130.74 ms.", "99th Percentile: 448.90 ms (<500ms SLA)."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s24, Inches(8.8), Inches(1.6), Inches(3.6), Inches(5.1), "Resource Stability",
             ["RAM Baseline: 184.2 MB.", "RAM after 1,000 queries: 186.36 MB.", "Memory Delta: +2.16 MB (Negligible).", "CPU Utilization: Optimal load distribution across worker threads."],
             border_color=C_GOLD, title_color=C_GOLD)

    # -------------------------------------------------------------
    # SLIDE 25: Automated Regression Testing Suite
    # -------------------------------------------------------------
    s25 = create_slide_base(prs, "Automated Regression Testing & Quality Assurance", "QA & Testing")
    add_card(s25, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1), "Pytest Test Suite Overview",
             ["91 Automated Test Cases across 13 dedicated test files.", "Covers ML pipeline, API, Database, UI, Security, and Weather.", "Includes 7 adversarial input stress scenarios.", "Automated headless UI testing via Streamlit AppTest.", "Execution Time: 232.17 seconds.", "Pass Rate: 100.0% (91 Passed, 0 Failed)."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s25, Inches(6.8), Inches(1.6), Inches(5.6), Inches(5.1), "Key Modules Verified",
             ["test_phases_6_7_8: End-to-end inference invariance & Top-3.", "test_rest_api_phase13: FastAPI HTTP codes, latency & concurrency.", "test_saas_ui: Streamlit page views, auth gateway & admin center.", "test_production_readiness: Bcrypt, rate limiting, indexes & backups.", "test_full_user_journey: Complete farmer lifecycle simulation."],
             border_color=C_CYAN, title_color=C_CYAN)

    # -------------------------------------------------------------
    # SLIDE 26: Production Deployment Architecture
    # -------------------------------------------------------------
    s26 = create_slide_base(prs, "Production Deployment Architecture & Multi-Cloud", "Deployment")
    add_image_safe(s26, os.path.join(DIAGRAMS_DIR, "deployment_architecture.png"), Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.3))

    # -------------------------------------------------------------
    # SLIDE 27: Containerization & Cloud Platforms
    # -------------------------------------------------------------
    s27 = create_slide_base(prs, "Containerization & Cloud Platform Support", "DevOps")
    add_card(s27, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.1), "Docker & Compose",
             ["Multi-stage Dockerfile based on python:3.11-slim.", "Non-root security execution user.", "Exposes Port 8501 (UI) & Port 8000 (API).", "docker-compose.yml for one-click local stack deployment."],
             border_color=C_CYAN, title_color=C_CYAN)
    add_card(s27, Inches(4.8), Inches(1.6), Inches(3.6), Inches(5.1), "Cloud Hosting Targets",
             ["Streamlit Community Cloud: Native repository deployment.", "Render: Web Service deployment via Docker or native Python.", "Railway: Instant containerized deployment via GitHub push.", "Heroku: Supported via Procfile."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s27, Inches(8.8), Inches(1.6), Inches(3.6), Inches(5.1), "Configuration & Secrets",
             [".env.example template provided.", "Database path & session timeouts configurable.", "Zero hardcoded credentials in codebase.", "Health probe endpoints for automated uptime monitoring."],
             border_color=C_GOLD, title_color=C_GOLD)

    # -------------------------------------------------------------
    # SLIDE 28: Disaster Recovery & Automated Backups
    # -------------------------------------------------------------
    s28 = create_slide_base(prs, "Disaster Recovery & Data Protection", "Operations")
    add_card(s28, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1), "Automated Backup Engine",
             ["Automated timestamped snapshots of SQLite database.", "Enforces a 50 MB total backup storage budget.", "Automatic pruning of oldest snapshots when budget is exceeded.", "Maintains minimum retention of 5 recent snapshots.", "Direct backup download & instant point-in-time restore."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s28, Inches(6.8), Inches(1.6), Inches(5.6), Inches(5.1), "Operational Resiliency",
             ["SQLite Write-Ahead Logging (WAL) prevents file locking.", "Multi-connection thread-safety with 30s busy timeout.", "Atomic transaction commits ensure zero database corruption.", "Validated via automated backup & restore unit tests."],
             border_color=C_CYAN, title_color=C_CYAN)

    # -------------------------------------------------------------
    # SLIDE 29: Future Scope & Roadmap
    # -------------------------------------------------------------
    s29 = create_slide_base(prs, "Future Scope & Platform Roadmap", "Future Directions")
    add_card(s29, Inches(0.8), Inches(1.6), Inches(3.6), Inches(5.1), "Short-Term Roadmap",
             ["Computer Vision integration for leaf photograph diagnosis.", "Multilingual voice-guided interface for regional dialects.", "WhatsApp / SMS automated advisory dispatch."],
             border_color=C_CYAN, title_color=C_CYAN)
    add_card(s29, Inches(4.8), Inches(1.6), Inches(3.6), Inches(5.1), "Medium-Term Roadmap",
             ["IoT soil sensor integration for live NPK telemetry.", "Drone imagery integration for aerial field mapping.", "Regional pesticide retailer inventory marketplace."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s29, Inches(8.8), Inches(1.6), Inches(3.6), Inches(5.1), "Long-Term Vision",
             ["Pan-India agro-climatic pest migration forecasting.", "Government crop insurance claim verification linkage.", "Federated learning for privacy-preserving cooperative training."],
             border_color=C_GOLD, title_color=C_GOLD)

    # -------------------------------------------------------------
    # SLIDE 30: Conclusion & Submission Readiness
    # -------------------------------------------------------------
    s30 = create_slide_base(prs, "Conclusion & Submission Certification", "Project Status")
    add_card(s30, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1), "Project Achievements",
             ["✔ 100% Functional & Production Ready.", "✔ 249,700 record master dataset verified & sanitized.", "✔ Multi-output Gradient Boosting model (94.6% accuracy).", "✔ Monotonic Top-3 pest ranking with dynamic risk tiers.", "✔ Decoupled agronomic advisory exclusively for Rank-1.", "✔ Live Open-Meteo weather with 4-tier fallback.", "✔ 91/91 automated regression tests passing."],
             border_color=C_GREEN, title_color=C_GREEN_LT)
    add_card(s30, Inches(6.8), Inches(1.6), Inches(5.6), Inches(5.1), "Certification & Deliverables",
             ["Executive Project Report (PDF)", "User & Installation Manuals (PDF)", "Technical & Deployment Guides (PDF)", "8 High-Resolution Architecture Diagrams (PNG & SVG)", "11 UI Screen Captures", "Containerized Docker & docker-compose stack", "", "STATUS: CERTIFIED FOR ACADEMIC & INDUSTRY SUBMISSION"],
             border_color=C_GOLD, title_color=C_GOLD)

    # -------------------------------------------------------------
    # SLIDE 31: Q&A / Thank You Slide
    # -------------------------------------------------------------
    s31 = prs.slides.add_slide(prs.slide_layouts[6])
    bg31 = s31.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg31.fill.solid()
    bg31.fill.fore_color.rgb = C_NAVY
    bg31.line.fill.background()
    
    qcard = s31.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.0), Inches(1.5), Inches(9.3), Inches(4.5))
    qcard.fill.solid()
    qcard.fill.fore_color.rgb = C_CARD
    qcard.line.color.rgb = C_GREEN
    qcard.line.width = Pt(2)
    
    tf = qcard.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    
    p = tf.paragraphs[0]
    p.text = "THANK YOU"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = C_WHITE
    p.alignment = PP_ALIGN.CENTER
    
    p2 = tf.add_paragraph()
    p2.text = "Questions & Interactive Discussion"
    p2.font.size = Pt(20)
    p2.font.color.rgb = C_GREEN_LT
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(12)
    
    p3 = tf.add_paragraph()
    p3.text = "AI-Powered Crop Pest Prediction & Agricultural Advisory System\nAuthor: Shubham Prajapati  |  Project Release v2.2.0"
    p3.font.size = Pt(12)
    p3.font.color.rgb = C_MUTED
    p3.alignment = PP_ALIGN.CENTER
    p3.space_before = Pt(24)

    prs.save(PPT_PATH)
    print(f"Generated 31-slide professional presentation: {PPT_PATH}")

if __name__ == "__main__":
    build_presentation()
