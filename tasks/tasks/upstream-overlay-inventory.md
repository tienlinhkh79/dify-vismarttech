# Upstream overlay inventory (frozen before Phase A vendor)

**Snapshot filesystem:** `C:\chatbot\dify-backup-pre-upstream-20260825`  
**Upgrade branch:** `upgrade/upstream-a-to-d`  
**Target A:** tag `1.14.2` (`fd98157034d39a82eb899f67878fa344e03a4cf2`)

## Overlay — never delete when vendoring

### API
- `api/services/omnichannel/**`
- `api/controllers/console/workspace/omnichannel.py`
- `api/controllers/console/workspace/zalo_personal.py`
- `api/controllers/console/workspace/mini_crm.py`
- `api/controllers/console/workspace/website_widget.py`
- `api/tasks/omnichannel_tasks.py`
- `api/core/tools/builtin_tool/providers/mini_crm/**`
- `api/tests/unit_tests/services/omnichannel/**`
- `api/tests/unit_tests/controllers/console/workspace/test_omnichannel.py`
- Migrations matching: `*omnichannel*`, `*zalo*`, `*mini_crm*` under `api/migrations/versions/`

### Web
- `web/app/(commonLayout)/omnichannel/**`
- `web/app/(commonLayout)/mini-crm/**`
- `web/app/components/mini-crm/**`
- `web/app/components/base/chat/omnichannel-rich-reply/**`
- `web/app/components/header/mini-crm-nav/**`
- `web/app/components/header/account-setting/channels-*.tsx`
- `web/app/components/header/account-setting/zalo-personal-qr-panel.tsx`
- `web/app/components/header/account-setting/channel-setup-config.ts`

### Product roots
- `landing/**`
- `billing_saas/**`
- `zalo-personal-worker/**`

## Hotspot — 3-way resolve after vendor (ours snapshot + upstream tag)

- `api/core/app/apps/advanced_chat/app_generator.py`
- `api/core/app/apps/advanced_chat/generate_task_pipeline.py`
- `api/core/app/apps/agent_chat/app_generator.py`
- `api/core/app/apps/chat/app_generator.py`
- `api/core/app/task_pipeline/easy_ui_based_generate_task_pipeline.py`
- `api/core/app/helpers/chat_query.py` (ours-only — keep)
- `api/core/workflow/node_runtime.py`
- `api/controllers/console/app/completion.py`
- `api/controllers/console/app/workflow.py`
- `api/controllers/console/explore/completion.py`
- `api/controllers/web/completion.py`
- `api/models/model.py`
- `api/models/account.py`
- `api/configs/feature/__init__.py`
- `docker/docker-compose.yaml`
- `docker/docker-compose-template.yaml`
- `docker/.env.example`
- `api/.env.example`

## Vendor command intent (Phase A)

1. Worktree or checkout paths from `1.14.2` for: `api/`, `web/`, `docker/`, `packages/` (if present), root `package.json` / `pnpm-workspace.yaml` / lockfiles as in tag.
2. **Exclude** overlay paths above from overwrite (restore from snapshot after checkout if needed).
3. Restore hotspot **ours** copies from snapshot into `tasks/pre-vendor-ours-hotspots/` for merge reference, then resolve into working tree.

## Restore overlay after vendor

```powershell
$snap = 'C:\chatbot\dify-backup-pre-upstream-20260825'
Copy-Item "$snap\api\services\omnichannel" api\services\omnichannel -Recurse -Force
# … similarly for other overlay paths
```
