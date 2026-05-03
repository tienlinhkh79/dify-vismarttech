"""9Pay REST signing parity with official PHP MessageBuilder + HMACSignature."""

from __future__ import annotations

import base64
import hashlib
import hmac
import unittest

from app.ninepay_rest import (
    authorization_header,
    build_rest_message,
    sign_rest_authorization,
)


class NinepayRestSigningTest(unittest.TestCase):
    def test_inquire_get_message_three_lines(self) -> None:
        """Empty params => message is METHOD + URI + Date only (no trailing blank line)."""
        uri = "https://sand-payment.9pay.vn/v2/payments/abc123/inquire"
        msg = build_rest_message("GET", uri, 1700000000, params={})
        lines = msg.split("\n")
        self.assertEqual(lines, ["GET", uri, "1700000000"])

    def test_post_params_fourth_line_sorted(self) -> None:
        uri = "https://sand-payment.9pay.vn/v2/refunds/create"
        fields = {"request_id": "r1", "amount": 1000, "payment_no": 99, "description": "d"}
        msg = build_rest_message("POST", uri, 1, params=fields)
        self.assertTrue(msg.startswith("POST\n" + uri + "\n1\n"))
        tail = msg.split("\n", 3)[3]
        self.assertLess(tail.index("amount="), tail.index("description="))

    def test_hmac_matches_php_style(self) -> None:
        message = "GET\nhttps://example.com/v2/payments/x/inquire\n42"
        sig = sign_rest_authorization(message=message, merchant_secret="secret")
        expected = base64.b64encode(
            hmac.new(b"secret", message.encode("utf-8"), hashlib.sha256).digest()
        ).decode("ascii")
        self.assertEqual(sig, expected)
        auth = authorization_header(merchant_key="MK", signature_b64=sig)
        self.assertIn("Credential=MK", auth)
        self.assertIn("Signature=" + sig, auth)


if __name__ == "__main__":
    unittest.main()
