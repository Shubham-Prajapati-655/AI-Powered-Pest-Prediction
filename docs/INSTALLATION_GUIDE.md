# AgriAI Platform — Installation & Setup Guide

## 1. System Requirements
- **Operating System:** Windows 10/11, Ubuntu 20.04/22.04/24.04 LTS, macOS Ventura/Sonoma
- **Python Version:** Python 3.10, 3.11, 3.12, or 3.13 (64-bit recommended)
- **RAM:** Minimum 4 GB, 8 GB recommended
- **Storage:** 5 GB free disk space

---

## 2. Step-by-Step Installation

### Step 1: Clone the Codebase
```bash
git clone https://github.com/Shubham-Prajapati-655/AI-Powered-Pest-Prediction.git
cd AI-Powered-Pest-Prediction
```

### Step 2: Set Up Virtual Environment
On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
On Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Core Dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Step 4: Verify Environment Configuration
Copy the template configuration file:
```bash
cp .env.example .env
```
Key parameters in `.env`:
- `SECRET_KEY`: Used for session authentication tokens.
- `DATABASE_URL`: Defaults to `sqlite:///database/predictions.db`.
- `ADMIN_EMAIL`: Default administrator username.
- `ADMIN_DEFAULT_PASSWORD`: Initial administrative password.

### Step 5: Initialize the Database
The SQLite database automatically initializes upon first run, or you can verify it directly:
```bash
python -c "from database.db_handler import init_db; init_db()"
```

### Step 6: Launch Applications
**Streamlit Dashboard:**
```bash
streamlit run app/app.py
```
Open `http://localhost:8501`.

**REST API Service:**
```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000
```
Open `http://localhost:8000/docs`.

---

## 3. Verification & Smoke Testing
Run the automated test suite to ensure clean installation:
```bash
pytest tests/ -v
```
All 91 unit and integration tests should pass with 100% success rate.
