"""
Vercel Serverless Function Entrypoint for AgriAI API.
Exposes FastAPI application instance as 'app'.
"""
import os
import sys
from pathlib import Path

# Add project root and app directory to Python path
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "app") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "app"))

# Mark environment as Vercel serverless
os.environ["VERCEL"] = "1"
os.environ["SERVERLESS"] = "1"

from src.api import app

# Vercel looks for 'app' by default in WSGI/ASGI handlers
__all__ = ["app"]
