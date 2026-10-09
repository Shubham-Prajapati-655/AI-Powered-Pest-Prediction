import os
import sqlite3
import shutil
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple, List, Dict, Optional

from config import BACKUPS_DIR, DATABASE_DIR, DEFAULT_SQLITE_PATH
from logger import log_admin_action, log_database_event, get_logger

logger = get_logger("backup")

def get_backup_dir() -> Path:
    """Ensure and return the backups directory."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUPS_DIR

def create_manual_backup(admin_email: str = "admin@agriai.org") -> Tuple[bool, str, Optional[str]]:
    """
    Create a complete timestamped backup snapshot of the SQLite database and schema.
    Returns: (success, message, backup_filename)
    """
    get_backup_dir()
    db_file = DEFAULT_SQLITE_PATH
    if not db_file.exists():
        return False, "Active database file not found to backup.", None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"agriai_backup_{timestamp}.db"
    backup_path = BACKUPS_DIR / backup_filename
    meta_path = BACKUPS_DIR / f"agriai_backup_{timestamp}.json"

    try:
        # Copy SQLite DB file cleanly
        shutil.copy2(db_file, backup_path)
        
        # Write metadata record
        meta = {
            "backup_filename": backup_filename,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_by": admin_email,
            "size_bytes": os.path.getsize(backup_path),
            "size_mb": round(os.path.getsize(backup_path) / (1024 * 1024), 2),
            "source": str(db_file),
            "version": "2.2.0-prod"
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        log_admin_action(admin_email, "CREATE_BACKUP", backup_filename, f"Size: {meta['size_mb']} MB")
        log_database_event("BACKUP_CREATED", "SUCCESS", f"File: {backup_filename}")
        return True, f"Backup created successfully: {backup_filename}", backup_filename

    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        log_database_event("BACKUP_ERROR", "ERROR", str(e))
        return False, f"Backup failed: {str(e)}", None

def list_available_backups() -> List[Dict]:
    """List all available database backups with metadata."""
    get_backup_dir()
    backups = []
    
    for f in sorted(BACKUPS_DIR.glob("*.db"), key=os.path.getmtime, reverse=True):
        size_bytes = os.path.getsize(f)
        mtime = datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Check if matching JSON metadata exists
        meta_file = f.with_suffix(".json")
        creator = "System"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as mf:
                    data = json.load(mf)
                    creator = data.get("created_by", "System")
            except Exception:
                pass

        backups.append({
            "filename": f.name,
            "path": str(f),
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "size_bytes": size_bytes,
            "created_at": mtime,
            "creator": creator
        })
    return backups

def restore_backup(backup_filename: str, admin_email: str = "admin@agriai.org") -> Tuple[bool, str]:
    """
    Restore the SQLite database from a valid backup file with safety rollback protection.
    Returns: (success, message)
    """
    get_backup_dir()
    clean_name = os.path.basename(backup_filename.strip())
    backup_path = BACKUPS_DIR / clean_name
    
    if not backup_path.exists():
        return False, f"Backup file '{clean_name}' does not exist."

    # Validate file integrity: check for SQLite header
    try:
        with open(backup_path, "rb") as bf:
            header = bf.read(16)
            if not header.startswith(b"SQLite format 3"):
                return False, "Corrupt or invalid backup file: missing SQLite signature."
    except Exception as e:
        return False, f"Failed reading backup file: {e}"

    db_file = DEFAULT_SQLITE_PATH
    pre_restore_safety = BACKUPS_DIR / f"pre_restore_safety_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    try:
        # 1. Take safety snapshot of current DB
        if db_file.exists():
            try:
                s_conn = sqlite3.connect(str(db_file))
                d_conn = sqlite3.connect(str(pre_restore_safety))
                s_conn.backup(d_conn)
                d_conn.close()
                s_conn.close()
            except Exception:
                shutil.copy2(db_file, pre_restore_safety)

        # 2. Restore active DB with selected backup using SQLite backup API (safe with open WAL on Windows)
        s_conn = sqlite3.connect(str(backup_path))
        d_conn = sqlite3.connect(str(db_file))
        s_conn.backup(d_conn)
        d_conn.close()
        s_conn.close()
        
        log_admin_action(admin_email, "RESTORE_BACKUP", clean_name, f"Safety snapshot saved to {pre_restore_safety.name}")
        log_database_event("BACKUP_RESTORED", "SUCCESS", f"Restored from {clean_name}")
        return True, f"Database restored successfully from '{clean_name}'. Previous state saved to '{pre_restore_safety.name}'."

    except Exception as e:
        # Rollback if failure
        if pre_restore_safety.exists():
            try:
                s_conn = sqlite3.connect(str(pre_restore_safety))
                d_conn = sqlite3.connect(str(db_file))
                s_conn.backup(d_conn)
                d_conn.close()
                s_conn.close()
            except Exception:
                pass
        logger.error(f"Restore failed: {e}")
        log_database_event("RESTORE_ERROR", "ERROR", str(e))
        return False, f"Restore failed (rolled back to original): {str(e)}"

def get_backup_bytes(backup_filename: str) -> Optional[bytes]:
    """Read backup file bytes for browser download."""
    clean_name = os.path.basename(backup_filename.strip())
    backup_path = BACKUPS_DIR / clean_name
    if backup_path.exists():
        with open(backup_path, "rb") as f:
            return f.read()
    return None

def trigger_auto_backup_demo() -> Tuple[bool, str]:
    """
    Simulated Daily Auto-Backup:
    Checks if a backup was generated today; if not, triggers an automatic snapshot.
    """
    backups = list_available_backups()
    today_str = datetime.now().strftime("%Y%m%d")
    for b in backups:
        if today_str in b["filename"]:
            return True, f"Daily backup already present for today ({b['filename']})."
    
    success, msg, name = create_manual_backup("auto_scheduler@agriai.org")
    return success, f"Automatic daily backup generated: {name}"

def get_backup_storage_stats() -> Dict:
    """Return storage metrics for database backups."""
    backups = list_available_backups()
    total_size = sum(b["size_bytes"] for b in backups)
    last_backup = backups[0]["created_at"] if backups else "Never"
    
    return {
        "count": len(backups),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "total_size_bytes": total_size,
        "last_backup_date": last_backup
    }
