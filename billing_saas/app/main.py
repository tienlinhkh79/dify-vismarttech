"""FastAPI Billing service compatible with Dify `BillingService` HTTP contract."""

from __future__ import annotations

import binascii
import json
import logging
import os
import secrets
import threading
import time as time_module
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import ninepay as ninepay_lib
from app import ninepay_rest as ninepay_rest_lib
from app.store import BillingStore

logger = logging.getLogger(__name__)

CATALOG_PATH = Path(os.environ.get("BILLING_PLAN_CATALOG_PATH", "")).resolve()
if not str(CATALOG_PATH):
    CATALOG_PATH = (Path(__file__).resolve().parent.parent / "plan_catalog.json").resolve()

DB_PATH = Path(os.environ.get("BILLING_SAAS_DB_PATH", "/data/billing_saas.db"))
API_SECRET = os.environ.get("BILLING_API_SECRET_KEY", "dev-billing-secret-change-me")

NINEPAY_ENABLED = os.environ.get("NINEPAY_ENABLED", "").lower() in ("1", "true", "yes")
NINEPAY_ENDPOINT = os.environ.get("NINEPAY_ENDPOINT", "https://sand-payment.9pay.vn").rstrip("/")
NINEPAY_MERCHANT_KEY = os.environ.get("NINEPAY_MERCHANT_KEY", "")
NINEPAY_SECRET_KEY = os.environ.get("NINEPAY_SECRET_KEY", "")
NINEPAY_CHECKSUM_KEY = os.environ.get("NINEPAY_CHECKSUM_KEY", "")
NINEPAY_RETURN_URL_BASE = os.environ.get("NINEPAY_RETURN_URL_BASE", "").rstrip("/")
# Empty = omit `method` so 9Pay portal shows all methods enabled for the merchant (per redirect doc).
NINEPAY_METHOD = os.environ.get("NINEPAY_METHOD", "").strip() or None
NINEPAY_TRANSACTION_TYPE = os.environ.get("NINEPAY_TRANSACTION_TYPE", "").strip() or None
NINEPAY_LANG = os.environ.get("NINEPAY_LANG", "").strip() or None
NINEPAY_CURRENCY = os.environ.get("NINEPAY_CURRENCY", "").strip() or None
NINEPAY_BANK_CODE = os.environ.get("NINEPAY_BANK_CODE", "").strip() or None
NINEPAY_CAMPAIGN_ID = os.environ.get("NINEPAY_CAMPAIGN_ID", "").strip() or None
NINEPAY_CARD_BRAND_ALLOW = os.environ.get("NINEPAY_CARD_BRAND_ALLOW", "").strip() or None
NINEPAY_BIN_ALLOW = os.environ.get("NINEPAY_BIN_ALLOW", "").strip() or None
NINEPAY_CARD_TYPE_ALLOW = os.environ.get("NINEPAY_CARD_TYPE_ALLOW", "").strip() or None
NINEPAY_INQUIRE_POLL_SECONDS = int(os.environ.get("NINEPAY_INQUIRE_POLL_SECONDS", "900"))
NINEPAY_INQUIRE_AFTER_SECONDS = int(os.environ.get("NINEPAY_INQUIRE_AFTER_SECONDS", "1200"))


def _env_optional_int(name: str) -> int | None:
    raw = os.environ.get(name, "").strip()
    if raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


NINEPAY_PROFILE_ID = _env_optional_int("NINEPAY_PROFILE_ID")
NINEPAY_CARD_ORIGIN_ALLOW = _env_optional_int("NINEPAY_CARD_ORIGIN_ALLOW")


def _console_public_base() -> str:
    """Public console origin (same as Dify docker CONSOLE_API_URL / CONSOLE_WEB_URL)."""
    return (os.environ.get("CONSOLE_API_URL") or os.environ.get("CONSOLE_WEB_URL") or "").strip().rstrip("/")


def _checkout_stub_base() -> str:
    """Non-9Pay redirect target; prefer explicit env, else same host as console (never example.com when console is set)."""
    explicit = (os.environ.get("BILLING_CHECKOUT_BASE_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    base = _console_public_base()
    if base:
        return f"{base}/billing/checkout"
    return "https://example.com/billing/checkout"


def _invoices_stub_url() -> str:
    explicit = (os.environ.get("BILLING_INVOICES_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    base = _console_public_base()
    if base:
        return f"{base}/account"
    checkout = (os.environ.get("BILLING_CHECKOUT_BASE_URL") or "").strip().rstrip("/")
    if checkout:
        return checkout
    return "https://example.com/billing/invoices"


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
    if NINEPAY_ENABLED and NINEPAY_MERCHANT_KEY and NINEPAY_SECRET_KEY and NINEPAY_INQUIRE_POLL_SECONDS > 0:
        threading.Thread(target=_ninepay_poll_loop, name="ninepay-inquire-poll", daemon=True).start()


def verify_secret(x_billing_secret: Annotated[str | None, Header(alias="Billing-Api-Secret-Key")] = None) -> None:
    if not x_billing_secret or x_billing_secret != API_SECRET:
        raise HTTPException(status_code=401, detail="invalid billing secret")


TenantId = Annotated[str, Query(description="Dify workspace / tenant id")]


def _plan_entry(plan: str) -> dict[str, Any]:
    entry = _catalog.get(plan) or _catalog["sandbox"]
    return entry


def _ninepay_amount_vnd(plan: str, interval: str) -> int:
    raw = os.environ.get("NINEPAY_PLAN_AMOUNTS_VND", "").strip()
    key = f"{plan}_{interval}"
    if raw:
        try:
            amounts = json.loads(raw)
            if key not in amounts:
                raise KeyError(key)
            return max(10_000, int(amounts[key]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            raise HTTPException(status_code=500, detail=f"invalid NINEPAY_PLAN_AMOUNTS_VND: {e}") from e
    defaults: dict[str, int] = {
        "professional_month": 10_000,
        "professional_year": 10_000,
        "team_month": 10_000,
        "team_year": 10_000,
    }
    return max(10_000, int(defaults.get(key, 10_000)))


def _ninepay_invoice_no() -> str:
    inv = secrets.token_hex(12)
    return inv if len(inv) <= 30 else inv[:30]


def _ninepay_poll_tick() -> None:
    if not (NINEPAY_ENABLED and NINEPAY_MERCHANT_KEY and NINEPAY_SECRET_KEY):
        return
    store = get_store()
    now = int(time_module.time())
    cutoff = now - NINEPAY_INQUIRE_AFTER_SECONDS
    for row in store.list_ninepay_pending_older_than(cutoff):
        invoice_no = str(row["invoice_no"])
        try:
            data = ninepay_rest_lib.inquire_payment(
                endpoint_base=NINEPAY_ENDPOINT,
                merchant_key=NINEPAY_MERCHANT_KEY,
                merchant_secret=NINEPAY_SECRET_KEY,
                invoice_no=invoice_no,
                unix_time=now,
            )
        except Exception:
            logger.exception("ninepay_inquire_failed invoice_no=%s", invoice_no)
            continue
        status = int(data.get("status", -1))
        if not ninepay_lib.is_payment_success_status(status):
            continue
        payment_no = str(data.get("payment_no", ""))
        outcome = store.try_apply_ninepay_success(invoice_no, payment_no, now)
        logger.info(
            "ninepay_inquire_apply invoice_no=%s outcome=%s status=%s",
            invoice_no,
            outcome,
            status,
        )


def _ninepay_poll_loop() -> None:
    while True:
        try:
            _ninepay_poll_tick()
        except Exception:
            logger.exception("ninepay_poll_tick_error")
        time_module.sleep(max(60, NINEPAY_INQUIRE_POLL_SECONDS))


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
    store: BillingStore = Depends(get_store),
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    _ = prefilled_email
    if NINEPAY_ENABLED:
        if not (NINEPAY_MERCHANT_KEY and NINEPAY_SECRET_KEY and NINEPAY_RETURN_URL_BASE):
            raise HTTPException(status_code=500, detail="ninepay_missing_env")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="tenant_id_required_for_ninepay")
        amount = _ninepay_amount_vnd(plan, interval)
        invoice_no = _ninepay_invoice_no()
        now = int(time_module.time())
        sep = "&" if "?" in NINEPAY_RETURN_URL_BASE else "?"
        return_url = f"{NINEPAY_RETURN_URL_BASE}{sep}tenant_id={tenant_id}&plan={plan}&interval={interval}"
        desc = os.environ.get("NINEPAY_INVOICE_DESCRIPTION_PREFIX", "Dify subscription")
        description = f"{desc} {plan} ({interval})"
        store.save_ninepay_pending(invoice_no, tenant_id, plan, interval, now)
        url = ninepay_lib.build_portal_redirect_url(
            endpoint_base=NINEPAY_ENDPOINT,
            merchant_key=NINEPAY_MERCHANT_KEY,
            secret_key=NINEPAY_SECRET_KEY,
            unix_time=now,
            invoice_no=invoice_no,
            amount_vnd=amount,
            description=description[:255],
            return_url=return_url[:2048],
            method=NINEPAY_METHOD,
            transaction_type=NINEPAY_TRANSACTION_TYPE,
            lang=NINEPAY_LANG,
            currency=NINEPAY_CURRENCY,
            bank_code=NINEPAY_BANK_CODE or None,
            profile_id=NINEPAY_PROFILE_ID,
            card_origin_allow=NINEPAY_CARD_ORIGIN_ALLOW,
            card_brand_allow=NINEPAY_CARD_BRAND_ALLOW or None,
            bin_allow=NINEPAY_BIN_ALLOW or None,
            card_type_allow=NINEPAY_CARD_TYPE_ALLOW or None,
            campaign_id=NINEPAY_CAMPAIGN_ID or None,
        )
        return {"url": url}

    base = _checkout_stub_base()
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
    base = (os.environ.get("BILLING_MODEL_PROVIDER_CHECKOUT_BASE_URL") or "").strip().rstrip("/") or _checkout_stub_base()
    return {"url": f"{base}?tenant_id={tenant_id}"}


@app.get("/invoices")
def invoices(
    tenant_id: str = "",
    prefilled_email: str = "",
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    _ = (tenant_id, prefilled_email)
    return {"url": _invoices_stub_url()}


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


@app.post("/webhooks/9pay/ipn")
def ninepay_ipn(
    result: str = Form(...),
    checksum: str = Form(...),
    version: str = Form(default=""),
    store: BillingStore = Depends(get_store),
) -> dict[str, str]:
    """9Pay server-to-server IPN (application/x-www-form-urlencoded). Register this URL in the 9Pay merchant portal."""
    _ = version
    if not NINEPAY_CHECKSUM_KEY:
        logger.error("ninepay_ipn_missing_checksum_key")
        raise HTTPException(status_code=500, detail="ninepay_checksum_key_not_configured")

    if not ninepay_lib.verify_ipn_checksum(result, checksum, NINEPAY_CHECKSUM_KEY):
        logger.warning("ninepay_ipn_checksum_mismatch")
        raise HTTPException(status_code=400, detail="bad_checksum")

    try:
        data: dict[str, Any] = ninepay_lib.decode_ipn_result(result)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError, binascii.Error) as e:
        logger.warning("ninepay_ipn_decode_failed: %s", e)
        raise HTTPException(status_code=400, detail="bad_result") from e

    status = int(data.get("status", -1))
    invoice_no = str(data.get("invoice_no", "")).strip()
    if not invoice_no:
        raise HTTPException(status_code=400, detail="missing_invoice_no")

    if not ninepay_lib.is_payment_success_status(status):
        logger.info("ninepay_ipn_non_success status=%s invoice_no=%s", status, invoice_no)
        return {"status": "ignored"}

    payment_no = str(data.get("payment_no", "")).strip() or "0"
    now = int(time_module.time())
    outcome = store.try_apply_ninepay_success(invoice_no, payment_no, now)
    if outcome == "applied":
        logger.info("ninepay_ipn_applied_plan invoice_no=%s payment_no=%s", invoice_no, payment_no)
    elif outcome == "duplicate":
        logger.info("ninepay_ipn_duplicate invoice_no=%s", invoice_no)
    else:
        logger.warning("ninepay_ipn_missing_pending invoice_no=%s", invoice_no)
    return {"status": "ok"}


class NinepayRefundBody(BaseModel):
    request_id: str = Field(..., max_length=30)
    payment_no: int | str
    amount: int | str
    description: str = Field(..., max_length=255)
    bank: str | None = None
    account_number: str | None = Field(default=None, max_length=20)
    customer_name: str | None = Field(default=None, max_length=32)


@app.post("/internal/ninepay/sync-stale-pending")
def internal_ninepay_sync_stale_pending(_: None = Depends(verify_secret)) -> dict[str, str]:
    """Run one 9Pay inquire pass for pending invoices older than NINEPAY_INQUIRE_AFTER_SECONDS."""
    _ninepay_poll_tick()
    return {"status": "ok"}


@app.get("/internal/ninepay/inquire/{invoice_no}")
def internal_ninepay_inquire(
    invoice_no: str,
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    """Debug / ops: raw 9Pay inquire JSON for an invoice_no."""
    if not (NINEPAY_ENABLED and NINEPAY_MERCHANT_KEY and NINEPAY_SECRET_KEY):
        raise HTTPException(status_code=400, detail="ninepay_disabled")
    now = int(time_module.time())
    return ninepay_rest_lib.inquire_payment(
        endpoint_base=NINEPAY_ENDPOINT,
        merchant_key=NINEPAY_MERCHANT_KEY,
        merchant_secret=NINEPAY_SECRET_KEY,
        invoice_no=invoice_no,
        unix_time=now,
    )


@app.post("/internal/ninepay/refund")
def internal_ninepay_refund(
    body: NinepayRefundBody,
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    """Create a refund on 9Pay (status=5 payments). Register refund IPN URL with 9Pay separately."""
    if not (NINEPAY_ENABLED and NINEPAY_MERCHANT_KEY and NINEPAY_SECRET_KEY):
        raise HTTPException(status_code=400, detail="ninepay_disabled")
    now = int(time_module.time())
    return ninepay_rest_lib.create_refund(
        endpoint_base=NINEPAY_ENDPOINT,
        merchant_key=NINEPAY_MERCHANT_KEY,
        merchant_secret=NINEPAY_SECRET_KEY,
        request_id=body.request_id,
        payment_no=body.payment_no,
        amount=body.amount,
        description=body.description[:255],
        unix_time=now,
        bank=body.bank,
        account_number=body.account_number,
        customer_name=body.customer_name,
    )


@app.get("/internal/ninepay/refund-inquire/{request_id}")
def internal_ninepay_refund_inquire(
    request_id: str,
    _: None = Depends(verify_secret),
) -> dict[str, Any]:
    if not (NINEPAY_ENABLED and NINEPAY_MERCHANT_KEY and NINEPAY_SECRET_KEY):
        raise HTTPException(status_code=400, detail="ninepay_disabled")
    now = int(time_module.time())
    return ninepay_rest_lib.inquire_refund(
        endpoint_base=NINEPAY_ENDPOINT,
        merchant_key=NINEPAY_MERCHANT_KEY,
        merchant_secret=NINEPAY_SECRET_KEY,
        request_id=request_id,
        unix_time=now,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def run() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
