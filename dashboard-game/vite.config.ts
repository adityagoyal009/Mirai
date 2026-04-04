import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
  plugins: [react()],
  server: { port: 3001 },
  // When building for production (served from FastAPI at /game/), set base path
  base: command === "build" ? "/game/" : "/",
}));
