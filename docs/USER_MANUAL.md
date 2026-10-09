# AgriAI Platform — End User Manual & Farmer Guide

## 1. Introduction
Welcome to the **AgriAI Crop Pest Prediction & Agricultural Advisory System**. This guide provides practical, step-by-step instructions for farmers, agronomists, extension officers, and agricultural researchers on how to utilize the platform for early pest risk detection and actionable treatment guidance.

---

## 2. Getting Started
### 2.1 Accessing the Application
Open any modern web browser (Google Chrome, Firefox, Safari, Microsoft Edge) and navigate to the application URL:
```
http://localhost:8501 (Local) or your deployed Cloud URL
```

### 2.2 Account Registration & Login
1. Click on **Register** in the sidebar authentication menu.
2. Enter your Full Name, Email Address, Phone Number, Primary Crop Type, and Farm Location.
3. Choose a strong password (minimum 8 characters with numbers and special symbols).
4. Click **Create Account**.
5. Once registered, log in using your email and password.

*Tip: If you forget your password, use the "Forgot Password" tab to securely reset your credentials.*

---

## 3. Platform Navigation
The left sidebar contains all navigation options:
- **🏠 Home & Overview**: High-level platform introduction, mission, and live agricultural indicators.
- **📊 Real-time Dashboard**: Overview of recent predictions, community risk levels, and seasonal alert feeds.
- **🎯 Pest Prediction Engine**: Main input module for predicting pest outbreaks.
- **⛅ Live Weather & Agro-Climate**: Real-time atmospheric forecasts and risk correlation.
- **📜 Prediction History**: Archive of past field assessments with search, filter, and CSV export.
- **📄 PDF Advisory Reports**: Instant generation of branded, multilingual agronomic diagnostic reports.
- **👤 Profile Settings**: Manage farm preferences, primary crops, and notification options.
- **🛠️ Admin Portal** *(Admin accounts only)*: Database records, model metrics, system logs, and user management.

---

## 4. How to Generate a Pest Prediction
Navigate to the **Pest Prediction Engine** page:

### Step 1: Input Field Conditions
- **Crop Information**: Select Crop Type (Wheat, Rice, Maize, Cotton, Soybean, Sugarcane, etc.), Current Growth Stage (Seedling, Vegetative, Flowering, Maturity), and Soil Type.
- **Environmental & Atmospheric Parameters**: Temperature (°C), Relative Humidity (%), Rainfall (mm), Wind Speed (km/h), and Sunlight Hours.
  - *Option*: Click **"Auto-Fetch Live Weather"** to automatically pull real-time weather data for your farm's GPS or city location.
- **Agronomic Practices**: Irrigation Type, Fertilizer Usage (N-P-K levels), Previous Pest History, and Neighboring Infestation Presence.

### Step 2: Run Inference
- Click the **"Analyze Pest Risk"** button.
- The platform executes the ensemble model within ~50 milliseconds.

### Step 3: Interpret Results
1. **Primary Prediction Banner**: Displays the most probable pest (e.g., *Aphids (Rhopalosiphum padi)*) with an overall Risk Category (**Low**, **Moderate**, **High**, or **Severe**).
2. **Top-3 Probability Breakdown**:
   - Primary Candidate: Estimated confidence (e.g., 78.4%)
   - Secondary Candidate: Differential diagnosis (e.g., 14.2%)
   - Tertiary Candidate: Minor probability (e.g., 5.1%)
3. **Interactive Probability Chart**: Horizontal bar graph illustrating class distribution.
4. **Actionable Advisory Card**:
   - **Cultural Controls**: Crop rotation, pruning, spacing, water regulation.
   - **Biological Controls**: Natural predators, parasitic wasps, bio-pesticides (e.g., *Beauveria bassiana*, Neem oil).
   - **Targeted Chemical Interventions**: Active ingredients, recommended dosage per hectare, safety withdrawal intervals, and resistance avoidance guidance.

---

## 5. Downloading PDF Advisory Reports
1. After generating a prediction or selecting a record from **Prediction History**, click **"Generate Official PDF Report"**.
2. A formal 2-page Agronomic Advisory Report is compiled featuring:
   - Official certification badge and timestamp.
   - Farm details and geolocation.
   - Complete input telemetry parameters.
   - Primary and Top-3 differential diagnoses with probability charts.
   - Integrated pest management (IPM) prescription.
3. Click **"Download PDF"** to save or print for field workers or regulatory compliance.

---

## 6. Offline and Mobile Usage
The web interface is 100% responsive:
- Bookmark the URL on your smartphone or tablet browser.
- Use mobile touch inputs for fast data entry in the field.
- If cellular connectivity is intermittent, enter parameters once online or consult pre-downloaded PDF reports.

---

## 7. Support & Feedback
For technical inquiries, bug reports, or agronomic feedback:
- Visit the **Contact & Support** page in the application.
- Email: `support@agriai.org`
- Hotline: `+1-800-AGRI-AI-HELP`
