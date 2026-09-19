import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Local dev only: forwards /api calls to the FastAPI backend so the
      // frontend never needs CORS configured for localhost. In production,
      // API_BASE_URL (see src/config/api.config.ts) points at the real
      // domain and Nginx handles routing instead (see nginx.conf).
      "/api": {
        target: "http://localhost:8005",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    chunkSizeWarningLimit: 800, // Raises the alert ceiling to 800 kB safely
    rollupOptions: {
      output: {
        // Splits heavy node_modules dependencies into separate vendor files for browser cache efficiency
        manualChunks(id) {
          if (id.includes('node_modules')) {
            return 'vendor';
          }
        }
      }
    }
  },
});
