# RefuPass Web

React frontend for the RefuPass prototype.

## Surfaces

- `Admin dashboard`
  - beneficiary search and review
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
