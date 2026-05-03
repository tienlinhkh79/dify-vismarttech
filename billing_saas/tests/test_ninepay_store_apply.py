"""BillingStore 9Pay idempotent apply."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.store import BillingStore


class NinepayStoreApplyTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = BillingStore(Path(self._tmp.name) / "t.db")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_try_apply_idempotent(self) -> None:
        self.store.ensure_tenant("t1")
        now = 1_700_000_000
        self.store.save_ninepay_pending("inv1", "t1", "professional", "month", now)
        self.assertEqual(self.store.try_apply_ninepay_success("inv1", "pay9", now + 1), "applied")
        row = self.store.get_tenant_row("t1")
        self.assertEqual(row["plan"], "professional")
        self.assertIsNone(self.store.get_ninepay_pending("inv1"))
        self.assertTrue(self.store.ninepay_is_applied("inv1"))
        self.assertEqual(self.store.try_apply_ninepay_success("inv1", "pay9", now + 2), "duplicate")

    def test_missing_pending_after_apply(self) -> None:
        now = 1_700_000_010
        self.store.ensure_tenant("t2")
        self.store.save_ninepay_pending("inv2", "t2", "team", "year", now)
        self.store.try_apply_ninepay_success("inv2", "1", now)
        self.assertEqual(self.store.try_apply_ninepay_success("inv2", "1", now), "duplicate")


if __name__ == "__main__":
    unittest.main()
