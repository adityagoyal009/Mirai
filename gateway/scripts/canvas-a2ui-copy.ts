// canvas-a2ui-copy.ts — Copies a2ui assets to dist.
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const src = path.join(root, "src", "canvas-host", "a2ui");
const dest = path.join(root, "dist", "canvas-host", "a2ui");

if (fs.existsSync(src)) {
  fs.mkdirSync(dest, { recursive: true });
  for (const file of fs.readdirSync(src)) {
    fs.copyFileSync(path.join(src, file), path.join(dest, file));
  }
  console.log("[a2ui] Copied to dist/canvas-host/a2ui/");
} else {
  console.log("[a2ui] No source assets found — skipping");
}
