// Thin REST client for the journey helper (004-journey-agent).
//
// The only module allowed to call the journey endpoints; the panel
// receives data as props. No model calls and no model key here —
// all AI traffic is the two versioned REST endpoints.
import { ApiError } from "./client.js";
import { debugLog } from "./debug.js";

const API_BASE = "/api/v1";

async function requestJson(path, body, { signal } = {}) {
  const started = Date.now();
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err?.name === "AbortError") throw err;
    debugLog("api", { path, outcome: "network-error" });
    throw new ApiError(
      0,
      "We could not reach the journey helper. Please check your connection and try again."
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
      path,
      outcome: `http-${response.status}`,
      duration_ms: Date.now() - started,
    });
    const detail =
      data && typeof data.detail === "string"
        ? data.detail
        : "The journey helper cannot answer right now. Please try again later.";
    throw new ApiError(response.status, detail);
  }
  debugLog("api", {
    path,
    outcome: `http-${response.status}`,
    duration_ms: Date.now() - started,
  });
  return data;
}

export function postJourney({ question, history, context } = {}, opts) {
  return requestJson(
    "/journey/",
    { question, history: history ?? [], context: context ?? {} },
    opts
  );
}

export async function postTranscribe(audioBlob, { signal } = {}) {
  const started = Date.now();
  const form = new FormData();
  form.append("audio", audioBlob, "question.webm");
  let response;
  try {
    response = await fetch(`${API_BASE}/journey/transcribe/`, {
      method: "POST",
      body: form,
      signal,
    });
  } catch (err) {
    if (err?.name === "AbortError") throw err;
    debugLog("api", {
      path: "/journey/transcribe/",
      outcome: "network-error",
    });
    throw new ApiError(
      0,
      "We could not reach the transcription service. Please check your connection and try again."
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
      path: "/journey/transcribe/",
      outcome: `http-${response.status}`,
      duration_ms: Date.now() - started,
    });
    const detail =
      data && typeof data.detail === "string"
        ? data.detail
        : "We could not transcribe that. Please try again.";
    throw new ApiError(response.status, detail);
  }
  debugLog("api", {
    path: "/journey/transcribe/",
    outcome: `http-${response.status}`,
    duration_ms: Date.now() - started,
  });
  return data;
}
