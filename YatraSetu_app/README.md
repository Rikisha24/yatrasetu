# YatraSetu: AI Agent for Travel Disruption Recovery

DevHack 2026 · PS 4.1 · Tourism, Travel & Creative Economy

An agent that detects a travel disruption, finds every booking it affects, searches alternatives inside the traveller's own rules, and produces a recovery itinerary the traveller approves. Nothing is booked without approval.

## Tech stack

| Layer | Used |
|---|---|
| Frontend | React, Tailwind CSS, installable PWA (manifest + service worker) |
| Backend | Python, FastAPI |
| Database | SQLite (saved profile, session metrics) |
| AI | Optional LLM hook (any OpenAI-compatible API). Explains only; never decides |
| Travel data | Mock JSON feeds (production: airline/NDC, rail and hotel APIs) |
| Alerts, payments | Planned: WhatsApp/SMS, payment gateway (booking is a sandbox) |

## Run it

Requirements: Python 3.10+ (Node is only needed to rebuild the frontend; the built app is included in `backend/static`).

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Open http://localhost:8000. Add `?fast=1` to the URL to remove the narration pauses.

### Rebuild the frontend (optional)

```bash
cd frontend
npm install
npm run build        # writes to ../backend/static
```

For live development run `npm run dev` (it proxies `/api` to port 8000).

### Optional: let an LLM write the explanations

```bash
export LLM_API_URL=https://<provider>/v1/chat/completions   # any OpenAI-compatible endpoint
export LLM_API_KEY=...        # stays on the server, never in the browser
export LLM_MODEL=<model name>
```

Only a masked payload is sent (see "What the AI sees" in the app). Every ₹ amount and time in the reply is checked against the data; if anything does not match, or the call fails, or the traveller has not given consent, the built-in template text is used. Without these variables the app runs fully offline.

## How it works

1. **Detect**: status-feed event (simulated by the button; push feeds in production).
2. **Impact**: bookings are a dependency chain (flight → hotel → meeting → return).
3. **Search + filter**: hard rules (budget, arrive-by, no night travel, seats for the group) remove options, each with a visible reason.
4. **Rank (plain code)**: weighted score of cost, arrival slack, comfort and seat availability. Weights come from the traveller's saved profile.
5. **Explain**: the AI (or template) writes the plain-language comparison; a validator checks every number.
6. **Approve → re-check → hold → confirm**, or roll back if any step fails.
7. **Track**: after confirmation the agent keeps watching and restarts the flow if the new trip breaks.

Also included: one-time **profile with editable defaults** (trip-level overrides never change it; stored in SQLite), a **help chatbot** that reads facts from data, drafted **refund / hotel / client messages**, a calendar `.ics` download, and per-session **metrics**.

## API (FastAPI, docs at `/docs`)

| Endpoint | Purpose |
|---|---|
| `POST /api/recover` | Detect → impact → search → rank → explain for a scenario |
| `POST /api/book` | Re-check, hold, confirm, or roll back (price-drift and failure simulation) |
| `POST /api/keep` | Accept "keep the original plan" |
| `POST /api/chat` | Rule-based help chatbot (can re-run the search with a trip-level override) |
| `POST /api/draft`, `POST /api/support` | Message drafts and the support hand-over summary |
| `GET/PUT/DELETE /api/profile` | Saved defaults, consent, delete-my-data |
| `GET /api/metrics`, `GET /api/ics` | Session metrics, calendar file |

## Privacy by design

- Only a masked payload (traveller 1, budget, times, prices) can reach a language model, and only if the traveller has consented.
- **Delete my data** removes the saved profile from SQLite.
- No card data, ID or phone number exists in the app.

## Honest limitations

- Travel data is mock. Production would use airline/NDC, railway and hotel APIs (IRCTC has no open booking API, so rail would hand off to the provider page).
- Booking is a sandbox. Production would use partner booking APIs plus a payment gateway.
- WhatsApp/SMS alerts and payments are not built yet.
- The "45 min → under 5 min" figure is a target from an assumed manual baseline, to be validated in a pilot. Times shown in the app are measured in the session and include deliberate pacing.

## Project layout

```
backend/   app/engine.py (decision engine) · app/main.py (API) · app/db.py (SQLite) · app/data.py (mock data) · static/ (built UI)
frontend/  Vite + React + Tailwind source
```
