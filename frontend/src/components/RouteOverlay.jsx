import { routeLabel } from "./ResultsList.jsx";

// Route detail overlay on the same page. Detail payload or state in,
// dismiss out. Ordered stops with origin/terminus marked; empty
// membership and unknown ids are explicit plain-language states.
export default function RouteOverlay({ detail, state, errorDetail, onDismiss }) {
  return (
    <section aria-label="Route detail" className="gonaj-overlay">
      <button type="button" onClick={onDismiss}>
        Close
      </button>
      {state === "loading" && <p role="status">Loading route…</p>}
      {state === "not-found" && (
        <p role="alert">
          We could not find that route. Please check the link and try again.
        </p>
      )}
      {state === "error" && (
        <p role="alert">{errorDetail || "That route cannot load right now."}</p>
      )}
      {(state === "ok" || state === "empty") && detail && (
        <>
          <h2>{routeLabel(detail)}</h2>
          <dl>
            <dt>Origin</dt>
            <dd>{detail.origin ?? "—"}</dd>
            <dt>Destination</dt>
            <dd>{detail.destination ?? "—"}</dd>
            <dt>Operator</dt>
            <dd>{detail.operator ?? "—"}</dd>
            <dt>Network</dt>
            <dd>{detail.network ?? "—"}</dd>
          </dl>
          {state === "empty" ? (
            <p role="status">
              No stops are recorded for this route yet.
            </p>
          ) : (
            <ol className="gonaj-timeline">
              {(detail.stops ?? []).map((step) => (
                <li
                  key={`${step.position}-${step.stop.id}`}
                  className={[
                    step.is_origin && "is-origin",
                    step.is_terminus && "is-terminus",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  <span aria-hidden="true" className="gonaj-tl-gutter" />
                  <span>
                    {step.stop.name}
                    {step.is_origin && " (origin)"}
                    {step.is_terminus && " (terminus)"}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  );
}
