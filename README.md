# RefuProof

RefuProof is a humanitarian aid access prototype for refugee-serving organizations. It verifies a beneficiary through `eSignet`, stores the verified person in a shared registry, lets NGOs enroll them into aid programs, issues a secure `PDF/QR pass`, and lets aid workers verify and redeem that pass at distribution time.

## Why We Moved Away From Inji

The first version of this project tried to use the full `Inji Web -> Mimoto -> Certify -> eSignet` issuance path. We moved away from that for the main flow because it was too brittle for this use case:

- callback/client setup was fragile across local and hosted environments
- browser wallet behavior was harder to keep stable for demos and field-style usage
- the operational need was a printable, shareable pass that can later work in low-connectivity settings

The current main flow is:

1. verify identity through `eSignet`
2. add the verified person to RefuProof
3. enroll them into an NGO program
4. issue a `RefuProof-native PDF/QR pass`
5. verify and redeem the pass in RefuProof

The older Inji-related work remains in `Experiments/` for research and future interoperability, but it is not the main beneficiary path.

## Repository Layout

- `apps/refupass-api` - FastAPI backend, JWT auth, eSignet integration, pass issuance and worker verification
- `apps/refupass-web` - React + Vite frontend for platform admin, NGO admin, and aid worker flows
- `Experiments/esignet-compose` - Docker Compose stack for local eSignet, mock identity system, Postgres, and Redis
- `Experiments/inji-certify` - older Inji issuance experiments
- `Experiments/inji-verify-compose` - older verification experiments

## Free And Open-Source Tooling

Everything below uses free/open-source tools only:

- `Git`
- `Python 3.12+`
- `Node.js 20+` and `npm`
- `Docker Engine` + Docker Compose plugin
- `PowerShell 7` (`pwsh`) on Linux only if you want to run the provided `.ps1` helper

## Required Environment Variables

### API

Copy `apps/refupass-api/.env.example` to `apps/refupass-api/.env`.

Required variables:

- `DATABASE_URL`
- `ALLOWED_ORIGINS`
- `ESIGNET_UI_URL`
- `ESIGNET_API_URL`
- `ESIGNET_CALLBACK_URL`
- `ESIGNET_CLIENT_NAME`
- `ESIGNET_CLIENT_LOGO_URL`
- `PASS_SIGNING_SECRET`
- `PLATFORM_ADMIN_USERNAME`
- `PLATFORM_ADMIN_PASSWORD`
- `PLATFORM_ADMIN_DISPLAY_NAME`
- `JWT_ACCESS_SECRET_KEY`
- `JWT_REFRESH_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_ACCESS_TOKEN_TTL_MINUTES`
- `JWT_REFRESH_TOKEN_TTL_DAYS`
- `JWT_ISSUER`

Optional experimental variables still present in the codebase:

- `INJI_VERIFY_MODE`
- `INJI_VERIFY_API_URL`
- `INJI_WEB_URL`
- `INJI_VERIFY_UI_URL`

### Web

Copy `apps/refupass-web/.env.example` to `apps/refupass-web/.env`.

Required variable:

- `VITE_REFUPASS_API_URL`

## Docker / Compose Dependency Stack

The repo already includes a working Docker Compose file for the identity dependency stack:

- [Experiments/esignet-compose/docker-compose.yml](C:/Users/biruk/OneDrive/Documents/programming/Hackatons/RefuPass/Experiments/esignet-compose/docker-compose.yml)

It starts:

- Postgres for eSignet
- Redis
- mock identity system
- eSignet API
- eSignet UI

Run it with no extra container configuration:

```bash
cd Experiments/esignet-compose
docker compose up -d
```

Health check:

```bash
curl http://127.0.0.1:8088/v1/esignet/actuator/health
```

Expected result:

```json
{"status":"UP"}
```

Optional helper to seed demo identities:

```bash
cd Experiments/esignet-compose
pwsh -File ./setup-demo-flow.ps1
```

On Windows:

```powershell
cd Experiments\esignet-compose
powershell -ExecutionPolicy Bypass -File .\setup-demo-flow.ps1
```

## Run Locally On Linux

1. Start eSignet:

```bash
cd Experiments/esignet-compose
docker compose up -d
```

2. Start the API:

```bash
cd apps/refupass-api
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

3. Start the frontend:

```bash
cd apps/refupass-web
cp .env.example .env
npm install
npm run dev
```

4. Open:

- frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- eSignet UI: `http://localhost:3000`

## Run Locally On Windows

1. Start eSignet:

```powershell
cd Experiments\esignet-compose
docker compose up -d
```

2. Start the API:

```powershell
cd apps\refupass-api
copy .env.example .env
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

3. Start the frontend:

```powershell
cd apps\refupass-web
copy .env.example .env
npm install
npm run dev
```

4. Open:

- frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- eSignet UI: `http://localhost:3000`

## Demo Accounts

Platform admin comes from the API `.env`:

- `PLATFORM_ADMIN_USERNAME`
- `PLATFORM_ADMIN_PASSWORD`

Default example values:

- `admin / admin123`

Seeded demo accounts may also exist depending on DB state:

- NGO admin: `ngoadmin / ngo123`
- aid worker: `aidworker / worker123`

## What The Prototype Does

1. Platform admin starts identity verification
2. Beneficiary verifies through `eSignet`
3. RefuProof adds the person to the shared registry
4. NGO admin enrolls the person into a program
5. NGO admin marks them eligible
6. RefuProof issues a `PDF/QR pass`
7. Aid worker verifies and redeems that pass

## Offline Support Direction

The current hosted prototype is online-first, but the intended field model is:

- one `local field node` at the distribution site
- multiple aid worker devices connected to it over local Wi-Fi/LAN
- all verifications and redemptions checked against the same local site ledger
- later sync back to the central RefuProof server when connectivity returns

Why this matters:

- it supports low-connectivity sites
- it prevents duplicate redemption across many aid workers at the same site
- it gives one authoritative site-level record during offline operation

## Deployment Shape Used In Practice

- frontend on Vercel
- RefuProof API on a Linux server
- eSignet on the same Linux server via Docker Compose

Example hostnames used in this project:

- frontend: `https://refuproof.birukabza.me`
- API: `https://api.birukabza.me`
- eSignet: `https://auth-esignet.birukabza.me`

## Verification Commands

Backend tests:

```bash
cd apps/refupass-api
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PLATFORM_ADMIN_USERNAME=admin PLATFORM_ADMIN_PASSWORD=admin123 PLATFORM_ADMIN_DISPLAY_NAME="RefuProof Platform Admin" pytest
```

Frontend build:

```bash
cd apps/refupass-web
npm run build
```

## Current Boundaries

- the main beneficiary flow no longer depends on Inji wallet issuance
- the offline model is planned architecture, not a fully implemented sync system yet
- the Inji experiment folders remain for future interoperability work, not the primary product path
