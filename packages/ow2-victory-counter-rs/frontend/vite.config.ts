import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { resolve } from "path";

export default defineConfig({
  plugins: [svelte()],

  // マルチページアプリケーション設定
  build: {
    rollupOptions: {
      input: {
        obs: resolve(__dirname, "obs.html"),
        admin: resolve(__dirname, "admin.html"),
      },
    },
  },

  // 開発サーバー設定（Rustサーバーへのプロキシ）
  server: {
    port: 5173,
    proxy: {
      "/events": {
        target: "http://localhost:3000",
        changeOrigin: true,
      },
      "/api": {
        target: "http://localhost:3000",
        changeOrigin: true,
      },
      "/custom.css": {
        target: "http://localhost:3000",
        changeOrigin: true,
      },
    },
  },
});
