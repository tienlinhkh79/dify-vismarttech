"""Unit tests for 9Pay portal signature and IPN checksum helpers."""

from __future__ import annotations

import base64
import hashlib
import json
import unittest

from app.ninepay import (
    build_signature_message,
    decode_ipn_result,
    sign_request,
    verify_ipn_checksum,
)


class NinepayHelpersTest(unittest.TestCase):
    def test_signature_message_format(self) -> None:
        params = {
            "merchantKey": "mk",
            "time": 1700000000,
            "invoice_no": "abc123",
            "amount": 10000,
            "description": "d",
            "return_url": "https://example.com/r",
            "back_url": "https://example.com/r",
        }
        msg = build_signature_message("https://sand-payment.9pay.vn", 1700000000, params)
        self.assertTrue(msg.startswith("POST\nhttps://sand-payment.9pay.vn/payments/create\n1700000000\n"))
        self.assertIn("amount=10000", msg)
        self.assertLess(msg.index("amount="), msg.index("merchantKey="))

    def test_sign_request_is_stable_base64(self) -> None:
        msg = "POST\nhttps://sand-payment.9pay.vn/payments/create\n1\namount=1&merchantKey=a"
        s1 = sign_request("secret-key", msg)
        s2 = sign_request("secret-key", msg)
        self.assertEqual(s1, s2)
        self.assertGreater(len(s1), 20)

    def test_ipn_checksum_round_trip(self) -> None:
        payload = {"invoice_no": "inv", "status": 5, "amount": 10000}
        result_b64 = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")
        ck = "checksum-key-test"
        digest = hashlib.sha256((result_b64 + ck).encode("utf-8")).hexdigest().upper()
        self.assertTrue(verify_ipn_checksum(result_b64, digest, ck))
        self.assertFalse(verify_ipn_checksum(result_b64, "DEADBEEF", ck))

    def test_decode_ipn_result(self) -> None:
        inner = {"status": 5, "invoice_no": "x"}
        result_b64 = base64.b64encode(json.dumps(inner).encode("utf-8")).decode("ascii")
        self.assertEqual(decode_ipn_result(result_b64)["invoice_no"], "x")


if __name__ == "__main__":
    unittest.main()
