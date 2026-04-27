from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import Request, Response

from core.entities.provider_entities import BasicProviderConfig, ProviderConfig
from core.plugin.entities.plugin_daemon import CredentialType
from core.plugin.entities.request import TriggerDispatchResponse, TriggerInvokeEventResponse
from core.tools.entities.common_entities import I18nObject
from core.trigger.entities.api_entities import EventApiEntity, TriggerProviderApiEntity
from core.trigger.entities.entities import (
    EventEntity,
    EventIdentity,
    EventParameter,
    EventParameterType,
    Subscription,
    SubscriptionConstructor,
    TriggerCreationMethod,
    TriggerProviderEntity,
    TriggerProviderIdentity,
    UnsubscribeResult,
)
from core.trigger.errors import EventIgnoreError
from models.provider_ids import TriggerProviderID
from services.omnichannel.messenger_service import MessengerService

MESSENGER_TRIGGER_PROVIDER_ID = TriggerProviderID("langgenius/messenger/messenger", is_hardcoded=True)


class MessengerTriggerProviderController:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.provider_id = MESSENGER_TRIGGER_PROVIDER_ID
        self.entity = TriggerProviderEntity(
            identity=TriggerProviderIdentity(
                author="langgenius",
                name="messenger",
                label=I18nObject(en_US="Facebook Messenger"),
                description=I18nObject(en_US="Receive and auto-reply Facebook Messenger messages"),
                icon=None,
                icon_dark=None,
                tags=["messenger", "omnichannel"],
            ),
            subscription_schema=[
                ProviderConfig(
                    type=BasicProviderConfig.Type.TEXT_INPUT,
                    name="app_id",
                    required=True,
                    label=I18nObject(en_US="Dify App ID"),
                ),
                ProviderConfig(
                    type=BasicProviderConfig.Type.TEXT_INPUT,
                    name="page_id",
                    required=True,
                    label=I18nObject(en_US="Facebook Page ID"),
                ),
                ProviderConfig(
                    type=BasicProviderConfig.Type.SECRET_INPUT,
                    name="verify_token",
                    required=True,
                    label=I18nObject(en_US="Webhook Verify Token"),
                ),
                ProviderConfig(
                    type=BasicProviderConfig.Type.SECRET_INPUT,
                    name="app_secret",
                    required=True,
                    label=I18nObject(en_US="Facebook App Secret"),
                ),
                ProviderConfig(
                    type=BasicProviderConfig.Type.SECRET_INPUT,
                    name="page_access_token",
                    required=True,
                    label=I18nObject(en_US="Page Access Token"),
                ),
                ProviderConfig(
                    type=BasicProviderConfig.Type.TEXT_INPUT,
                    name="graph_api_version",
                    required=False,
                    default="v23.0",
                    label=I18nObject(en_US="Graph API Version"),
                ),
            ],
            subscription_constructor=SubscriptionConstructor(parameters=[], credentials_schema=[]),
            events=[
                EventEntity(
                    identity=EventIdentity(
                        author="langgenius",
                        name="message_received",
                        label=I18nObject(en_US="Message Received"),
                        provider=str(MESSENGER_TRIGGER_PROVIDER_ID),
                    ),
                    description=I18nObject(en_US="Incoming Facebook Messenger message"),
                    parameters=[
                        EventParameter(
                            name="message_text",
                            label=I18nObject(en_US="Message Text"),
                            type=EventParameterType.STRING,
                            required=False,
                        )
                    ],
                    output_schema=None,
                )
            ],
        )

    def get_provider_id(self) -> TriggerProviderID:
        return self.provider_id

    def to_api_entity(self) -> TriggerProviderApiEntity:
        return TriggerProviderApiEntity(
            author=self.entity.identity.author,
            name=self.entity.identity.name,
            label=self.entity.identity.label,
            description=self.entity.identity.description,
            icon=None,
            icon_dark=None,
            tags=self.entity.identity.tags,
            plugin_id=self.provider_id.plugin_id,
            plugin_unique_identifier=str(self.provider_id),
            subscription_constructor=self.entity.subscription_constructor,
            subscription_schema=self.entity.subscription_schema,
            supported_creation_methods=[TriggerCreationMethod.MANUAL],
            events=[
                EventApiEntity(
                    name=event.identity.name,
                    identity=event.identity,
                    description=event.description,
                    parameters=event.parameters,
                    output_schema=event.output_schema,
                )
                for event in self.entity.events
            ],
        )

    def get_subscription_default_properties(self) -> Mapping[str, Any]:
        return {"graph_api_version": "v23.0"}

    def get_subscription_constructor(self) -> SubscriptionConstructor | None:
        return self.entity.subscription_constructor

    def validate_credentials(self, user_id: str, credentials: Mapping[str, str]) -> None:
        return None

    def get_supported_credential_types(self) -> list[CredentialType]:
        return []

    def get_credentials_schema(self, credential_type: CredentialType | str) -> list[ProviderConfig]:
        return []

    def get_credential_schema_config(self, credential_type: CredentialType | str) -> list[BasicProviderConfig]:
        return []

    def get_oauth_client_schema(self) -> list[ProviderConfig]:
        return []

    def get_properties_schema(self) -> list[BasicProviderConfig]:
        return [x.to_basic_provider_config() for x in self.entity.subscription_schema]

    def get_events(self) -> list[EventEntity]:
        return self.entity.events

    def get_event(self, event_name: str) -> EventEntity | None:
        for event in self.entity.events:
            if event.identity.name == event_name:
                return event
        return None

    def get_event_parameters(self, event_name: str) -> Mapping[str, EventParameter]:
        event = self.get_event(event_name)
        if not event:
            return {}
        return {parameter.name: parameter for parameter in event.parameters}

    def dispatch(
        self,
        request: Request,
        subscription: Subscription,
        credentials: Mapping[str, str],
        credential_type: CredentialType,
    ) -> TriggerDispatchResponse:
        properties = dict(subscription.properties)
        verify_token = str(properties.get("verify_token", ""))
        app_secret = str(properties.get("app_secret", ""))

        if request.method == "GET":
            challenge = MessengerService.verify_webhook_handshake(
                mode=request.args.get("hub.mode"),
                verify_token=request.args.get("hub.verify_token"),
                expected_verify_token=verify_token,
                challenge=request.args.get("hub.challenge"),
            )
            if challenge is None:
                return TriggerDispatchResponse(
                    user_id=subscription.endpoint,
                    events=[],
                    response=Response("Forbidden", status=403),
                    payload={},
                )
            return TriggerDispatchResponse(
                user_id=subscription.endpoint,
                events=[],
                response=Response(challenge, status=200, content_type="text/plain"),
                payload={},
            )

        raw_body = request.get_data(cache=True, as_text=False)
        signature = request.headers.get("X-Hub-Signature-256")
        if not MessengerService.verify_payload_signature(raw_body, signature, app_secret):
            return TriggerDispatchResponse(
                user_id=subscription.endpoint,
                events=[],
                response=Response("Invalid signature", status=403),
                payload={},
            )

        payload = request.get_json(silent=True) or {}
        events = MessengerService.parse_message_events(payload)
        if events:
            from services.omnichannel.messenger_runtime_service import MessengerRuntimeService

            runtime_config = {
                "app_id": str(properties.get("app_id", "")),
                "page_access_token": str(properties.get("page_access_token", "")),
                "graph_api_version": str(properties.get("graph_api_version", "v23.0")),
            }
            MessengerRuntimeService.process_events(subscription.endpoint, events, runtime_config)

        return TriggerDispatchResponse(
            user_id=subscription.endpoint,
            events=[],
            response=Response("EVENT_RECEIVED", status=200),
            payload=payload,
        )

    def invoke_trigger_event(
        self,
        user_id: str,
        event_name: str,
        parameters: Mapping[str, Any],
        credentials: Mapping[str, str],
        credential_type: CredentialType,
        subscription: Subscription,
        request: Request,
        payload: Mapping[str, Any],
    ) -> TriggerInvokeEventResponse:
        raise EventIgnoreError("Messenger trigger dispatch is handled directly")

    def subscribe_trigger(
        self,
        user_id: str,
        endpoint: str,
        parameters: Mapping[str, Any],
        credentials: Mapping[str, str],
        credential_type: CredentialType,
    ) -> Subscription:
        return Subscription(expires_at=-1, endpoint=endpoint, parameters=parameters, properties={})

    def unsubscribe_trigger(
        self,
        user_id: str,
        subscription: Subscription,
        credentials: Mapping[str, str],
        credential_type: CredentialType,
    ) -> UnsubscribeResult:
        return UnsubscribeResult(success=True, message="ok")

    def refresh_trigger(
        self,
        user_id: str,
        subscription: Subscription,
        credentials: Mapping[str, str],
        credential_type: CredentialType,
    ) -> Subscription:
        return subscription
