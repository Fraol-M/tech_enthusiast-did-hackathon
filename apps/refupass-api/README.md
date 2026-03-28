# RefuPass API

FastAPI backend for the RefuPass food-aid prototype.

## What it handles

- local role-based staff login for `admin` and `aid_worker`
- beneficiary, household, aid-cycle, eligibility, redemption, and grievance state
- issuance handoff metadata for the existing `Inji Web` holder flow
- aid-worker verification orchestration with a pluggable `Inji Verify` client

## Quick start

```powershell
cd apps\refupass-api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

The app seeds demo users and beneficiaries on first run.

## Demo credentials

- `admin` / `admin123`
- `aidworker` / `worker123`

## Environment

Copy `.env.example` to `.env` and adjust as needed.

For the full local demo, keep these values:

```env
DATABASE_URL=sqlite:///./refupass.db
INJI_VERIFY_MODE=passthrough
INJI_VERIFY_API_URL=http://localhost:18080/v1/verify
INJI_WEB_URL=http://localhost:3001
INJI_VERIFY_UI_URL=http://localhost:13000
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:4173
DEMO_BENEFICIARY_SUBJECT=5860356276
```

`DATABASE_URL` defaults to SQLite for local development, but the SQL seed file in [`sql/postgres_init.sql`](./sql/postgres_init.sql) shows the intended Postgres schema for hosted deployment.

## Tests

Run the backend suite from this folder:

```powershell
.venv\Scripts\Activate.ps1
python -m pytest
```

The tests use an isolated temporary SQLite database per test run, so they do not touch your working `refupass.db`.
