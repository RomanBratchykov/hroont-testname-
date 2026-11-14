import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import path from "node:path";

export default defineConfig({
  server: { host: "127.0.0.1", proxy: { "/api": { target: process.env.API_PROXY_URL || "http://127.0.0.1:8000", changeOrigin: true } } },
  plugins: [react(), tailwindcss()],

  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },

});
