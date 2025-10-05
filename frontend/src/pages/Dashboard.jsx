import React, { useEffect, useState } from 'react';

export default function Dashboard() {
  const [logs, setLogs] = useState([]);

  // For demo: pull recent logs from localStorage (UXEventCapture pushes demo logs there optionally)
  useEffect(() => {
    try {
      const raw = localStorage.getItem('ux_demo_logs');
      if (raw) setLogs(JSON.parse(raw).slice(0, 50));
    } catch (e) {
      // ignore
    }
  }, []);

  return (
    <div style={{ padding: 18 }}>
      <h2 style={{ marginTop: 0 }}>Dashboard — Recent Event Batches</h2>
      <p style={{ color: '#6b7280' }}>This panel shows the latest event batches captured by the frontend (demo only).</p>

      <div style={styles.container}>
        {logs.length === 0 && <div style={{ color: '#9ca3af' }}>No demo logs found. Interact with the Home page to generate events.</div>}
        {logs.map((l, i) => (
          <div key={i} style={styles.card}>
            <div style={{ fontSize: 12, color: '#374151' }}>{new Date(l.ts || Date.now()).toLocaleString()}</div>
            <pre style={styles.pre}>{JSON.stringify(l.payload || l, null, 2)}</pre>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  container: { marginTop: 12, display: 'grid', gap: 10 },
  card: { background: '#fff', padding: 10, borderRadius: 8, boxShadow: '0 6px 14px rgba(2,6,23,0.03)' },
  pre: { background: '#f8fafc', padding: 8, borderRadius: 6, overflowX: 'auto', maxHeight: 160 }
};
