export function routeLabel(route) {
  if (route.name) return route.name;
  return `${route.origin ?? "?"} — ${route.destination ?? "?"}`;
}

// Route/stop candidates with loading, browse-all, no-match, and error
// states. Selections out; data in as props.
export default function ResultsList({
  routes = [],
  stops = [],
  state = "idle",
  errorDetail = "",
  onSelectRoute,
  onSelectStop,
}) {
  if (state === "loading") {
    return <p role="status">Searching…</p>;
  }
  if (state === "error") {
    return <p role="alert">{errorDetail || "Search cannot load right now."}</p>;
  }
  if (state === "no-match") {
    return (
      <p role="status">
        Nothing matched that search. Check the spelling or browse the map.
      </p>
    );
  }
  if (state === "empty") {
    return <p role="status">No routes or stops listed yet.</p>;
  }
  if (state !== "ok" || (routes.length === 0 && stops.length === 0)) {
    return null;
  }
  return (
    <div className="gonaj-results-list">
      {routes.length > 0 && (
        <section aria-label="Matching routes">
          <h2>Routes</h2>
          <ul>
            {routes.map((route) => (
              <li key={route.id}>
                <button type="button" onClick={() => onSelectRoute?.(route.id)}>
                  {routeLabel(route)}
                </button>
                {(route.operator || route.origin) && (
                  <span>
                    {" "}
                    — {[route.operator, route.origin, route.destination].filter(Boolean).join(" · ")}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
      {stops.length > 0 && (
        <section aria-label="Matching stops">
          <h2>Stops</h2>
          <ul>
            {stops.map((stop) => (
              <li key={stop.id}>
                <button type="button" onClick={() => onSelectStop?.(stop)}>
                  {stop.name}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
