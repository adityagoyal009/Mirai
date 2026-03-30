// copy-export-html-templates.ts — Copies HTML templates to dist.
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const templates = [
  {
    src: "src/auto-reply/reply/export-html/template.html",
    dest: "dist/auto-reply/reply/export-html/template.html",
  },
];

for (const { src, dest } of templates) {
  const srcPath = path.join(root, src);
  const destPath = path.join(root, dest);
  if (fs.existsSync(srcPath)) {
    fs.mkdirSync(path.dirname(destPath), { recursive: true });
    fs.copyFileSync(srcPath, destPath);
    console.log(`[templates] Copied ${src}`);
  }
}
console.log("[templates] HTML template copy complete.");
