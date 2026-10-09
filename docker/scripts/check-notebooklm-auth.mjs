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
  command: process.platform === "win32" ? "cmd.exe" : "npx",
  args: process.platform === "win32" ? ["/c", "npx", "notebooklm-mcp@latest"] : ["notebooklm-mcp@latest"],
  env: { ...process.env, HEADLESS: "true" },
});
const client = new Client({ name: "dify-check", version: "1.0.0" });
await client.connect(transport);
console.log("HEALTH:", JSON.stringify(unwrap(await client.callTool({ name: "get_health", arguments: {} })), null, 2));
console.log("NOTEBOOKS:", JSON.stringify(unwrap(await client.callTool({ name: "list_notebooks", arguments: {} })), null, 2));
await transport.close();
