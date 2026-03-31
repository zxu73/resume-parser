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
      "/upload-resume": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/evaluate-resume": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/analyze-experience-swaps": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/apply-swaps-docx": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/resume-pdf": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/resume-doc": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/download-modified-pdf": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/download-modified-docx": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
