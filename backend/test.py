import requests
import time

URL = "http://127.0.0.1:8000/api/events"

def send(label, events, page="/checkout"):
    payload = {
        "userId": "u1",
        "page": page,
        "timestamp": time.time(),
        "events": events,
        "meta": {}
    }
    resp = requests.post(URL, json=payload)
    print(f"--- {label} ---")
    print("status:", resp.status_code)
    print(resp.json())
    print()

# 1) Rage click test: 3 clicks on same element within 5s window
now = time.time()
rage_events = [
    {"type": "click", "ts": now, "elementId": "submit"},
    {"type": "click", "ts": now + 0.5, "elementId": "submit"},
    {"type": "click", "ts": now + 1.0, "elementId": "submit"},
]
send("Rage click", rage_events)

# 2) Long hover test: single dwell event >= 3000ms
now = time.time()
hover_events = [
    {"type": "dwell", "ts": now, "elementId": "faq-tooltip", "dwellMs": 4200},
]
send("Long hover", hover_events)

# 3) Cursor thrash test (tier 1): 1 strong velocity + dirChanges >= 1
now = time.time()
thrash_events = [
    {"type": "mousemove", "ts": now, "velocity": 1500.0, "dirChanges": 2},
    {"type": "mousemove", "ts": now + 0.1, "velocity": 1400.0, "dirChanges": 1},
]
send("Cursor thrash (strong, single batch)", thrash_events)

# 4) Cursor thrash (weak-memory path): needs 2 batches with >=2 weak-velocity
#    moves each, within 8s, WITHOUT dirChanges
now = time.time()
weak_batch = [
    {"type": "mousemove", "ts": now, "velocity": 400.0},
    {"type": "mousemove", "ts": now + 0.1, "velocity": 450.0},
]
send("Cursor thrash weak batch #1 (should NOT trigger yet)", weak_batch)

time.sleep(1)

now2 = time.time()
weak_batch2 = [
    {"type": "mousemove", "ts": now2, "velocity": 420.0},
    {"type": "mousemove", "ts": now2 + 0.1, "velocity": 460.0},
]
send("Cursor thrash weak batch #2 (SHOULD trigger via memory)", weak_batch2)

# 5) Normal/no-signal batch
now = time.time()
normal_events = [
    {"type": "mousemove", "ts": now, "velocity": 50.0},
    {"type": "click", "ts": now + 0.2, "elementId": "menu"},
]
send("Normal activity (no signal expected)", normal_events)