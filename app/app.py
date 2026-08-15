import streamlit as st
import pandas as pd
import numpy as np
import os

from utils import load_pest_weather_data, load_crop_yield_data, calculate_thi, log_prediction
from prediction import predict_pest_outbreak
from recommendation import get_pest_recommendations, get_crop_yield_advisory

# Page Configuration
st.set_page_config(
    page_title="AI Pest Prediction & Crop Advisory System",
    page_icon="🌾",
    layout="wide"
)

# Header
st.title("🌾 AI-Powered Pest Prediction & Advisory System")
st.markdown("""
Predict pest outbreak risks using machine learning models (Random Forest / XGBoost) trained on climate, crop, and seasonal data.
""")

# Sidebar - Parameters
st.sidebar.header("📊 Input Advisory Parameters")
state = st.sidebar.selectbox("Select State", ["Andhra Pradesh", "Gujarat", "Maharashtra", "Karnataka", "Uttar Pradesh", "West Bengal", "Tamil Nadu"])
district = st.sidebar.text_input("District Name", value="Guntur")
crop = st.sidebar.selectbox("Select Crop", ["Maize", "Wheat", "Cotton", "Rice", "Tur (Arhar)", "Mustard", "Groundnut"])
season = st.sidebar.selectbox("Season", ["Kharif", "Rabi", "Zaid"])

temp = st.sidebar.slider("Temperature (°C)", min_value=10.0, max_value=45.0, value=28.0, step=0.5)
humidity = st.sidebar.slider("Humidity (%)", min_value=20.0, max_value=100.0, value=65.0, step=1.0)
rainfall = st.sidebar.slider("Rainfall (mm)", min_value=0.0, max_value=800.0, value=120.0, step=5.0)

model_choice = st.sidebar.selectbox("ML Architecture", ["Random Forest", "XGBoost"])

# Main Dashboard Tabs
tab1, tab2, tab3 = st.tabs(["🔮 Pest Prediction & Advisory", "📈 Regional Yield Insights", "📁 Dataset Explorer"])

# Tab 1: Prediction & Recommendations
with tab1:
    st.subheader("Pest Outbreak Risk Predictor")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Temperature", f"{temp} °C")
    with col2:
        st.metric("Humidity", f"{humidity} %")
    with col3:
        st.metric("Rainfall", f"{rainfall} mm")
    with col4:
        thi_val = round(calculate_thi(temp, humidity), 2)
        st.metric("Weather THI Index", f"{thi_val}")
        
    st.markdown("---")
    
    if st.button("🔍 Run AI Pest Outbreak Prediction", type="primary", use_container_width=True):
        risk_level, model_info = predict_pest_outbreak(model_choice, state, crop, season, temp, humidity, rainfall)
        
        # Log to Database
        logged = log_prediction(state, district, crop, temp, humidity, rainfall, risk_level)
        
        # Advisory Recommendations
        rec = get_pest_recommendations(crop, risk_level)
        
        st.subheader(rec["severity_badge"])
        
        if risk_level == "High":
            st.error(rec["alert_message"])
        elif risk_level == "Medium":
            st.warning(rec["alert_message"])
        else:
            st.success(rec["alert_message"])
            
        col_rec1, col_rec2 = st.columns(2)
        with col_rec1:
            st.info(f"🌿 **Cultural & Biological Control:**\n\n- {rec['cultural_control']}\n- {rec['biological_control']}")
        with col_rec2:
            st.info(f"🧪 **Chemical & Monitoring Advisory:**\n\n- {rec['chemical_control']}\n- **Monitoring:** {rec['monitoring_frequency']}")
            
        st.caption(f"Engine: {model_info} | Logged to Database: {'Yes' if logged else 'No'}")

# Tab 2: Yield Insights
with tab2:
    st.subheader("Regional Crop Yield Analytics")
    ydf = load_crop_yield_data()
    if not ydf.empty:
        filtered_ydf = ydf[(ydf['State'] == state) & (ydf['Crop'] == crop)]
        if not filtered_ydf.empty:
            avg_yield = round(filtered_ydf['Yield_Kg_Per_Ha'].mean(), 2)
            st.metric(f"Average {crop} Yield in {state}", f"{avg_yield} kg/ha")
            st.info(f"💡 Yield Advisory: {get_crop_yield_advisory(avg_yield)}")
            st.dataframe(filtered_ydf, use_container_width=True)
        else:
            st.warning(f"No regional yield data found for {crop} in {state}.")
            st.dataframe(ydf.head(20), use_container_width=True)
    else:
        st.write("Crop yield dataset not found.")

# Tab 3: Dataset Explorer
with tab3:
    st.subheader("Raw Pest & Weather Dataset Explorer")
    pdf = load_pest_weather_data(nrows=500)
    if not pdf.empty:
        st.dataframe(pdf, use_container_width=True)
    else:
        st.write("Pest weather dataset not found.")
