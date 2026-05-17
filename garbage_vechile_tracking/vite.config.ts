import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return;
          if (id.includes("@react-google-maps")) return "vendor-maps";
          if (id.includes("@tanstack/react-query")) return "vendor-query";
          if (id.includes("react-router-dom")) return "vendor-router";
          if (id.includes("recharts")) return "vendor-charts";
          if (id.includes("react") || id.includes("react-dom")) return "vendor-react";
          return "vendor-misc";
        },
      },
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
