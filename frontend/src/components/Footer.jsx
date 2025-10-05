import React from 'react';

export default function Footer() {
  return (
    <footer style={styles.footer}>
      <div>
        <small>© {new Date().getFullYear()} UX-Aware Project — Demo build</small>
      </div>
      <div style={styles.right}>
        <small style={{ color: '#6b7280' }}>Made by: Abhishek</small>
      </div>
    </footer>
  );
}

const styles = {
  footer: {
    marginTop: 30,
    padding: '12px 18px',
    borderTop: '1px solid #e6edf3',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    background: '#fff'
  },
  right: { opacity: 0.9 }
};
