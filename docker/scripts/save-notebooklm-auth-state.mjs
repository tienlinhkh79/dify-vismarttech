/** Save browser_state from existing MCP chrome profile (after manual login). */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import os from "node:os";

const dataDir = path.join(os.homedir(), "AppData", "Local", "notebooklm-mcp", "Data");
const profileDir = path.join(dataDir, "chrome_profile");
const stateDir = path.join(dataDir, "browser_state");
const stateFile = path.join(stateDir, "state.json");

mkdirSync(stateDir, { recursive: true });

console.log("Mo Chrome voi profile MCP...");
const context = await chromium.launchPersistentContext(profileDir, {
  headless: false,
  channel: "chrome",
  args: ["--disable-blink-features=AutomationControlled"],
});

const page = context.pages()[0] ?? (await context.newPage());
await page.goto("https://notebook.google.com/", { waitUntil: "domcontentloaded", timeout: 120_000 });
console.log("URL hien tai:", page.url());

if (!page.url().includes("notebook.google.com") && !page.url().includes("notebooklm.google.com")) {
  console.error("Chua vao duoc Gemini Notebook. Hay dang nhap trong Chrome roi chay lai.");
  await context.close();
  process.exit(1);
}

await context.storageState({ path: stateFile });
try {
  const sessionStorageData = await page.evaluate(() => {
    const storage = {};
    for (let i = 0; i < sessionStorage.length; i += 1) {
      const key = sessionStorage.key(i);
      if (key) storage[key] = sessionStorage.getItem(key) || "";
    }
    return JSON.stringify(storage);
  });
  writeFileSync(path.join(stateDir, "session.json"), sessionStorageData, "utf8");
} catch {
  // optional
}

console.log("Da luu browser state:", stateFile);
await context.close();
process.exit(0);
