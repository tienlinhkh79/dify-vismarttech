"""FastAPI Billing service compatible with Dify `BillingService` HTTP contract."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.store import BillingStore

CATALOG_PATH = Path(os.environ.get("BILLING_PLAN_CATALOG_PATH", "")).resolve()
if not str(CATALOG_PATH):
    CATALOG_PATH = (Path(__file__).resolve().parent.parent / "plan_catalog.json").resolve()

DB_PATH = Path(os.environ.get("BILLING_SAAS_DB_PATH", "/data/billing_saas.db"))
API_SECRET = os.environ.get("BILLING_API_SECRET_KEY", "dev-billing-secret-change-me")

app = FastAPI(title="Dify Billing SaaS (reference)", version="0.1.0")
_store: BillingStore | None = None
_catalog: dict[str, Any] = {}


def get_store() -> BillingStore:
    global _store
    if _store is None:
        _store = BillingStore(DB_PATH)
    return _store


def load_catalog() -> dict[str, Any]:
    global _catalog
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    _catalog = raw
    return _catalog


@app.on_event("startup")
def _startup() -> None:
    load_catalog()
    get_store()


def verify_secret(x_billing_secret: Annotated[str | None, Header(alias="Billing-Api-Secret-Key")] = None) -> None:
    if not x_billing_secret or x_billing_secret != API_SECRET:
        raise HTTPException(status_code=401, detail="invalid billing secret")


TenantId = Annotated[str, Query(description="Dify workspace / tenant id")]


def _plan_entry(plan: str) -> dict[str, Any]:
    entry = _catalog.get(plan) or _catalog["sandbox"]
    return entry


def _subscription_info(store: BillingStore, tenant_id: str) -> dict[str, Any]:
    row = store.get_tenant_row(tenant_id)
    plan = row["plan"]
    limits = _plan_entry(plan)
    oc_lim = int(limits.get("omnichannel_channels", {}).get("limit", 0))
    crm_lim = int(limits.get("crm_leads", {}).get("limit", 0))
    return {
        "enabled": True,
        "subscription": {
            "plan": plan,
            "interval": row["interval"],
            "education": bool(row["education"]),
        },
        "members": {"size": int(row["members_used"]), "limit": int(limits["members"]["limit"])},
        "apps": {"size": int(row["apps_used"]), "limit": int(limits["apps"]["limit"])},
        "vector_space": {"size": int(row["vector_used"]), "limit": int(limits["vector_space"]["limit"])},
        "documents_upload_quota": {
            "size": int(row["documents_used"]),
            "limit": int(limits["documents_upload_quota"]["limit"]),
        },
        "annotation_quota_limit": {
            "size": int(row["annotations_used"]),
            "limit": int(limits["annotation_quota_limit"]["limit"]),
        },
        "docs_processing": "priority"
        if plan == "professional"
        else ("top-priority" if plan == "team" else "standard"),
        "can_replace_logo": plan != "sandbox",
        "model_load_balancing_enabled": plan == "team",
        "knowledge_rate_limit": {"limit": int(limits["knowledge_rate_limit"]["limit"])},
        "knowledge_pipeline_publish_enabled": plan != "sandbox",
        "next_credit_reset_date": int(row["next_reset"]),
        "omnichannel_channels": {"limit": oc_lim},
        "crm_leads": {"limit": crm_lim},
    }


def _usage_info(store: BillingStore, tenant_id: str) -> dict[str, Any]:
    row = store.get_tenant_row(tenant_id)
    plan = row["plan"]
    limits = _plan_entry(plan)
    tr_limit = int(limits["trigger_event"]["limit"])
    wf_limit = int(limits["api_rate_limit"]["limit"])
    reset = int(row["next_reset"])
    out: dict[str, Any] = {}
    out["trigger_event"] = {
        "usage": int(row["trigger_used"]),
        "limit": tr_limit,
        "reset_date": reset,
    }
    out["api_rate_limit"] = {
        "usage": int(row["workflow_used"]),
        "limit": wf_limit,
        "reset_date": reset,
    }
    return out


@app.get("/subscription/info")
def subscription_info(
    tenant_id: TenantId,
    store: BillingStore = Depends(get_store),
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    return _subscription_info(store, tenant_id)


@app.get("/tenant-feature-usage/info")
def tenant_feature_usage_info(
    tenant_id: TenantId,
    store: BillingStore = Depends(get_store),
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    return _usage_info(store, tenant_id)


@app.get("/subscription/knowledge-rate-limit")
def knowledge_rate_limit(
    tenant_id: TenantId,
    store: BillingStore = Depends(get_store),
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    row = store.get_tenant_row(tenant_id)
    limits = _plan_entry(row["plan"])
    return {
        "limit": int(limits["knowledge_rate_limit"]["limit"]),
        "subscription_plan": row["plan"],
    }


@app.get("/subscription/payment-link")
def payment_link(
    plan: str,
    interval: str,
    tenant_id: str = "",
    prefilled_email: str = "",
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    _ = prefilled_email
    base = os.environ.get("BILLING_CHECKOUT_BASE_URL", "https://example.com/billing/checkout")
    return {"url": f"{base}?plan={plan}&interval={interval}&tenant_id={tenant_id}"}


@app.get("/model-provider/payment-link")
def model_provider_payment_link(
    provider_name: str,
    tenant_id: str,
    account_id: str,
    prefilled_email: str = "",
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    _ = (provider_name, account_id, prefilled_email)
    base = os.environ.get("BILLING_CHECKOUT_BASE_URL", "https://example.com/billing/model-provider")
    return {"url": f"{base}?tenant_id={tenant_id}"}


@app.get("/invoices")
def invoices(
    tenant_id: str = "",
    prefilled_email: str = "",
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    _ = (tenant_id, prefilled_email)
    return {"url": "https://example.com/billing/invoices"}


@app.post("/tenant-feature-usage/usage")
def post_usage(
    tenant_id: str = Query(...),
    feature_key: str = Query(...),
    delta: int = Query(...),
    store: BillingStore = Depends(get_store),
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    if feature_key not in ("trigger_event", "api_rate_limit"):
        return {"result": "error", "detail": "unsupported_feature_key"}

    row = store.get_tenant_row(tenant_id)
    limits = _plan_entry(row["plan"])
    if feature_key == "trigger_event":
        lim = int(limits["trigger_event"]["limit"])
        used = int(row["trigger_used"])
    else:
        lim = int(limits["api_rate_limit"]["limit"])
        used = int(row["workflow_used"])

    if lim > 0 and used + delta > lim:
        return {"result": "error", "detail": "quota_exceeded"}

    ok, err, history_id = store.increment_feature_usage(tenant_id, feature_key, delta)
    if not ok:
        return {"result": "error", "detail": err}
    return {"result": "success", "history_id": history_id}


@app.post("/tenant-feature-usage/refund")
def post_refund(
    quota_usage_history_id: str = Query(..., alias="quota_usage_history_id"),
    store: BillingStore = Depends(get_store),
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    if store.refund_charge(quota_usage_history_id):
        return {"result": "success", "history_id": quota_usage_history_id}
    return {"result": "error", "detail": "unknown_history"}


@app.get("/billing/tenant_feature_plan/usage")
def tenant_feature_plan_usage(
    tenant_id: TenantId,
    feature_key: str = Query(...),
    store: BillingStore = Depends(get_store),
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    row = store.get_tenant_row(tenant_id)
    limits = _plan_entry(row["plan"])
    if feature_key == "trigger_event":
        used = int(row["trigger_used"])
        lim = int(limits["trigger_event"]["limit"])
    elif feature_key == "api_rate_limit":
        used = int(row["workflow_used"])
        lim = int(limits["api_rate_limit"]["limit"])
    else:
        return {"used": 0, "limit": 0, "remaining": -1}

    if lim <= 0:
        return {"used": used, "limit": lim, "remaining": -1}
    return {"used": used, "limit": lim, "remaining": max(0, lim - used)}


@app.delete("/account")
def delete_account(account_id: str = Query(...), _: None = Depends(verify_secret)) -> dict[str, Any]:
    _ = account_id
    return {"result": "ok"}


@app.get("/account/in-freeze")
def account_in_freeze(email: str = Query(...), _: None = Depends(verify_secret)) -> dict[str, Any]:
    _ = email
    return {"data": False}


class DeleteFeedback(BaseModel):
    email: str
    feedback: str


@app.post("/account/delete-feedback")
def delete_feedback(body: DeleteFeedback, _: None = Depends(verify_secret)) -> dict[str, Any]:
    _ = body
    return {"result": "ok"}


@app.get("/education/verify")
def education_verify(account_id: str = Query(...), _: None = Depends(verify_secret)) -> dict[str, Any]:
    _ = account_id
    return {"verified": False}


@app.get("/education/status")
def education_status(account_id: str = Query(...), _: None = Depends(verify_secret)) -> dict[str, Any]:
    _ = account_id
    return {"active": False}


class EducationActivateBody(BaseModel):
    institution: str
    token: str
    role: str


@app.post("/education/")
def education_activate(
    body: EducationActivateBody,
    account_id: str = Query(...),
    curr_tenant_id: str = Query(...),
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    _ = (body, account_id, curr_tenant_id)
    return {"result": "ok"}


@app.get("/education/autocomplete")
def education_autocomplete(
    keywords: str = "",
    page: int = 0,
    limit: int = 20,
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    _ = (keywords, page, limit)
    return {"items": []}


class ComplianceDownloadBody(BaseModel):
    doc_name: str
    account_id: str
    tenant_id: str
    ip_address: str
    device_info: str


@app.post("/compliance/download")
def compliance_download(body: ComplianceDownloadBody, _: None = Depends(verify_secret)) -> dict[str, Any]:
    _ = body
    return {"download_link": "https://example.com/compliance/stub"}


class PartnerTenantsBody(BaseModel):
    account_id: str
    click_id: str


@app.put("/partners/{partner_key}/tenants")
def partner_tenants(partner_key: str, body: PartnerTenantsBody, _: None = Depends(verify_secret)) -> dict[str, Any]:
    _ = (partner_key, body)
    return {"result": "ok"}


class PlanBatchBody(BaseModel):
    tenant_ids: list[str] = Field(default_factory=list)


@app.post("/subscription/plan/batch")
def plan_batch(body: PlanBatchBody, store: BillingStore = Depends(get_store), _: None = Depends(verify_secret)) -> dict[str, Any]:
    data: dict[str, dict[str, int | str]] = {}
    for tid in body.tenant_ids[:200]:
        row = store.get_tenant_row(tid)
        data[tid] = {"plan": row["plan"], "expiration_date": 0}
    return {"data": data}


@app.get("/subscription/cleanup/whitelist")
def cleanup_whitelist(_: None = Depends(verify_secret)) -> dict[str, Any]:
    return {"data": []}


@app.get("/notifications/active")
def notifications_active(account_id: str = Query(...), _: None = Depends(verify_secret)) -> dict[str, Any]:
    _ = account_id
    return {"should_show": False}


class NotificationCreate(BaseModel):
    contents: list[dict[str, Any]]
    frequency: str = "once"
    status: str = "active"
    notification_id: str | None = None
    start_time: str | None = None
    end_time: str | None = None


@app.post("/notifications")
def notifications_create(body: NotificationCreate, _: None = Depends(verify_secret)) -> dict[str, Any]:
    _ = body
    return {"notification_id": "stub"}


class NotificationAccounts(BaseModel):
    account_ids: list[str]


@app.post("/notifications/{notification_id}/accounts")
def notifications_accounts(notification_id: str, body: NotificationAccounts, _: None = Depends(verify_secret)) -> dict[str, Any]:
    _ = (notification_id, body)
    return {"count": 0}


class NotificationDismiss(BaseModel):
    account_id: str


@app.post("/notifications/{notification_id}/dismiss")
def notifications_dismiss(notification_id: str, body: NotificationDismiss, _: None = Depends(verify_secret)) -> dict[str, Any]:
    _ = (notification_id, body)
    return {"success": True}


class TenantMetricsBody(BaseModel):
    """Optional operator sync: align resource counters used in /subscription/info."""

    apps_used: int | None = None
    members_used: int | None = None
    vector_used: int | None = None
    documents_used: int | None = None
    annotations_used: int | None = None


@app.post("/internal/tenant/{tenant_id}/metrics")
def internal_set_metrics(
    tenant_id: str,
    body: TenantMetricsBody,
    store: BillingStore = Depends(get_store),
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    store.adjust_counters(
        tenant_id,
        apps=body.apps_used,
        members=body.members_used,
        vector=body.vector_used,
        documents=body.documents_used,
        annotations=body.annotations_used,
    )
    return {"result": "ok"}


class SetPlanBody(BaseModel):
    plan: str = "sandbox"
    interval: str = "month"


@app.post("/internal/tenant/{tenant_id}/plan")
def internal_set_plan(
    tenant_id: str,
    body: SetPlanBody,
    store: BillingStore = Depends(get_store),
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    store.set_plan(tenant_id, body.plan, body.interval)
    return {"result": "ok", "subscription": _subscription_info(store, tenant_id)["subscription"]}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def run() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
