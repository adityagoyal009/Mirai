// write-build-info.ts — Writes dist/build-info.json with version and build metadata.
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const pkg = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));

let commit = "unknown";
try {
  commit = execSync("git rev-parse --short HEAD", { cwd: root, encoding: "utf8" }).trim();
} catch {
  // Not in a git repo or git not available
}

const buildInfo = {
  name: pkg.name ?? "mirai-gateway",
  version: pkg.version ?? "0.0.0",
  commit,
  buildTime: new Date().toISOString(),
};

const distDir = path.join(root, "dist");
fs.mkdirSync(distDir, { recursive: true });
fs.writeFileSync(path.join(distDir, "build-info.json"), JSON.stringify(buildInfo, null, 2) + "\n");
console.log(`[build-info] Wrote dist/build-info.json (v${buildInfo.version}, ${buildInfo.commit})`);
