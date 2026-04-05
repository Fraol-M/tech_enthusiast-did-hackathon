# RefuProof Web

React frontend for the RefuProof platform.

## Surfaces

- `Platform dashboard`
  - register NGO workspaces
  - register shared people
  - review the shared registry
- `Admin dashboard`
  - search shared people
  - create NGO program enrollments
  - eligibility decisions
  - issuance handoff
  - printable fallback pass
  - redemption and grievance overview
- `Aid worker console`
  - credential upload or paste
  - worker-facing verification result
  - confirm delivery
  - open grievance

## Run

```powershell
cd apps\refupass-web
npm install
npm run dev
```

Set `VITE_REFUPASS_API_URL` if the API is not running on `http://localhost:8000`.
