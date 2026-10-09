/** Patch notebooklm-mcp to accept notebook.google.com (Gemini Notebook rebrand). */
import { execSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { globSync } from "node:fs";
import path from "node:path";
import os from "node:os";

function findAuthManagerFiles() {
  const roots = [
    path.join(os.homedir(), "AppData", "Local", "npm-cache", "_npx"),
    path.join(os.homedir(), "AppData", "Roaming", "npm", "node_modules"),
  ];
  const files = [];
  for (const root of roots) {
    if (!existsSync(root)) continue;
    for (const hit of globSync(path.join(root, "**", "notebooklm-mcp", "dist", "auth", "auth-manager.js"))) {
      files.push(hit);
    }
  }
  return [...new Set(files)];
}

const OLD = 'currentUrl.startsWith("https://notebooklm.google.com/")';
const NEW =
  '(currentUrl.startsWith("https://notebooklm.google.com/") || currentUrl.startsWith("https://notebook.google.com/"))';

let patched = 0;
for (const file of findAuthManagerFiles()) {
  let text = readFileSync(file, "utf8");
  if (text.includes("notebook.google.com/")) {
    console.log("Already patched:", file);
    continue;
  }
  if (!text.includes(OLD)) {
    console.log("Pattern not found:", file);
    continue;
  }
  text = text.split(OLD).join(NEW);
  text = text.replace(
    'currentUrl.includes("notebooklm.google.com")',
    '(currentUrl.includes("notebooklm.google.com") || currentUrl.includes("notebook.google.com"))',
  );
  writeFileSync(file, text, "utf8");
  patched += 1;
  console.log("Patched:", file);
}

if (patched === 0) {
  console.error("No notebooklm-mcp auth-manager.js files patched.");
  process.exit(1);
}

console.log(`Done. Patched ${patched} file(s).`);
