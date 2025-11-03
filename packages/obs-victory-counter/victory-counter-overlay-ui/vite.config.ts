import { defineConfig } from "vite";

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        admin: "index.html",
        overlay: "overlay.html"
      }
    }
  },
  server: {
    port: 5173
  }
});
