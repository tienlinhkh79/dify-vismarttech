/**
 * Fetches https://preny.ai/en via Firecrawl and writes landing/content/preny-en.firecrawl.json
 *
 * Cloud: set FIRECRAWL_API_KEY (Bearer). Default base https://api.firecrawl.dev
 * Self-host: set FIRECRAWL_BASE_URL (e.g. http://localhost:3002). API key optional if your
 * instance does not require auth (omit header when empty).
 *
 * Optional: FIRECRAWL_ONLY_MAIN=false to scrape broader DOM (not just main content).
 *
 * Usage (repo root): pnpm --filter dify-landing scrape:preny-en
 */
import { writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const TARGET_URL = 'https://preny.ai/en'
const DEFAULT_CLOUD = 'https://api.firecrawl.dev'
const BASE = (process.env.FIRECRAWL_BASE_URL || DEFAULT_CLOUD).replace(/\/$/, '')
const apiKey = (process.env.FIRECRAWL_API_KEY || '').trim()
const onlyMainContent = process.env.FIRECRAWL_ONLY_MAIN !== 'false'

const __dirname = dirname(fileURLToPath(import.meta.url))
const outFile = join(__dirname, '..', 'content', 'preny-en.firecrawl.json')

const isCloudApi = BASE === DEFAULT_CLOUD
if (isCloudApi && !apiKey) {
  console.error(
    'Missing FIRECRAWL_API_KEY for cloud API. For self-host, set FIRECRAWL_BASE_URL (e.g. http://localhost:3002); key optional.\nSee: landing/content/preny-en.firecrawl.BLOCKER.md',
  )
  process.exit(1)
}

const body = {
  url: TARGET_URL,
  formats: ['markdown', 'html'],
  onlyMainContent,
  timeout: 30000,
}

/** @type {Record<string, string>} */
const headers = { 'Content-Type': 'application/json' }
if (apiKey)
  headers.Authorization = `Bearer ${apiKey}`

const res = await fetch(`${BASE}/v2/scrape`, {
  method: 'POST',
  headers,
  body: JSON.stringify(body),
})

const text = await res.text()
let json
try {
  json = JSON.parse(text)
}
catch {
  console.error('Non-JSON response', res.status, text.slice(0, 500))
  process.exit(1)
}

if (!res.ok) {
  console.error('Firecrawl error', res.status, json)
  process.exit(1)
}

const artifact = {
  scrapedAt: new Date().toISOString(),
  requestUrl: TARGET_URL,
  firecrawlBaseUrl: BASE,
  onlyMainContent,
  response: json,
}

writeFileSync(outFile, `${JSON.stringify(artifact, null, 2)}\n`, 'utf8')
console.log(`Wrote ${outFile}`)
