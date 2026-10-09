# Implementation Plan: NotebookLM as Dify Knowledge Source

## Overview

**Tính năng mới cho Dify (Vismarttech):** thêm **NotebookLM** làm **nguồn kiến thức bổ sung** trong hệ Knowledge — cùng hàng với upload file, website crawl, Notion, External API.

Google NotebookLM chưa có REST API chính thức → dùng [notebooklm-mcp](https://github.com/PleasePrompto/notebooklm-mcp) làm backend, expose qua **External Knowledge API** của Dify để:

1. Tạo **Knowledge dataset** kiểu External (provider = NotebookLM notebook)
2. Nối **Knowledge Retrieval node** trong Workflow App / Chat App
3. App retrieve context từ notebook Google (grounded + citations)

**Không liên quan CV, JD, HR hay tuyển dụng** — đó chỉ là ví dụ cũ trong thảo luận trước, **đã loại khỏi scope**.

### So với Knowledge hiện có

| Nguồn Dify hiện tại | Cách hoạt động |
|---|---|
| Upload file / website / Notion | Extract → embed → vector search (nhanh) |
| **NotebookLM (mới)** | Query notebook qua MCP → grounded answer + citations (chậm hơn, nhiều tài liệu phức tạp) |

Hai loại **cùng tồn tại** — user chọn dataset phù hợp khi nối Knowledge Retrieval node.

### Phases

- **Phase 1 (infra):** Docker `notebooklm-mcp` + Google auth **Windows host**
- **Phase 2 (feature):** Retrieval proxy + External Knowledge → **Knowledge Retrieval node**
- **Out of scope:** Sync notebook → local embed (Phase 3), MCP Agent tool riêng, Audio Overview

## Architecture Decisions

| Quyết định | Lựa chọn | Lý do |
|---|---|---|
| Product framing | **Knowledge source extension** | Feature Dify Knowledge, không phải agent tool / HR app |
| UI integration | External Knowledge dataset + existing KB UI | `web/app/components/datasets/external-knowledge-base/` — không cần UI mới ngay |
| Workflow integration | **Knowledge Retrieval node** | Node có sẵn (`api/core/workflow/nodes/knowledge_retrieval/`) |
| Notebook binding | **Per dataset** (`external_knowledge_id` = notebook UUID) | Mỗi Knowledge dataset = 1 notebook Google |
| Backend | `notebooklm-retrieval-proxy` → MCP `ask_question` | Dify contract: `POST /retrieval` |
| Auth Google | **Windows host** — `%APPDATA%\notebooklm-mcp\` mount vào Docker | Máy dev Windows; Chrome GUI login 1 lần |
| Proxy security | **Bearer API key** (`NOTEBOOKLM_PROXY_API_KEY`) | Approved |
| Port MCP | **8010** internal | Tránh `CHROMA_PORT=8000` |
| AI marker | `NOTEBOOKLM_AI_MARKER=false` | Context sạch cho LLM downstream |
| Latency note | Document trong UI/docs | 5–30s/query — user chọn nguồn phù hợp |

## Dependency Graph

```
Windows: Google login (1 lần) → %APPDATA%\notebooklm-mcp\
    │
    ▼
Docker: notebooklm-mcp (:8010)
    │
    └── notebooklm-retrieval-proxy (:8080, Bearer)
              │
              ▼
Dify Knowledge: External API template + Dataset(s)
    │              (mỗi dataset ↔ 1 notebook)
    ▼
Workflow / Chat App:
  [Start] → [Knowledge Retrieval] → [LLM] → [Answer]
                ↑ chọn NotebookLM dataset
```

## Scope Boundaries

### In scope
- Infra: notebooklm-mcp + Windows profile mount
- Proxy: `/retrieval` + Bearer auth + mapper → Dify `records[]`
- Knowledge: External dataset tạo được trong Dify UI
- Workflow: Knowledge Retrieval node nối NotebookLM dataset
- Docs: khi nào dùng NotebookLM vs dataset local
- Unit tests proxy

### Out of scope
- CV / JD / HR / recruitment workflows
- MCP Tool Provider / Agent App riêng (Phase 1b — **removed**)
- Custom workflow node type mới (dùng node có sẵn)
- Sync sources → IndexingRunner / local embed
- Multi-tenant Google account per workspace (v1)
- `generate_audio` / Audio Overview

## Task List

### Phase 1: Infrastructure (Windows + Docker)

- [ ] Task 1: Docker service notebooklm-mcp (Windows profile mount)
- [ ] Task 2: Google auth trên Windows host + health verification
- [ ] Task 3: Runbook infra (Windows)

### Checkpoint: Infra Complete
- [ ] Profile mount OK, MCP authenticated, `ask_question` smoke test

### Phase 2: Knowledge feature (deliverable)

- [ ] Task 6: notebooklm-retrieval-proxy scaffold (+ Bearer auth)
- [ ] Task 7: MCP session client + ask_question wrapper
- [ ] Task 8: Map response → Dify `/retrieval` records
- [ ] Task 9: Docker compose + env wiring
- [ ] Task 10: External Knowledge dataset + Workflow Knowledge Retrieval test
- [ ] Task 11: Runbook Knowledge + workflow wiring

### Checkpoint: Feature Complete
- [ ] User tạo NotebookLM External dataset trong Knowledge UI
- [ ] Workflow node Knowledge Retrieval chọn dataset → retrieve context OK
- [ ] Nhiều dataset = nhiều notebook khác nhau
- [ ] Docs: NotebookLM vs local Knowledge

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Google session hết hạn | High | Runbook `re_auth` trên Windows |
| Query chậm (5–30s) | Med | Document; user chọn nguồn; không ép vào use case cần real-time |
| Synthesized answer ≠ chunks | Med | Document behavior; map citations vào `metadata` |
| Windows Docker profile mount | Med | Runbook path bind Docker Desktop |
| MCP session 400 | Med | Proxy retry + session re-init |

## Decisions (resolved)

| # | Quyết định |
|---|---|
| 1 | **Feature Knowledge** — nối qua Knowledge Retrieval node, mỗi dataset = 1 notebook |
| 2 | Auth **Windows host** |
| 3 | Proxy **Bearer API key** bắt buộc |
| 4 | **Không** CV/JD/HR — removed from scope |

## Key Files

| Area | Path |
|---|---|
| External retrieval contract | `api/services/external_knowledge_service.py` |
| Knowledge Retrieval node | `api/core/workflow/nodes/knowledge_retrieval/` |
| External KB UI | `web/app/components/datasets/external-knowledge-base/` |
| Docker | `docker/docker-compose.yaml`, `docker/.env.example` |

## Verification

```bash
uv run --project api pytest services/notebooklm-retrieval-proxy/tests/
docker compose exec api curl -sf http://notebooklm-mcp:8010/healthz
```
