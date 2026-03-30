// write-cli-startup-metadata.ts — Writes CLI startup metadata for fast command routing.
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const distDir = path.join(root, "dist");
fs.mkdirSync(distDir, { recursive: true });

const metadata = {
  generatedAt: new Date().toISOString(),
  cli: {
    name: "mirai",
    entryPoint: "entry.js",
  },
};

fs.writeFileSync(
  path.join(distDir, "cli-startup-metadata.json"),
  JSON.stringify(metadata, null, 2) + "\n",
);
console.log("[cli-metadata] Wrote dist/cli-startup-metadata.json");
