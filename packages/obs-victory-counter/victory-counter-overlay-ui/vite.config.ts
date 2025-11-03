import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  build: {
    rollupOptions: {
      input: {
        admin: "index.html",
        overlay: "overlay.html",
      },
    },
  },
  server: {
    port: 5173,
  },
});
