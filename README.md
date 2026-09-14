# UX-Aware Workload Optimization in Cloud Environments

A real-time system that captures raw browser interaction signals (clicks, mouse
movement, hover/dwell time), detects behavioral signs of user frustration on
the backend, and simulates a corrective cloud-infrastructure response —
demonstrating how UX telemetry could drive autoscaling decisions instead of
relying solely on server-side load metrics.

## How it works

```
Browser (React)                FastAPI backend                 SQLite
─────────────────              ─────────────────                ───────
Click / mousemove /             Rule-based detection:            Structured
hover listeners        ──POST──▶  • rage_click            ──▶   log of every
(throttled, batched              • long_hover                    analyzed
every 3s)                        • cursor_thrash                 batch
                                       │
                                       ▼
                                Simulated action
                                (e.g. Azure scale-up,
                                help tooltip)
```

1. **Frontend** (`frontend/`) instruments the page with `click`, `mousemove`,
   `mouseenter`/`mouseleave`, and visibility listeners. Mouse movement is
   throttled to every 60ms and enriched with velocity, an EMA-smoothed
   velocity, and a rolling direction-change count (`dirChanges`). Every 3
   seconds, the buffered events are batched and POSTed to the backend.

2. **Backend** (`backend/main.py`) receives each batch and runs three
   independent heuristics:
   - **`rage_click`** — 3+ clicks on the same element within a 5-second
     sliding window.
   - **`long_hover`** — a single dwell event ≥3 seconds on an element.
   - **`cursor_thrash`** — detected two ways: (a) a strong single-batch
     signal (a high-velocity move plus a direction change), or (b) a
     cross-batch memory path that accumulates weaker evidence across
     multiple batches within an 8-second window. This means thrash
     detection still works even if a frontend never sends `dirChanges`.

3. **Action layer** — `rage_click` triggers a simulated Azure scale-up call
   (logged, not a real API call); `long_hover` triggers a simulated
   "enable help tooltip" action. Both run asynchronously via FastAPI
   background tasks so they never block the response to the frontend.
   `cursor_thrash` is currently detected but has **no action mapped** — a
   known, intentional gap (see [Known limitations](#known-limitations)).

4. **Analytics layer** — every analyzed batch (regardless of whether it
   contained a signal) is recorded to a local SQLite database
   (`ux_events.db`), separately from the live detection path, so a logging
   failure can never break a request. `analyze.py` reads this database with
   pandas and produces:
   - A printed summary: total batches, frustration rate, per-signal counts,
     per-user activity.
   - A saved chart (`signal_frequency.png`) showing signal frequency bucketed
     by minute.
   The backend also exposes a live `GET /api/stats` endpoint with the same
   aggregates.


## Screenshots

**Frontend detecting a live `cursor_thrash` signal:**
![Frontend demo panel](docs/screenshots/demo-panel.png)

**Backend logs showing real-time detection:**
![Backend logs](docs/screenshots/backend-logs.png)

**Signal frequency analysis (`analyze.py` output):**
![Signal frequency chart](docs/screenshots/signal_frequency.png)


## Project structure

```
backend/
  main.py              FastAPI app: event ingestion, detection, actions, analytics
  analyze.py           Offline analysis script (pandas + matplotlib)
  events_and_actions.log   Human-readable log (debugging)
  ux_events.db         SQLite analytics store (created automatically)

frontend/
  src/
    App.jsx            Entry component; renders UXEventCapture
    main.jsx           React root
    components/
      UXEventCapture.jsx                       Thin wrapper
      Frontend-UX_Event_Capture_Component.jsx   Actual capture logic
      Navbar.jsx, Footer.jsx
    pages/
      Home.jsx, Dashboard.jsx
    styles/
      index.css, custom.css
    utils/
      throttle.js
  .env                 VITE_BACKEND_URL, VITE_PROJECT_TOKEN
  vite.config.js
```

## Running it locally

**Backend:**
```bash
cd backend
pip install fastapi uvicorn requests pandas matplotlib
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend** (separate terminal):
```bash
cd frontend
npm install
npm run dev
```
Open the URL Vite prints (default `http://localhost:3000`). Make sure
`frontend/.env` points at the backend:
```
VITE_BACKEND_URL=http://127.0.0.1:8000/api/events
VITE_PROJECT_TOKEN=SOME_SHARED_TOKEN
```

Interact with the page — click rapidly, hover, move your mouse around — and
watch the backend terminal for `INCOMING_BATCH` / `ANALYZE` log lines.

**Run the analysis** (after some interaction, in a separate terminal from the
one running uvicorn):
```bash
cd backend
python analyze.py
```
This prints a summary and saves `signal_frequency.png`.

**Check live aggregate stats** while the server is running:
```
GET http://127.0.0.1:8000/api/stats
```

## Example output

```
Total batches analyzed : 60
Frustration detected   : 30 (50.0%)
Unique users            : 1

Signal breakdown:
  cursor_thrash   28
  rage_click      6
  long_hover      2
```

## Known limitations

- **`cursor_thrash` has no mapped corrective action.** It's detected,
  logged, and returned to the frontend, but `decide_action()` doesn't handle
  it — a deliberate scope decision for this demo, not a bug.
- **The Azure integration is fully simulated.** No real cloud API calls are
  made; the "scale-up" action only logs what a real call would look like.
- **Single-process, in-memory detection state.** Rage-click and thrash-memory
  tracking use in-process data structures (`deque`), so state resets on
  server restart and won't work across multiple backend instances without
  moving to a shared store (e.g. Redis).
- **No authentication beyond an optional shared token** (`x-project-token`),
  which is a no-op unless the `API_KEY` environment variable is set.

## Tech stack

React, Vite, FastAPI, Python, SQLite, pandas, matplotlib
