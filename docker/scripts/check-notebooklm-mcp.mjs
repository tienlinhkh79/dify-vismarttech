/** Quick MCP health check for notebooklm-mcp container. */
const base = process.env.MCP_URL ?? "http://127.0.0.1:8010/mcp";
const headers = {
  "Content-Type": "application/json",
  Accept: "application/json, text/event-stream",
};

function parseSse(text) {
  for (const line of text.split("\n")) {
    if (line.startsWith("data: ")) {
      return JSON.parse(line.slice(6));
    }
  }
  throw new Error(`No SSE data in response: ${text.slice(0, 200)}`);
}

async function post(body, sessionId) {
  const h = { ...headers };
  if (sessionId) h["mcp-session-id"] = sessionId;
  const res = await fetch(base, { method: "POST", headers: h, body: JSON.stringify(body) });
  const text = await res.text();
  return { sessionId: res.headers.get("mcp-session-id") ?? sessionId, data: parseSse(text) };
}

const init = await post({
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "check-script", version: "1.0" },
  },
});
const sid = init.sessionId;
await post({ jsonrpc: "2.0", method: "notifications/initialized", params: {} }, sid);
const health = await post(
  { jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "get_health", arguments: {} } },
  sid,
);
console.log(JSON.stringify(health.data, null, 2));
