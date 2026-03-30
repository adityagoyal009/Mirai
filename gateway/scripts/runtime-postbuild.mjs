#!/usr/bin/env node
// runtime-postbuild.mjs — Ensures critical dist files exist after tsdown build.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const dist = path.join(root, "dist");

// Ensure dist/warning-filter.js exists (mirai.mjs imports it early).
const warningFilterPath = path.join(dist, "warning-filter.js");
if (!fs.existsSync(warningFilterPath)) {
  console.log("[postbuild] Creating stub dist/warning-filter.js");
  fs.writeFileSync(
    warningFilterPath,
    `// Auto-generated stub — installProcessWarningFilter is a no-op if the real build didn't emit it.\nexport function installProcessWarningFilter() {}\n`,
    "utf8",
  );
}

console.log("[postbuild] Runtime post-build complete.");
