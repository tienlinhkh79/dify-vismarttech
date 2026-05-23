# Firecrawl scrape for `https://preny.ai/en` — **blocked**

**Status:** No `FIRECRAWL_API_KEY` was available when this was generated (cloud default).

- **Checked:** `docker/.env` in this repo (file exists; no `FIRECRAWL_API_KEY=` line).
- **Checked:** Host environment variable `FIRECRAWL_API_KEY` (empty).

## Self-hosted Firecrawl (e.g. `localhost:3002`)

If you run Firecrawl locally, point the script at your instance; **API key is optional** when the base URL is not the public cloud API:

```powershell
$env:FIRECRAWL_BASE_URL = 'http://localhost:3002'
# Optional if your stack sets a secret:
# $env:FIRECRAWL_API_KEY = 'your-local-secret'
pnpm --filter dify-landing scrape:preny-en
```

To capture more than “main content” (closer to full-page layout cues), try:

```powershell
$env:FIRECRAWL_ONLY_MAIN = 'false'
```

## Unblock (cloud): where to set the API key

1. **Recommended (team Docker stack):** add to your **local** `docker/.env` next to `docker-compose.yaml` (path: `docker/.env` from repo root, e.g. `c:\chatbot\dify\docker\.env`):

   ```env
   FIRECRAWL_API_KEY=fc-YOUR_KEY_HERE
   ```

   Do **not** commit real keys. `docker/.env` should stay untracked or private.

2. **One-off (shell only):** export or set the variable, then run the scrape script from repo root:

   - **PowerShell:** `$env:FIRECRAWL_API_KEY = 'fc-...'`
   - **bash:** `export FIRECRAWL_API_KEY='fc-...'`

3. Obtain a key from [Firecrawl](https://www.firecrawl.dev/) (dashboard / API keys).

## Generate the artifact (after key is set)

From the **repository root** (same level as `landing/` and `docker/`):

```bash
pnpm --filter dify-landing scrape:preny-en
```

Or:

```bash
node landing/scripts/scrape-preny-en.mjs
```

**Output file:** `landing/content/preny-en.firecrawl.json` (public page content only; no secrets in the JSON).

## API note (aligned with this repo’s Dify integration)

This codebase calls Firecrawl **`v2` scrape**, not `v1`:

- **Endpoint:** `POST https://api.firecrawl.dev/v2/scrape`
- **Header:** `Authorization: Bearer <FIRECRAWL_API_KEY>`
- **Implementation reference:** `api/core/rag/extractor/firecrawl/firecrawl_app.py` (`FirecrawlApp.scrape_url`)

After `preny-en.firecrawl.json` exists, align `landing/content/home-content.ts` (and related UI) to the **markdown/html** in that file, rebrand copy to **Vismarttech**, and delete or archive this blocker file if you no longer need the audit trail.
