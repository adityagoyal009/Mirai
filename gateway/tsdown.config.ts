import { readFileSync, existsSync } from "node:fs";
import { defineConfig } from "tsdown";

const pkg = JSON.parse(readFileSync("./package.json", "utf8"));
const version = pkg.version ?? "0.0.0";

// Build entry map from package.json exports
const entries: Record<string, string> = {
  entry: "src/entry.ts",
  index: "src/index.ts",
  extensionAPI: "src/extensionAPI.ts",
};

const exports = pkg.exports ?? {};
for (const [key, value] of Object.entries(exports)) {
  const target = typeof value === "object" && value !== null
    ? (value as Record<string, string>).default
    : value;
  if (typeof target !== "string" || !target.startsWith("./dist/") || !target.endsWith(".js")) {
    continue;
  }
  const entryName = target.replace("./dist/", "").replace(".js", "");
  const srcPath = `src/${entryName}.ts`;
  // Only include entries whose source files exist
  if (!(entryName in entries) && existsSync(srcPath)) {
    entries[entryName] = srcPath;
  }
}

export default defineConfig({
  entry: entries,
  outDir: "dist",
  format: "esm",
  target: "node22",
  platform: "node",
  fixedExtension: false,
  clean: true,
  splitting: true,
  sourcemap: false,
  dts: false,
  deps: {
    // Externalize all node_modules AND missing monorepo extension imports
    // Match only paths like ../../extensions/ or ../extensions/ (relative to src files)
    neverBundle: [/^[^./]/, /\.\.\/extensions\//],
  },
  define: {
    __MIRAI_VERSION__: JSON.stringify(version),
  },
});
