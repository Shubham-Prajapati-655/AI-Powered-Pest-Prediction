# Model Card — AgriAI Multi-Class Pest Classification Model

## Model Details
- **Developer:** AgriAI Core Intelligence Team
- **Model Date:** October 2026
- **Model Version:** 1.4.0-Production
- **Model Type:** Balanced Ensemble Random Forest Classifier with Softmax Probability Calibration
- **Library & Framework:** Scikit-Learn 1.6+, Python 3.11/3.13
- **Artifacts:** `models/best_model.pkl`, `models/preprocessing_pipeline.pkl`

---

## Intended Use
- **Primary Use Case:** Real-time prediction of crop pest infestations across 10 major economic crops based on weather, soil, and agronomic inputs.
- **Primary Users:** Farmers, agricultural extension officers, agronomists, and crop protection researchers.
- **Out-of-Scope Uses:** Autonomous lethal chemical spraying without human verification.

---

## Training Data
- **Dataset Size:** 249,700 validated agricultural records across 12 agro-climatic zones.
- **Target Classes:** 10 major crop pests (Aphids, Armyworm, Stem Borer, Bollworm, Leafhopper, Whitefly, Thrips, Brown Planthopper, Cutworm, Mites).
- **Features (17 total):** 11 continuous environmental metrics + 6 categorical agronomic descriptors.

---

## Performance Metrics
- **Overall Accuracy:** 98.4%
- **Macro Precision:** 0.982
- **Macro Recall:** 0.981
- **Macro F1-Score:** 0.981
- **Top-3 Diagnostic Accuracy:** 99.8%
- **Inference Latency:** 24ms per sample on single CPU core.

---

## Ethical & Agronomic Considerations
- Model emphasizes low false negative rates for high-devastation quarantine pests (e.g., Fall Armyworm).
- Advisory engine enforces Integrated Pest Management (IPM), prioritizing biological and cultural controls over chemical pesticides.
