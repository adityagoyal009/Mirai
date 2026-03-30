// write-plugin-sdk-entry-dts.ts — Generates merged plugin-sdk index.d.ts barrel.
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const sdkDistDir = path.join(root, "dist", "plugin-sdk");

if (!fs.existsSync(sdkDistDir)) {
  console.log("[plugin-sdk-dts] No dist/plugin-sdk/ found — skipping");
  process.exit(0);
}

// Find all .d.ts files in plugin-sdk dist
const dtsFiles = fs
  .readdirSync(sdkDistDir)
  .filter((f) => f.endsWith(".d.ts") && f !== "index.d.ts");

const lines = [
  "// Auto-generated plugin-sdk barrel — do not edit manually.",
  ...dtsFiles.map((f) => {
    const name = f.replace(".d.ts", "");
    return `export * from "./${name}.js";`;
  }),
  "",
];

fs.writeFileSync(path.join(sdkDistDir, "index.d.ts"), lines.join("\n"));
console.log(`[plugin-sdk-dts] Generated index.d.ts with ${dtsFiles.length} re-exports`);
