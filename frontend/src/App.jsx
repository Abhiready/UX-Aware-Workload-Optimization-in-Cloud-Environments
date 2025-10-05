import React from 'react';
import UXEventCapture from './components/UXEventCapture'; // <- the canvas file goes here
import './styles/index.css';

export default function App() {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:4000/api/events';
  const projectToken = import.meta.env.VITE_PROJECT_TOKEN || 'SOME_SHARED_TOKEN';

  return (
    <div>
      <header className="app-header">
        <h1>UX-Aware Frontend (Demo)</h1>
      </header>

      <main className="app-main">
        <section>
          <p>Interact with the page — clicks, hovers, and mouse movement will be captured and batched.</p>
          <button id="place-order-btn" data-eid="place-order-btn" className="cta">Place Order</button>
        </section>

        <section className="event-capture">
          <UXEventCapture backendUrl={backendUrl} projectToken={projectToken} />
        </section>
      </main>
    </div>
  );
}
