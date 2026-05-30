import time
import traceback

from app_factory import create_app
from core.app.entities.app_invoke_entities import InvokeFrom
from extensions.ext_database import db
from models.account import Account, Tenant
from models.model import App
from services.app_generate_service import AppGenerateService

APP_ID = "d8dbcb3c-afe5-409d-941e-0033e927d839"
USER_ID = "d98a9258-d9d8-405f-b869-c63e33ffb5da"
TENANT_ID = "e79ce4ee-c3b6-4a95-9f2d-b6b7282bd8f0"
QUERY = "có giày búp bê không"

app = create_app()
with app.app_context():
    app_model = db.session.get(App, APP_ID)
    user = db.session.get(Account, USER_ID)
    tenant = db.session.get(Tenant, TENANT_ID)
    user.current_tenant = tenant
    t0 = time.perf_counter()
    try:
        result = AppGenerateService.generate(
            app_model=app_model,
            user=user,
            args={"query": QUERY, "inputs": {}},
            invoke_from=InvokeFrom.DEBUGGER,
            streaming=False,
        )
        print("OK", round(time.perf_counter() - t0, 2), "s")
        print(str(result)[:800])
    except Exception as e:
        print("FAIL", round(time.perf_counter() - t0, 2), "s", e)
        traceback.print_exc()
