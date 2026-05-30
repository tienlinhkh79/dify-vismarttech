"""Benchmark PJ Store workflow responses (blocking mode)."""

from __future__ import annotations

import time
import traceback
import uuid

from app_factory import create_app
from extensions.ext_database import db
from models.account import Account, Tenant
from models.model import App
from core.app.entities.app_invoke_entities import InvokeFrom
from services.app_generate_service import AppGenerateService

APP_ID = "d8dbcb3c-afe5-409d-941e-0033e927d839"
USER_ID = "d98a9258-d9d8-405f-b869-c63e33ffb5da"
TENANT_ID = "e79ce4ee-c3b6-4a95-9f2d-b6b7282bd8f0"

TESTS = [
    ("chao", "Xin chào"),
    ("tra_sp", "Shop còn áo HD004 size M không?"),
    ("tu_van", "PJ STORE ở đâu và ship thế nào?"),
]


def main() -> None:
    app = create_app()
    with app.app_context():
        app_model = db.session.get(App, APP_ID)
        user = db.session.get(Account, USER_ID)
        tenant = db.session.get(Tenant, TENANT_ID)
        if not app_model or not user or not tenant:
            raise RuntimeError("App, user or tenant not found")
        user.current_tenant = tenant

        print(f"App: {app_model.name} mode={app_model.mode}")
        print(f"Workflow: {app_model.workflow_id}")
        print("-" * 60)
        summary = []
        for label, query in TESTS:
            print(f"\n[{label}] Query: {query}")
            try:
                started = time.perf_counter()
                result = AppGenerateService.generate(
                    app_model=app_model,
                    user=user,
                    args={"query": query, "inputs": {}},
                    invoke_from=InvokeFrom.DEBUGGER,
                    streaming=False,
                )
                elapsed = time.perf_counter() - started
                answer = ""
                if isinstance(result, dict):
                    answer = str(result.get("answer") or result.get("data", {}).get("answer") or "")[:200]
                summary.append((label, round(elapsed, 2), "OK"))
                print(f"  Time: {round(elapsed, 2)}s")
                print(f"  Answer: {answer}")
            except Exception as exc:
                summary.append((label, -1, str(exc)[:120]))
                print(f"  ERROR: {exc}")
                traceback.print_exc()

        print("\n" + "=" * 60)
        print("SUMMARY")
        for label, sec, status in summary:
            print(f"  {label:10} {sec:>6}s  {status}")


if __name__ == "__main__":
    main()
