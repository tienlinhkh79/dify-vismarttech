"""Tests for Zalo OA durable job queue."""

from __future__ import annotations

from services.omnichannel.zalo_bridge_job_service import backoff_seconds


def test_backoff_seconds_exponential_cap() -> None:
    assert backoff_seconds(1) == 1
    assert backoff_seconds(3) == 4
    assert backoff_seconds(10) == 300
