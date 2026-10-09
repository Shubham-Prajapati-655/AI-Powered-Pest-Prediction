# AgriAI Platform — Technical Architecture & Engineering Documentation

## 1. System Overview
AgriAI is a modular, high-throughput crop pest prediction platform that fuses machine learning classification algorithms with real-time agro-meteorological streaming data and an expert Integrated Pest Management (IPM) advisory rule engine.

---

## 2. Software Architecture
The system follows a Decoupled Service-Oriented Architecture (SOA):
- **Presentation Layer:** Streamlit (Python) and FastAPI OpenAPI documentation.
- **Application & Orchestration Layer:** FastAPI REST microservice and Streamlit multi-page router.
- **Inference & Preprocessing Engine:** Scikit-Learn pipeline and tuned Random Forest / Gradient Boosting ensemble.
- **Advisory Engine:** Domain knowledge rule engine mapping pest classification to IPM controls.
- **Data Persistence Layer:** SQLite with WAL (Write-Ahead Logging) and thread-safe connection pooling.
- **Reporting Engine:** ReportLab PDF compilation subsystem with custom cryptographic verification hashes.

---

## 3. Machine Learning Pipeline
1. **Feature Ingestion:** 17 agronomic and meteorological features:
   - Categorical: Crop Type, Growth Stage, Soil Type, Region, Irrigation Type, Previous Infestation.
   - Continuous: Temperature (°C), Humidity (%), Rainfall (mm), Wind Speed (km/h), Soil pH, Soil Nitrogen, Soil Phosphorus, Soil Potassium.
2. **Preprocessing Pipeline (`models/preprocessing_pipeline.pkl`):**
   - Numeric Features: Median imputation + Standard Scaling (`StandardScaler`).
   - Categorical Features: Most frequent imputation + One-Hot Encoding (`OneHotEncoder(handle_unknown='ignore')`).
3. **Classification Ensemble (`models/best_model.pkl`):**
   - Algorithm: Random Forest Classifier (200 estimators, balanced class weights, max_depth=20).
   - Multi-Class Output: Softmax probability distribution over all target pest classes.
   - Top-3 Ranking: Slices top-3 argmax indices with confidence scores.

---

## 4. Database Schema
- `users`: User authentication, hashed passwords (PBKDF2/SHA256), roles (`farmer`, `agronomist`, `admin`).
- `predictions`: Stored prediction telemetry, crop inputs, top-3 outputs, risk category, and advisory summary.
- `weather_cache`: 1-hour TTL cache for external OpenWeatherMap / Open-Meteo responses.
- `system_logs`: Audit trail for security, user logins, and prediction requests.

---

## 5. Security & Compliance
- Passwords hashed using industry-standard salted hashing.
- Input validation enforced with Pydantic models on REST endpoints.
- Database access uses parameterized SQL queries preventing SQL injection.
- Session timeout protection and CSRF validation in production.
