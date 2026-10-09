import logging
from logging.handlers import RotatingFileHandler
import os
import re
from datetime import datetime
from pathlib import Path

from config import LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT

# Patterns for sensitive data masking
SENSITIVE_PATTERNS = [
    (re.compile(r'(password|passwd|pwd|secret|token|hash)[\'":\s=]+([^\s,;\'"\}]+)', re.IGNORECASE), r'\1=***REDACTED***'),
    (re.compile(r'(\$2[aby]\$[0-9]{2}\$[A-Za-z0-9\./]{53})'), r'***BCRYPT_HASH_MASKED***'),
    (re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', re.IGNORECASE), lambda m: m.group(1)[:2] + "***@" + m.group(1).split('@')[1] if '@' in m.group(1) else '***@***')
]

class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive credentials, tokens, and hashes from log output."""
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = self.mask_sensitive_text(record.msg)
        if record.args:
            args_list = list(record.args)
            for i, arg in enumerate(args_list):
                if isinstance(arg, str):
                    args_list[i] = self.mask_sensitive_text(arg)
            record.args = tuple(args_list)
        return True

    @staticmethod
    def mask_sensitive_text(text: str) -> str:
        if not isinstance(text, str):
            return text
        masked = text
        for pattern, replacement in SENSITIVE_PATTERNS:
            if callable(replacement):
                masked = pattern.sub(replacement, masked)
            else:
                masked = pattern.sub(replacement, masked)
        return masked

# Ensure log directory exists
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Create Root App Logger
app_logger = logging.getLogger("agriai")
log_level = getattr(logging, LOG_LEVEL, logging.INFO)
app_logger.setLevel(log_level)

# Avoid attaching duplicate handlers if re-imported
if not app_logger.handlers:
    # Rotating File Handler
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8"
    )
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-7s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(SensitiveDataFilter())
    app_logger.addHandler(file_handler)

    # Console Stream Handler for dev terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())
    app_logger.addHandler(console_handler)

def get_logger(module_name: str) -> logging.Logger:
    """Get a namespaced child logger under agriai."""
    return logging.getLogger(f"agriai.{module_name}")

# Specialized Structured Event Loggers

def log_auth_event(event_type: str, email: str, success: bool, ip: str = "127.0.0.1", details: str = ""):
    """Log authentication activity (Login, Logout, Session Expiry)."""
    status_str = "SUCCESS" if success else "FAILED"
    logger = get_logger("auth")
    msg = f"AUTH_{event_type.upper()} | Status={status_str} | User={email} | IP={ip} | Details={details}"
    if success:
        logger.info(msg)
    else:
        logger.warning(msg)

def log_prediction_event(user_id: int, crop: str, state: str, district: str, pest: str, risk: str, is_live: bool = True):
    """Log prediction request and model inference results."""
    logger = get_logger("prediction")
    data_source = "LIVE_WEATHER" if is_live else "DEMO_PRESET"
    logger.info(f"PREDICTION_GENERATED | UserID={user_id} | Crop={crop} | Location={district},{state} | Pest={pest} | Risk={risk} | Source={data_source}")

def log_weather_event(status: str, location: str, latency_ms: float = 0.0, error: str = ""):
    """Log weather API calls, latency, cache hits, or network errors."""
    logger = get_logger("weather")
    if status == "SUCCESS":
        logger.info(f"WEATHER_FETCH_OK | Location={location} | Latency={latency_ms:.1f}ms")
    elif status == "CACHE_HIT":
        logger.info(f"WEATHER_CACHE_HIT | Location={location}")
    elif status == "FALLBACK":
        logger.warning(f"WEATHER_FALLBACK_USED | Location={location} | Reason={error}")
    else:
        logger.error(f"WEATHER_FETCH_FAILED | Location={location} | Error={error}")

def log_pdf_event(doc_type: str, user_id: int, filename: str, status: str = "SUCCESS"):
    """Log PDF advisory report creation and downloads."""
    logger = get_logger("pdf")
    logger.info(f"PDF_GENERATED | Type={doc_type} | UserID={user_id} | File={filename} | Status={status}")

def log_admin_action(admin_email: str, action: str, target: str, details: str = ""):
    """Audit log all administrator operations."""
    logger = get_logger("admin_audit")
    logger.info(f"ADMIN_ACTION | Admin={admin_email} | Action={action} | Target={target} | Details={details}")

def log_security_event(event_type: str, message: str, level: str = "WARNING"):
    """Log security alarms, rate limit breaches, or invalid access attempts."""
    logger = get_logger("security")
    log_func = getattr(logger, level.lower(), logger.warning)
    log_func(f"SECURITY_ALERT | Type={event_type} | Message={message}")

def log_database_event(action: str, status: str, details: str = ""):
    """Log database transactions, backup, or maintenance actions."""
    logger = get_logger("database")
    if status == "ERROR":
        logger.error(f"DATABASE_OP | Action={action} | Status={status} | Details={details}")
    else:
        logger.info(f"DATABASE_OP | Action={action} | Status={status} | Details={details}")

def get_recent_logs(limit: int = 100, level_filter: str = None) -> list[dict]:
    """
    Read and parse recent log records for admin health dashboard.
    Returns list of dicts: [{'timestamp': ..., 'level': ..., 'module': ..., 'message': ...}]
    """
    if not LOG_FILE.exists():
        return []

    results = []
    log_pattern = re.compile(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[([A-Z]+)\s*\] \[([a-zA-Z0-9_\.]+)\] (.*)$')

    try:
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            match = log_pattern.match(line)
            if match:
                ts, level, module, msg = match.groups()
                if level_filter and level_filter != "ALL" and level != level_filter:
                    continue
                results.append({
                    "timestamp": ts,
                    "level": level,
                    "module": module,
                    "message": msg
                })
                if len(results) >= limit:
                    break
    except Exception as e:
        app_logger.error(f"Error reading log file: {e}")

    return results
