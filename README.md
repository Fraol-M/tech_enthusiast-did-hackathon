# RefuPass

RefuPass is a humanitarian aid access prototype for refugee-serving organizations. It verifies a beneficiary through `eSignet`, stores that person in a shared registry, lets NGOs enroll them into aid programs, issues a `RefuPass-native PDF/QR pass`, and lets aid workers verify and redeem that pass at distribution time.

This repository contains the working RefuPass applications plus the MOSIP/eSignet experiment stacks used for identity verification.

## Why We Moved Away From Inji For The Main Flow

The first version of this project tried to use the full `Inji Web -> Mimoto -> Certify -> eSignet` issuance path for the beneficiary journey. That path proved too brittle for this use case because:

- hosted and local eSignet client registration/callback handling was fragile
- the browser wallet flow was hard to keep stable across local and deployed environments
- the real operational need was a pass that can be printed, shared as PDF, and later supported in low-connectivity field settings

So the current product path is:

1. verify identity through `eSignet`
2. enroll the person in RefuPass
3. issue a `RefuPass-native PDF/QR pass`
4. verify and redeem that pass in RefuPass

The old Inji-related files are still in `Experiments/` for research and future interoperability work, but they are no longer the main beneficiary path.

## Current Product Flow

1. A platform operator starts identity verification for a person in RefuPass.
2. The person completes verification through `eSignet`.
3. RefuPass adds the verified person to the shared registry.
4. An NGO admin enrolls that person into an NGO program.
5. The NGO marks the person as eligible.
6. RefuPass generates a secure beneficiary pass as a PDF with an embedded QR code.
7. The beneficiary presents the PDF or mobile pass image at the distribution point.
8. An aid worker uploads the pass in RefuPass, verifies it, and records redemption.

## Repo Layout

- `apps/refupass-api`
  - FastAPI backend
  - JWT auth
  - eSignet verification integration
  - RefuPass-native pass issuance and worker verification
- `apps/refupass-web`
  - React + Vite frontend
  - platform admin, NGO admin, and aid worker flows
- `Experiments/esignet-compose`
  - local eSignet + mock identity system
  - Docker Compose stack used by RefuPass identity verification
- `Experiments/inji-certify`
  - older/experimental Inji issuance research
- `Experiments/inji-verify-compose`
  - older/experimental verification research

## Free And Open-Source Tooling

The documented setup below uses only free/open-source tools:

- `Git`
- `Python 3.12+`
- `Node.js 20+` and `npm`
- `Docker Engine` + Docker Compose plugin
- `nginx` for deployment examples
- `PowerShell 7` (`pwsh`) on Linux only if you want to run the provided `.ps1` helper

Notes:

- On Linux, install Docker Engine directly.
- On Windows, the most reproducible open-source path is to use `WSL2 Ubuntu` with Docker Engine inside WSL for the eSignet stack, while running the frontend/backend either from Windows or WSL.

## Environment Variables

### API

Copy:

```bash
cp apps/refupass-api/.env.example apps/refupass-api/.env
```

Key variables:

- `DATABASE_URL`
  - SQLite for local quick start
  - Neon/Postgres or another Postgres URL for deployment
- `ALLOWED_ORIGINS`
  - comma-separated frontend origins
- `ESIGNET_UI_URL`
  - browser-facing eSignet UI host
- `ESIGNET_API_URL`
  - backend-facing eSignet API host
- `ESIGNET_CALLBACK_URL`
  - RefuPass callback URL for eSignet verification
- `PASS_SIGNING_SECRET`
  - used to sign RefuPass pass payloads
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

They are not required for the main RefuPass-native pass flow.

### Web

Copy:

```bash
cp apps/refupass-web/.env.example apps/refupass-web/.env
```

Required variable:

- `VITE_REFUPASS_API_URL`

## Local Setup On Linux

### 1. Start eSignet

```bash
cd Experiments/esignet-compose
docker compose up -d
```

Check health:

```bash
curl http://127.0.0.1:8088/v1/esignet/actuator/health
```

Expected result:

```json
{"status":"UP"}
```

### 2. Seed demo identities / eSignet flow

If `pwsh` is installed:

```bash
cd Experiments/esignet-compose
pwsh -File ./setup-demo-flow.ps1
```

This helper is mainly used to prepare the mock identity personas and demo flow. RefuPass itself dynamically creates the verification client during person verification.

### 3. Run the API

```bash
cd apps/refupass-api
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Run the frontend

```bash
cd apps/refupass-web
npm install
npm run dev
```

### 5. Open the app

- frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- eSignet UI: `http://localhost:3000`

## Local Setup On Windows

### 1. Start eSignet

Use Docker Engine in WSL2 Ubuntu or your existing local Docker setup:

```powershell
cd Experiments\esignet-compose
docker compose up -d
```

### 2. Seed demo identities / eSignet flow

```powershell
cd Experiments\esignet-compose
powershell -ExecutionPolicy Bypass -File .\setup-demo-flow.ps1
```

### 3. Run the API

```powershell
cd apps\refupass-api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Run the frontend

```powershell
cd apps\refupass-web
npm install
npm run dev
```

### 5. Open the app

- frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- eSignet UI: `http://localhost:3000`

## Demo Accounts

The platform admin is seeded from the API `.env`:

- `PLATFORM_ADMIN_USERNAME`
- `PLATFORM_ADMIN_PASSWORD`

Default example values:

- `admin` / `admin123`

Seeded NGO/worker demo accounts may also exist depending on your DB state and seed data:

- NGO admin: `ngoadmin` / `ngo123`
- aid worker: `aidworker` / `worker123`

## Docker / Compose

The repo already includes a Compose file for the identity dependency stack:

- [`Experiments/esignet-compose/docker-compose.yml`](./Experiments/esignet-compose/docker-compose.yml)

This stack includes:

- Postgres for eSignet
- Redis
- mock identity system
- eSignet API
- eSignet UI

You can run it with no extra container configuration:

```bash
cd Experiments/esignet-compose
docker compose up -d
```

RefuPass API and web currently run natively rather than through a top-level Docker Compose file. That keeps the local development loop simpler while the product flow evolves.

## Deployment Notes

The working public deployment pattern used in this project is:

- frontend on Vercel
- RefuPass API on a Linux server
- eSignet on the same Linux server via Docker Compose

Example production hostnames:

- frontend: `https://refuproof.birukabza.me`
- API: `https://api.birukabza.me`
- eSignet: `https://auth-esignet.birukabza.me`

## Reproducible Deployment Notes

For Linux deployment:

- run the API under `systemd`
- run the eSignet Docker Compose stack through a `systemd` wrapper
- place `nginx` in front of both services

Typical service commands:

```bash
systemctl restart refupass-api
systemctl restart refupass-esignet
```

## Offline Support Roadmap

The current deployed implementation assumes network connectivity for:

- platform identity verification
- NGO enrollment
- pass issuance
- worker redemption submission to the central API

The intended offline-capable design for field distribution is:

1. Before field deployment, the distribution site downloads:
   - the current beneficiary roster
   - current-cycle eligibility data
   - signed pass verification keys
   - open/pass-ready records for the site
2. At the distribution site, all worker devices connect to a `local field node` over a local Wi-Fi/LAN.
3. Workers verify and redeem passes against that local node, not directly against the cloud.
4. The local node keeps the authoritative site-level redemption ledger during the offline window.
5. When connectivity returns, the local node syncs the site ledger back to the central RefuPass server.

### Why a local network matters

If many aid workers operate fully independently offline, duplicate redemption risk increases because each device only knows its own local state. To prevent that, the recommended model is:

- one site-level local server or laptop
- multiple worker devices on the same local network
- all redemption checks go through that site-local ledger

That lets all workers see the same up-to-date redemption state even without internet.

## How Duplicate Redemption Would Be Prevented Offline

Planned approach:

1. Each pass has a unique signed identifier.
2. The local field node stores every verification and redemption event for the active aid cycle.
3. When a worker attempts redemption, the local node checks:
   - pass authenticity
   - cycle validity
   - site/program match
   - whether redemption already exists
4. The local node returns either:
   - `valid / redeemable`
   - `already redeemed`
   - `invalid / expired / unrecognized`

If multiple workers are connected to the same local node, duplicates can be blocked immediately.

## How Sync Would Work Later

Planned sync model:

- every offline verification/redemption gets a unique event ID
- the local node stores timestamped events in an append-only log
- when internet returns, the local node pushes unsynced events to the central API
- the central API marks those events as received and updates the main ledger
- conflict rules prefer:
  - first valid redemption per enrollment/cycle
  - later duplicates marked as duplicate attempts, not successful deliveries

This means offline field work remains operational, while later synchronization preserves a single central record.

## Recommended Real-World Field Topology

For multi-worker distribution sites, the recommended pattern is:

- `central RefuPass server` for normal online operations
- `site-local field node` at the distribution point
- `aid worker tablets/laptops/phones` connected over local network to that field node

That is the most practical way to support offline operation and prevent duplicate redemption when many workers are active at the same site.

## What Is Tested

Backend:

```bash
cd apps/refupass-api
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PLATFORM_ADMIN_USERNAME=admin PLATFORM_ADMIN_PASSWORD=admin123 PLATFORM_ADMIN_DISPLAY_NAME="RefuPass Platform Admin" pytest
```

Frontend:

```bash
cd apps/refupass-web
npm run build
```

## Current Main Screens

- platform admin
  - verify person through eSignet
  - register NGOs
- NGO admin
  - search shared registry
  - create program enrollments
  - set eligibility
  - issue RefuPass pass
- aid worker
  - upload RefuPass PDF or mobile pass image
  - verify pass
  - redeem delivery
  - open grievance

## Known Boundaries

- The main beneficiary flow no longer depends on Inji wallet issuance.
- The current offline model is a planned architecture, not a fully implemented distributed sync system yet.
- The experimental Inji and Verify stacks remain in the repo for future interoperability work, but they are not the primary product path.
