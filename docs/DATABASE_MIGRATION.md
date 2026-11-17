# AgriAI Advisor - Database Migration Guide (SQLite to PostgreSQL)

## Overview

The AgriAI Advisor platform database layer has been migrated from local SQLite to production-grade PostgreSQL using **SQLAlchemy 2.x** and **psycopg** (psycopg 3).

The new architecture provides:
1. **Multi-Engine Support**: Native PostgreSQL for production with seamless SQLite support for local offline development.
2. **Serverless Compatibility**: Optimized for stateless, ephemeral environments like Vercel with `NullPool` to prevent connection exhaustion.
3. **Strict Fallback Prevention**: Never silently falls back to SQLite when PostgreSQL fails, raising explicit errors during startup.
4. **Idempotent Migrations**: Database initialization and table creation (`Base.metadata.create_all(checkfirst=True)`) safely run on every deployment without destroying or overwriting existing user data.
5. **Alembic Versioning**: Version-controlled migrations in `alembic/` for tracked, reproducible schema evolution.
6. **Data Preservation Utility**: Automated script to copy all existing historical records, users, and configurations from SQLite to PostgreSQL.

---

## Database Architecture & Tables

All 7 core platform tables and their composite performance indexes are mapped via SQLAlchemy 2.x declarative models in [`app/models.py`](file:///app/models.py):

| Table Name | Primary Key | Description | Cascades & Foreign Keys |
| :--- | :--- | :--- | :--- |
| `users` | `id` (SERIAL / Auto-increment) | User profiles, bcrypt credentials, roles (`admin`, `farmer`), and agricultural preferences. | Unique on `email` |
| `prediction_history` | `id` (SERIAL / Auto-increment) | Meteorological telemetry, crop, predicted pests, risk levels, and advisory outputs. | `user_id` -> `users.id` (ON DELETE SET NULL) |
| `contact_queries` | `id` (SERIAL / Auto-increment) | Support inquiries and feedback with status tracking. | Standalone |
| `user_preferences` | `user_id` (Integer) | Farmer UI preferences (theme, language, alerts, privacy). | `user_id` -> `users.id` (ON DELETE CASCADE) |
| `account_activity` | `id` (SERIAL / Auto-increment) | Audit logs and user action history. | `user_id` -> `users.id` (ON DELETE CASCADE) |
| `user_sessions` | `token` (String) | Persistent session tokens for "Remember Me" authentication. | `user_id` -> `users.id` (ON DELETE CASCADE) |
| `password_reset_tokens` | `token` (String) | Single-use time-limited password reset tokens. | `user_id` -> `users.id` (ON DELETE CASCADE) |

---

## Connection Configuration

The application reads the connection string from the `DATABASE_URL` environment variable.

### 1. PostgreSQL (Production Standard)
```bash
# Standard URI (using psycopg v3 driver):
DATABASE_URL=postgresql://agri_user:secure_password@db-host:5432/agriai_db

# Managed cloud providers with SSL (Neon, Supabase, Vercel Postgres, AWS RDS):
DATABASE_URL=postgresql://agri_user:secure_password@ep-sample.us-east-1.aws.neon.tech/agriai_db?sslmode=require
```

### 2. SQLite (Local Development)
```bash
# Relative / project-local path:
DATABASE_URL=sqlite:///database/predictions.db

# In-memory testing:
DATABASE_URL=sqlite:///:memory:
```

---

## Migration Steps (Zero Data Loss)

### Step 1: Set Target PostgreSQL Connection
Export your PostgreSQL connection string:
```bash
export DATABASE_URL="postgresql://<user>:<password>@<host>:5432/<dbname>?sslmode=require"
```
*(On Windows PowerShell):*
```powershell
$env:DATABASE_URL="postgresql://<user>:<password>@<host>:5432/<dbname>?sslmode=require"
```

### Step 2: Initialize PostgreSQL Schema via Alembic
Run version-controlled Alembic migrations to construct the PostgreSQL schema:
```bash
alembic upgrade head
```

### Step 3: Transfer Existing Records from SQLite
To copy all existing registered users, prediction history, queries, and preferences from `database/predictions.db` into PostgreSQL without duplicate collisions:
```bash
python scripts/migrate_to_postgres.py
```

The script will:
- Check for existing tables and create any missing structures.
- Stream existing SQLite user accounts, converting salts and bcrypt hashes accurately.
- Preserve all prediction history entries and foreign key mappings.
- Re-index and verify total row counts.

### Step 4: Verify Migration Health
Run the automated migration verification suite:
```bash
python -m pytest tests/test_postgres_migration.py -v
```

All 10 migration tests should pass:
1. PostgreSQL connection & driver loading
2. Schema & index initialization
3. Public user registration role constraint
4. Duplicate email rejection
5. Login & JWT generation
6. JWT signature & claims verification
7. Unauthorized profile access (401 & 403 isolation)
8. Unauthorized history access (401 & 403 isolation)
9. Prediction history persistence & deduplication
10. Admin access control & multi-tenant isolation
