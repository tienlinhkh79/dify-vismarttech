from __future__ import annotations

from flask_restx import Resource
from graphon.model_runtime.utils.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from werkzeug.exceptions import BadRequest

from controllers.common.schema import register_schema_models
from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, is_admin_or_owner_required, setup_required
from libs.login import current_account_with_tenant, login_required
from services.omnichannel.channel_management_service import ChannelManagementService


class WebsiteWidgetProvisionPayload(BaseModel):
    app_id: str = Field(min_length=1, max_length=255)


register_schema_models(console_ns, WebsiteWidgetProvisionPayload)


@console_ns.route("/workspaces/current/channels/website-widget/provision")
class WebsiteWidgetProvisionApi(Resource):
    @console_ns.expect(console_ns.models[WebsiteWidgetProvisionPayload.__name__])
    @setup_required
    @login_required
    @is_admin_or_owner_required
    @account_initialization_required
    def post(self):
        account, tenant_id = current_account_with_tenant()
        payload = WebsiteWidgetProvisionPayload.model_validate(console_ns.payload or {})
        try:
            data = ChannelManagementService.provision_website_widget_channel(
                tenant_id=tenant_id,
                user_id=account.id,
                app_id=payload.app_id,
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return jsonable_encoder({"data": data}), 201
