# Upstream Upgrade A → D — Task Checklist

> **Plan:** `tasks/plan.md`  
> **Conflict policy:** upstream hay hơn → lấy upstream; cả hai hay → gộp; product-only → giữ overlay.  
> **Sau mỗi phase:** chạy Stability Gate trong `tasks/plan.md` — fail thì dừng.

**Overlay giữ:** `api/services/omnichannel/**`, omnichannel controllers/migrations, `landing/**`, `billing_saas/**`, `zalo-personal-worker/**`

---

## Phase 0: Prep

### Task 0.1: Branch + backup WIP

**Description:** Tạo branch nâng cấp; đảm bảo WIP local không mất khi vendor.

**Acceptance criteria:**
- [ ] Branch `upgrade/upstream-a-to-d` từ `main` hiện tại
- [ ] WIP dirty tree: stash hoặc commit tạm / branch `backup/pre-upstream-upgrade-YYYYMMDD`
- [ ] `git fetch upstream --tags` đã chạy

**Verification:**
- [ ] `git status` sạch trên branch upgrade (hoặc chỉ file plan)
- [ ] Tag `1.14.2`, `1.15.0`, `1.16.1` resolve được

**Dependencies:** None  
**Files likely touched:** (git only)  
**Estimated scope:** S

---

### Task 0.2: Custom inventory freeze

**Description:** Liệt kê overlay + hotspot để vendor không xóa nhầm.

**Acceptance criteria:**
- [ ] File inventory (có thể `tasks/upstream-overlay-inventory.md`) gồm: path overlay, migration local, hotspot 3-way
- [ ] Ghi rõ lệnh copy/exclude sẽ dùng khi vendor

**Verification:**
- [ ] Review nhanh: mọi file omnichannel trong inventory
- [ ] Hotspot list khớp plan (generators, completion, workflow, models, docker)

**Dependencies:** Task 0.1  
**Files likely touched:**
- `tasks/upstream-overlay-inventory.md` (new)

**Estimated scope:** S

---

### Task 0.3: Baseline Stability Gate (pre-upgrade)

**Description:** Chạy gate trên code hiện tại để có baseline so sánh.

**Acceptance criteria:**
- [ ] Omnichannel unit tests chạy xong; ghi số pass/fail
- [ ] Core helpers/workflow tests (nếu fail sẵn → ghi known-fail, không coi là regression sau này nếu không xấu hơn)

**Verification:**
- [ ] `make test TARGET_TESTS=./api/tests/unit_tests/services/omnichannel`
- [ ] Ghi kết quả vào cuối `tasks/todo.md` hoặc log session

**Dependencies:** Task 0.1  
**Files likely touched:** (none / log only)  
**Estimated scope:** S

### Checkpoint: Prep
- [ ] Branch sẵn sàng, inventory có, baseline gate đã ghi
- [ ] **Human OK** trước Phase A

---

## Phase A: → `1.14.2`

### Task A.1: Vendor platform tree từ tag `1.14.2`

**Description:** Worktree/checkout `1.14.2`; copy vào working tree các path platform (`api/`, `web/`, `docker/`, `packages/`, …) **trừ** overlay.

**Acceptance criteria:**
- [ ] `api/pyproject.toml` + `web/package.json` version = `1.14.2` (hoặc khớp tag)
- [ ] Overlay paths vẫn tồn tại sau copy
- [ ] Không còn thiếu file platform quan trọng so với tag (spot-check `api/services/`, `api/core/workflow/`)

**Verification:**
- [ ] Diff version files vs `1.14.2`
- [ ] `git status` cho thấy overlay còn

**Dependencies:** Checkpoint Prep  
**Files likely touched:** bulk under `api/`, `web/`, `docker/`, `packages/`  
**Estimated scope:** M (mechanical; nhiều file nhưng 1 thao tác vendor)

---

### Task A.2: Re-apply omnichannel overlay + wire imports

**Description:** Đảm bảo omnichannel services/controllers/routes vẫn register trên codebase 1.14.2.

**Acceptance criteria:**
- [ ] `api/services/omnichannel/**` intact
- [ ] Controllers omnichannel import được; blueprint/register không 404 route chính
- [ ] Tasks `api/tasks/omnichannel_tasks.py` (nếu có) vẫn load

**Verification:**
- [ ] Import smoke: `uv run --project api python -c "from services.omnichannel..."` (module chính)
- [ ] Grep register route omnichannel còn trong console init

**Dependencies:** Task A.1  
**Files likely touched:**
- `api/controllers/console/__init__.py`
- `api/controllers/console/workspace/*`
- `api/services/omnichannel/**`

**Estimated scope:** M

---

### Task A.3: Resolve hotspot — app generators / pipelines / completion

**Description:** 3-way resolve file hotspot theo conflict policy; giữ hook omnichannel nếu cần inputs/reply.

**Acceptance criteria:**
- [ ] Các file hotspot list A compile được
- [ ] Upstream engine/security wins trừ chỗ cần hook product
- [ ] Không để lại conflict marker

**Verification:**
- [ ] `make test TARGET_TESTS=./api/tests/unit_tests/core/app/helpers`
- [ ] Related controller tests nếu có

**Dependencies:** Task A.2  
**Files likely touched:**
- `api/core/app/apps/**/app_generator.py`
- `api/core/app/**/generate_task_pipeline.py`
- `api/core/app/task_pipeline/easy_ui_based_generate_task_pipeline.py`
- `api/controllers/console/app/completion.py`
- `api/controllers/console/app/workflow.py`
- `api/controllers/web/completion.py`

**Estimated scope:** M

---

### Task A.4: Resolve hotspot — workflow runtime / models / feature config

**Description:** Gộp `node_runtime`, models, feature flags; migrations upstream 1.14.x + giữ omnichannel migrations.

**Acceptance criteria:**
- [ ] Không trùng revision id migration
- [ ] `models` load được với cả schema mới upstream + cột omnichannel
- [ ] Feature config có flag mới upstream; flag custom vẫn còn

**Verification:**
- [ ] `make test TARGET_TESTS=./api/tests/unit_tests/core/workflow`
- [ ] List `api/migrations/versions` — cả hai chuỗi có mặt

**Dependencies:** Task A.3  
**Files likely touched:**
- `api/core/workflow/node_runtime.py`
- `api/models/model.py`
- `api/models/account.py`
- `api/configs/feature/__init__.py`
- `api/migrations/versions/**`

**Estimated scope:** M

---

### Task A.5: Docker / env Phase A

**Description:** Cập nhật compose + `.env.example` theo 1.14.2; giữ custom nginx/tunnel/omnichannel volumes nếu còn cần.

**Acceptance criteria:**
- [ ] `docker compose ... config` OK
- [ ] Env mới 1.14.x documented trong example
- [ ] Custom service/volume omnichannel không bị xóa vô tình

**Verification:**
- [ ] `docker compose -f docker/docker-compose.yaml config`
- [ ] Diff `.env.example` reviewed

**Dependencies:** Task A.4  
**Files likely touched:**
- `docker/docker-compose.yaml`
- `docker/docker-compose-template.yaml`
- `docker/.env.example`
- `api/.env.example`

**Estimated scope:** M

---

### Task A.6: Stability Gate A + fix regressions

**Description:** Chạy full Stability Gate Phase A; sửa đến khi omnichannel + core xanh (hoặc chỉ còn known-fail đã ghi ở baseline).

**Acceptance criteria:**
- [ ] Gate automated commands pass (trừ known-fail baseline)
- [ ] Manual smoke checklist Phase A
- [ ] Version = 1.14.2

**Verification:**
- [ ] Toàn bộ Stability Gate trong `tasks/plan.md`
- [ ] `uv run --project api flask db upgrade` trên DB dev/staging

**Dependencies:** Task A.5  
**Files likely touched:** (fixes as needed)  
**Estimated scope:** M

### Checkpoint A
- [ ] Gate A xanh
- [ ] Omnichannel inbox smoke OK
- [ ] **Human review trước Phase B**

---

## Phase B: → `1.15.0`

### Task B.1: Vendor platform tree từ tag `1.15.0`

**Description:** Giống A.1 nhưng target `1.15.0`; giữ overlay.

**Acceptance criteria:**
- [ ] Version files = `1.15.0`
- [ ] Overlay còn
- [ ] `cli/` xuất hiện nếu có trong tag

**Verification:**
- [ ] Spot-check `cli/`, `api/controllers/openapi/`
- [ ] Overlay paths exist

**Dependencies:** Checkpoint A  
**Files likely touched:** bulk platform  
**Estimated scope:** M

---

### Task B.2: Re-apply overlay + fix breakages từ RBAC/API churn

**Description:** Omnichannel controllers/services adapt permission decorators / member APIs nếu 1.15 đổi.

**Acceptance criteria:**
- [ ] Omnichannel routes vẫn auth được với model quyền mới (hoặc feature-flag legacy path documented)
- [ ] Mini CRM / members hooks không 500 vì thiếu RBAC binding

**Verification:**
- [ ] `make test TARGET_TESTS=./api/tests/unit_tests/services/omnichannel`
- [ ] `make test TARGET_TESTS=./api/tests/unit_tests/controllers/console/workspace`

**Dependencies:** Task B.1  
**Files likely touched:**
- `api/controllers/console/workspace/**`
- `api/services/omnichannel/**`
- RBAC-touched account/member files as needed

**Estimated scope:** M

---

### Task B.3: Resolve hotspot generators/pipelines lại (delta 1.15)

**Description:** Re-resolve chỉ file diff `1.14.2..1.15.0` trên hotspot; giữ hook đã gộp ở A.

**Acceptance criteria:**
- [ ] Không mất omnichannel hooks từ A
- [ ] Upstream 1.15 behavior (HITL/CoT/polling) không bị regress cố ý

**Verification:**
- [ ] Core app helper + workflow unit tests

**Dependencies:** Task B.2  
**Files likely touched:** same hotspot set as A.3–A.4  
**Estimated scope:** M

---

### Task B.4: Migrations 1.15 + HITL/OAuth tables + omnichannel chain

**Description:** Thêm migrations upstream 1.15; chạy upgrade; xử lý `backfill-plugin-auto-upgrade` theo release notes.

**Acceptance criteria:**
- [ ] `flask db upgrade` success
- [ ] Omnichannel tables vẫn query được
- [ ] HITL/human_input tables tồn tại nếu trong 1.15

**Verification:**
- [ ] DB upgrade log clean
- [ ] Spot SQL/ORM read omnichannel config row

**Dependencies:** Task B.3  
**Files likely touched:**
- `api/migrations/versions/**`

**Estimated scope:** M

---

### Task B.5: RBAC migrate CLI + permission smoke

**Description:** Chạy `flask rbac-migrate-member-roles` và `flask rbac-migrate-dataset-permissions` (theo 1.15/1.16 notes); verify member access.

**Acceptance criteria:**
- [ ] CLI chạy không error trên DB staging
- [ ] Owner/admin/editor vào console được
- [ ] Không lock-out toàn workspace

**Verification:**
- [ ] Manual login smoke
- [ ] Document bất kỳ permission gap với Mini CRM

**Dependencies:** Task B.4  
**Files likely touched:**
- `api/commands/rbac.py` (vendor)
- possibly workspace member controllers

**Estimated scope:** M

---

### Task B.6: Docker/env Phase B + OpenAPI/difyctl optional

**Description:** Env mới 1.15 (`OPENAPI_*`, SSRF, …); compose; optional smoke `cli` binary/docs path.

**Acceptance criteria:**
- [ ] `.env.example` có key 1.15 cần thiết
- [ ] `docker compose config` OK
- [ ] Ghi chú: difyctl optional — không block gate nếu chưa cài binary

**Verification:**
- [ ] Compose config
- [ ] Diff env reviewed

**Dependencies:** Task B.5  
**Files likely touched:**
- `docker/**`
- `api/.env.example`
- `cli/**` (vendor only)

**Estimated scope:** M

---

### Task B.7: Stability Gate B + fix

**Description:** Full Stability Gate + extras RBAC/HITL smoke.

**Acceptance criteria:**
- [ ] Automated gate pass
- [ ] Manual smoke + member access OK
- [ ] Version = 1.15.0

**Verification:**
- [ ] Stability Gate + Phase B extras trong plan

**Dependencies:** Task B.6  
**Files likely touched:** fixes as needed  
**Estimated scope:** M

### Checkpoint B
- [ ] Gate B xanh, RBAC không lock-out
- [ ] **Human review trước Phase C**

---

## Phase C: → `1.16.1`

### Task C.1: Vendor platform + `dify-agent` + `dify-agent-runtime` từ `1.16.1`

**Description:** Vendor full tree 1.16.1 gồm agent packages; giữ overlay.

**Acceptance criteria:**
- [ ] Version = `1.16.1`
- [ ] `dify-agent/`, `dify-agent-runtime/` present
- [ ] Overlay present

**Verification:**
- [ ] Tree spot-check agent dirs
- [ ] Overlay intact

**Dependencies:** Checkpoint B  
**Files likely touched:** bulk + new top-level packages  
**Estimated scope:** M

---

### Task C.2: Re-apply overlay; adapt agent-related console if collisions

**Description:** Đảm bảo omnichannel không bị route/name collision với Agent console APIs mới.

**Acceptance criteria:**
- [ ] Omnichannel routes unique
- [ ] Agent routes load (nếu enabled)
- [ ] Tests omnichannel vẫn pass sau adapt

**Verification:**
- [ ] Omnichannel unit tests
- [ ] Import agent services không crash app factory

**Dependencies:** Task C.1  
**Files likely touched:**
- `api/controllers/console/**`
- `api/services/agent/**` (vendor)
- `api/services/omnichannel/**`

**Estimated scope:** M

---

### Task C.3: Hotspot resolve delta `1.15.0..1.16.1`

**Description:** Re-resolve generators/pipelines/workflow/models cho delta Agent/HITL/security.

**Acceptance criteria:**
- [ ] Conflict markers gone
- [ ] Omnichannel hooks preserved where still required
- [ ] Prefer upstream sandbox/security code

**Verification:**
- [ ] Core unit tests helpers + workflow

**Dependencies:** Task C.2  
**Files likely touched:** hotspot set  
**Estimated scope:** M

---

### Task C.4: Migrations 1.16.1 (agent domain, archive, telemetry, …)

**Description:** Apply upstream migrations; keep omnichannel chain; upgrade DB.

**Acceptance criteria:**
- [ ] `flask db upgrade` OK
- [ ] Agent tables exist; omnichannel tables intact

**Verification:**
- [ ] Upgrade log; ORM smoke both domains

**Dependencies:** Task C.3  
**Files likely touched:**
- `api/migrations/versions/**`

**Estimated scope:** M

---

### Task C.5: Docker Agent sandbox + tokens

**Description:** Mang compose changes: `agent_backend`, sandbox networks, Squid proxy, `DIFY_AGENT_API_TOKEN` / `AGENT_BACKEND_API_TOKEN`. Có thể dùng compose profile để tắt Agent runtime nếu chưa deploy.

**Acceptance criteria:**
- [ ] Compose config validates với và không với agent profile (nếu tách)
- [ ] `.env.example` có token keys + cảnh báo đổi default
- [ ] Custom omnichannel volumes/services retained

**Verification:**
- [ ] `docker compose ... config`
- [ ] Env reviewed

**Dependencies:** Task C.4  
**Files likely touched:**
- `docker/docker-compose.yaml`
- `docker/docker-compose-template.yaml`
- `docker/envs/**`
- `api/.env.example`

**Estimated scope:** M

---

### Task C.6: Web Agent UI vendor + branding gộp tối thiểu

**Description:** Đảm bảo web build với Agent UI; branding Vismarttech không phá layout chính. Nếu conflict branding vs upstream UI — gộp (policy #3) hoặc tạm upstream shell + giữ landing riêng.

**Acceptance criteria:**
- [ ] `pnpm type-check:tsgo` hoặc subset agreed không fail block
- [ ] Landing/custom routes vẫn serve nếu còn

**Verification:**
- [ ] `cd web && pnpm type-check:tsgo` (hoặc scoped nếu full quá nặng — ghi rõ)
- [ ] Manual: console shell load

**Dependencies:** Task C.5  
**Files likely touched:**
- `web/**`
- `packages/dify-ui/**`
- `landing/**` (only if broken)

**Estimated scope:** M

---

### Task C.7: Stability Gate C + fix

**Description:** Full gate + Agent extras (UI load hoặc profile disabled documented).

**Acceptance criteria:**
- [ ] Automated gate pass
- [ ] Manual smoke + version 1.16.1
- [ ] Agent: either smoke OK or explicitly disabled with runbook note

**Verification:**
- [ ] Stability Gate + Phase C extras

**Dependencies:** Task C.6  
**Files likely touched:** fixes  
**Estimated scope:** M

### Checkpoint C
- [ ] Gate C xanh
- [ ] **Human review trước Phase D**

---

## Phase D: → `upstream/main`

### Task D.1: Inventory delta `1.16.1..upstream/main`

**Description:** Liệt kê feat/risk (agent skills, app deploy v2, New RAG/KnowledgeFS, tracing). Quyết định **include / defer** từng cụm.

**Acceptance criteria:**
- [ ] Short written include/defer list trong `tasks/` hoặc section Gate D
- [ ] New RAG deferred nếu high-risk chưa sẵn sàng

**Verification:**
- [ ] Human agrees include/defer list

**Dependencies:** Checkpoint C  
**Files likely touched:**
- `tasks/upstream-main-delta.md` (new)

**Estimated scope:** S

---

### Task D.2: Selective vendor included deltas

**Description:** Chỉ mang cụm đã include; không blind copy toàn `main` nếu defer RAG.

**Acceptance criteria:**
- [ ] Included paths updated
- [ ] Deferred paths untouched / documented
- [ ] Overlay intact

**Verification:**
- [ ] Diffstat vs 1.16.1 matches include list
- [ ] Omnichannel tests still planned to run

**Dependencies:** Task D.1  
**Files likely touched:** per include list  
**Estimated scope:** M

---

### Task D.3: Hotspot + migration delta post-1.16.1

**Description:** Resolve conflicts; apply only migrations for included features.

**Acceptance criteria:**
- [ ] DB upgrade OK for included migrations
- [ ] No broken imports from half-vendored features

**Verification:**
- [ ] `flask db upgrade`
- [ ] Import smoke app factory

**Dependencies:** Task D.2  
**Files likely touched:** hotspots + migrations  
**Estimated scope:** M

---

### Task D.4: Docker/env delta main

**Description:** Env/compose keys mới cho included features only.

**Acceptance criteria:**
- [ ] Compose config OK
- [ ] No required secret missing for enabled profiles

**Verification:**
- [ ] `docker compose ... config`

**Dependencies:** Task D.3  
**Files likely touched:**
- `docker/**`
- `api/.env.example`

**Estimated scope:** S

---

### Task D.5: Stability Gate D + fix

**Description:** Full gate; confirm A–C behaviors không regress; deferred features không được gọi nhầm.

**Acceptance criteria:**
- [ ] Automated gate pass
- [ ] Manual smoke OK
- [ ] Deferred features documented as off/absent

**Verification:**
- [ ] Stability Gate + Gate D notes

**Dependencies:** Task D.4  
**Files likely touched:** fixes  
**Estimated scope:** M

### Checkpoint D
- [ ] Gate D xanh
- [ ] Include/defer list finalized
- [ ] **Human review — release candidate**

---

## Closing

### Task Z.1: Upgrade report

**Description:** Tóm tắt version cuối, overlay còn lại, known gaps, lệnh migrate production.

**Acceptance criteria:**
- [ ] Short report in `tasks/upstream-upgrade-report.md`
- [ ] Links to gates results

**Verification:**
- [ ] Human can follow production upgrade steps from report

**Dependencies:** Checkpoint D  
**Files likely touched:**
- `tasks/upstream-upgrade-report.md`

**Estimated scope:** S

---

## Baseline / Gate log (điền khi chạy)

| Gate | Date | Omnichannel tests | Core tests | db upgrade | Notes |
|------|------|-------------------|------------|------------|-------|
| Baseline 0.3 | | | | | |
| A | | | | | |
| B | | | | | |
| C | | | | | |
| D | | | | | |


## Session progress 2026-08-25
- Branch: upgrade/upstream-a-to-d
- Snapshot: C:\chatbot\dify-backup-pre-upstream-20260825
- Worktree: C:\chatbot\dify-upstream-1.14.2
- Version files: 1.14.2
- Overlay restored; models/celery/config/console wired
- docker compose build api: in progress


### Gate A log (2026-08-25)
- dify-api:local rebuilt from 1.14.2 + overlay
- API healthy after MiniCrmBusinessLine + merge migration k7l8m9n0o1p2
- Omnichannel unit tests: **109 passed, 24 failed** (baseline was 80/21; failure set largely same messenger/billing/oauth mocks)
- Compose: custom dify-api:local restored

## Gate results (session 2026-08-27)

- Phase A/B: omnichannel **109 passed / 24 failed** (known messenger/billing/oauth mocks)
- Phase C (1.16.1): API healthy ersion=1.16.1; DB head m9n0o1p2q3r4; omnichannel **109 passed / 24 failed** (same known fails)
- Docker: api/worker healthy, beat running
- Phase D: **851 commits** on upstream/main after 1.16.1 � selective vendor not applied yet (needs human priority pick)

