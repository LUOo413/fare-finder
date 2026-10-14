import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Plain client-side SPA: `vite build` emits a static site to dist/.
// Deep links (e.g. /app) are rewritten to index.html by vercel.json.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    tsconfigPaths: true,
    dedupe: ["react", "react-dom"],
  },
  build: {
    outDir: "dist",
  },
});
