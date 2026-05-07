# RefuProof API

FastAPI backend for the RefuProof platform.

## What it handles

- local role-based login for `platform_admin`, `ngo_admin`, and `aid_worker`
- shared people, households, NGO programs, enrollments, aid cycles, redemptions, and grievances
- RefuProof-native pass issuance for verified, eligible beneficiaries
- aid-worker verification orchestration, with a legacy pluggable `Inji Verify` client still available for future interoperability work

## Quick start

```powershell
cd apps\refupass-api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

The app seeds demo users, shared people, and NGO enrollments on first run.

## Demo credentials

- `admin` / `admin123`
- `ngoadmin` / `ngo123`
- `aidworker` / `worker123`

## Environment

Copy `.env.example` to `.env` and adjust as needed.

For the full local demo, keep these values and add the remaining secrets from `.env.example`:

```env
DATABASE_URL=sqlite:///./refupass.db
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:4173
ESIGNET_UI_URL=http://localhost:3000
ESIGNET_API_URL=http://localhost:8088
ESIGNET_CALLBACK_URL=http://127.0.0.1:8000/platform/identity/esignet/callback
DEMO_BENEFICIARY_SUBJECT=5860356276
```

The `INJI_*` variables in `.env.example` are legacy compatibility settings and are not required for the current RefuProof-native pass flow.

## Tests

Run the backend suite from this folder:

```powershell
.venv\Scripts\Activate.ps1
python -m pytest
```

The tests use an isolated temporary SQLite database per test run, so they do not touch your working `refupass.db`.

## Local eSignet demo personas

If you are testing `Verify with eSignet`, run the local helper first:

```powershell
cd ..\esignet-compose
powershell -ExecutionPolicy Bypass -File .\setup-demo-flow.ps1
```

Available mock identities:

- `Amina Hassan` -> `5860356276`
- `Sami Bekele` -> `5555444433`
- `Nura Ali` -> `7777888899`

Use `Nura Ali` in the RefuProof Web platform UI when you want to test adding a new person through eSignet without colliding with the two people already seeded in RefuProof.
