# Phase D — Delta inventory: `1.16.1` → `upstream/main`

**Fetched:** 2026-08-27  
**Local runtime:** `1.16.1` (API healthy)  
**Upstream tip:** `main` ≈ **1.17.0** (+39 commits after tag)  
**Span:** `1.16.1..upstream/main` ≈ **859 commits**, **~6001 files** (+304k / −221k)

| Area | Changed files (approx) |
|------|------------------------|
| `web/app` | 2867 |
| `packages` | 227 |
| `api/services` | 186 |
| `dify-agent` | 177 |
| `api/controllers` | 170 |
| `api/core` | 167 |
| `web/service` | 58 |
| `api/configs` | 14 |
| `docker` | 13 |
| `api/migrations` | 12 |
| `api/models` | 12 |

## Strategy

Do **not** merge `upstream/main`. Vendor **selectively** by area, keep overlay (`omnichannel`, Mini CRM, Zalo, `landing`, `billing_saas`, `zalo-personal-worker`).

Prefer landing on tag **`1.17.0`** first (stable release), then cherry-pick only needed post-1.17.0 fixes from `main` if required.

## Include (Phase D)

| Bucket | Why | Paths / notes |
|--------|-----|----------------|
| **Version bump → 1.17.0** | Shipable release target | `api/pyproject.toml`, `web/package.json`, compose version strings |
| **Agent / Skills** | Main product delta after 1.16 | `dify-agent/**`, agent UI, skill enable switches, RBAC on agent endpoints |
| **Workflow / HITL fixes** | Stability on existing overlay hotspots | `api/core/workflow/**`, human-input timeout/DSL align |
| **RBAC / auth hardening** | Continues Phase B surface | permission on agent/MCP GET, OAuth controller thinning, login a11y |
| **API refactors (safe)** | Cleaner boundaries, fewer future conflicts | workflow run archive/stats services, console app site command, compliance downloads |
| **Docker / agent compose** | Keep C runtime working | `docker/**` harden agent compose; re-apply custom selective mounts |
| **Migrations (upstream)** | Required for 1.17 features | `api/migrations` (12 files) — merge with omnichannel chain, no id reuse |
| **Web console (selective)** | Needed for agent/skills UX | Prefer vendor agent/skills/datasets settings slices over full `web/app` dump |

## Defer / high-risk

| Bucket | Why defer | Paths / notes |
|--------|-----------|---------------|
| **New RAG / KnowledgeFS / indexing rewrite** | High conflict with existing RAG + omnichannel retrieval; plan explicitly said defer if risky | `api/core/rag*`, dataset indexing pipelines, large knowledge UI |
| **Full `web/app` wholesale vendor** | 2800+ files; branding/i18n/overlay churn | Vendor by feature folder instead |
| **Billing SaaS upstream** | Custom `billing_saas` overlay — keep ours | Do not replace local billing; keep `/quota/info` fix |
| **Omnichannel / Mini CRM / Zalo / landing** | Product-only overlay | Never overwrite |
| **Post-1.17.0 tip-of-main churn** | Moving target (~39 commits) | Only cherry-pick if gate needs a specific fix |

## Hotspots (3-way before overwrite)

- Generators / pipelines / `completion.py` / `workflow.py` / `node_runtime.py`
- `api/models/model.py`, `api/configs/feature*`
- `docker/docker-compose.yaml` (custom image + bind mounts)
- Account / workspace / RBAC shapes already adapted for 1.16
- Any file also touched by omnichannel controllers/services

## Gate D (after vendor)

1. Omnichannel unit tests: expect baseline **109 passed / 24 failed** (no worse).
2. `flask db upgrade` → single alembic head (merge rev if needed).
3. Compose up: API health `version` matches target; Agent services if enabled.
4. Smoke: console login, chat message, omnichannel inbox, `/api/site` (billing quota) OK.
5. Confirm New RAG deferred paths were **not** required for boot.

## Suggested vendor order

1. `api/migrations` + configs/version  
2. `dify-agent` + agent-related `api/` + docker agent bits  
3. Workflow/HITL/RBAC API slices  
4. Selective `web/` for agent/skills (not full tree)  
5. Re-apply overlay → hotspot resolve → Gate D  
6. Optional: cherry-pick specific `1.17.0..main` fixes only if gate fails on known upstream bugs
