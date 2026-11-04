import { useCallback, useEffect, useRef, useState } from "react";
import { Link, Route, Routes, useNavigate, useParams } from "react-router-dom";
import MapView from "./components/MapView.jsx";
import ResultsList from "./components/ResultsList.jsx";
import RouteOverlay from "./components/RouteOverlay.jsx";
import JourneyPanel from "./components/JourneyPanel.jsx";
import {
  getRoute,
  getStop,
  listAllStops,
  listRoutes,
  listStops,
} from "./api/client.js";
import "./App.css";

function toBbox(bounds) {
  return `${bounds.west},${bounds.south},${bounds.east},${bounds.north}`;
}

const emptyListResult = () => ({ items: [], page: 1, totalPages: 1, count: 0 });

// Visible build version (016 FR-008): full `v{version}+{sha7} · built {UTC}`
// when build metadata exists, plain `v{version}` fallback otherwise.
function appVersionLabel() {
  const version =
    typeof __APP_VERSION__ !== "undefined" && __APP_VERSION__
      ? __APP_VERSION__
      : "0.1.0";
  const sha =
    typeof __APP_SHA__ !== "undefined" && __APP_SHA__
      ? String(__APP_SHA__).slice(0, 7)
      : "";
  const builtAt =
    typeof __APP_BUILT_AT__ !== "undefined" && __APP_BUILT_AT__
      ? __APP_BUILT_AT__
      : "";
  const base = sha ? `v${version}+${sha}` : `v${version}`;
  return builtAt ? `${base} · built ${builtAt}` : base;
}

function toListResult(body) {
  return {
    items: body.results ?? [],
    page: body.current_page ?? 1,
    totalPages: body.total_pages ?? 1,
    count: body.count ?? 0,
  };
}

export default function App() {
  return (
    <Routes>
      <Route path="/routes/:routeId" element={<MapPage />} />
      <Route path="*" element={<MapPage />} />
    </Routes>
  );
}

export function MapPage() {
  const { routeId } = useParams();
  const navigate = useNavigate();

  const [area, setArea] = useState({ status: "loading", markers: [], detail: "" });
  const [query, setQuery] = useState("");
  const [routePage, setRoutePage] = useState(1);
  const [stopPage, setStopPage] = useState(1);
  const [search, setSearch] = useState({
    state: "loading",
    routes: emptyListResult(),
    stops: emptyListResult(),
    errorDetail: "",
  });
  const [stopCard, setStopCard] = useState(null);
  const [overlay, setOverlay] = useState({ state: "idle", detail: null, errorDetail: "" });
  const [center, setCenter] = useState(null);
  const [candidateView, setCandidateView] = useState(null);
  const [locateOptIn, setLocateOptIn] = useState(false);
  const panelChooseRef = useRef(null);

  const areaAbort = useRef(null);
  const searchAbort = useRef(null);
  const stopAbort = useRef(null);
  const overlayAbort = useRef(null);

  const handleAreaChange = useCallback((bounds) => {
    areaAbort.current?.abort();
    const controller = new AbortController();
    areaAbort.current = controller;
    setArea({ status: "loading", markers: [], detail: "" });
    listAllStops({ bbox: toBbox(bounds), pageSize: 100 }, { signal: controller.signal }).then(
      (body) => {
        if (body.status === "zoom_in") {
          setArea({
            status: "zoom_in",
            markers: [],
            detail:
              body.detail ||
              "That area is too large to list stops for. Please zoom in and try again.",
          });
        } else if (body.status === "empty" || (body.count ?? 0) === 0) {
          setArea({ status: "empty", markers: [], detail: body.detail ?? "" });
        } else {
          setArea({ status: "ok", markers: body.results ?? [], detail: "" });
        }
      },
      (err) => {
        if (err?.name === "AbortError") return;
        setArea({
          status: "error",
          markers: [],
          detail:
            err?.detail ?? "The map cannot load right now. Please try again later.",
        });
      }
    );
  }, []);

  const handleQuery = useCallback((next) => {
    setQuery(next);
    setRoutePage(1);
    setStopPage(1);
  }, []);

  useEffect(() => {
    searchAbort.current?.abort();
    const controller = new AbortController();
    searchAbort.current = controller;
    setSearch((s) => ({ ...s, state: "loading", errorDetail: "" }));
    const text = query.trim();
    Promise.all([
      listRoutes(
        { ...(text ? { search: text } : {}), pageSize: 20, page: routePage },
        { signal: controller.signal }
      ),
      listStops(
        { ...(text ? { search: text } : {}), pageSize: 20, page: stopPage },
        { signal: controller.signal }
      ),
    ]).then(
      ([routesBody, stopsBody]) => {
        const routes = toListResult(routesBody);
        const stops = toListResult(stopsBody);
        if (routes.count === 0 && stops.count === 0) {
          setSearch({
            state: text ? "no-match" : "empty",
            routes,
            stops,
            errorDetail: "",
          });
        } else {
          setSearch({ state: "ok", routes, stops, errorDetail: "" });
        }
      },
      (err) => {
        if (err?.name === "AbortError") return;
        setSearch({
          state: "error",
          routes: emptyListResult(),
          stops: emptyListResult(),
          errorDetail:
            err?.detail ?? "Search cannot load right now. Please try again later.",
        });
      }
    );
    return () => controller.abort();
  }, [query, routePage, stopPage]);

  useEffect(() => {
    overlayAbort.current?.abort();
    if (!routeId) {
      setOverlay({ state: "idle", detail: null, errorDetail: "" });
      return undefined;
    }
    const controller = new AbortController();
    overlayAbort.current = controller;
    setOverlay({ state: "loading", detail: null, errorDetail: "" });
    getRoute(routeId, { signal: controller.signal }).then(
      (detail) => {
        const stops = detail.stops ?? [];
        setOverlay({ state: stops.length === 0 ? "empty" : "ok", detail, errorDetail: "" });
      },
      (err) => {
        if (err?.name === "AbortError") return;
        if (err?.status === 404) {
          setOverlay({ state: "not-found", detail: null, errorDetail: "" });
        } else {
          setOverlay({
            state: "error",
            detail: null,
            errorDetail:
              err?.detail ?? "That route cannot load right now. Please try again later.",
          });
        }
      }
    );
    return () => controller.abort();
  }, [routeId]);

  // Route focus (016): while a route detail is open, the map shows only
  // that route's stops (area markers hidden), fits the route bounds, and
  // marks endpoints by role. Close restores area markers via the null path.
  const routeStops =
    overlay.detail && (overlay.state === "ok" || overlay.state === "empty")
      ? (overlay.detail.stops ?? [])
          .filter(
            (s) =>
              typeof s?.stop?.lat === "number" &&
              typeof s?.stop?.lon === "number"
          )
          .map((s) => ({
            id: s.stop.id,
            name: s.stop.name,
            lat: s.stop.lat,
            lon: s.stop.lon,
            role: s.is_origin
              ? "origin"
              : s.is_terminus
                ? "terminus"
                : undefined,
          }))
      : null;

  const highlight = routeStops
    ? routeStops.map((m) => [m.lat, m.lon])
    : null;

  const routeBounds =
    routeStops && routeStops.length > 0
      ? {
          south: Math.min(...routeStops.map((m) => m.lat)),
          west: Math.min(...routeStops.map((m) => m.lon)),
          north: Math.max(...routeStops.map((m) => m.lat)),
          east: Math.max(...routeStops.map((m) => m.lon)),
        }
      : null;

  const handleSelectRoute = useCallback(
    (id) => {
      navigate(`/routes/${id}`);
    },
    [navigate]
  );

  const handleSelectStop = useCallback((stop) => {
    if (stop.lat !== undefined && stop.lon !== undefined) {
      setCenter({ lat: stop.lat, lon: stop.lon, nonce: Date.now() });
    }
    stopAbort.current?.abort();
    const controller = new AbortController();
    stopAbort.current = controller;
    setStopCard({ state: "loading", detail: null, errorDetail: "" });
    getStop(stop.id, { signal: controller.signal }).then(
      (detail) => setStopCard({ state: "ok", detail, errorDetail: "" }),
      (err) => {
        if (err?.name === "AbortError") return;
        setStopCard({
          state: "error",
          detail: null,
          errorDetail:
            err?.detail ?? "That stop cannot load right now. Please try again later.",
        });
      }
    );
  }, []);

  const handleShowCandidates = useCallback((view, _payload) => {
    setCandidateView(view);
  }, []);

  const handleMapTap = useCallback(
    (marker) => {
      const ids = new Set((candidateView?.stops ?? []).map((s) => s.id));
      if (ids.has(marker.id)) {
        panelChooseRef.current?.({ id: marker.id, name: marker.name });
        return;
      }
      handleSelectStop(marker);
    },
    [candidateView, handleSelectStop]
  );

  const handleLocateOptIn = useCallback(() => {
    setLocateOptIn(true);
    navigator.geolocation?.getCurrentPosition?.((position) => {
      setCenter({
        lat: position.coords.latitude,
        lon: position.coords.longitude,
        nonce: Date.now(),
      });
    });
  }, []);

  const handleDismissOverlay = useCallback(() => {
    navigate("/");
  }, [navigate]);

  return (
    <div className="gonaj-page">
      <header className="gonaj-header">
        <h1 className="gonaj-title">
          <Link to="/">Gonaj</Link>
        </h1>
      </header>

      <div className="gonaj-body">
        <section className="gonaj-map-wrap" aria-label="Transport map">
          <MapView
            markers={routeStops ?? area.markers}
            highlight={highlight}
            center={center}
            selectedId={
              stopCard?.state === "ok" && stopCard.detail ? stopCard.detail.id : null
            }
            highlightIds={(candidateView?.stops ?? []).map((s) => s.id)}
            fitBounds={routeBounds ?? candidateView?.bounds ?? null}
            onAreaChange={handleAreaChange}
            onSelectStop={handleMapTap}
          />
          {!locateOptIn && (
            <button type="button" onClick={handleLocateOptIn}>
              Show my location
            </button>
          )}
          {area.status === "loading" && (
            <p role="status" className="gonaj-area-note">Loading stops…</p>
          )}
          {area.status === "zoom_in" && (
            <p role="status" className="gonaj-area-note gonaj-area-note--warn">{area.detail}</p>
          )}
          {area.status === "empty" && (
            <p role="status" className="gonaj-area-note">
              No stops in this area. Try panning the map or searching by name.
            </p>
          )}
          {area.status === "error" && (
            <p role="alert" className="gonaj-area-note">{area.detail}</p>
          )}
        </section>

        <aside className="gonaj-results" aria-label="Search results">
          <ResultsList
            routeList={search.routes}
            stopList={search.stops}
            state={search.state}
            errorDetail={search.errorDetail}
            onSelectRoute={handleSelectRoute}
            onSelectStop={handleSelectStop}
            onRoutePage={setRoutePage}
            onStopPage={setStopPage}
            onQuery={handleQuery}
            journeyContent={
              <JourneyPanel
                onShowCandidates={handleShowCandidates}
                chooseRef={panelChooseRef}
              />
            }
          />
        </aside>
      </div>

      <footer className="gonaj-version" data-testid="app-version">
        {appVersionLabel()}
      </footer>

      {routeId && overlay.state !== "idle" ? (
        <RouteOverlay
          detail={overlay.detail}
          state={overlay.state}
          errorDetail={overlay.errorDetail}
          onDismiss={handleDismissOverlay}
        />
      ) : (
        !routeId &&
        stopCard && (
          <section aria-label="Selected stop" className="gonaj-overlay">
            <button type="button" onClick={() => setStopCard(null)}>
              Close
            </button>
            {stopCard.state === "loading" && <p role="status">Loading stop…</p>}
            {stopCard.state === "error" && (
              <p role="alert">{stopCard.errorDetail}</p>
            )}
            {stopCard.state === "ok" && stopCard.detail && (
              <>
                <h2>{stopCard.detail.name}</h2>
                <h3>Serving routes</h3>
                {(stopCard.detail.serving_routes ?? []).length === 0 ? (
                  <p>No routes serve this stop.</p>
                ) : (
                  <ul>
                    {(stopCard.detail.serving_routes ?? []).map((r) => (
                      <li key={r.id}>
                        <button type="button" onClick={() => handleSelectRoute(r.id)}>
                          {r.name ?? `Route ${r.id}`}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </section>
        )
      )}
    </div>
  );
}
