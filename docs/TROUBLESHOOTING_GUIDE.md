# AgriAI Platform — Troubleshooting & FAQ Guide

## 1. Common Issues & Solutions

### Issue 1: "ModuleNotFoundError: No module named 'reportlab'" or similar
- **Cause:** Virtual environment is not activated or dependencies are missing.
- **Solution:**
  ```bash
  source venv/bin/activate  # (or venv\Scripts\activate on Windows)
  pip install -r requirements.txt
  ```

### Issue 2: "Port 8501 is already in use"
- **Cause:** Another instance of Streamlit or another web server is occupying port 8501.
- **Solution:**
  Launch Streamlit on an alternative port:
  ```bash
  streamlit run app/app.py --server.port 8502
  ```
  Or kill the existing process:
  ```powershell
  # Windows
  Get-Process -Id (Get-NetTCPConnection -LocalPort 8501).OwningProcess | Stop-Process
  ```

### Issue 3: "Weather API returns fallback default values"
- **Cause:** No internet connection or OpenWeatherMap API key rate limit reached.
- **Solution:** The platform features automatic failover to the Open-Meteo public service and cached seasonal averages, ensuring 100% operational uptime even without an API key.

### Issue 4: "PyArrow conversion warning on Admin Portal"
- **Cause:** Mismatched column datatypes in Streamlit dataframes.
- **Solution:** Dataframe columns are pre-cast to string types before rendering in `app/admin_portal.py`, preventing Arrow serialization errors.

### Issue 5: "Database locked error"
- **Cause:** Multiple concurrent writes in high-concurrency environments without WAL enabled.
- **Solution:** SQLite is configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`). For high-throughput production clusters, switch `DATABASE_URL` in `.env` to PostgreSQL.

---

## 2. Diagnostic Commands
Check system health and environment status:
```bash
python -c "import torch, sklearn, streamlit; print('All core libraries operational!')"
```
