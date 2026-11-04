import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build metadata for the visible footer version (016 FR-008).
// Missing values degrade gracefully: the UI falls back to the plain
// package version. Never throws — a version label must not break a build.
function appMeta() {
  let version = "0.1.0";
  try {
    version =
      JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8"))
        .version ?? version;
  } catch {
    // Keep the default; the footer renders the fallback.
  }
  let sha = "";
  try {
    sha = execSync("git rev-parse --short=7 HEAD", { encoding: "utf8" }).trim();
  } catch {
    // No git metadata (e.g. source tarball); SHA stays empty.
  }
  return { version, sha, builtAt: new Date().toISOString() };
}

const meta = appMeta();

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(meta.version),
    __APP_SHA__: JSON.stringify(meta.sha),
    __APP_BUILT_AT__: JSON.stringify(meta.builtAt),
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
