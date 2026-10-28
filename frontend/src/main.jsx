import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

// Scaffold placeholder: proves the frontend slot, toolchain, and the
// API-call path to the versioned backend. Replaced by the real map UI
// with the first transport feature.
function App() {
  const [api, setApi] = useState("checking…");

  useEffect(() => {
    fetch("/api/v1/")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => setApi(`OK: ${data.name} ${data.version}`))
      .catch(() => setApi("backend not reachable"));
  }, []);

  return (
    <main>
      <h1>Gonaj scaffold placeholder</h1>
      <p>Backend API root: {api}</p>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
