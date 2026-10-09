/** Run setup_auth on Windows via local notebooklm-mcp HTTP server. */
import { execSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as sleep } from "node:timers/promises";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const scriptPath = (name) => join(scriptDir, name);

const PORT = 8012;
const MCP_URL = `http://127.0.0.1:${PORT}/mcp`;
const HEALTH_URL = `http://127.0.0.1:${PORT}/healthz`;

function killPort() {
  if (process.platform !== "win32") return;
  try {
    execSync(
      `powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort ${PORT} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"`,
      { stdio: "ignore" },
    );
  } catch {
    // port already free
  }
}

const headers = {
  "Content-Type": "application/json",
  Accept: "application/json, text/event-stream",
};

function parseSse(text) {
  const trimmed = text.trim();
  if (!trimmed) throw new Error("empty MCP response");
  if (trimmed.startsWith("{")) return JSON.parse(trimmed);
  for (const line of trimmed.split("\n")) {
    if (line.startsWith("data: ")) return JSON.parse(line.slice(6));
  }
  throw new Error(`Unexpected MCP response: ${trimmed.slice(0, 200)}`);
}

async function post(body, sessionId) {
  const h = { ...headers };
  if (sessionId) h["mcp-session-id"] = sessionId;
  const res = await fetch(MCP_URL, { method: "POST", headers: h, body: JSON.stringify(body) });
  const text = await res.text();
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`);
  return { sessionId: res.headers.get("mcp-session-id") ?? sessionId, data: parseSse(text) };
}

async function callTool(sessionId, name, args = {}) {
  const { data } = await post(
    { jsonrpc: "2.0", id: Date.now(), method: "tools/call", params: { name, arguments: args } },
    sessionId,
  );
  const block = data.result?.content?.find((c) => c.type === "text");
  if (!block?.text) return data.result ?? data;
  try {
    const parsed = JSON.parse(block.text);
    return parsed.data ?? parsed;
  } catch {
    return block.text;
  }
}

async function waitForMcpReady(timeoutMs = 120_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const health = await fetch(HEALTH_URL);
      if (!health.ok) throw new Error("health not ok");
      const init = await post({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: {
          protocolVersion: "2024-11-05",
          capabilities: {},
          clientInfo: { name: "dify-setup-probe", version: "1.0" },
        },
      });
      if (init.sessionId) {
        await post({ jsonrpc: "2.0", method: "notifications/initialized", params: {} }, init.sessionId);
        return init.sessionId;
      }
    } catch {
      // not ready yet
    }
    await sleep(2000);
  }
  throw new Error("notebooklm-mcp MCP endpoint did not become ready in time");
}

async function waitForAuth(sessionId, timeoutMs = 300_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const health = await callTool(sessionId, "get_health");
    if (health?.authenticated === true) return health;
    process.stdout.write(".");
    await sleep(5000);
  }
  throw new Error("Google login not detected within 5 minutes");
}

killPort();
await sleep(2000);

if (process.platform === "win32") {
  execSync(`cmd /c start "" /B "${scriptPath("start-notebooklm-mcp-local.cmd")}"`, {
    stdio: "ignore",
    windowsHide: true,
  });
} else {
  execSync(`npx notebooklm-mcp@latest --transport http --port ${PORT} --host 127.0.0.1 &`, {
    env: { ...process.env, HEADLESS: "false", NOTEBOOKLM_HEADLESS: "false" },
    stdio: "ignore",
  });
}

const stopServer = () => {
  killPort();
};

process.on("SIGINT", () => {
  stopServer();
  process.exit(130);
});

try {
  console.log(`Starting notebooklm-mcp on http://127.0.0.1:${PORT} ...`);
  const sessionId = await waitForMcpReady();
  console.log("MCP ready");

  console.log("Calling setup_auth — Chrome se mo de dang nhap Google...");

  const before = await callTool(sessionId, "get_health");
  console.log("Truoc auth:", before?.authenticated === true ? "da dang nhap" : "chua dang nhap");

  const setup = await callTool(sessionId, "setup_auth");
  console.log("setup_auth:", setup?.status ?? setup);

  console.log("\n>>> Hay dang nhap Google trong cua so Chrome vua mo (cho toi da 5 phut) <<<\n");
  const health = await waitForAuth(sessionId);
  console.log("\nDa dang nhap thanh cong:", health);
  console.log("\nBuoc tiep theo:");
  console.log("  cd docker");
  console.log("  docker compose --profile notebooklm restart notebooklm-mcp");
} catch (err) {
  console.error("Loi:", err.message ?? err);
  process.exitCode = 1;
} finally {
  stopServer();
}
