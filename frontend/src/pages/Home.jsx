import React from 'react';
import UXEventCapture from './UXEventCapture';

export default function Home() {
  return (
    <div style={{ padding: 18 }}>
      <section style={styles.hero}>
        <h2 style={{ margin: 0 }}>Welcome — UX Event Capture Demo</h2>
        <p style={{ marginTop: 8, color: '#6b7280' }}>
          This demo captures micro-interactions (clicks, hovers, mouse velocity) and sends batched events to your backend.
        </p>
        <div style={{ marginTop: 12 }}>
          <button id="place-order-btn" data-eid="place-order-btn" style={styles.cta}>Place Order</button>
        </div>
      </section>

      <section style={{ marginTop: 18 }}>
        <UXEventCapture />
      </section>
    </div>
  );
}

const styles = {
  hero: {
    background: '#fff',
    padding: 16,
    borderRadius: 10,
    boxShadow: '0 6px 18px rgba(2,6,23,0.04)'
  },
  cta: {
    marginTop: 8,
    padding: '10px 14px',
    borderRadius: 8,
    border: 0,
    background: '#0ea5a4',
    color: '#fff',
    cursor: 'pointer'
  }
};
