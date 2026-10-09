import html
import re
import time
import uuid
from pathlib import Path
from typing import Tuple, Optional

from config import (
    MAX_LOGIN_ATTEMPTS,
    LOGIN_LOCKOUT_MINUTES,
    MAX_AVATAR_SIZE_BYTES,
    ALLOWED_AVATAR_EXTENSIONS,
    AVATARS_DIR
)
from logger import log_security_event

# In-Memory Rate Limiting Cache: {identifier: [timestamp1, timestamp2, ...]}
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOCKOUT_EXPIRATIONS: dict[str, float] = {}

def sanitize_text(text: Optional[str], allow_multiline: bool = False) -> str:
    """
    Sanitize text input against Cross-Site Scripting (XSS) and injection attacks.
    Escapes HTML characters (&, <, >, ", ') and strips null bytes.
    """
    if text is None:
        return ""
    # Strip null bytes and control chars
    clean = text.replace("\x00", "").strip()
    if not allow_multiline:
        clean = re.sub(r'[\r\n]+', ' ', clean)
    # Escape HTML entities
    return html.escape(clean)

def check_login_rate_limit(identifier: str) -> Tuple[bool, int]:
    """
    Check if an identifier (email or IP) is rate-limited.
    Returns: (is_allowed, seconds_remaining)
    """
    clean_id = identifier.strip().lower()
    now = time.time()
    
    # Check active lockout
    if clean_id in _LOCKOUT_EXPIRATIONS:
        lockout_until = _LOCKOUT_EXPIRATIONS[clean_id]
        if now < lockout_until:
            rem = int(lockout_until - now)
            return False, rem
        else:
            # Lockout expired
            del _LOCKOUT_EXPIRATIONS[clean_id]
            _LOGIN_ATTEMPTS.pop(clean_id, None)

    # Clean old attempts outside the window
    window_seconds = LOGIN_LOCKOUT_MINUTES * 60
    attempts = _LOGIN_ATTEMPTS.get(clean_id, [])
    valid_attempts = [t for t in attempts if now - t < window_seconds]
    _LOGIN_ATTEMPTS[clean_id] = valid_attempts

    if len(valid_attempts) >= MAX_LOGIN_ATTEMPTS:
        lockout_end = now + window_seconds
        _LOCKOUT_EXPIRATIONS[clean_id] = lockout_end
        log_security_event("RATE_LIMIT_EXCEEDED", f"Identifier '{clean_id}' exceeded max login attempts ({MAX_LOGIN_ATTEMPTS}). Locked for {LOGIN_LOCKOUT_MINUTES} mins.")
        return False, int(window_seconds)

    return True, 0

def record_failed_login(identifier: str):
    """Record a failed login attempt for rate limiting."""
    clean_id = identifier.strip().lower()
    now = time.time()
    if clean_id not in _LOGIN_ATTEMPTS:
        _LOGIN_ATTEMPTS[clean_id] = []
    _LOGIN_ATTEMPTS[clean_id].append(now)

def reset_login_rate_limit(identifier: str):
    """Clear failed attempts on successful login."""
    clean_id = identifier.strip().lower()
    _LOGIN_ATTEMPTS.pop(clean_id, None)
    _LOCKOUT_EXPIRATIONS.pop(clean_id, None)

def validate_avatar_upload(file_name: str, file_bytes: bytes) -> Tuple[bool, str, Optional[str]]:
    """
    Validate uploaded avatar file size, extension, and generate a secure random filename.
    Returns: (is_valid, message, secure_filename)
    """
    if not file_bytes:
        return False, "Uploaded file is empty.", None

    if len(file_bytes) > MAX_AVATAR_SIZE_BYTES:
        max_mb = MAX_AVATAR_SIZE_BYTES // (1024 * 1024)
        return False, f"Avatar file exceeds maximum allowed size of {max_mb} MB.", None

    ext = Path(file_name).suffix.lower()
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        allowed = ", ".join(ALLOWED_AVATAR_EXTENSIONS)
        return False, f"Invalid file type ({ext}). Allowed formats: {allowed}.", None

    # Magic byte check for common image types (PNG, JPG, WEBP)
    is_image = False
    if file_bytes.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
        is_image = True
    elif file_bytes.startswith(b'\xff\xd8\xff'):      # JPEG
        is_image = True
    elif file_bytes.startswith(b'RIFF') and b'WEBP' in file_bytes[:12]:  # WEBP
        is_image = True

    if not is_image:
        return False, "File content is not a valid image format.", None

    # Generate secure non-guessable filename
    secure_name = f"avatar_{uuid.uuid4().hex}{ext}"
    return True, "", secure_name

def save_validated_avatar(secure_filename: str, file_bytes: bytes) -> str:
    """Save the validated avatar bytes into the secure avatars directory."""
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = AVATARS_DIR / secure_filename
    with open(target_path, "wb") as f:
        f.write(file_bytes)
    return str(target_path)
