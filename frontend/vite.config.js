import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: Vite on :5173 proxies /api to Flask on :5000.
// Build: output goes straight into backend/static so Flask can serve it.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:5000" },
  },
  build: {
    outDir: "../backend/static",
    emptyOutDir: true,
    chunkSizeWarningLimit: 1200,
  },
});
