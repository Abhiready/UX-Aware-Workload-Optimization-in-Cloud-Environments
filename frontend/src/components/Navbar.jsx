import React from 'react';

export default function Navbar() {
  return (
    <nav style={styles.nav}>
      <div style={styles.brand}>UX-Aware Demo</div>
      <div style={styles.links}>
        <a href="/" style={styles.link}>Home</a>
        <a href="/dashboard" style={styles.link}>Dashboard</a>
      </div>
    </nav>
  );
}

const styles = {
  nav: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 18px',
    borderBottom: '1px solid #e6edf3',
    background: 'linear-gradient(90deg,#fff,#fbfdfd)'
  },
  brand: {
    fontWeight: 700,
    fontSize: '1rem'
  },
  links: {
    display: 'flex',
    gap: 12
  },
  link: {
    color: '#0f172a',
    textDecoration: 'none',
    fontSize: '0.95rem'
  }
};
