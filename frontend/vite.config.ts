import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src")
    },
    extensions: [".mjs", ".js", ".ts", ".jsx", ".tsx", ".json"]
  },
  server: {
    proxy: {
      // Proxy all API endpoints to backend server
      "/upload-resume": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/evaluate-resume": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/analyze-experience-swaps": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
