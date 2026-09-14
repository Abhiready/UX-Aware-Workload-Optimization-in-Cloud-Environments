# main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel
from typing import Optional, Dict, List, Any, Tuple
from collections import defaultdict, deque
from fastapi.middleware.cors import CORSMiddleware
import time, logging, json, os
import statistics
import requests
import sqlite3
from contextlib import contextmanager

# ---------------- CONFIG ----------------
API_KEY = os.getenv("API_KEY")        # optional API key protection (set to "MY_DEMO_KEY" if using)
RAGE_CLICK_COUNT = 3                  # clicks to trigger rage-click
RAGE_CLICK_WINDOW = 5.0               # seconds window for rage-click detection
THRASH_VEL_STRONG = 1200.0            # px/sec — single very strong velocity threshold
THRASH_VEL_WEAK = 300.0               # px/sec — weaker velocity considered evidence
THRASH_WEAK_COUNT = 4                 # number of weak high-vel events in a batch to consider
THRASH_DIRCHANGE_MIN = 2              # direction-changes threshold supporting thrash
THRASH_MEMORY_WINDOW = 8.0            # seconds to keep weak-thrash evidence per user
THRASH_MEMORY_REQUIRED = 2            # number of recent batches with evidence to elevate to thrash
LONG_HOVER_MS = 3000                  # dwell threshold for 'long_hover'
AZURE_SCALING_ENDPOINT = "https://management.azure.com/mock/scale"  # conceptual endpoint
DB_PATH = "ux_events.db"              # structured analytics store (SQLite)
# ----------------------------------------

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("events_and_actions.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("backend")

# -------- Structured analytics store (SQLite) --------
# Purpose: the text log (events_and_actions.log) is fine for debugging, but not
# queryable. This table records one row per analyzed batch so we can later run
# aggregate analysis (signal frequency over time, per-user rates, etc.) with pandas/SQL.
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS batch_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at REAL,       -- server-side wall clock when analyzed
            batch_ts REAL,          -- client-reported batch timestamp (normalized, seconds)
            user_id TEXT,
            page TEXT,
            num_events INTEGER,
            frustration_detected INTEGER,  -- 0/1
            signals TEXT,           -- JSON list, e.g. ["rage_click"]
            confidence REAL,
            action TEXT,            -- nullable
            median_vel REAL,
            max_vel REAL,
            dir_changes INTEGER
        )
    """)
    conn.commit()
    conn.close()

@contextmanager
def db_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def record_batch_analysis(payload: "BatchPayload", result: dict, movement_summary: dict, batch_ts: float):
    try:
        with db_conn() as conn:
            conn.execute(
                """INSERT INTO batch_analysis
                   (received_at, batch_ts, user_id, page, num_events, frustration_detected,
                    signals, confidence, action, median_vel, max_vel, dir_changes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    time.time(),
                    batch_ts,
                    payload.userId,
                    payload.page,
                    len(payload.events),
                    1 if result.get("frustrationDetected") else 0,
                    json.dumps(result.get("signals", [])),
                    result.get("confidence", 0.0),
                    result.get("action"),
                    movement_summary.get("median_vel", 0.0),
                    movement_summary.get("max_vel", 0.0),
                    movement_summary.get("dir_changes", 0),
                ),
            )
            conn.commit()
    except Exception as e:
        # Analytics logging must never break the live detection path.
        logger.error("[DB LOG ERROR] %s", str(e))

init_db()

app = FastAPI(title="Real-time Frustration Detector (Backend)")

# Allow Vite dev server origins (adjust if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores
click_store: Dict[Tuple[str, str], deque] = defaultdict(lambda: deque())
# short-term memory for weak thrash evidence per user: deque of timestamps
user_thrash_memory: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))

# -------- Pydantic models to match frontend batch payload --------
class EventItem(BaseModel):
    type: str
    ts: float
    x: Optional[float] = None
    y: Optional[float] = None
    elementId: Optional[str] = None
    dwellMs: Optional[float] = None
    velocity: Optional[float] = None
    # allow extra fields from frontend
    class Config:
        extra = "allow"

class BatchPayload(BaseModel):
    userId: str
    page: Optional[str] = None
    timestamp: float
    events: List[EventItem]
    meta: Optional[dict] = {}
    class Config:
        extra = "allow"

# -------- Helper utilities --------
def normalize_timestamp(ts: float) -> float:
    """Normalize timestamp: accept seconds or milliseconds (convert to seconds)."""
    ts = float(ts)
    # heuristics: if timestamp looks like ms (> 1e11 or >1e10), convert
    if ts > 1e11 or ts > 1e10:
        return ts / 1000.0
    return ts

def decide_action(signals: List[str]) -> Optional[str]:
    """Map detected signals to corrective actions (simulated)."""
    if "rage_click" in signals:
        return "restart_service"
    if "long_hover" in signals:
        return "enable_help_tooltip"
    return None

def execute_action_simulation(action: str, context: dict):
    """
    Simulates corrective actions such as scaling cloud resources.
    This demonstrates how the backend could integrate with Azure's
    autoscaling API when frustration signals are detected.
    """
    log_entry = {
        "action": action,
        "context": context,
        "time": time.time()
    }

    # --- Conceptual Azure API Integration (simulation) ---
    try:
        if action == "restart_service":
            logger.info("[AZURE] Simulating scale-up trigger to Azure Cloud...")

            # Simulated payload that would be sent to Azure
            scale_payload = {
                "subscriptionId": "demo-sub-id",
                "resourceGroup": "ux-aware-system",
                "action": "scale_up",
                "targetInstances": 2,
                "reason": "User frustration detected",
                "timestamp": time.time()
            }

            # Log locally (in real Azure integration, this would use requests.post)
            logger.info("[AZURE MOCK CALL] POST %s payload=%s", AZURE_SCALING_ENDPOINT, json.dumps(scale_payload))

            # Optional: uncomment if using real Azure REST API
            # response = requests.post(AZURE_SCALING_ENDPOINT, json=scale_payload, headers={"Authorization": "Bearer <TOKEN>"})
            # logger.info("[AZURE RESPONSE] %s", response.text)

        elif action == "enable_help_tooltip":
            logger.info("[UX ACTION] Triggering contextual help tooltip...")

        else:
            logger.info("[ACTION] Executing default simulation...")

    except Exception as e:
        logger.error("[AZURE SIMULATION ERROR] %s", str(e))

    logger.info("EXECUTE_ACTION (simulated): %s", json.dumps(log_entry))

# ---------- Thrash detection helpers ----------
def summarize_movements(events: List[EventItem]) -> Dict[str, Any]:
    """
    Build a small summary of mousemove events in this batch:
    median_vel, max_vel, count_strong, count_weak, total_dir_changes (if provided), etc.
    """
    vel_list = []
    dir_changes_sum = 0
    dir_provided = False

    for ev in events:
        if ev.type and ev.type.lower() == "mousemove":
            if getattr(ev, "velocity", None) is not None:
                try:
                    v = float(ev.velocity)
                    vel_list.append(v)
                except Exception:
                    continue
            # if frontend added dir/dirChanges fields, include them
            if getattr(ev, "dirChanges", None) is not None:
                try:
                    dir_changes_sum += int(ev.dirChanges)
                    dir_provided = True
                except Exception:
                    pass

    summary = {
        "median_vel": float(statistics.median(vel_list)) if vel_list else 0.0,
        "max_vel": max(vel_list) if vel_list else 0.0,
        "count_strong": sum(1 for v in vel_list if v >= THRASH_VEL_STRONG),
        "count_weak": sum(1 for v in vel_list if v >= THRASH_VEL_WEAK),
        "dir_changes": dir_changes_sum if dir_provided else 0,
        "has_mousemoves": bool(vel_list)
    }
    return summary

def record_weak_thrash(userId: str, now_ts: float):
    """Add a weak-thrash evidence timestamp for user and prune old entries."""
    dq = user_thrash_memory[userId]
    dq.append(now_ts)
    # prune anything older than THRASH_MEMORY_WINDOW
    cutoff = now_ts - THRASH_MEMORY_WINDOW
    while dq and dq[0] < cutoff:
        dq.popleft()

def weak_thrash_count_recent(userId: str, now_ts: float) -> int:
    dq = user_thrash_memory[userId]
    cutoff = now_ts - THRASH_MEMORY_WINDOW
    # count items within window
    return sum(1 for t in dq if t >= cutoff)

# -------- Core detection logic (process each event in the batch) --------
def analyze_batch(payload: BatchPayload) -> Dict[str, Any]:
    signals = []
    confidences: Dict[str, float] = {}

    # Normalize batch timestamp (seconds)
    try:
        batch_ts = normalize_timestamp(payload.timestamp)
    except Exception:
        batch_ts = time.time()

    # First: basic checks & compute movement summary
    movement_summary = summarize_movements(payload.events)

    # Process each event for rage-click & dwell
    for ev in payload.events:
        ev_type = ev.type.lower() if ev.type else ""
        # Normalize event timestamp (s)
        try:
            ev_ts = normalize_timestamp(ev.ts)
        except Exception:
            ev_ts = batch_ts

        # Rage-click detection (per user+element)
        if ev_type == "click":
            element = (ev.elementId or "unknown")
            key = (payload.userId, element)
            dq = click_store[key]
            dq.append(ev_ts)
            cutoff = ev_ts - RAGE_CLICK_WINDOW
            while dq and dq[0] < cutoff:
                dq.popleft()
            count = len(dq)
            if count >= RAGE_CLICK_COUNT and "rage_click" not in signals:
                signals.append("rage_click")
                # confidence ramps to 1.0 at count >= RAGE_CLICK_COUNT
                confidences["rage_click"] = min(1.0, float(count) / float(RAGE_CLICK_COUNT))

        # Long hover (dwell)
        if ev_type == "dwell" and getattr(ev, "dwellMs", None) is not None:
            try:
                dwell = float(ev.dwellMs)
                if dwell >= LONG_HOVER_MS and "long_hover" not in signals:
                    signals.append("long_hover")
                    # confidence scaled relative to 5s (cap 1.0)
                    confidences["long_hover"] = min(1.0, dwell / 5000.0)
            except Exception:
                pass

    # Cursor thrash detection: combine single-batch and short-term memory evidence
    thrash_flag = False
    thrash_conf = 0.0
    now = batch_ts or time.time()

    # Strong single-batch rule: a few very high velocities OR very high max with direction changes
    if movement_summary["has_mousemoves"]:
        if movement_summary["count_strong"] >= 1 and movement_summary["dir_changes"] >= 1:
            thrash_flag = True
            thrash_conf = max(thrash_conf, min(1.0, movement_summary["max_vel"] / (THRASH_VEL_STRONG * 1.5)))
        elif movement_summary["count_weak"] >= THRASH_WEAK_COUNT and movement_summary["dir_changes"] >= THRASH_DIRCHANGE_MIN:
            # multiple weak velocities plus direction changes -> strong evidence
            thrash_flag = True
            thrash_conf = max(thrash_conf, min(0.9, movement_summary["median_vel"] / (THRASH_VEL_WEAK * 2)))
        else:
            # not strong enough in this batch -> store weak evidence for memory-based aggregation
            if movement_summary["count_weak"] >= 2:  # two or more weak high-vel events in batch
                record_weak_thrash(payload.userId, now)
                recent = weak_thrash_count_recent(payload.userId, now)
                # require at least THRASH_MEMORY_REQUIRED such batches within memory window
                if recent >= THRASH_MEMORY_REQUIRED:
                    thrash_flag = True
                    # confidence increases with recent count
                    thrash_conf = min(0.9, float(recent) / float(THRASH_MEMORY_REQUIRED) * 0.5 + 0.4)

    # Finalize thrash signal
    if thrash_flag:
        signals.append("cursor_thrash")
        confidences["cursor_thrash"] = round(thrash_conf, 3) if thrash_conf else 0.5

    # Aggregate result
    frustration = len(signals) > 0
    overall_conf = round(max(confidences.values()) if confidences else 0.0, 3)

    # Logging for debugging and tuning
    logger.info("ANALYZE user=%s page=%s signals=%s conf=%s summary=%s",
                payload.userId, payload.page, signals, overall_conf, json.dumps(movement_summary))

    # Decide action if any
    action = decide_action(signals) if frustration else None

    result = {
        "frustrationDetected": frustration,
        "signals": signals,
        "confidence": overall_conf,
        "action": action
    }

    # Structured analytics record — separate from the live detection path so a
    # DB error can never break the response to the frontend.
    record_batch_analysis(payload, result, movement_summary, batch_ts)

    return result

# -------- API endpoints --------
@app.post("/api/events")
async def receive_events(
    payload: BatchPayload,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None),
    x_project_token: Optional[str] = Header(None, alias="x-project-token"),
):
    # Flexible API key check — supports both x-api-key and x-project-token
    key = x_api_key or x_project_token
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Normalize timestamps inside payload for safety
    try:
        payload.timestamp = normalize_timestamp(payload.timestamp)
        for ev in payload.events:
            ev.ts = normalize_timestamp(ev.ts)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timestamps")

    # Log incoming batch
    logger.info("INCOMING_BATCH user=%s page=%s events=%d headers_project_token=%s",
                payload.userId, payload.page, len(payload.events), bool(x_project_token))

    # Analyze the batch for frustration signals
    result = analyze_batch(payload)

    # If an action is selected, execute it safely in background
    if result.get("action"):
        ctx = {"userId": payload.userId, "page": payload.page, "signals": result.get("signals", [])}
        background_tasks.add_task(execute_action_simulation, result["action"], ctx)

    # Return result to frontend
    return result

@app.get("/")
async def root():
    return {"message": "Backend is running!"}

@app.get("/api/stats")
async def get_stats():
    """
    Aggregate stats over all recorded batches: total batches, frustration rate,
    per-signal counts, and per-user breakdown. Backed by the SQLite analytics
    store (ux_events.db), separate from the live detection path.
    """
    with db_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM batch_analysis").fetchall()

    total = len(rows)
    frustrated = sum(1 for r in rows if r["frustration_detected"])
    signal_counts: Dict[str, int] = defaultdict(int)
    per_user: Dict[str, int] = defaultdict(int)

    for r in rows:
        for sig in json.loads(r["signals"] or "[]"):
            signal_counts[sig] += 1
        per_user[r["user_id"]] += 1

    return {
        "total_batches": total,
        "frustrated_batches": frustrated,
        "frustration_rate": round(frustrated / total, 3) if total else 0.0,
        "signal_counts": dict(signal_counts),
        "batches_per_user": dict(per_user),
    }