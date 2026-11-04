// Thin REST client for anonymous passenger feedback (017).
//
// Posts curation reports to the single versioned endpoint. No auth,
// no tracking — the server returns a receipt-only reference.
import { ApiError } from "./client.js";
import { debugLog } from "./debug.js";

const API_BASE = "/api/v1";

export async function postFeedback(
  { category, message, routeId, stopId, journey } = {},
  { signal } = {}
) {
  const started = Date.now();
  const body = { category, message };
  if (routeId !== undefined && routeId !== null) body.route_id = routeId;
  if (stopId !== undefined && stopId !== null) body.stop_id = stopId;
  if (journey) body.journey = journey;
  let response;
  try {
    response = await fetch(`${API_BASE}/feedback/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err?.name === "AbortError") throw err;
    debugLog("api", { path: "/feedback/", outcome: "network-error" });
    throw new ApiError(
      0,
      "We could not reach the reporting service. Please check your connection and try again."
    );
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    debugLog("api", {
      path: "/feedback/",
      outcome: `http-${response.status}`,
      duration_ms: Date.now() - started,
    });
    const detail =
      data && typeof data.detail === "string"
        ? data.detail
        : "Your report could not be saved. Please try again later.";
    const error = new ApiError(response.status, detail);
    if (data && typeof data.code === "string") error.code = data.code;
    throw error;
  }
  debugLog("api", {
    path: "/feedback/",
    outcome: `http-${response.status}`,
    duration_ms: Date.now() - started,
  });
  return data;
}
