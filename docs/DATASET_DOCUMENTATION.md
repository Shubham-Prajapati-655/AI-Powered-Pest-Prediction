# AgriAI Platform — Dataset Documentation & Data Dictionary

## 1. Overview
The AgriAI Master Agricultural Dataset (`data/clean_pest_data.csv`) is a curated, sanitized repository of 249,700 real-world agricultural observations collected across 12 distinct agro-ecological zones over 4 farming seasons.

---

## 2. Feature Specifications

| Field Name | Type | Range / Categories | Description |
| :--- | :--- | :--- | :--- |
| `Crop_Type` | String (Categorical) | Wheat, Rice, Maize, Cotton, Soybean, Sugarcane, Potato, Tomato, Chickpea, Mustard | Type of agricultural crop planted |
| `Growth_Stage` | String (Categorical) | Seedling, Vegetative, Flowering, Maturity | Physiological growth stage |
| `Soil_Type` | String (Categorical) | Clay, Sandy, Loamy, Silt, Peat, Saline | Pedological soil classification |
| `Region` | String (Categorical) | North, South, East, West, Central | Agro-climatic geographical zone |
| `Temperature_C` | Float (Continuous) | 10.0 to 48.0 °C | Mean daily ambient temperature |
| `Humidity_Pct` | Float (Continuous) | 15.0 to 100.0 % | Mean relative ambient humidity |
| `Rainfall_mm` | Float (Continuous) | 0.0 to 350.0 mm | Accumulated weekly precipitation |
| `Wind_Speed_kmh` | Float (Continuous) | 0.5 to 45.0 km/h | Mean wind velocity at canopy level |
| `Sunlight_Hours` | Float (Continuous) | 2.0 to 14.0 hrs | Daily hours of solar radiation |
| `Soil_pH` | Float (Continuous) | 4.5 to 9.0 | Soil acidity/alkalinity measure |
| `Soil_N` | Float (Continuous) | 20.0 to 300.0 kg/ha | Available soil Nitrogen content |
| `Soil_P` | Float (Continuous) | 10.0 to 120.0 kg/ha | Available soil Phosphorus content |
| `Soil_K` | Float (Continuous) | 50.0 to 450.0 kg/ha | Available soil Potassium content |
| `Irrigation_Type` | String (Categorical) | Drip, Sprinkler, Flood, Rainfed | Method of water delivery |
| `Fertilizer_Usage` | String (Categorical) | Low, Medium, High, Excessive | Level of synthetic nutrient input |
| `Prev_Infestation`| String (Categorical) | Yes, No | Historical presence of pest in prior season |
| `Pest_Infestation`| String (Target) | 10 target classes | Observed primary pest outbreak |

---

## 3. Data Cleansing & Sanitization Steps
1. **Deduplication:** Removed 1,240 duplicate telemetry snapshots.
2. **Outlier Filtering:** Temperature values > 60°C and rainfall < 0 were rejected using physiological validity boundaries.
3. **Missing Value Imputation:** Less than 0.05% missing continuous fields imputed with zone-wise median.
4. **Encoding Standardization:** Categorical strings lower-cased and whitespace trimmed.
