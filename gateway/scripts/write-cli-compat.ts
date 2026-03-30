// write-cli-compat.ts — Writes CLI compatibility shims.
// Since Mirai is a clean fork with no legacy names to support,
// this writes an empty compat map.
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const distDir = path.join(root, "dist");
fs.mkdirSync(distDir, { recursive: true });

const compat = {
  legacyNames: [],
  renamedCommands: {},
};

fs.writeFileSync(
  path.join(distDir, "cli-compat.json"),
  JSON.stringify(compat, null, 2) + "\n",
);
console.log("[cli-compat] Wrote dist/cli-compat.json");
