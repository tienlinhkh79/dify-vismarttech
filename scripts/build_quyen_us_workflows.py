#!/usr/bin/env python3
"""Create and publish full omnichannel workflows for US Restaurant + Nail verticals.

Includes:
- Knowledge datasets (economy / keyword index) from scripts/kb/*.md
- advanced-chat workflows: classifier → KB → LLM rich reply → CRM lead capture
- Publish draft workflows

Run inside docker-api-1:
  docker cp scripts/kb docker-api-1:/tmp/quyen_kb
  docker cp scripts/quyen_us_workflow_common.py docker-api-1:/tmp/
  docker cp scripts/add_omnichannel_rich_reply_nodes.py docker-api-1:/tmp/
  docker cp scripts/build_quyen_us_workflows.py docker-api-1:/tmp/
  docker exec docker-api-1 bash -lc "cd /app/api && /app/api/.venv/bin/python /tmp/build_quyen_us_workflows.py"

Optional env:
  TENANT_ID, ACCOUNT_ID — otherwise first owner/admin account is used.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# KB files may be copied to /tmp/quyen_kb when run from /tmp
_KB_CANDIDATES = [
    _SCRIPT_DIR / "kb",
    Path("/tmp/quyen_kb"),
    Path("/app/api/scripts/kb"),
]

for _kb in _KB_CANDIDATES:
    if _kb.is_dir():
        import quyen_us_workflow_common as common

        common.KB_DIR = _kb
        break

from sqlalchemy import func, select

from app_factory import create_app
from extensions.ext_database import db
from models.account import Account, Tenant, TenantAccountJoin, TenantAccountRole
from models.dataset import Dataset, Document
from models.model import App
from graphon.model_runtime.entities.model_entities import ModelType
from core.model_manager import ModelManager
from services.app_service import AppService
from services.dataset_service import DatasetService, DocumentService
from services.entities.knowledge_entities.knowledge_entities import (
    DataSource,
    FileInfo,
    InfoList,
    KnowledgeConfig,
    PreProcessingRule,
    ProcessRule,
    Rule,
    Segmentation,
)
from services.file_service import FileService
from services.workflow_service import WorkflowService

from add_omnichannel_rich_reply_nodes import publish_draft
from quyen_us_workflow_common import VERTICALS, VerticalSpec, binding_instructions, build_graph, workflow_features

import psycopg2


def resolve_account() -> tuple[Account, str]:
    tenant_id = os.environ.get("TENANT_ID")
    account_id = os.environ.get("ACCOUNT_ID")

    if tenant_id and account_id:
        account = db.session.get(Account, account_id)
        tenant = db.session.get(Tenant, tenant_id)
        if not account or not tenant:
            raise SystemExit(f"Account {account_id} or tenant {tenant_id} not found")
        account.current_tenant = tenant
        return account, tenant_id

    row = db.session.execute(
        select(Account, Tenant)
        .join(TenantAccountJoin, TenantAccountJoin.account_id == Account.id)
        .join(Tenant, Tenant.id == TenantAccountJoin.tenant_id)
        .where(TenantAccountJoin.role.in_([TenantAccountRole.OWNER, TenantAccountRole.ADMIN]))
        .limit(1)
    ).first()
    if not row:
        raise SystemExit("No workspace owner/admin account found")
    account, tenant = row
    account.current_tenant = tenant
    return account, tenant.id


def default_chat_model(tenant_id: str) -> dict[str, Any]:
    model_manager = ModelManager.for_tenant(tenant_id=tenant_id)
    try:
        instance = model_manager.get_default_model_instance(tenant_id=tenant_id, model_type=ModelType.LLM)
        schema = instance.model_type_instance.get_model_schema(instance.model_name, instance.credentials)
        mode = "chat"
        if schema and schema.model_properties:
            mode = schema.model_properties.get("mode") or "chat"
        return {
            "provider": instance.provider,
            "name": instance.model_name,
            "mode": mode,
            "completion_params": {"temperature": 0.4, "max_tokens": 512},
        }
    except Exception:
        return {
            "provider": "langgenius/openai_api_compatible/openai_api_compatible",
            "name": "cx/gpt-5.4-mini",
            "mode": "chat",
            "completion_params": {"temperature": 0.4, "max_tokens": 512},
        }


def ensure_app(account: Account, tenant_id: str, spec: VerticalSpec) -> App:
    app = db.session.scalar(
        select(App).where(App.tenant_id == tenant_id, App.name == spec.app_name).limit(1)
    )
    if app:
        print(f"  App exists: {app.id} ({spec.app_name})")
        return app

    app = AppService().create_app(
        tenant_id,
        {
            "name": spec.app_name,
            "description": f"Omnichannel chatbot for US {spec.key} vertical (Mini CRM)",
            "mode": "advanced-chat",
            "icon_type": "emoji",
            "icon": spec.app_icon,
            "icon_background": "#FFEAD5",
        },
        account,
    )
    db.session.commit()
    print(f"  Created app: {app.id} ({spec.app_name})")
    return app


def ensure_kb_dataset(account: Account, tenant_id: str, spec: VerticalSpec) -> str:
    dataset = db.session.scalar(
        select(Dataset).where(Dataset.tenant_id == tenant_id, Dataset.name == spec.dataset_name).limit(1)
    )
    if dataset:
        doc_count = db.session.scalar(
            select(func.count()).select_from(Document).where(Document.dataset_id == dataset.id)
        )
        if doc_count and doc_count > 0:
            print(f"  Dataset exists: {dataset.id} ({spec.dataset_name})")
            return dataset.id
        print(f"  Dataset exists but empty — seeding documents: {dataset.id}")
    else:
        if not spec.kb_path.is_file():
            raise FileNotFoundError(f"KB file not found: {spec.kb_path}")

        dataset = DatasetService.create_empty_dataset(
            tenant_id=tenant_id,
            name=spec.dataset_name,
            description=f"US market knowledge base for {spec.key} omnichannel bot",
            indexing_technique="economy",
            account=account,
            permission="all_team_members",
        )
        db.session.commit()
        print(f"  Created dataset: {dataset.id} ({spec.dataset_name})")

    if not spec.kb_path.is_file():
        raise FileNotFoundError(f"KB file not found: {spec.kb_path}")

    content = spec.kb_path.read_text(encoding="utf-8")
    upload = FileService(db.engine).upload_file(
        filename=spec.kb_filename,
        content=content.encode("utf-8"),
        mimetype="text/markdown",
        user=account,
        source="datasets",
    )
    db.session.commit()

    knowledge_config = KnowledgeConfig(
        indexing_technique="economy",
        data_source=DataSource(
            info_list=InfoList(
                data_source_type="upload_file",
                file_info_list=FileInfo(file_ids=[upload.id]),
            )
        ),
        process_rule=ProcessRule(
            mode="custom",
            rules=Rule(
                pre_processing_rules=[
                    PreProcessingRule(id="remove_extra_spaces", enabled=True),
                    PreProcessingRule(id="remove_urls_emails", enabled=False),
                ],
                segmentation=Segmentation(separator="\n## ", max_tokens=800, chunk_overlap=40),
            ),
        ),
        doc_form="text_model",
        doc_language="English",
    )

    with patch("services.dataset_service.current_user", account):
        DocumentService.save_document_with_dataset_id(dataset, knowledge_config, account)
    db.session.commit()
    print(f"  KB document queued for indexing on dataset {dataset.id}")
    return dataset.id


def sync_and_publish(account: Account, app: App, spec: VerticalSpec, dataset_id: str, model: dict[str, Any]) -> None:
    graph = build_graph(spec, dataset_id, model)
    features = workflow_features(spec)
    wf_service = WorkflowService()
    draft = wf_service.get_draft_workflow(app_model=app)
    draft_hash = draft.unique_hash if draft else None
    wf_service.sync_draft_workflow(
        app_model=app,
        graph=graph,
        features=features,
        unique_hash=draft_hash,
        account=account,
        environment_variables=[],
        conversation_variables=[],
    )
    db.session.commit()
    print(f"  Draft workflow synced for {app.id}")

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:difyai123456@db_postgres:5432/dify",
    )
    # publish_draft uses psycopg2 directly
    parts = db_url.replace("postgresql://", "").split("@")
    userpass, hostdb = parts[0], parts[1]
    user, password = userpass.split(":")
    host, dbname = hostdb.split("/")
    if ":" in host:
        host, port = host.split(":")
    else:
        port = "5432"

    conn = psycopg2.connect(host=host, port=int(port), dbname=dbname, user=user, password=password)
    try:
        published_id = publish_draft(conn, app.id)
        conn.commit()
        if published_id:
            print(f"  Published workflow: {published_id}")
        else:
            print("  WARN: publish_draft returned None")
    finally:
        conn.close()


def setup_vertical(account: Account, tenant_id: str, spec: VerticalSpec, model: dict[str, Any]) -> tuple[str, str]:
    print(f"\n--- {spec.key.upper()} ---")
    app = ensure_app(account, tenant_id, spec)
    dataset_id = ensure_kb_dataset(account, tenant_id, spec)
    sync_and_publish(account, app, spec, dataset_id, model)
    return app.id, dataset_id


def main() -> None:
    flask_app = create_app()
    with flask_app.app_context():
        account, tenant_id = resolve_account()
        model = default_chat_model(tenant_id)
        print(f"Tenant: {tenant_id}")
        print(f"Account: {account.id}")
        print(f"LLM model: {model['provider']} / {model['name']}")

        summary: list[str] = []
        for spec in VERTICALS:
            app_id, dataset_id = setup_vertical(account, tenant_id, spec, model)
            summary.append(binding_instructions(spec, app_id, dataset_id))

        print("\n" + "=" * 60)
        print("SETUP COMPLETE — Channel binding")
        print("=" * 60)
        for block in summary:
            print(block)
        print(
            "\nAfter KB documents finish indexing (Knowledge → dataset → check status), "
            "test each app in Studio Debugger, then connect Messenger/Zalo channels."
        )


if __name__ == "__main__":
    main()
