# NotebookLM Integration — Task Checklist

> **Scope:** Tính năng **Knowledge mới cho Dify** — NotebookLM là nguồn kiến thức bổ sung. Không liên quan CV/JD/HR.

---

## Phase 1: Infrastructure (Windows + Docker)

### Task 1: Docker service notebooklm-mcp (Windows profile mount)

**Description:** Thêm service `notebooklm-mcp` vào Docker Compose, port 8010, mount Chrome profile từ **Windows host** (`%APPDATA%\notebooklm-mcp`).

**Acceptance criteria:**
- [ ] Service `notebooklm-mcp` trong `docker/docker-compose-template.yaml` và `docker/docker-compose.yaml`
- [ ] Env trong `docker/.env.example`: `NOTEBOOKLM_PORT`, `NOTEBOOKLM_HOST`, `NOTEBOOKLM_TRANSPORT`, `NOTEBOOKLM_AI_MARKER`, `NOTEBOOKLM_PROFILE_HOST_PATH`
- [ ] Volume bind: host `%APPDATA%\notebooklm-mcp` (hoặc `${NOTEBOOKLM_PROFILE_HOST_PATH}`) → container profile path
- [ ] Healthcheck `GET /healthz`
- [ ] Cùng network với `api` → `http://notebooklm-mcp:8010/mcp`

**Verification:**
- [ ] `docker compose up notebooklm-mcp -d` OK trên Windows + Docker Desktop
- [ ] Container đọc được profile sau Task 2 auth
- [ ] Manual: log không crash loop

**Dependencies:** None

**Files likely touched:**
- `docker/docker-compose-template.yaml`
- `docker/docker-compose.yaml`
- `docker/.env.example`

**Estimated scope:** M

---

### Task 2: Google auth trên Windows host + health verification

**Description:** One-time login Google trên **Windows** (Chrome GUI), lưu session vào `%APPDATA%\notebooklm-mcp\`, verify MCP từ Docker.

**Acceptance criteria:**
- [ ] Runbook Windows: cài Node ≥18, chạy auth trên host:
  ```powershell
  npx notebooklm-mcp@latest
  # hoặc clone repo → MCP tool setup_auth / scripts/login.mjs
  ```
- [ ] Profile tồn tại: `%APPDATA%\notebooklm-mcp\chrome_profile\` (+ `state.json` nếu có)
- [ ] Sau mount, container MCP `get_health` → authenticated
- [ ] `list_notebooks` trả ≥1 notebook; ghi notebook ID mẫu vào runbook
- [ ] **Không** chạy setup_auth trong Linux container headless (chỉ reuse profile Windows)

**Verification:**
- [ ] `docker compose exec api curl -sf http://notebooklm-mcp:8010/healthz`
- [ ] MCP `ask_question` smoke test (5–30s)
- [ ] Manual: đăng nhập Google trên Chrome Windows, thấy NotebookLM dashboard

**Dependencies:** Task 1

**Files likely touched:**
- `docker/NOTEBOOKLM.md`
- `docker/.env.example`

**Estimated scope:** S

---

### Task 3: Runbook infra (Windows)

**Description:** Tài liệu vận hành Phase 1: Windows auth, profile mount, re-auth, troubleshoot.

**Acceptance criteria:**
- [ ] `docker/NOTEBOOKLM.md`: Windows auth steps, profile paths, Docker Desktop volume bind
- [ ] Section `re_auth` khi session hết hạn
- [ ] Ghi rõ: auth **không** chạy trong container trên Windows

**Verification:**
- [ ] Dev mới follow runbook trên Windows deploy được infra

**Dependencies:** Task 2

**Files likely touched:**
- `docker/NOTEBOOKLM.md`

**Estimated scope:** XS

---

## Checkpoint: Infra Complete

- [ ] Windows profile mount OK
- [ ] `healthz` + `get_health` authenticated
- [ ] `ask_question` smoke test pass
- [ ] **Human review** → bắt Phase 2

---

## Phase 2: Workflow node (deliverable chính)

### Task 6: notebooklm-retrieval-proxy scaffold

**Description:** FastAPI service: `POST /retrieval`, `GET /health`, **Bearer auth middleware** (bắt buộc).

**Acceptance criteria:**
- [ ] Thư mục `services/notebooklm-retrieval-proxy/`
- [ ] `POST /retrieval` nhận Dify contract (`query`, `knowledge_id`, `retrieval_setting`)
- [ ] Middleware: `Authorization: Bearer ${NOTEBOOKLM_PROXY_API_KEY}` — reject 401 nếu thiếu/sai
- [ ] `GET /health` không cần auth (liveness)
- [ ] Dockerfile

**Verification:**
- [ ] `curl /health` → 200
- [ ] `POST /retrieval` không Bearer → 401
- [ ] `POST /retrieval` Bearer đúng → 200/501 (trước mapper)

**Dependencies:** Checkpoint Infra

**Files likely touched:**
- `services/notebooklm-retrieval-proxy/` (new)

**Estimated scope:** M

---

### Task 7: MCP session client + ask_question wrapper

**Description:** JSON-RPC client: initialize, `Mcp-Session-Id`, `tools/call`, retry on 400.

**Acceptance criteria:**
- [ ] `NOTEBOOKLM_MCP_URL=http://notebooklm-mcp:8010/mcp`
- [ ] Session lifecycle + retry
- [ ] `query_notebook(notebook_id, query, source_format="json")`
- [ ] `_clean_notebooklm_answer()` strip AI marker

**Verification:**
- [ ] Unit tests với mock MCP
- [ ] (Optional) integration test live MCP

**Dependencies:** Task 6

**Files likely touched:**
- `services/notebooklm-retrieval-proxy/app/mcp_client.py`
- `services/notebooklm-retrieval-proxy/tests/test_mcp_client.py`

**Estimated scope:** M

---

### Task 8: Map response → Dify `records[]`

**Description:** Map `ask_question` → External Knowledge response format.

**Acceptance criteria:**
- [ ] `{ "records": [{ "content", "score", "title", "metadata" }] }`
- [ ] `knowledge_id` request → `notebook_id` MCP arg (**per-dataset notebook**)
- [ ] `metadata.citations`, `metadata.source=notebooklm`
- [ ] Error: auth→503, timeout→504, MCP→502

**Verification:**
- [ ] Unit tests mapper fixtures
- [ ] Contract match `ExternalDatasetService.fetch_external_knowledge_retrieval`

**Dependencies:** Task 7

**Files likely touched:**
- `services/notebooklm-retrieval-proxy/app/retrieval.py`
- `services/notebooklm-retrieval-proxy/tests/test_retrieval_mapper.py`

**Estimated scope:** M

---

### Task 9: Docker compose + env wiring

**Description:** Deploy proxy, wire env, generate/set `NOTEBOOKLM_PROXY_API_KEY`.

**Acceptance criteria:**
- [ ] Service `notebooklm-retrieval-proxy` port 8080 internal
- [ ] Env: `NOTEBOOKLM_MCP_URL`, `NOTEBOOKLM_PROXY_API_KEY` trong `.env.example`
- [ ] `api` reach `http://notebooklm-retrieval-proxy:8080/retrieval`
- [ ] `depends_on`: proxy → notebooklm-mcp

**Verification:**
- [ ] Full stack `docker compose up`
- [ ] E2E POST `/retrieval` từ `api` container với Bearer

**Dependencies:** Task 8

**Files likely touched:**
- `docker/docker-compose-template.yaml`
- `docker/docker-compose.yaml`
- `docker/.env.example`

**Estimated scope:** S

---

### Task 10: External Knowledge dataset + Workflow App (Knowledge Retrieval node)

**Description:** Tạo External Knowledge API + dataset(s), build **Workflow App** có node Knowledge Retrieval nối NotebookLM.

**Acceptance criteria:**
- [ ] External API: endpoint `http://notebooklm-retrieval-proxy:8080`, **api_key = NOTEBOOKLM_PROXY_API_KEY**
- [ ] Dataset A: `external_knowledge_id` = notebook ID #1 (vd. "Product docs notebook")
- [ ] (Optional) Dataset B: notebook ID #2 — chứng minh **mỗi Knowledge dataset = 1 notebook**
- [ ] Workflow App graph:
  ```
  [Start] → [Knowledge Retrieval] → [LLM] → [Answer]
                ↑ dataset: NotebookLM External
  ```
- [ ] Node config: chọn external dataset trong UI (`KnowledgeRetrievalNode`)
- [ ] Chat test workflow: query → context từ NotebookLM → LLM trả lời
- [ ] **Không** sửa workflow omnichannel hiện có (Restaurant/Nail) trừ khi user tự chọn thêm NotebookLM dataset

**Verification:**
- [ ] Manual: 2 queries trong Workflow App test
- [ ] Workflow editor: node Knowledge Retrieval chọn được NotebookLM dataset
- [ ] 2 datasets khác notebook_id → trả context khác nhau

**Dependencies:** Task 9

**Files likely touched:**
- `docker/NOTEBOOKLM.md`
- `scripts/dev/create_notebooklm_workflow_app.py` (optional)

**Estimated scope:** M

---

### Task 11: Runbook workflow + giới hạn

**Description:** Hướng dẫn tạo NotebookLM Knowledge dataset, nối Knowledge Retrieval node, Bearer key.

**Acceptance criteria:**
- [ ] Section: "Thêm NotebookLM làm Knowledge source" (UI: External Knowledge → dataset → workflow node)
- [ ] Decision tree: **Local Knowledge** (file/website, nhanh) vs **NotebookLM** (notebook Google, grounded, chậm hơn)
- [ ] Troubleshooting: auth, proxy 401, timeout

**Verification:**
- [ ] Human review runbook complete

**Dependencies:** Task 10

**Files likely touched:**
- `docker/NOTEBOOKLM.md`

**Estimated scope:** XS

---

## Checkpoint: Phase 2 Complete

- [ ] Bearer auth proxy OK
- [ ] Workflow Knowledge Retrieval node hoạt động
- [ ] Per-notebook dataset binding OK
- [ ] Omnichannel / workflow hiện có không bị break
- [ ] **Human review** — pilot ready

---

## Checkpoint: Complete

- [ ] NotebookLM = Knowledge source trong Dify (External dataset + Retrieval node)
- [ ] Infra Windows auth documented
- [ ] Bearer key configured
- [ ] Human review
