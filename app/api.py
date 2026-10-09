"""
Entrypoint wrapper for FastAPI REST API Server.
Enables execution via: uvicorn app.api:app --host 0.0.0.0 --port 8000
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api import app, run_server

if __name__ == "__main__":
    run_server()
