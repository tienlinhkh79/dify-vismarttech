/** Debug NotebookLM page load inside Docker MCP container. */
import { chromium } from "patchright";

const notebookUrl =
  "https://notebook.google.com/notebook/0a469926-b901-426d-afe5-843096613137";
const profilePath = "/root/.local/share/notebooklm-mcp/chrome_profile";
const statePath = "/root/.local/share/notebooklm-mcp/browser_state/state.json";

const ctx = await chromium.launchPersistentContext(profilePath, {
  headless: true,
  storageState: statePath,
});
const page = ctx.pages()[0] ?? (await ctx.newPage());
await page.goto(notebookUrl, { waitUntil: "networkidle", timeout: 120_000 });
console.log("URL:", page.url());
console.log("Title:", await page.title());
const inputs = await page.evaluate(() =>
  Array.from(document.querySelectorAll("textarea")).map((e) => ({
    cls: e.className,
    aria: e.getAttribute("aria-label"),
    visible: e.offsetParent !== null,
  })),
);
console.log("textareas:", JSON.stringify(inputs, null, 2));
await page.screenshot({ path: "/tmp/nb-persistent.png", fullPage: true });
console.log("screenshot: /tmp/nb-persistent.png");
await ctx.close();
