# RefuPass

RefuPass is a food-aid access prototype built on top of the MOSIP demo stack already proven in this repo.

## Repo layout

- `Experiments/`
  - working MOSIP integration layer
  - local `eSignet`
  - `Inji Certify`
  - `Inji Verify`
- `apps/refupass-api`
  - FastAPI backend for NGO admin and aid-worker operations
- `apps/refupass-web`
  - React frontend with separate admin and aid-worker surfaces

## What is implemented

- seeded beneficiary, household, aid-cycle, eligibility, redemption, and grievance models
- local role-based login for `admin` and `aidworker`
- issuance handoff metadata for the existing `Inji Web` holder flow
- worker verification orchestration through a pluggable `Inji Verify` client
- RefuPass-specific `RefuPassFoodAidCredential` scaffolding in the Certify/Mimoto demo config

## Run the new apps

### API

```powershell
cd apps\refupass-api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Demo users:

- `admin` / `admin123`
- `aidworker` / `worker123`

### Web

```powershell
cd apps\refupass-web
npm install
npm run dev
```

The web app expects the API at `http://localhost:8000` by default.

## Notes

- The beneficiary-facing holder remains `Inji Web` for v1.
- The aid worker uses the new RefuPass worker UI instead of the raw Verify UI.
- The current `Inji Verify` integration defaults to `stub` mode in the API for local development, but the client is structured to call the real verify service when `INJI_VERIFY_MODE=passthrough`.
