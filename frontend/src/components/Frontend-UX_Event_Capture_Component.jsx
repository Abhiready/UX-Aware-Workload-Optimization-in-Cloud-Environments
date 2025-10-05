import React, { useEffect, useRef, useState } from "react";

/**
 * UX Event Capture — improved velocity, smoothing, direction-change detection,
 * movementType (calm/slightly_agitated/agitated) and safe batching.
 *
 * - velocity units: pixels / second (px/s)
 * - smoothedVelocity: EMA of velocity (px/s) sent to backend
 * - movementType: "calm" | "slightly_agitated" | "agitated" computed from smoothedVelocity
 * - dirChanges: count of recent sign changes in X/Y motion direction window
 */

export default function UXEventCapture({
  backendUrl = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000/api/events",
  projectToken = import.meta.env.VITE_PROJECT_TOKEN || "SOME_SHARED_TOKEN",
}) {
  const [eventsBuffer, setEventsBuffer] = useState([]);
  const [logs, setLogs] = useState([]);
  const lastMouse = useRef({ x: null, y: null, ts: null });
  const lastClickTs = useRef(0);
  const batchTimer = useRef(null);
  const userId = useRef("anon-" + Math.random().toString(36).slice(2, 9));

  // smoothing / direction detection
  const emaAlpha = 0.25; // EMA alpha for velocity smoothing (tuneable)
  const smoothedVelocity = useRef(0);
  const dirWindow = useRef([]); // keep last N direction signs
  const DIR_WINDOW_MAX = 6;

  const throttledMouseMoveRef = useRef(null);
  const attachedHoverElsRef = useRef(new Set());

  function pushEvent(e) {
    setEventsBuffer((buf) => {
      const next = [...buf, e];
      if (next.length > 300) next.splice(0, next.length - 300);
      return next;
    });
  }

  function onClick(e) {
    const ts = Date.now();
    const rect = e.target.getBoundingClientRect ? e.target.getBoundingClientRect() : { left: 0, top: 0 };
    const payload = {
      type: "click",
      ts,
      x: Math.round(e.clientX - rect.left),
      y: Math.round(e.clientY - rect.top),
      elementId: e.target.id || e.target.dataset.eid || e.target.tagName.toLowerCase(),
    };
    pushEvent(payload);

    if (ts - lastClickTs.current < 400) {
      pushEvent({ type: "rapid_click", ts, elementId: payload.elementId, count: 2 });
    }
    lastClickTs.current = ts;
  }

  function signOf(n) {
    if (n > 0) return 1;
    if (n < 0) return -1;
    return 0;
  }

  function computeMovementType(v) {
    // conservative thresholds (px/s) — tune to your app
    if (v >= 600) return "agitated";
    if (v >= 150) return "slightly_agitated";
    return "calm";
  }

  function onMouseMove(e) {
    const ts = Date.now();
    if (lastMouse.current.ts === null) {
      lastMouse.current = { x: e.clientX, y: e.clientY, ts };
      return;
    }

    const dtMs = Math.max(1, ts - lastMouse.current.ts);
    const dx = e.clientX - lastMouse.current.x;
    const dy = e.clientY - lastMouse.current.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    // velocity in px/s
    const velocity = (dist / dtMs) * 1000;

    // clamp raw velocity to avoid absurd spikes (safety)
    const MAX_RAW_V = 5000;
    const clamped = Math.min(MAX_RAW_V, velocity);

    // EMA smoothing
    smoothedVelocity.current = emaAlpha * clamped + (1 - emaAlpha) * (smoothedVelocity.current || clamped);

    // track direction changes (use horizontal sign as simple proxy)
    const dir = signOf(dx || dy);
    const prevDir = dirWindow.current.length ? dirWindow.current[dirWindow.current.length - 1] : dir;
    if (dir !== prevDir && prevDir !== 0) {
      dirWindow.current.push(dir);
    } else {
      dirWindow.current.push(dir);
    }
    if (dirWindow.current.length > DIR_WINDOW_MAX) dirWindow.current.shift();
    const dirChanges = dirWindow.current.reduce((acc, s, i, arr) => {
      if (i === 0) return 0;
      return acc + (s !== arr[i - 1] && arr[i - 1] !== 0 ? 1 : 0);
    }, 0);

    // compute movementType from smoothed velocity and dirChanges
    const movementType = computeMovementType(smoothedVelocity.current);

    lastMouse.current = { x: e.clientX, y: e.clientY, ts };

    // distance threshold to avoid tiny micro-movements
    if (dist < 2) return;

    // push a composed mousemove event with smoothedVelocity and movement metadata
    pushEvent({
      type: "mousemove",
      ts,
      x: e.clientX,
      y: e.clientY,
      velocity: +clamped.toFixed(2), // raw but bounded
      smoothedVelocity: +smoothedVelocity.current.toFixed(2),
      dir: dir,
      dirChanges: dirChanges,
      movementType,
    });
  }

  function onVisibilityChange() {
    const ts = Date.now();
    if (document.hidden) pushEvent({ type: "hidden", ts });
    else pushEvent({ type: "visible", ts });
  }

  const hoverStart = useRef({});
  function onMouseEnter(e) {
    const id = e.target.dataset.eid || e.target.id || e.target.tagName;
    hoverStart.current[id] = Date.now();
  }
  function onMouseLeave(e) {
    const id = e.target.dataset.eid || e.target.id || e.target.tagName;
    const start = hoverStart.current[id] || Date.now();
    const dwell = Date.now() - start;
    pushEvent({ type: "dwell", ts: Date.now(), elementId: id, dwellMs: dwell });
  }

  async function sendPayloadToBackend(payload) {
    try {
      const res = await fetch(backendUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-project-token": projectToken,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status} ${res.statusText} ${text}`);
      }

      const json = await res.json().catch(() => ({}));
      setLogs((l) => [{ ts: Date.now(), response: json }, ...l].slice(0, 50));
      return json;
    } catch (err) {
      setLogs((l) => [{ ts: Date.now(), error: String(err) }, ...l].slice(0, 50));
      throw err;
    }
  }

  // batch sender
  useEffect(() => {
    function sendBatch() {
      setEventsBuffer((buf) => {
        if (!buf || buf.length === 0) return buf;
        const payload = {
          userId: userId.current,
          page: window.location.pathname,
          timestamp: Date.now(),
          events: buf,
          meta: {
            clientPerf: { rtt: null },
            clientTime: Date.now(),
          },
        };

        setLogs((l) => [{ ts: Date.now(), payload }, ...l].slice(0, 50));
        sendPayloadToBackend(payload).catch(() => {});
        return [];
      });
    }

    batchTimer.current = setInterval(sendBatch, 3000);
    return () => {
      clearInterval(batchTimer.current);
      batchTimer.current = null;
    };
  }, [backendUrl, projectToken]);

  // attach listeners (throttle mousemove)
  useEffect(() => {
    throttledMouseMoveRef.current = throttle(onMouseMove, 60); // 60ms throttle

    window.addEventListener("click", onClick, true);
    window.addEventListener("mousemove", throttledMouseMoveRef.current, true);
    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("focus", () => pushEvent({ type: "focus", ts: Date.now() }));
    window.addEventListener("blur", () => pushEvent({ type: "blur", ts: Date.now() }));

    const attachHover = () => {
      document.querySelectorAll("button, a, input, textarea, [data-eid]").forEach((el) => {
        if (!attachedHoverElsRef.current.has(el)) {
          el.addEventListener("mouseenter", onMouseEnter);
          el.addEventListener("mouseleave", onMouseLeave);
          attachedHoverElsRef.current.add(el);
        }
      });
    };

    attachHover();
    const mo = new MutationObserver(attachHover);
    mo.observe(document.body, { childList: true, subtree: true });

    return () => {
      window.removeEventListener("click", onClick, true);
      if (throttledMouseMoveRef.current) window.removeEventListener("mousemove", throttledMouseMoveRef.current, true);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      attachedHoverElsRef.current.forEach((el) => {
        try {
          el.removeEventListener("mouseenter", onMouseEnter);
          el.removeEventListener("mouseleave", onMouseLeave);
        } catch (e) {}
      });
      attachedHoverElsRef.current.clear();
      mo.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const forceSend = () => {
    setEventsBuffer((buf) => {
      if (!buf || buf.length === 0) return buf;
      const payload = {
        userId: userId.current,
        page: window.location.pathname,
        timestamp: Date.now(),
        events: buf,
        meta: {
          clientPerf: { rtt: null },
          clientTime: Date.now(),
        },
      };
      setLogs((l) => [{ ts: Date.now(), payload }, ...l].slice(0, 50));
      sendPayloadToBackend(payload).catch(() => {});
      return [];
    });
  };

  return (
    <div style={{ padding: 16, background: "#fff", borderRadius: 8, boxShadow: "0 4px 10px rgba(0,0,0,0.05)" }}>
      <h2 style={{ fontSize: "1rem", margin: 0, marginBottom: 8 }}>UX Event Capture (Demo)</h2>
      <p style={{ fontSize: "0.85rem", marginBottom: 10 }}>
        Captures clicks, rapid clicks, mouse velocity (px/s), smoothedVelocity, direction changes and movementType.
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <button onClick={() => pushEvent({ type: "test_click", ts: Date.now(), elementId: "manual-btn" })}>Send Test Click</button>
        <button onClick={forceSend}>Force Send</button>
      </div>

      <div style={{ marginTop: 10, maxHeight: 360, overflow: "auto", fontSize: 12, background: "#f9fafb", padding: 8, borderRadius: 6 }}>
        {logs.length === 0 && <div style={{ color: "#6b7280" }}>No logs yet — click or hover on the page.</div>}
        {logs.map((l, i) => (
          <div key={i} style={{ marginBottom: 6 }}>
            <strong>{new Date(l.ts).toLocaleTimeString()}:</strong>
            <pre style={{ margin: 0 }}>{JSON.stringify(l.payload || l.response || l.error, null, 2)}</pre>
          </div>
        ))}
      </div>
    </div>
  );
}

function throttle(fn, wait) {
  let last = 0;
  let timer = null;
  return function (...args) {
    const now = Date.now();
    if (now - last >= wait) {
      last = now;
      fn.apply(this, args);
    } else {
      clearTimeout(timer);
      timer = setTimeout(() => {
        last = Date.now();
        fn.apply(this, args);
      }, wait - (now - last));
    }
  };
}
