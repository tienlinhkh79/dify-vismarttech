/** Debug NotebookLM page load inside Docker MCP container. */
import { chromium } from "patchright";

const notebookUrl =
  process.env.NOTEBOOK_URL ||
  "https://notebook.google.com/notebook/62135409-89d2-4bcc-9fd2-247bf40d0b35";
const profilePath = "/root/.local/share/notebooklm-mcp/chrome_profile";
const statePath = "/root/.local/share/notebooklm-mcp/browser_state/state.json";

const ctx = await chromium.launchPersistentContext(profilePath, {
  headless: true,
  storageState: statePath,
});
const page = ctx.pages()[0] ?? (await ctx.newPage());
await page.goto(notebookUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });
await page.waitForTimeout(15_000);
console.log("URL:", page.url());
console.log("Title:", await page.title());
const inputs = await page.evaluate(() =>
  Array.from(document.querySelectorAll("textarea")).map((e) => ({
    cls: e.className,
    aria: e.getAttribute("aria-label"),
    ph: e.placeholder,
    visible: e.offsetParent !== null,
  })),
);
console.log("textareas:", JSON.stringify(inputs, null, 2));
await page.screenshot({ path: "/tmp/nb-docker-debug.png", fullPage: true });
console.log("screenshot: /tmp/nb-docker-debug.png");
await ctx.close();
