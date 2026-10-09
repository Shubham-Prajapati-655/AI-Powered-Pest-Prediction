# ==============================================================================
# AgriAI Platform - Production Dockerfile
# Multi-stage security hardened container image for cloud deployment
# ==============================================================================

FROM python:3.11-slim AS runtime

# Set security and runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    DEBUG=False \
    PORT=8501

# Install lightweight system dependencies for healthcheck and image handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a dedicated non-root user and group
RUN groupadd -r agriai && useradd -r -g agriai -u 1001 -m agriai

# Set working directory
WORKDIR /app

# Install Python dependencies first for caching efficiency
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and models
COPY . .

# Ensure runtime directories exist and have proper permissions for the non-root user
RUN mkdir -p database logs backups uploads/avatars && \
    chown -R agriai:agriai /app

# Switch to the non-root user
USER agriai

# Expose Streamlit default port
EXPOSE 8501

# Healthcheck to verify that Streamlit server is active and responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Launch the Streamlit application in headless production mode
CMD ["python", "-m", "streamlit", "run", "app/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=true"]
