# AgriAI Platform — System Administrator Guide

## 1. Role & Access Management
The platform provides role-based access control (RBAC):
- **Farmer / General User:** Can run predictions, view personal history, fetch weather, and download personal reports.
- **Agronomist:** Can review community predictions, add custom advisory recommendations, and validate diagnoses.
- **System Administrator:** Full access to user management, database inspection, audit logs, system telemetry, and model registry.

---

## 2. Managing Users via Admin Portal
1. Log in with administrative credentials.
2. In the sidebar, select **Admin Portal**.
3. View registered user accounts, active sessions, and status.
4. Administrative actions:
   - Promote user to Agronomist or Administrator.
   - Deactivate compromised accounts.
   - Reset user passwords.

---

## 3. Database Maintenance & Backups
The database uses SQLite located at `database/predictions.db`.

### Automated Daily Backups
The system automatically backs up the database to `backups/` every 24 hours.
To perform an immediate manual backup:
```bash
python -c "from database.db_handler import backup_db; backup_db()"
```

### Restoring from Backup
```bash
cp backups/predictions_backup_YYYYMMDD.db database/predictions.db
```

---

## 4. System Telemetry & Logs
Logs are recorded in `logs/agriai.log` with structured log levels:
- `INFO`: Normal prediction requests and logins.
- `WARNING`: Failed login attempts, API rate limits.
- `ERROR`: Unhandled exceptions, database timeouts.
- `CRITICAL`: Corrupted model files or filesystem failures.

Log rotation is preconfigured at 10 MB per file, retaining 5 historical archives.
