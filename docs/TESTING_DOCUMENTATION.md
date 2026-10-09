# AgriAI Platform — Testing & Quality Assurance Documentation

## 1. Testing Framework & Philosophy
The AgriAI verification suite leverages `pytest` and `unittest` with comprehensive coverage across:
- Unit tests for preprocessing, mathematical models, and advisory lookups.
- Integration tests for SQLite transactions, auth sessions, and external weather APIs.
- UI tests verifying Streamlit AppTest headless execution.
- Performance and stress benchmarks verifying sub-100ms response targets.

---

## 2. Test Execution
Execute the entire test suite:
```bash
pytest tests/ -v
```

### Test Suite Breakdown:
- `tests/test_saas_ui.py`: End-to-end Streamlit page transitions, auth guards, and UI rendering.
- `tests/test_rest_api_phase13.py`: FastAPI REST API routes, Pydantic validations, batch limits, and error codes.
- `tests/test_ml_pipeline.py`: Model inference, Top-3 probability calibration, feature alignment, and edge cases.
- `tests/test_weather_integration.py`: OpenWeatherMap/Open-Meteo fallbacks, caching, and network fault tolerance.
- `tests/test_pdf_generation.py`: ReportLab generation, styling, table formatting, and PDF validity.
- `tests/test_db_and_auth.py`: Password hashing, user creation, session isolation, and record archival.

---

## 3. Test Results & Metrics
- **Total Test Cases:** 91
- **Passed:** 91 (100%)
- **Failed:** 0
- **Code Coverage:** > 92% across core modules (`src/`, `app/`, `database/`).
