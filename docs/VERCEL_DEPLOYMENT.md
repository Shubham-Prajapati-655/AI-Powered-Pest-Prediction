# AgriAI Advisor - Vercel Serverless Deployment Guide

## Overview

This guide details the deployment of the production FastAPI REST API to **Vercel** as a Python Serverless Function with an external PostgreSQL database (e.g. Neon, Supabase, or AWS RDS).

---

## Key Serverless Considerations

1. **Stateless Execution**: Vercel executes functions in ephemeral AWS Lambda environments. Local SQLite files or local disk writes to the application directory are read-only and ephemeral.
2. **Serverless Connection Pooling**: PostgreSQL connections must not exceed connection limits during concurrent invocations. AgriAI automatically uses SQLAlchemy's `NullPool` when `VERCEL=1` or `APP_ENV=production` is detected, establishing quick connections per request and tearing them down immediately upon response completion.
3. **No Module-Level Database Inits**: The FastAPI `lifespan` handler boots connections and verifies models safely during cold starts rather than on file import.
4. **CORS Hardening**: Access is restricted strictly to the configured `FRONTEND_ORIGIN` rather than insecure wildcards.

---

## File Structure for Vercel

```
AI-Powered Pest Prediction/
├── api/
│   └── index.py             # Vercel entrypoint exposing 'app'
├── vercel.json              # Route mapping and build configuration
├── requirements.txt         # Core dependencies including psycopg, SQLAlchemy, PyJWT
├── app/
│   ├── config.py            # Environment validation & secrets verification
│   ├── database.py          # SQLAlchemy 2.x PostgreSQL/SQLite layer
│   ├── models.py            # Declarative database models
│   └── security.py          # JWT generation & password hashing
└── src/
    └── api.py               # FastAPI application with protected endpoints
```

---

## Step-by-Step Deployment

### 1. Provision a PostgreSQL Database
Create a serverless PostgreSQL instance on:
- [Neon Serverless Postgres](https://neon.tech/) (Recommended for Vercel)
- [Supabase](https://supabase.com/)
- [Vercel Postgres](https://vercel.com/storage/postgres)

Copy the connection string (with SSL mode required):
```
postgresql://agri_user:your_password@ep-cold-shadow.us-east-2.aws.neon.tech/agriai?sslmode=require
```

### 2. Configure Environment Variables in Vercel
In your Vercel Project Dashboard (`Settings` -> `Environment Variables`), configure:

| Variable | Recommended Production Value | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `production` | Enables strict production validations. |
| `DATABASE_URL` | `postgresql://...` | Connection URI to your managed PostgreSQL database. |
| `SECRET_KEY` | *(Random 64-char hex)* | Generated via `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_SECRET_KEY` | *(Random 64-char hex)* | Separate key used for signing user JWT tokens. |
| `FRONTEND_ORIGIN` | `https://your-frontend.vercel.app` | Allowed CORS origin domain(s). |
| `ADMIN_EMAIL` | `admin@agriai.org` | Initial administrator account. |
| `ADMIN_DEFAULT_PASSWORD` | `YourSecureAdmin@2026!` | Initial administrator password. |
| `JWT_EXPIRATION_HOURS` | `24` | Token lifespan. |

### 3. Deploy via Vercel CLI or GitHub
Using the Vercel CLI:
```bash
npm install -g vercel
vercel login
vercel --prod
```
Or connect your GitHub repository directly in the Vercel dashboard. Vercel automatically detects `vercel.json` and builds the `@vercel/python` serverless function.

---

## Production API Endpoint Summary

All responses strip sensitive password hashes and internal salts.

### Public Endpoints:
- `GET  /health` - Healthcheck and ML model readiness probe.
- `POST /predict` - Inference endpoint with Top-3 probabilities and IPM advisory.
- `POST /advisory` - Agronomic recommendations by crop and pest.
- `POST /register` - User registration (strictly forces `farmer` role).
- `POST /login` - Issues JWT Bearer access token.
- `GET  /crops` - Supported crop taxonomy and pest species.
- `GET  /weather` - Meteorological proxy.

### Protected Endpoints (Requires `Authorization: Bearer <token>`):
- `GET  /profile` - Authenticated user account details (enforces user isolation).
- `POST /profile` - Profile lookup.
- `GET  /history` - Historical prediction records (enforces user isolation).
- `POST /history` - Query filtered prediction logs.
- `POST /report` - Generate and download PDF advisory reports.

### Admin-Only Endpoints (Requires Admin Role JWT):
- `GET  /admin/users` - View and manage platform user directory.
