import { useEffect, useState } from "react";

export function routeLabel(route) {
  if (route.name) return route.name;
  return `${route.origin ?? "?"} — ${route.destination ?? "?"}`;
}

// Same-named stops collapse into one entry, order preserved.
function groupStopsByName(stops) {
  const groups = [];
  const byName = new Map();
  for (const stop of stops) {
    const key = stop.name ?? "";
    let group = byName.get(key);
    if (!group) {
      group = { name: key === "" ? "Unnamed stop" : key, members: [] };
      byName.set(key, group);
      groups.push(group);
    }
    group.members.push(stop);
  }
  return groups;
}

const emptyList = { items: [], page: 1, totalPages: 1, count: 0 };

function Pager({ kind, list, onPage }) {
  const { page, totalPages, count } = list;
  return (
    <div className="gonaj-pager">
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => {
          if (page > 1) onPage?.(page - 1);
        }}
        aria-label={`Previous ${kind} page`}
      >
        ‹ Prev
      </button>
      <span role="status">
        Page {page} of {totalPages} · {count} {kind}
      </span>
      <button
        type="button"
        disabled={page >= totalPages}
        onClick={() => {
          if (page < totalPages) onPage?.(page + 1);
        }}
        aria-label={`Next ${kind} page`}
      >
        Next ›
      </button>
    </div>
  );
}

// Route/stop candidates with loading, browse-all, no-match, and error
// states, plus per-tab page info. Selections and page changes out;
// data in as props.
export default function ResultsList({
  routeList = emptyList,
  stopList = emptyList,
  state = "idle",
  errorDetail = "",
  onSelectRoute,
  onSelectStop,
  onRoutePage,
  onStopPage,
}) {
  const [tab, setTab] = useState("routes");
  const [expanded, setExpanded] = useState(null);

  // When only one side has results, show it without asking.
  useEffect(() => {
    if (routeList.items.length > 0 && stopList.items.length === 0) setTab("routes");
    else if (stopList.items.length > 0 && routeList.items.length === 0) setTab("stops");
  }, [routeList, stopList]);

  // Collapse groups whenever the result set changes.
  useEffect(() => {
    setExpanded(null);
  }, [stopList]);

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
  if (
    state !== "ok" ||
    (routeList.items.length === 0 && stopList.items.length === 0)
  ) {
    return null;
  }
  return (
    <div className="gonaj-results-list">
      <div role="tablist" aria-label="Result type" className="gonaj-tabs">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "routes"}
          onClick={() => setTab("routes")}
        >
          Routes
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "stops"}
          onClick={() => setTab("stops")}
        >
          Stops
        </button>
      </div>
      {tab === "routes" && routeList.items.length > 0 && (
        <section aria-label="Matching routes">
          <h2>Routes</h2>
          <ul>
            {routeList.items.map((route) => (
              <li key={route.id}>
                <button type="button" onClick={() => onSelectRoute?.(route.id)}>
                  <span className="gonaj-route-name">{routeLabel(route)}</span>
                  {(route.operator || route.origin || route.destination) && (
                    <span className="gonaj-route-meta">
                      {[
                        route.operator,
                        [route.origin, route.destination]
                          .filter(Boolean)
                          .join(" → "),
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
          <Pager kind="routes" list={routeList} onPage={onRoutePage} />
        </section>
      )}
      {tab === "stops" && stopList.items.length > 0 && (
        <section aria-label="Matching stops">
          <h2>Stops</h2>
          <ul>
            {groupStopsByName(stopList.items).map((group) =>
              group.members.length === 1 ? (
                <li key={group.members[0].id}>
                  <button type="button" onClick={() => onSelectStop?.(group.members[0])}>
                    {group.members[0].name}
                  </button>
                </li>
              ) : (
                <li key={`group-${group.name}`}>
                  <button
                    type="button"
                    aria-expanded={expanded === group.name}
                    onClick={() =>
                      setExpanded((current) => (current === group.name ? null : group.name))
                    }
                  >
                    <span className="gonaj-route-name">{group.name}</span>
                    <span className="gonaj-route-meta">
                      {group.members.length} stops
                    </span>
                  </button>
                  {expanded === group.name && (
                    <ul className="gonaj-group-members">
                      {group.members.map((stop) => (
                        <li key={stop.id}>
                          <button type="button" onClick={() => onSelectStop?.(stop)}>
                            {stop.name}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              )
            )}
          </ul>
          <Pager kind="stops" list={stopList} onPage={onStopPage} />
        </section>
      )}
    </div>
  );
}
