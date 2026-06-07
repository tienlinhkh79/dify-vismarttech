"""Central Zalo OA bridge dispatcher (inbound / shared_info / backfill jobs)."""

from __future__ import annotations

import logging
from typing import Any

from models.trigger import OmniChannelMessageDirection, OmniChannelMessageSource, OmniChannelZaloJobStatus
from services.omnichannel.channel_config_service import ChannelConfigService
from services.omnichannel.omnichannel_ops_service import MessageWritePayload, OmnichannelOpsService
from services.omnichannel.zalo_bridge_job_service import ZaloBridgeJobService
from services.omnichannel.zalo_oa_backfill_service import ZaloOaBackfillService
from services.omnichannel.zalo_oa_shared_info import format_shared_info_note, parse_shared_info
from services.omnichannel.zalo_runtime_service import ZaloRuntimeService
from services.omnichannel.zalo_service import ZaloService

logger = logging.getLogger(__name__)


class ZaloBridgeDispatchService:
    @classmethod
    def enqueue_webhook(cls, *, channel_id: str, payload: dict[str, Any]) -> bool:
        event_name = str(payload.get("event_name") or payload.get("event") or "").strip()
        if event_name == "user_submit_info":
            dedup = f"{channel_id}:shared:{payload.get('timestamp') or payload.get('sender', {}).get('id') or ''}"
            return ZaloBridgeJobService.enqueue(
                channel_id=channel_id,
                kind="shared_info",
                dedup_key=dedup[:512],
                payload={"raw": payload},
            )
        event = ZaloService.parse_webhook_event(channel_id, payload)
        if not event:
            return False
        msg_id = str(event.get("message_id") or "").strip()
        dedup = f"{channel_id}:inbound:{msg_id or event.get('event_name')}:{event.get('external_user_id')}"
        return ZaloBridgeJobService.enqueue(
            channel_id=channel_id,
            kind="inbound",
            dedup_key=dedup[:512],
            payload={"event": dict(event)},
        )

    @classmethod
    def process_job(cls, job) -> None:
        kind = str(getattr(job.kind, "value", job.kind))
        channel_id = job.channel_id
        cfg = ChannelConfigService.get_zalo_channel_config(channel_id, skip_oauth_refresh=False)
        if not cfg:
            raise ValueError(f"Zalo channel not found: {channel_id}")

        if kind == "inbound":
            event = (job.payload or {}).get("event") or {}
            ZaloRuntimeService.process_events(channel_id, [event], cfg)
            return

        if kind == "shared_info":
            raw = (job.payload or {}).get("raw") or {}
            cls._process_shared_info(channel_id=channel_id, payload=raw, channel_config=cfg)
            return

        if kind == "backfill":
            ZaloOaBackfillService.run_job_payload(channel_id=channel_id, payload=job.payload or {}, channel_config=cfg)
            return

        raise ValueError(f"Unsupported Zalo bridge job kind: {kind}")

    @classmethod
    def _process_shared_info(
        cls,
        *,
        channel_id: str,
        payload: dict[str, Any],
        channel_config: dict[str, Any],
    ) -> None:
        info = parse_shared_info(payload)
        if not info:
            return
        sender = payload.get("sender") if isinstance(payload.get("sender"), dict) else {}
        user_id = str(sender.get("id") or "").strip()
        if not user_id:
            return
        from services.omnichannel.zalo_oa_classify import ZaloOaWebhookEvent

        event: ZaloOaWebhookEvent = {
            "channel": "zalo_oa",
            "channel_id": channel_id,
            "external_account_id": str(channel_config.get("oa_id") or ""),
            "external_user_id": user_id,
            "text": format_shared_info_note(info),
            "raw_event": payload,
            "event_name": "user_submit_info",
        }
        ZaloRuntimeService.process_events(channel_id, [event], channel_config)

    @classmethod
    def _notify_permanent_failure(cls, *, job, error: str) -> None:
        payload = job.payload or {}
        event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
        user_id = str(event.get("external_user_id") or "").strip()
        if not user_id:
            return
        cfg = ChannelConfigService.get_zalo_channel_config(job.channel_id, skip_oauth_refresh=True)
        if not cfg:
            return
        note = f"⚠️ Zalo bridge job failed ({job.kind}): {(error or '')[:500]}"
        record: MessageWritePayload = {
            "tenant_id": str(cfg.get("tenant_id") or ""),
            "channel_id": job.channel_id,
            "external_user_id": user_id,
            "direction": OmniChannelMessageDirection.OUTBOUND,
            "source": OmniChannelMessageSource.SYSTEM,
            "content": note,
            "attachments": [],
            "metadata": {"system_note": True, "system_note_type": "bridge_job_failed", "job_id": job.id},
            "created_at": None,
        }
        try:
            OmnichannelOpsService.record_message(record)
        except Exception:
            logger.debug("Failed to post bridge failure note job=%s", job.id, exc_info=True)

    @classmethod
    def run_worker_tick(cls, *, max_jobs: int = 10) -> int:
        processed = 0
        for _ in range(max_jobs):
            job = ZaloBridgeJobService.claim_next()
            if not job:
                break
            try:
                cls.process_job(job)
                ZaloBridgeJobService.mark_done(job.id)
            except Exception as e:
                status = ZaloBridgeJobService.mark_retry(job.id, str(e), attempts=int(job.attempts or 1))
                logger.warning(
                    "Zalo bridge job failed id=%s kind=%s status=%s err=%s",
                    job.id,
                    job.kind,
                    status,
                    e,
                )
                if status == OmniChannelZaloJobStatus.FAILED:
                    cls._notify_permanent_failure(job=job, error=str(e))
            processed += 1
        return processed
