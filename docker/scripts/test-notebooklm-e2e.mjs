/** E2E test: add notebook (if URL env set) + ask_question + proxy /retrieval */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const NOTEBOOK_URL = process.env.NOTEBOOK_URL ?? "";
const QUERY = process.env.QUERY ?? "What is this notebook about? Summarize in 2 sentences.";
const PROXY_URL = process.env.PROXY_URL ?? "http://127.0.0.1:8080";
const PROXY_KEY = process.env.PROXY_KEY ?? "test-secret";

function unwrap(result) {
  const block = result?.content?.find((c) => c.type === "text");
  if (!block?.text) return result;
  try {
    const parsed = JSON.parse(block.text);
    return parsed.data ?? parsed;
  } catch {
    return block.text;
  }
}

const transport = new StdioClientTransport({
  command: "cmd.exe",
  args: ["/c", "npx", "notebooklm-mcp@latest"],
  env: { ...process.env, HEADLESS: "true" },
});
const client = new Client({ name: "dify-e2e-test", version: "1.0.0" });
await client.connect(transport);

const health = unwrap(await client.callTool({ name: "get_health", arguments: {} }));
console.log("1) HEALTH authenticated:", health?.authenticated);
if (!health?.authenticated) {
  console.error("FAIL: chua authenticated");
  process.exit(1);
}

let notebooks = unwrap(await client.callTool({ name: "list_notebooks", arguments: {} }))?.notebooks ?? [];
console.log("2) Local notebooks:", notebooks.length);

if (notebooks.length === 0 && NOTEBOOK_URL) {
  console.log("3) Adding notebook from NOTEBOOK_URL...");
  const added = unwrap(
    await client.callTool({
      name: "add_notebook",
      arguments: {
        url: NOTEBOOK_URL,
        name: "Test Notebook",
        description: "E2E test notebook",
        topics: ["test"],
      },
    }),
  );
  const nb = added?.notebook ?? added;
  if (!nb?.id) {
    console.error("FAIL add_notebook:", added);
    process.exit(1);
  }
  notebooks = [nb];
  console.log("   Added id:", nb.id);
}

if (notebooks.length === 0) {
  console.error("FAIL: khong co notebook. Set NOTEBOOK_URL=https://notebooklm.google.com/notebook/...");
  process.exit(1);
}

const notebookId = notebooks[0].id;
console.log("4) ask_question on", notebookId, "...");
const answer = unwrap(
  await client.callTool(
    {
      name: "ask_question",
      arguments: {
        question: QUERY,
        notebook_id: notebookId,
        source_format: "json",
      },
    },
    undefined,
    { timeout: 600_000, maxTotalTimeout: 600_000 },
  ),
);
console.log("   Answer preview:", String(answer?.answer ?? answer).slice(0, 400));

console.log("5) Proxy /retrieval ...");
const res = await fetch(`${PROXY_URL}/retrieval`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${PROXY_KEY}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    query: QUERY,
    knowledge_id: notebookId,
    retrieval_setting: { top_k: 3 },
  }),
});
const body = await res.text();
console.log("   HTTP", res.status);
console.log("   Body preview:", body.slice(0, 600));
if (!res.ok) {
  process.exit(1);
}

await transport.close();
console.log("OK - E2E test passed");
