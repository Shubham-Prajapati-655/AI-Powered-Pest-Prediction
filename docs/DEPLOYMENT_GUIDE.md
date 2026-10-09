# AgriAI Platform — Deployment & Operations Guide

## Overview

This guide provides end-to-end instructions for deploying the **AI-Powered Crop Pest Prediction & Agricultural Advisory System** across multiple environments, including:
1. **Local Bare-Metal / Virtual Environment**
2. **Docker & Docker Compose**
3. **Streamlit Community Cloud**
4. **Render**
5. **Railway**
6. **AWS EC2 / DigitalOcean Droplet (Production Linux)**

---

## 1. System Requirements & Architecture

| Component | Minimum Specification | Recommended Production |
| :--- | :--- | :--- |
| **CPU** | 2 Cores (x86_64 or ARM64) | 4 Cores |
| **RAM** | 4 GB | 8 GB |
| **Disk Space** | 5 GB SSD | 20 GB NVMe |
| **Python** | 3.10 - 3.13 | 3.11 |
| **Ports** | `8501` (Streamlit UI), `8000` (FastAPI REST API) | Reverse Proxied via Nginx (`80`/`443`) |

---

## 2. Environment Configuration (`.env`)

Copy `.env.example` to `.env` and configure appropriate values:

```bash
cp .env.example .env
```

Key variables:
```ini
APP_NAME="AgriAI - Pest Prediction System"
APP_ENV="production"
DEBUG=False
SECRET_KEY="generate-a-strong-random-hex-string"
DATABASE_URL="sqlite:///database/predictions.db"
ADMIN_EMAIL="admin@agriai.org"
ADMIN_DEFAULT_PASSWORD="YourSecurePasswordHere!"
WEATHER_API_TIMEOUT=5
WEATHER_API_RETRIES=3
LOG_LEVEL="INFO"
```

---

## 3. Local Installation & Execution

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/Shubham-Prajapati-655/AI-Powered-Pest-Prediction.git
cd AI-Powered-Pest-Prediction

# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Locked Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Run the Streamlit Dashboard
```bash
streamlit run app/app.py
```
Access in your browser at: `http://localhost:8501`

### Step 4: Run the FastAPI REST Microservice
```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation available at: `http://localhost:8000/docs`

---

## 4. Docker & Docker Compose Deployment

### Running via Docker Standalone
Build and execute the production container:
```bash
# Build image
docker build -t agriai-platform:latest .

# Run container
docker run -d \
  --name agriai-app \
  -p 8501:8501 \
  -v $(pwd)/database:/app/database \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  agriai-platform:latest
```

### Running via Docker Compose
Docker Compose starts both the Streamlit web application and an isolated persistent volume:
```bash
# Start in detached mode
docker-compose up -d --build

# View real-time logs
docker-compose logs -f web

# Check health status
docker-compose ps

# Stop service
docker-compose down
```

---

## 5. Streamlit Community Cloud

Streamlit Community Cloud offers the fastest zero-cost deployment:

1. Push your repository to **GitHub**.
2. Sign in to [share.streamlit.io](https://share.streamlit.io) using GitHub.
3. Click **New app**.
4. Select:
   - **Repository:** `Shubham-Prajapati-655/AI-Powered-Pest-Prediction`
   - **Branch:** `main`
   - **Main file path:** `app/app.py`
5. Under **Advanced Settings**, add Secrets matching your `.env`:
   ```toml
   SECRET_KEY = "your-production-secret-key"
   ADMIN_EMAIL = "admin@agriai.org"
   ADMIN_DEFAULT_PASSWORD = "StrongPassword@2026"
   APP_ENV = "production"
   ```
6. Click **Deploy!**. The app will be live within 2-3 minutes.

---

## 6. Render Deployment

Render supports both web services and background workers:

1. Link your GitHub account on [render.com](https://render.com).
2. Create a **New Web Service**.
3. Select your repository.
4. Settings:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run app/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
5. Under **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.9`
   - `SECRET_KEY`: `your-secure-secret-key`
   - `ADMIN_EMAIL`: `admin@agriai.org`
   - `ADMIN_DEFAULT_PASSWORD`: `RenderAdmin@2026`
6. Click **Create Web Service**.

To host the FastAPI endpoint alongside it, create a second Web Service pointing to `uvicorn app.api:app --host 0.0.0.0 --port $PORT`.

---

## 7. Railway Deployment

Railway offers instantaneous container builds using the included `Dockerfile` or `Procfile`:

1. Log in to [railway.app](https://railway.app).
2. Click **New Project** → **Deploy from GitHub repo**.
3. Select `AI-Powered-Pest-Prediction`.
4. Railway will automatically detect the `Dockerfile`.
5. Under **Variables**, add:
   - `PORT`: `8501`
   - `SECRET_KEY`: `your-railway-secret-key`
   - `ADMIN_EMAIL`: `admin@agriai.org`
6. Generate a domain under **Networking**.

---

## 8. Nginx Reverse Proxy & SSL Configuration (Linux Production)

For enterprise deployments on an Ubuntu 22.04/24.04 LTS VPS:

### Systemd Service (`/etc/systemd/system/agriai.service`)
```ini
[Unit]
Description=AgriAI Streamlit Platform
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/AI-Powered-Pest-Prediction
ExecStart=/var/www/AI-Powered-Pest-Prediction/venv/bin/streamlit run app/app.py --server.port=8501 --server.address=127.0.0.1
Restart=always
RestartSec=5
EnvironmentFile=/var/www/AI-Powered-Pest-Prediction/.env

[Install]
WantedBy=multi-user.target
```

### Nginx Site Configuration (`/etc/nginx/sites-available/agriai`)
```nginx
server {
    server_name pestprediction.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable SSL via Certbot:
```bash
sudo certbot --nginx -d pestprediction.yourdomain.com
```

---

## 9. Verification & Smoke Testing

After deployment, run the automated health check:
```bash
curl -f http://localhost:8501/_stcore/health
curl -f http://localhost:8000/health
```

Both endpoints will return HTTP 200 OK.
