"""SQLite persistence for tenant billing state (reference SaaS billing service)."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any


class BillingStore:
    """Thread-safe SQLite store."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id TEXT PRIMARY KEY,
                    plan TEXT NOT NULL DEFAULT 'sandbox',
                    interval TEXT NOT NULL DEFAULT 'month',
                    education INTEGER NOT NULL DEFAULT 0,
                    apps_used INTEGER NOT NULL DEFAULT 0,
                    members_used INTEGER NOT NULL DEFAULT 0,
                    vector_used INTEGER NOT NULL DEFAULT 0,
                    documents_used INTEGER NOT NULL DEFAULT 0,
                    annotations_used INTEGER NOT NULL DEFAULT 0,
                    trigger_used INTEGER NOT NULL DEFAULT 0,
                    workflow_used INTEGER NOT NULL DEFAULT 0,
                    next_reset INTEGER NOT NULL DEFAULT -1
                );
                CREATE TABLE IF NOT EXISTS usage_charges (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    feature_key TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    refunded INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS ninepay_pending (
                    invoice_no TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ninepay_applied (
                    invoice_no TEXT PRIMARY KEY,
                    payment_no TEXT,
                    tenant_id TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    applied_at INTEGER NOT NULL
                );
                """
            )
            conn.commit()

    def ensure_tenant(self, tenant_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id) VALUES (?)",
                (tenant_id,),
            )
            conn.commit()

    def get_tenant_row(self, tenant_id: str) -> dict[str, Any]:
        self.ensure_tenant(tenant_id)
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone()
            assert row is not None
            return dict(row)

    def set_plan(self, tenant_id: str, plan: str, interval: str = "month") -> None:
        self.ensure_tenant(tenant_id)
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE tenants SET plan = ?, interval = ? WHERE tenant_id = ?",
                (plan, interval, tenant_id),
            )
            conn.commit()

    def adjust_counters(
        self,
        tenant_id: str,
        *,
        apps: int | None = None,
        members: int | None = None,
        vector: int | None = None,
        documents: int | None = None,
        annotations: int | None = None,
    ) -> None:
        self.ensure_tenant(tenant_id)
        fields: list[str] = []
        values: list[int] = []
        if apps is not None:
            fields.append("apps_used = ?")
            values.append(apps)
        if members is not None:
            fields.append("members_used = ?")
            values.append(members)
        if vector is not None:
            fields.append("vector_used = ?")
            values.append(vector)
        if documents is not None:
            fields.append("documents_used = ?")
            values.append(documents)
        if annotations is not None:
            fields.append("annotations_used = ?")
            values.append(annotations)
        if not fields:
            return
        values.append(tenant_id)
        with self._lock, self._connect() as conn:
            conn.execute(f"UPDATE tenants SET {', '.join(fields)} WHERE tenant_id = ?", values)
            conn.commit()

    @staticmethod
    def _usage_column(feature_key: str) -> str:
        if feature_key == "trigger_event":
            return "trigger_used"
        if feature_key == "api_rate_limit":
            return "workflow_used"
        raise ValueError(f"unsupported feature_key: {feature_key}")

    def increment_feature_usage(self, tenant_id: str, feature_key: str, delta: int) -> tuple[bool, str | None, str | None]:
        if delta <= 0:
            return False, "delta_must_be_positive", None
        try:
            column = self._usage_column(feature_key)
        except ValueError as e:
            return False, str(e), None

        history_id = str(uuid.uuid4())
        self.ensure_tenant(tenant_id)
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE tenants SET {column} = {column} + ? WHERE tenant_id = ?",
                (delta, tenant_id),
            )
            conn.execute(
                "INSERT INTO usage_charges (id, tenant_id, feature_key, amount, refunded) VALUES (?, ?, ?, ?, 0)",
                (history_id, tenant_id, feature_key, delta),
            )
            conn.commit()
        return True, None, history_id

    def refund_charge(self, history_id: str) -> bool:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM usage_charges WHERE id = ? AND refunded = 0",
                (history_id,),
            ).fetchone()
            if row is None:
                return False
            tenant_id = row["tenant_id"]
            feature_key = row["feature_key"]
            amount = int(row["amount"])
            column = self._usage_column(feature_key)
            cur = conn.execute(
                f"SELECT {column} FROM tenants WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
            if cur is None:
                return False
            new_val = max(0, int(cur[0]) - amount)
            conn.execute(
                f"UPDATE tenants SET {column} = ? WHERE tenant_id = ?",
                (new_val, tenant_id),
            )
            conn.execute("UPDATE usage_charges SET refunded = 1 WHERE id = ?", (history_id,))
            conn.commit()
        return True

    def save_ninepay_pending(self, invoice_no: str, tenant_id: str, plan: str, interval: str, created_at: int) -> None:
        self.ensure_tenant(tenant_id)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ninepay_pending (invoice_no, tenant_id, plan, interval, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (invoice_no, tenant_id, plan, interval, created_at),
            )
            conn.commit()

    def get_ninepay_pending(self, invoice_no: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM ninepay_pending WHERE invoice_no = ?", (invoice_no,)).fetchone()
            if row is None:
                return None
            return dict(row)

    def delete_ninepay_pending(self, invoice_no: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM ninepay_pending WHERE invoice_no = ?", (invoice_no,))
            conn.commit()

    def ninepay_is_applied(self, invoice_no: str) -> bool:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM ninepay_applied WHERE invoice_no = ? LIMIT 1",
                (invoice_no,),
            ).fetchone()
            return row is not None

    def list_ninepay_pending_older_than(self, max_created_at: int) -> list[dict[str, Any]]:
        """Pending rows with created_at <= max_created_at (e.g. now - 20 minutes)."""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ninepay_pending WHERE created_at <= ? ORDER BY created_at ASC",
                (max_created_at,),
            ).fetchall()
            return [dict(r) for r in rows]

    def try_apply_ninepay_success(self, invoice_no: str, payment_no: str, applied_at: int) -> str:
        """Load pending row inside txn; apply plan once per invoice. Returns applied | duplicate | missing_pending."""
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                pending = conn.execute(
                    "SELECT * FROM ninepay_pending WHERE invoice_no = ?",
                    (invoice_no,),
                ).fetchone()
                if pending is None:
                    dup = conn.execute(
                        "SELECT 1 FROM ninepay_applied WHERE invoice_no = ? LIMIT 1",
                        (invoice_no,),
                    ).fetchone()
                    conn.rollback()
                    return "duplicate" if dup is not None else "missing_pending"

                tenant_id = str(pending["tenant_id"])
                plan = str(pending["plan"])
                interval = str(pending["interval"])
                conn.execute("INSERT OR IGNORE INTO tenants (tenant_id) VALUES (?)", (tenant_id,))

                try:
                    conn.execute(
                        "INSERT INTO ninepay_applied (invoice_no, payment_no, tenant_id, plan, interval, applied_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (invoice_no, payment_no, tenant_id, plan, interval, applied_at),
                    )
                except sqlite3.IntegrityError:
                    conn.rollback()
                    return "duplicate"

                conn.execute(
                    "UPDATE tenants SET plan = ?, interval = ? WHERE tenant_id = ?",
                    (plan, interval, tenant_id),
                )
                conn.execute("DELETE FROM ninepay_pending WHERE invoice_no = ?", (invoice_no,))
            except Exception:
                conn.rollback()
                raise
            else:
                conn.commit()
        return "applied"
