import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

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
  env: { ...process.env, HEADLESS: "false", NOTEBOOKLM_HEADLESS: "false" },
});
const client = new Client({ name: "dify-check", version: "1.0.0" });
await client.connect(transport);
const health = unwrap(await client.callTool({ name: "get_health", arguments: {} }));
console.log(JSON.stringify(health, null, 2));
await transport.close();
