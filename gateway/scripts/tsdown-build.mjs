#!/usr/bin/env node
// tsdown-build.mjs — Runs tsdown using the project config.
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(root);

console.log("[build] Running tsdown...");
execSync("npx tsdown", {
  stdio: "inherit",
  cwd: root,
  env: { ...process.env, NODE_ENV: "production" },
});
console.log("[build] tsdown complete.");
