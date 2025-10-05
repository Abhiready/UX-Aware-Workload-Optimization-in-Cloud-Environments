// This file is a small wrapper that imports the big component you already have on the canvas.
// Move the canvas file into this folder as: Frontend-UX_Event_Capture_Component.jsx
// or update the import path below to point to where you placed it.

import UXBig from './Frontend-UX_Event_Capture_Component.jsx'; // <- big canvas file (keep the exact filename)
export default function UXEventCapture(props) {
  // Re-export but allow prop overrides (backendUrl, projectToken)
  return <UXBig {...props} />;
}
