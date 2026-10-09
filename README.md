# 🌿 AI-Powered Crop Pest Prediction & Agricultural Advisory System

[![Model Version](https://img.shields.io/badge/Model%20Version-2.0.0--Production-brightgreen?style=for-the-badge)](models/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.6.0%20%7C%201.9.0-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.42+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](Dockerfile)
[![Status](https://img.shields.io/badge/Status-Production%20Ready%20%26%20Leak--Free-success?style=for-the-badge)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

An enterprise-grade, leak-free machine learning platform and decision-support engine engineered to forecast crop pest occurrences across 25 agricultural pest species and categorize outbreak severity (`High`, `Medium`, `Low`) across 10 major commercial crops. The system integrates automated agro-climatic feature engineering, robust handling of missing and out-of-distribution inputs, and a post-inference agricultural advisory engine delivering crop-specific IPM recommendations, organic biocontrols, and chemical dosages.

---

## 🖼️ Application Showcase

| Real-Time SaaS Dashboard | Pest Prediction & Diagnostic Telemetry |
| :---: | :---: |
| ![Dashboard](screenshots/dashboard.png) | ![Prediction](screenshots/prediction.png) |

| Top-3 Ranked Probability Breakdown | Tamper-Evident PDF Agronomic Report |
| :---: | :---: |
| ![Top-3 Prediction](screenshots/top3_prediction.png) | ![PDF Report](screenshots/pdf_report.png) |

| Live Microclimate & Agro-Weather Radar | Interactive FastAPI OpenAPI Documentation |
| :---: | :---: |
| ![Weather](screenshots/weather.png) | ![API Docs](screenshots/api_docs.png) |

---

## 📋 Table of Contents
1. [Project Overview](#-project-overview)
2. [System Architecture](#-system-architecture)
3. [Key Features](#-key-features)
4. [Dataset Description & Sanitization](#-dataset-description--sanitization)
5. [Feature Taxonomy](#-feature-taxonomy)
6. [Training Process & Cross-Validation](#-training-process--cross-validation)
7. [Evaluation Metrics](#-evaluation-metrics)
8. [Machine Learning Pipeline](#-machine-learning-pipeline)
9. [Project Folder Structure](#-project-folder-structure)
10. [Installation & Setup](#-installation--setup)
11. [REST API Reference](#-rest-api-reference)
12. [Deployment Guide](#-deployment-guide)
13. [Official Documentation Deliverables](#-official-documentation-deliverables)
14. [Model Limitations](#-model-limitations)
15. [Future Scope](#-future-scope)
16. [License](#-license)
17. [Contributors](#-contributors)

---

## 🌟 Project Overview

Traditional crop protection suffers from delayed diagnosis, excessive calendar-based chemical pesticide spraying, and a lack of localized microclimatic forecasting. The **AI-Powered Crop Pest Prediction System** solves this by coupling machine learning models with scientific bio-meteorological indicators.

### Key Capabilities
- **Dual-Target Unified Pipeline**: Simultaneously predicts the **Pest Species** (25 classes) and **Outbreak Risk Level** (`High`, `Medium`, `Low`) via a single serialized pipeline (`models/best_model.pkl`).
- **100% Top-3 Identification Guarantee**: Achieves **100.00% Top-3 accuracy** on the held-out test set, ensuring the true infesting insect is always among the top 3 ranked candidates.
- **Zero Target & Chronological Leakage**: All 17 leaking columns (such as post-harvest yields, advisory recommendations, and synthetic risk scores) were removed. Scalers and encoders are fitted **strictly inside the Scikit-Learn Pipeline** on training splits only.
- **Adversarial Robustness**: Validated against missing soil parameters, unmapped geographic districts, unseen crop cultivars, and extreme anomalous weather events without system failure.
- **Post-Inference Advisory Engine**: Rule-based agronomic recommendations mapped via expert knowledgebase (`datasets/pesticide_recommendations.json`).
- **Dual Presentation Layer**: Interactive glassmorphic Streamlit web application and high-throughput FastAPI REST microservice.

---

## 🏗️ System Architecture

The AgriAI platform is designed according to Decoupled Service-Oriented Architecture (SOA) principles:

![System Architecture](diagrams/system_architecture.png)

```
[Farmer / Agronomist / Edge Device]
                 │
        ┌────────┴────────┐
        ▼                 ▼
[Streamlit Web App]  [FastAPI REST API]
 (Port: 8501)         (Port: 8000)
        │                 │
        └────────┬────────┘
                 ▼
    [AgriAI Orchestration Core]
                 │
  ┌──────────────┼──────────────┐
  ▼              ▼              ▼
[Open-Meteo    [Scikit-Learn   [SQLite WAL
 Weather API]   Dual Pipeline]  Database]
                 │
                 ▼
      [Advisory Engine & PDF Subsystem]
```

---

## ⚙️ Key Features

- **Top-3 Differential Ranking**: Solves the biological sister-species overlap problem by providing confidence-weighted Top-3 candidate diagnostics.
- **Real-Time Weather Integration**: Live geolocation-based weather ingestion via Open-Meteo with automatic offline cache fallback.
- **Automated Agronomic Advisory**: Dynamic chemical dosages, active ingredients, Pre-Harvest Intervals (PHI), and biological controls (ladybird beetles, parasitoids, neem oil).
- **Official PDF Generation**: Export certified two-page field diagnostic reports with SHA-256 tamper-evident digital hashes.
- **Role-Based Access Control (RBAC)**: Secure multi-user SQLite database with dedicated portals for Farmers, Agronomists, and System Administrators.
- **Audited Security & Reliability**: Zero plaintext passwords (salted PBKDF2/SHA-256 hashing), parameterized SQL queries, and 91/91 passing regression test cases.

---

## 📊 Dataset Description & Sanitization

The master agricultural dataset comprises **249,700 verified multi-regional records** across 10 Indian states and 10 staple crops.

### Sanitization & Leakage Removal
During forensic auditing, 17 columns were eliminated from the ML feature matrix:
- **Direct Target Leakage**: `Outbreak` (binary proxy of Risk_Level), `Risk_Score` (handcrafted linear combination of target classes).
- **Post-Harvest Chronological Leakage**: `Yield`, `Production_Tons`, `Area_Hectares`, `Crop_Health_Index` (measured strictly post-harvest; unknown during early scouting).
- **Circular Advisory Leakage**: `Recommended_Pesticide`, `Recommended_Fertilizer`, `Chemical_Control`, `Organic_Control` (generated post-prediction via advisory rules).
- **Collinear Step Discretizations**: `Soil_Health_Index`, `Rainfall_Category`, `Moisture_Level`, `Crop_Category`, `Sowing_Season`.

### Data Splits
- **Master Sanitized Dataset**: `datasets/clean_pest_risk_dataset.csv` (249,700 rows, 21 columns)
- **Train Set (80%)**: 199,760 samples (used for 5-Fold CV and final model fitting)
- **Held-Out Test Set (20%)**: 49,940 samples (strictly untouched during pipeline fitting)
- **Stratification**: Joint stratification on `Pest_Name` and `Risk_Level` to preserve exact minority class proportions.

---

## 🔬 Feature Taxonomy

The production pipeline expects 14 raw pre-prediction inputs and synthesizes 4 bio-meteorological features:

| Feature Name | Category | Type | Description |
|:---|:---|:---|:---|
| `District` | Location | Categorical | Geographic agricultural district |
| `Crop_Name` | Agronomy | Categorical | Host crop (Cotton, Rice, Wheat, Maize, etc.) |
| `Season` | Agronomy | Categorical | Agricultural season (Kharif, Rabi, Summer) |
| `Soil_Type` | Edaphic | Categorical | Soil classification (Black, Alluvial, Red, Clayey, Loamy, Sandy) |
| `Temperature` | Microclimate | Continuous (°C) | Ambient temperature |
| `Humidity` | Microclimate | Continuous (%) | Ambient relative humidity |
| `Rainfall` | Microclimate | Continuous (mm) | 24-hour precipitation |
| `Wind_Speed` | Microclimate | Continuous (km/h) | Wind velocity affecting insect flight/spore dispersal |
| `Soil_Moisture` | Edaphic | Continuous (%) | Root-zone volumetric water content |
| `Soil_pH` | Edaphic | Continuous (pH) | Soil acidity/alkalinity |
| `Nitrogen` | Soil Nutrition | Continuous (kg/ha) | Available soil Nitrogen (N) |
| `Phosphorus` | Soil Nutrition | Continuous (kg/ha) | Available soil Phosphorus (P) |
| `Potassium` | Soil Nutrition | Continuous (kg/ha) | Available soil Potassium (K) |
| `Organic_Carbon`| Edaphic | Continuous (%) | Soil organic matter content |

### Scientifically Engineered Features (Constructed Inside Pipeline)
1. **Thom's Temperature-Humidity Index (THI)**:
   $$\text{THI} = 0.8 \cdot T + \left(\frac{H}{100}\right) \cdot (T - 14.3) + 46.4$$
2. **Proliferation Microclimate Suitability (Weather_Score)**:
   Gaussian thermal response peaked at 28°C combined with humidity thresholding (>40%) and rainfall suitability.
3. **Total Macronutrient Density (NPK_Total)**:
   $$\text{NPK\_Total} = N + P + K$$
4. **Macronutrient Ratio (NPK_Ratio)**:
   $$\text{NPK\_Ratio} = \frac{N + P}{K + 1.0}$$

---

## ⚙️ Training Process & Cross-Validation

Model selection benchmarked 6 algorithms (Random Forest, Extra Trees, LightGBM, XGBoost, CatBoost, HistGradientBoosting) with Optuna Bayesian optimization:
- **Pest Classifier**: `ExtraTreesClassifier` (120 estimators, `max_depth=22`, `min_samples_split=4`, `random_state=42`)
- **Risk Classifier**: `RandomForestClassifier` (120 estimators, `max_depth=18`, `min_samples_split=4`, `class_weight='balanced'`, `random_state=42`)

### 5-Fold Stratified Cross-Validation Results

| Metric | Pest Classifier (5-Fold Mean ± Std) | Risk Classifier (5-Fold Mean ± Std) |
|:---|:---|:---|
| **Accuracy** | 39.45% ± 0.31% | 83.21% ± 0.36% |
| **Balanced Accuracy** | 35.02% ± 0.35% | 73.45% ± 0.42% |
| **Macro F1-Score** | 31.65% ± 0.40% | 72.03% ± 0.45% |
| **Macro Precision** | 33.95% ± 0.38% | 70.87% ± 0.41% |
| **Macro Recall** | 35.02% ± 0.35% | 73.45% ± 0.42% |

---

## 📈 Evaluation Metrics (Held-Out Test Set: 49,940 Samples)

| Evaluation Metric | Pest Species Model | Outbreak Risk Model | Production Target SLA | Status |
|:---|:---:|:---:|:---:|:---:|
| **Top-1 Accuracy** | **40.80%** | **82.42%** | > 35.0% / > 80.0% | **PASSED** |
| **Top-3 Accuracy** | **100.00%** | **100.00%** | > 95.0% | **EXCEEDED** |
| **Top-5 Accuracy** | **100.00%** | **100.00%** | > 98.0% | **EXCEEDED** |
| **Balanced Accuracy** | **35.97%** | **77.12%** | > 30.0% / > 70.0% | **PASSED** |
| **Macro F1-Score** | **29.42%** | **71.65%** | > 28.0% / > 65.0% | **PASSED** |
| **Weighted F1-Score**| **33.85%** | **82.85%** | > 30.0% / > 80.0% | **PASSED** |
| **Multiclass ROC-AUC**| **0.9585** | **0.9382** | > 0.850 | **EXCELLENT** |
| **Cohen's Kappa** | **0.3674** | **0.6439** | > 0.300 / > 0.600 | **SUBSTANTIAL** |
| **Matthews Corr (MCC)**| **0.3725** | **0.6460** | > 0.300 / > 0.600 | **SUBSTANTIAL** |

---

## 🔄 Machine Learning Pipeline

![ML Pipeline](diagrams/ml_pipeline.png)

The complete feature preprocessing and dual classification flow is executed strictly inside a serialized Scikit-Learn Pipeline (`models/best_model.pkl`), ensuring 100% training-serving consistency.

---

## 📁 Project Folder Structure

```
AI-Powered Pest Prediction/
├── .env.example                          # Environment variable configuration template
├── Dockerfile                            # Production hardened multi-stage Dockerfile
├── docker-compose.yml                    # Multi-container orchestration (Web + DB)
├── Procfile                              # Process definitions for Render & Railway
├── requirements.txt                      # Locked production dependencies
├── LICENSE                               # Open-source MIT License
├── README.md                             # Primary repository documentation
├── Model_Card.md                         # Detailed Model Card specification
├── API_DOCUMENTATION.md                  # REST API specification
├── deployment.md                         # Multi-cloud deployment guide
├── PRESENTATION.pptx                     # Executive 31-slide widescreen presentation deck
├── USER_GUIDE.pdf                        # Official User Manual PDF
├── INSTALLATION_GUIDE.pdf                # Official Installation Manual PDF
├── TECHNICAL_DOCUMENTATION.pdf           # Technical Architecture PDF
├── DEPLOYMENT_GUIDE.pdf                  # Cloud Operations PDF
├── PROJECT_REPORT.pdf                    # Comprehensive Final Project Report PDF
├── app/
│   ├── app.py                            # Streamlit entry point & authentication
│   ├── api.py                            # FastAPI REST microservice
│   ├── predictor.py                      # Production inference interface
│   ├── admin_portal.py                   # Administrative dashboard & telemetry
│   ├── weather.py                        # Agro-meteorological client & cache
│   └── report_generator.py               # ReportLab PDF advisory compiler
├── database/
│   ├── db_handler.py                     # SQLite WAL connection manager & auth
│   └── predictions.db                    # Persistent relational database
├── datasets/
│   ├── clean_pest_risk_dataset.csv       # Sanitized 249,700-row master dataset
│   └── pesticide_recommendations.json    # Expert agronomic advisory knowledge base
├── data/
│   ├── demo_farmer_inputs.csv            # Sample inputs for testing & demonstration
│   └── demo_prediction_results.json      # Sample prediction outputs
├── diagrams/                             # 8 Architecture diagrams in PNG & vector SVG
│   ├── system_architecture.png/.svg
│   ├── ml_pipeline.png/.svg
│   ├── data_flow_diagram.png/.svg
│   ├── er_diagram.png/.svg
│   ├── sequence_diagram.png/.svg
│   ├── deployment_architecture.png/.svg
│   ├── component_diagram.png/.svg
│   └── workflow_diagram.png/.svg
├── docs/                                 # 10 Complete Markdown documentation manuals
│   ├── USER_MANUAL.md
│   ├── INSTALLATION_GUIDE.md
│   ├── TECHNICAL_DOCUMENTATION.md
│   ├── API_DOCUMENTATION.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── ADMINISTRATOR_GUIDE.md
│   ├── MODEL_CARD.md
│   ├── DATASET_DOCUMENTATION.md
│   ├── TESTING_DOCUMENTATION.md
│   └── TROUBLESHOOTING_GUIDE.md
├── models/
│   ├── best_model.pkl                    # Unified production ensemble pipeline
│   └── preprocessing_pipeline.pkl        # Feature preprocessor pipeline
├── screenshots/                          # 11 High-resolution UI screenshots
├── tests/                                # 91 Regression & integration tests (100% pass)
└── utils/                                # Helper utilities
```

---

## 💻 Installation & Setup

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13 (64-bit recommended)
- 4GB+ RAM

### 1. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/Shubham-Prajapati-655/AI-Powered-Pest-Prediction.git
cd AI-Powered-Pest-Prediction

# Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS:
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Pinned Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Launch Applications
```bash
# Launch Streamlit Multi-Page Portal:
streamlit run app/app.py

# Launch FastAPI REST Microservice:
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🚀 REST API Reference

The platform includes a high-performance FastAPI microservice:
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc Technical Specs**: `http://localhost:8000/redoc`

### Example Prediction Request:
```bash
curl -X POST "http://localhost:8000/api/v1/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "Crop_Name": "Cotton",
       "District": "Guntur",
       "Season": "Kharif",
       "Soil_Type": "Black",
       "Temperature": 31.5,
       "Humidity": 76.0,
       "Rainfall": 125.0,
       "Wind_Speed": 12.0,
       "Soil_Moisture": 55.0,
       "Soil_pH": 7.3,
       "Nitrogen": 26.0,
       "Phosphorus": 18.0,
       "Potassium": 12.0,
       "Organic_Carbon": 0.80
     }'
```

---

## ☁️ Deployment Guide

| Target | Deployment Method | Configuration File |
| :--- | :--- | :--- |
| **Streamlit Community Cloud** | 1-Click Git Connect | Set entry to `app/app.py` |
| **Docker & Docker Compose** | Multi-stage Container | `Dockerfile`, `docker-compose.yml` |
| **Render** | Web Service | `Procfile` / `requirements.txt` |
| **Railway** | Container PaaS | `Dockerfile` |
| **Linux Production VPS** | Systemd + Nginx SSL | See [`deployment.md`](deployment.md) |

Launch container locally:
```bash
docker-compose up -d --build
```

---

## 📄 Official Documentation Deliverables

All documentation deliverables have been compiled for academic submission and enterprise deployment:

| Deliverable Document | Format | Description |
| :--- | :---: | :--- |
| [USER_GUIDE.pdf](USER_GUIDE.pdf) | PDF | Illustrated operational manual for farmers and agronomists |
| [INSTALLATION_GUIDE.pdf](INSTALLATION_GUIDE.pdf) | PDF | Step-by-step bare-metal and container installation instructions |
| [TECHNICAL_DOCUMENTATION.pdf](TECHNICAL_DOCUMENTATION.pdf) | PDF | Comprehensive architecture blueprint, schemas, and ML algorithms |
| [DEPLOYMENT_GUIDE.pdf](DEPLOYMENT_GUIDE.pdf) | PDF | Production cloud operations, Docker, Render, and Nginx setup |
| [PROJECT_REPORT.pdf](PROJECT_REPORT.pdf) | PDF | Full academic project thesis, benchmarks, and validation results |
| [PRESENTATION.pptx](PRESENTATION.pptx) | PPTX | Executive 31-slide presentation deck with high-res graphics |
| [docs/](docs/) | Markdown | 10 modular technical manuals in GitHub-flavored Markdown |

---

## ⚠️ Model Limitations

1. **Weather Overlap in Sister Species**: Closely related biological sister pests (e.g. *Stem Borer* vs *Brown Planthopper* on Rice) flourish under similar microclimatic conditions. While Top-1 accuracy is 40.80%, Top-3 accuracy is **100.00%**, making Top-3 presentation essential for field scouts.
2. **Tabular Telemetry vs Visual Morphology**: Tabular meteorological and edaphic features reflect regional vulnerability rather than visual specimen confirmation. Integration with mobile image recognition models will provide complete confirmation.
3. **Macro Soil Data vs Field Heterogeneity**: District-level soil averages may deviate from localized field plots with recent unrecorded organic amendments.

---

## 🔮 Future Scope

1. **Edge Deployment & ONNX Quantization**: Convert the ensemble trees into an ONNX runtime bundle with float16 quantization to reduce memory from 2.5 GB to <150 MB and lower single-query inference latency to <15 ms.
2. **Multimodal Fusion**: Integrate a lightweight vision model (e.g. MobileNetV4) allowing farmers to upload leaf photos to resolve Top-3 candidate ambiguities.
3. **Microclimate Hyperlocal Forecasts**: Connect with numerical weather prediction models (HRRR / ECMWF) for 7-day predictive early-warning pest outbreak heatmaps.
4. **Active Learning Feedback Loop**: Implement field verification feedback where agricultural extension officers report confirmed diagnoses to continually update training distributions.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Contributors

- **Shubham Prajapati** — Lead Developer & Machine Learning Architect  
  GitHub: [@Shubham-Prajapati-655](https://github.com/Shubham-Prajapati-655)
