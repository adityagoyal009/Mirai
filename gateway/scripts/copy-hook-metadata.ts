// copy-hook-metadata.ts — Copies bundled hook metadata (HOOK.md) files to dist.
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const bundledDir = path.join(root, "src", "hooks", "bundled");
const distDir = path.join(root, "dist", "hooks", "bundled");

if (!fs.existsSync(bundledDir)) {
  console.log("[hooks] No bundled hooks found — skipping");
  process.exit(0);
}

for (const entry of fs.readdirSync(bundledDir, { withFileTypes: true })) {
  if (!entry.isDirectory()) continue;
  const hookMd = path.join(bundledDir, entry.name, "HOOK.md");
  if (fs.existsSync(hookMd)) {
    const destDir = path.join(distDir, entry.name);
    fs.mkdirSync(destDir, { recursive: true });
    fs.copyFileSync(hookMd, path.join(destDir, "HOOK.md"));
  }
}
console.log("[hooks] Copied bundled hook metadata to dist/");
