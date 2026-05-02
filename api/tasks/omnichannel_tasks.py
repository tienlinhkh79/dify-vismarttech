from __future__ import annotations

from celery import shared_task

from services.omnichannel.channel_config_service import ChannelConfigService
from services.omnichannel.messenger_runtime_service import MessengerRuntimeService
from services.omnichannel.omnichannel_ops_service import OmnichannelOpsService
from services.omnichannel.zalo_oauth_service import ZaloOAuthService
from services.omnichannel.zalo_runtime_service import ZaloRuntimeService


@shared_task(queue="dataset")
def run_omnichannel_sync_job(tenant_id: str, channel_id: str, job_id: str) -> dict[str, str]:
    OmnichannelOpsService.run_sync_job(tenant_id=tenant_id, channel_id=channel_id, job_id=job_id)
    return {"status": "ok", "job_id": job_id}


@shared_task(queue="dataset")
def process_meta_webhook_events(
    channel_id: str, events: list[dict], channel_config: dict
) -> dict[str, int]:
    sent_replies = MessengerRuntimeService.process_events(
        channel_id=channel_id,
        events=events,
        channel_config=channel_config,
    )
    return {"accepted_events": len(events), "sent_replies": sent_replies}


@shared_task(queue="dataset")
def process_zalo_webhook_events(
    channel_id: str, events: list[dict], channel_config: dict
) -> dict[str, int]:
    # Reload with OAuth refresh on the worker; webhook HTTP path skips refresh to avoid tunnel timeouts.
    fresh = ChannelConfigService.get_zalo_channel_config(channel_id, skip_oauth_refresh=False)
    cfg = fresh if fresh else channel_config
    sent_replies = ZaloRuntimeService.process_events(
        channel_id=channel_id,
        events=events,
        channel_config=cfg,
    )
    return {"accepted_events": len(events), "sent_replies": sent_replies}


@shared_task(queue="dataset")
def refresh_zalo_oa_tokens_task() -> dict[str, int]:
    return ZaloOAuthService.refresh_due_tokens_batch()
