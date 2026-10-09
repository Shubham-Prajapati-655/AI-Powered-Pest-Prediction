# AgriAI Platform — REST API Reference

## Base URL
```
http://localhost:8000/api/v1
```
Interactive Swagger UI: `http://localhost:8000/docs`
ReDoc Specification: `http://localhost:8000/redoc`

---

## Endpoints

### 1. System Health Check
- **GET** `/health`
- **Description:** Returns the operational status of the API, loaded model status, and database latency.
- **Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "database": "connected"
}
```

### 2. Predict Pest Risk (Single Record)
- **POST** `/api/v1/predict`
- **Request Body:**
```json
{
  "crop_type": "Wheat",
  "growth_stage": "Vegetative",
  "soil_type": "Loamy",
  "temperature": 24.5,
  "humidity": 68.0,
  "rainfall": 12.0,
  "wind_speed": 8.5,
  "soil_ph": 6.5,
  "soil_nitrogen": 140.0,
  "soil_phosphorus": 45.0,
  "soil_potassium": 190.0,
  "irrigation_type": "Drip",
  "previous_infestation": "No"
}
```
- **Response (200 OK):**
```json
{
  "prediction_id": "pred_98418f7a",
  "timestamp": "2026-10-02T10:15:00Z",
  "predicted_pest": "Aphids",
  "risk_level": "Moderate",
  "confidence": 0.842,
  "top_3_predictions": [
    {"pest": "Aphids", "probability": 0.842},
    {"pest": "Armyworm", "probability": 0.098},
    {"pest": "Stem Borer", "probability": 0.035}
  ],
  "advisory": {
    "cultural_control": "Introduce sticky yellow traps and maintain field hygiene.",
    "biological_control": "Release Ladybird beetles (Coccinellidae) or spray Neem oil extract at 3ml/L.",
    "chemical_control": "If infestation exceeds 15% threshold, apply Imidacloprid 17.8% SL at 0.5ml/L."
  }
}
```

### 3. Batch Prediction
- **POST** `/api/v1/predict/batch`
- **Request Body:** Array of prediction request objects (up to 500 items).
- **Response (200 OK):** Array of prediction result objects.

### 4. Fetch Prediction History
- **GET** `/api/v1/predictions`
- **Query Parameters:** `limit=50`, `offset=0`, `crop_type=Wheat`
- **Response (200 OK):** Paginated array of stored prediction records.

### 5. Fetch Live Weather Data
- **GET** `/api/v1/weather`
- **Query Parameters:** `latitude=28.6139&longitude=77.2090` or `city=Delhi`
- **Response (200 OK):** Current temperature, humidity, rainfall, and wind speed.
