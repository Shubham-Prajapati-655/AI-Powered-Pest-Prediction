"""
Logging utilities for AI-Powered Crop Pest Prediction & Advisory System.
"""
import os
import sys
import logging

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name: str = "pest_pipeline", log_file: str = "pipeline.log", level=logging.INFO) -> logging.Logger:
    """Configures and returns a thread-safe logger with console and file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File Handler
        fh = logging.FileHandler(os.path.join(LOG_DIR, log_file), encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # Console Handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger
