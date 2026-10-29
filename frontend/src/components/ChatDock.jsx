import { useState } from "react";

// Inert coming-soon dock reserving the 004 journey helper's home.
// By contract: activating the control sends no request, collects no
// input, and stores nothing.
export default function ChatDock() {
  const [message, setMessage] = useState("");
  return (
    <section aria-label="Journey helper" className="gonaj-dock">
      <h2>Journey helper</h2>
      <span className="gonaj-tag">Coming soon</span>
      <p>Plain-language direct-route answers will live here.</p>
      <button type="button" onClick={() => setMessage("The journey helper is not available yet.")}>
        Ask the journey helper
      </button>
      {message && <p role="status">{message}</p>}
    </section>
  );
}
