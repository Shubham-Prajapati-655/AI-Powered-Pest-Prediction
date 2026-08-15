import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PEST_DATA_PATH = os.path.join(BASE_DIR, "datasets", "pest_weather.csv")
CROP_YIELD_PATH = os.path.join(BASE_DIR, "datasets", "crop_yield.csv")
DB_PATH = os.path.join(BASE_DIR, "database", "pest_prediction.db")

def load_pest_weather_data(nrows=None):
    """Load raw pest weather dataset."""
    if os.path.exists(PEST_DATA_PATH):
        return pd.read_csv(PEST_DATA_PATH, nrows=nrows)
    return pd.DataFrame()

def load_crop_yield_data():
    """Load crop yield dataset."""
    if os.path.exists(CROP_YIELD_PATH):
        return pd.read_csv(CROP_YIELD_PATH)
    return pd.DataFrame()

def calculate_thi(temperature, humidity):
    """Calculate Temperature-Humidity Index (THI)."""
    return 0.8 * temperature + (humidity / 100.0) * (temperature - 14.3) + 46.4

def log_prediction(state, district, crop, temp, humidity, rainfall, risk_level):
    """Log prediction result to SQLite database."""
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO weather_records (state, district, temperature, humidity, rainfall_mm)
            VALUES (?, ?, ?, ?, ?)
        """, (state, district, temp, humidity, rainfall))
        record_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO pest_outbreaks (record_id, crop, pest_name, outbreak_severity)
            VALUES (?, ?, ?, ?)
        """, (record_id, crop, "Predicted Pest", risk_level))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error logging to DB: {e}")
        return False
