// DEV-gated debug helper (specs/007-debug-production-logging,
// contracts/logging.md section 7).
//
// One debug entry per call in development builds only. The
// `import.meta.env.DEV` gate is statically eliminated from production
// bundles, so no log call through this helper can reach production.
export function debugLog(operation, context = {}) {
  if (import.meta.env.DEV) {
    console.debug(operation, context);
  }
}
