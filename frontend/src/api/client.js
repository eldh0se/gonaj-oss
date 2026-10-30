// Fetch wrapper for the 003 read API (005-route-map FR-003–FR-005).
//
// The single module allowed to call the read API; every other module
// receives transit data as props. Envelopes are returned verbatim —
// including `status`/`detail` on the stops list — so views can render
// the `zoom_in` and `empty` outcomes exactly as contracted.
const API_BASE = "/api/v1";

export const PAGE_SIZE_DEFAULT = 20;
export const PAGE_SIZE_MAX = 100;

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, { signal } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { signal });
  } catch (err) {
    if (err?.name === "AbortError") throw err;
    throw new ApiError(
      0,
      "We could not reach the map service. Please check your connection and try again."
    );
  }
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (!response.ok) {
    const detail =
      body && typeof body.detail === "string"
        ? body.detail
        : "Something went wrong loading map data. Please try again.";
    throw new ApiError(response.status, detail);
  }
  return body;
}

function params(obj) {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(obj)) {
    if (value === undefined || value === null || value === "") continue;
    qs.set(key, String(value));
  }
  const s = qs.toString();
  return s ? `?${s}` : "";
}

function pageParams(page, pageSize) {
  const size = Math.min(
    Math.max(1, Number(pageSize) || PAGE_SIZE_DEFAULT),
    PAGE_SIZE_MAX
  );
  return { page: Math.max(1, Number(page) || 1), page_size: size };
}

export function listRoutes(
  { search, operator, network, page, pageSize } = {},
  opts
) {
  return request(
    `/routes/${params({ search, operator, network, ...pageParams(page, pageSize) })}`,
    opts
  );
}

export function getRoute(id, opts) {
  return request(`/routes/${encodeURIComponent(id)}/`, opts);
}

export function listStops({ search, bbox, page, pageSize } = {}, opts) {
  return request(
    `/stops/${params({ search, bbox, ...pageParams(page, pageSize) })}`,
    opts
  );
}

export function getStop(id, opts) {
  return request(`/stops/${encodeURIComponent(id)}/`, opts);
}

export function getConnectivity(fromId, toId, opts) {
  return request(
    `/connectivity/${params({ from: fromId, to: toId })}`,
    opts
  );
}

// Follow every page until the envelope's `count` is satisfied, so the
// marker set is never a partial page. Safe to page through because
// oversized areas return zero stops by contract.
export async function listAllStops(query = {}, opts) {
  const first = await listStops({ ...query, page: 1 }, opts);
  const results = [...(first.results ?? [])];
  const totalPages = first.total_pages ?? 1;
  for (let page = 2; page <= totalPages; page += 1) {
    const next = await listStops({ ...query, page }, opts);
    results.push(...(next.results ?? []));
  }
  return { ...first, results };
}
