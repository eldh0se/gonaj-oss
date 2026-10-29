// Tile provider configuration (005-route-map FR-009).
//
// Public OSM tiles only for the small MVP, with required attribution.
// The browser Referer satisfies the OSMF Tile Usage Policy's
// self-identification rule; there is no server-side tile fetching
// anywhere in this app, so no custom User-Agent is needed.
export const tileConfig = {
  url:
    import.meta.env.VITE_TILE_URL ??
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  attribution:
    import.meta.env.VITE_TILE_ATTRIBUTION ??
    "© OpenStreetMap contributors",
};
