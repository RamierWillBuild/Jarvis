import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Hot Module Replacement is on by default in `vite dev`.
// The polling watcher makes HMR reliable inside Docker volume mounts.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    watch: { usePolling: true },
  },
});
