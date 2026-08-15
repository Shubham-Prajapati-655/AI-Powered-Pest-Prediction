-- SQL Schema for Pest Prediction Database

CREATE TABLE IF NOT EXISTS weather_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    recorded_date DATE DEFAULT CURRENT_DATE,
    temperature REAL,
    humidity REAL,
    rainfall_mm REAL
);

CREATE TABLE IF NOT EXISTS pest_outbreaks (
    outbreak_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER,
    crop TEXT NOT NULL,
    pest_name TEXT NOT NULL,
    outbreak_severity TEXT CHECK(outbreak_severity IN ('Low', 'Medium', 'High')),
    FOREIGN KEY (record_id) REFERENCES weather_records(record_id)
);

CREATE TABLE IF NOT EXISTS crop_yields (
    yield_id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    crop TEXT NOT NULL,
    season TEXT,
    area_hectares REAL,
    production_tons REAL,
    yield_kg_per_ha REAL
);
