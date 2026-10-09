# Implementation Plan: Upstream Upgrade A → D

## Overview

Nâng fork Vismarttech từ baseline **Dify 1.13.3** lên lần lượt:

| Phase | Target | Ý nghĩa |
|-------|--------|---------|
| **A** | `1.14.2` | Security, collaboration nền, workflow ổn định |
| **B** | `1.15.0` | RBAC, difyctl/OpenAPI, HITL giàu form, Agent v2 nền |
| **C** | `1.16.1` | Dify Agent open beta + sandbox hardening |
| **D** | `upstream/main` | ~797 commit sau 1.16.1 (skills, deploy v2, New RAG…) |

Mỗi phase **kết thúc bằng stability gate** (unit tests omnichannel + core hotspots + migrate + compose config). Không nhảy phase nếu gate fail. Chỉ lập plan ở bước này — **chưa implement**.

**Lịch sử Git:** `main` hiện tại không có merge-base với `upstream/main` (snapshot/rebrand). Không dùng `git merge upstream/main` trực tiếp. Dùng **vendor theo tag** + **re-apply custom overlay**.

**Conflict policy (đã chốt):**

1. Conflict → sửa cho compile/test xanh.
2. Upstream hay hơn (platform/security/engine thuần) → **lấy upstream, bỏ bản cũ của ta**.
3. Cả hai hay (upstream nền + custom omnichannel/product) → **gộp thành một implementation**.
4. Custom product-only (Zalo/Messenger/Mini CRM/landing/billing) → **giữ overlay**, upstream không có tương đương.

**Archive:** Plan NotebookLM cũ nằm tại `tasks/notebooklm-plan.md` / `tasks/notebooklm-todo.md` (không thuộc scope này).

## Architecture Decisions

- **Chiến lược nâng:** Sequential A→B→C→D; mỗi mốc shipable trên branch `upgrade/upstream-a-to-d` (hoặc `upgrade/to-1.14.2` rồi merge dần).
- **Cách mang code:** Worktree/checkout tag upstream → copy/vendor thư mục platform → re-apply overlay custom → resolve hotspot bằng policy trên.
- **Overlay bất biến (không xóa khi vendor):**
  - `api/services/omnichannel/**`
  - `api/controllers/console/workspace/{omnichannel,zalo_personal,mini_crm,website_widget}.py` (+ related)
  - `api/migrations/versions/*omnichannel*` / `*zalo*` / `*mini_crm*`
  - `landing/**`, `billing_saas/**`, `zalo-personal-worker/**`
  - Branding/i18n Vismarttech chỉ đụng khi upstream redesign bắt buộc gộp
- **Hotspot 3-way bắt buộc** (cả hai bên sửa): generators/pipelines, `completion.py` / `workflow.py`, `node_runtime.py`, `models/model.py`, `configs/feature`, `docker-compose*`
- **Migrations:** Giữ **cả hai** chuỗi (upstream + omnichannel). Không reuse revision id. Sau mỗi phase: `flask db upgrade` trên DB staging/dev.
- **Docker/Agent:** Chỉ bắt buộc đầy đủ từ Phase C; Phase A/B cập nhật compose tối thiểu để boot.
- **Test gate sau mỗi phase (bắt buộc):** xem mục Stability Gate bên dưới.
- **Không** merge thẳng `upstream/main` trước khi A–C xanh.

## Dependency Graph

```
Prep: branch + baseline tests + custom inventory
    │
    ▼
Phase A: vendor 1.14.2 → re-apply overlay → hotspot resolve → migrate → GATE A
    │
    ▼
Phase B: vendor 1.15.0 → RBAC/OpenAPI/HITL → overlay → migrate + rbac CLI → GATE B
    │
    ▼
Phase C: vendor 1.16.1 → dify-agent* + docker sandbox → overlay → migrate → GATE C
    │
    ▼
Phase D: vendor upstream/main (selective) → overlay → GATE D
    │
    ▼
Human review / release candidate
```

## Stability Gate (lặp lại sau mỗi phase)

Chạy trên máy/agent sau khi code phase xong. **Fail → fix trước khi phase tiếp.**

### Automated

```bash
# Omnichannel (custom — phải xanh)
make test TARGET_TESTS=./api/tests/unit_tests/services/omnichannel

# Core đã chỉnh / hay conflict
make test TARGET_TESTS=./api/tests/unit_tests/core/app/helpers
make test TARGET_TESTS=./api/tests/unit_tests/core/workflow
make test TARGET_TESTS=./api/tests/unit_tests/controllers/console/workspace

# Lint/type tối thiểu backend
make lint
make type-check
```

### Runtime / config

```bash
# Compose validate (không cần full up nếu thiếu secret)
docker compose -f docker/docker-compose.yaml config

# Dev/staging DB only:
uv run --project api flask db upgrade
# Phase B+: flask rbac-migrate-member-roles ; flask rbac-migrate-dataset-permissions (theo release notes)
```

### Manual smoke (mỗi gate)

- [ ] Console login OK
- [ ] Mở 1 Chat/Workflow app, gửi 1 message (không 500)
- [ ] Omnichannel inbox list API hoặc UI load được
- [ ] Version string trong `api/pyproject.toml` / `web/package.json` khớp target phase

### Phase-specific extras

| Phase | Extra |
|-------|--------|
| A | Collaboration env optional; không yêu cầu Agent |
| B | RBAC: member vẫn vào workspace sau migrate; OpenAPI/difyctl optional smoke |
| C | `agent_backend` / sandbox services defined; `DIFY_AGENT_API_TOKEN` set; Agent UI load nếu bật |
| D | Không regress A–C; New RAG/features mới không phá indexing cũ |

## Task List

Tasks chi tiết + checkbox: **`tasks/todo.md`**.

### Phase 0: Prep
- Task 0.1–0.3 — branch, inventory, baseline gate

### Phase A → 1.14.2
- Task A.1–A.6 + **Checkpoint A**

### Phase B → 1.15.0
- Task B.1–B.7 + **Checkpoint B**

### Phase C → 1.16.1
- Task C.1–C.7 + **Checkpoint C**

### Phase D → upstream/main
- Task D.1–D.5 + **Checkpoint D**

### Closing
- Task Z.1 — summary + known gaps

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Disconnected git history → merge hell | High | Vendor-by-tag + overlay; không `merge upstream/main` sớm |
| Hotspot generators/pipelines conflict | High | Resolve từng file; prefer upstream engine + giữ hook omnichannel |
| Migration id / date collision | High | Inventory trước; rename local only nếu trùng; test `db upgrade` |
| RBAC lock-out workspace (B) | High | Backup DB; chạy migrate CLI; test member login trước Gate B |
| Agent sandbox docker phức tạp (C) | Med | Có thể disable Agent profile compose nếu chưa cần; vẫn mang code/migrations |
| `web/app` redesign quá lớn | High | Phase A–C: ưu tiên API/docker ổn; web vendor có kiểm soát, branding gộp dần |
| Phase D quá nóng (New RAG) | Med | Selective vendor; skip KnowledgeFS nếu phá indexing — ghi rõ trong Gate D |
| Uncommitted local WIP mất | High | Task 0.1: stash/commit WIP hoặc branch backup trước vendor |

## Open Questions (chốt lúc implement, không chặn plan)

- Production có cần **bật Agent** ngay ở Phase C, hay chỉ mang code/disable profile?
- Web: mỗi phase vendor full `web/`, hay A/B chỉ API + docker rồi C mới full web?
- DB nào dùng cho Gate migrate (local docker volume vs staging)?

**Default đề xuất nếu không trả lời:** Agent profile optional ở C; mỗi phase vendor cả `api`+`web`+`docker` tối thiểu để version khớp; Gate migrate trên docker local.

## Human Approval Gate

Trước khi bất kỳ agent nào implement:

- [ ] Bạn đã đọc `tasks/plan.md` + `tasks/todo.md`
- [ ] Đồng ý conflict policy + overlay list
- [ ] Trả lời (hoặc chấp nhận default) Open Questions
- [ ] Explicit **“approved, start Phase 0/A”** (hoặc tương đương)

---

*Plan only — no code changes in this step.*
