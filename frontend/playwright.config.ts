import { defineConfig } from "@playwright/test";

// Requires backend on :8000 (with seed + corpus) and frontend dev on :5173.
// scripts\start.ps1 leaves both running; e2e evidence lands in evidence/screenshots.
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  workers: 1,
  use: {
    baseURL: "http://localhost:5173",
    screenshot: "only-on-failure",
    viewport: { width: 1366, height: 850 },
  },
  reporter: [["list"]],
});
