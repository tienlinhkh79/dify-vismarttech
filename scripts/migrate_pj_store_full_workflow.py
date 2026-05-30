"""Full roadmap migration for PJ Store_v2 sales + KiotViet workflow."""

from __future__ import annotations

import copy
import json
import uuid
from typing import Any

import psycopg2

APP_ID = "d8dbcb3c-afe5-409d-941e-0033e927d839"
WORKFLOW_IDS = (
    "e46ef02f-e392-4e41-870c-040add152a1f",
    "7d0fd8d0-96d6-4cc4-98c1-229e1a9e85f1",
)

# Existing node IDs
START = "1711528708197"
QC = "1711528709608"
KB = "1711528770201"
A_HELLO = "1711528775142"
LLM_ADVICE = "1711528815414"
A_ADVICE = "1711528835179"
A_THANKS = "1775459665592"
PE_LOOKUP = "1776147263725"
TMPL_LOOKUP = "1776150090873"
LLM_LOOKUP = "1775471817904"
A_LOOKUP = "1775471929100"
PE_CHOT = "1779987263725"
TMPL_CHOT = "1779980090874"
LLM_CHOT = "1779981817905"
A_CHOT = "17799741695020"

# QC class handles
CLS_LOOKUP = "1711528736036"
CLS_ADVICE = "1711528736549"
CLS_HELLO = "1711528737066"
CLS_THANKS = "1775459651863"
CLS_CHOT = "1779974034495"
CLS_ORDER_LOOKUP = "177999020001"
CLS_CANCEL = "177999020002"
CLS_SUPPLEMENT = "177999020003"

# New node IDs
IF_LOOKUP_CODE = "177999010001"
KVP_BY_CODE = "177999010002"
KVP_SEARCH = "177999010003"
ASSIGN_PRODUCT = "177999010004"
IF_CHOT_PRODUCT = "177999010026"
A_CHOT_NO_PRODUCT = "177999010027"
KVP_CHOT = "177999010007"
IF_CHOT_READY = "177999010005"
A_CHOT_MISSING = "177999010006"
CODE_ORDER = "177999010031"
KVC_GET = "177999010008"
KVC_CREATE = "177999010010"
KVO_CREATE = "177999011001"
CODE_RESOLVE = "177999010033"
IF_CUSTOMER = "177999010009"
CODE_CANCEL_PARSE = "177999013008"
A_SUPPLEMENT_WAIT = "177999014005"
PE_ORDER = "177999012001"
KVO_LOOKUP = "177999012002"
TMPL_ORDER = "177999012003"
LLM_ORDER = "177999012004"
A_ORDER = "177999012005"
PE_CANCEL = "177999013001"
KVO_GET = "177999013002"
IF_ORDER_FOUND = "177999013003"
KVO_CANCEL = "177999013004"
LLM_CANCEL = "177999013005"
A_CANCEL = "177999013006"
A_ORDER_NOT_FOUND = "177999013007"
PE_SUPPLEMENT = "177999014001"
ASSIGN_CUSTOMER = "177999014002"
IF_SUPPLEMENT_READY = "177999014003"
A_SUPPLEMENT = "177999014004"

DB = {
    "host": "db_postgres",
    "port": 5432,
    "dbname": "dify",
    "user": "postgres",
    "password": "difyai123456",
}

CONV_VARS = {
    "product_code": {
        "id": "0f3c5350-4216-455c-a401-4d83dd830a4f",
        "name": "product_code",
        "value_type": "string",
        "value": "",
        "description": "Mã sản phẩm đang quan tâm",
        "selector": ["conversation", "product_code"],
    },
    "product_name": {
        "id": "17e78d47-b54d-42e2-9f56-f7c20ea8e799",
        "name": "product_name",
        "value_type": "string",
        "value": "",
        "description": "Tên sản phẩm đang quan tâm",
        "selector": ["conversation", "product_name"],
    },
    "customer_name": {
        "id": "c19af338-c2a5-4d71-bdea-685ad2d7a5e5",
        "name": "customer_name",
        "value_type": "string",
        "value": "",
        "description": "Họ tên người nhận",
        "selector": ["conversation", "customer_name"],
    },
    "customer_phone": {
        "id": "ec9c6e57-18c7-4268-9481-6207b86dd338",
        "name": "customer_phone",
        "value_type": "string",
        "value": "",
        "description": "SĐT người nhận",
        "selector": ["conversation", "customer_phone"],
    },
    "customer_address": {
        "id": "718eef83-3750-49bb-a554-ac7401897f2e",
        "name": "customer_address",
        "value_type": "string",
        "value": "",
        "description": "Địa chỉ giao hàng",
        "selector": ["conversation", "customer_address"],
    },
}

FEATURES = {
    "opening_statement": (
        "Xin chào! Em là trợ lý PJ STORE. Em có thể giúp anh/chị tra cứu sản phẩm, "
        "tư vấn, chốt đơn hoặc kiểm tra đơn hàng."
    ),
    "suggested_questions": [
        "Shop có áo HD004 không?",
        "Giới thiệu về PJ STORE",
        "Em chốt mua 2 cái",
        "Kiểm tra đơn hàng SĐT 0901234567",
    ],
    "suggested_questions_after_answer": {"enabled": False},
    "text_to_speech": {"enabled": False, "language": "", "voice": ""},
    "speech_to_text": {"enabled": False},
    "retriever_resource": {"enabled": False},
    "sensitive_word_avoidance": {"enabled": False},
    "file_upload": {
        "image": {
            "enabled": False,
            "number_limits": 3,
            "transfer_methods": ["local_file", "remote_url"],
        },
        "enabled": False,
        "allowed_file_types": ["image"],
        "allowed_file_extensions": [".JPG", ".JPEG", ".PNG", ".GIF", ".WEBP", ".SVG"],
        "allowed_file_upload_methods": ["local_file", "remote_url"],
        "number_limits": 3,
        "fileUploadConfig": {
            "file_size_limit": 15,
            "batch_count_limit": 5,
            "file_upload_limit": 20,
            "image_file_size_limit": 10,
            "video_file_size_limit": 100,
            "audio_file_size_limit": 50,
            "workflow_file_upload_limit": 10,
            "image_file_batch_limit": 10,
            "single_chunk_attachment_limit": 10,
            "attachment_image_file_size_limit": 2,
        },
    },
}


def canvas(node_id: str, data: dict[str, Any], x: float, y: float, height: int = 98) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": "custom",
        "position": {"x": x, "y": y},
        "positionAbsolute": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
        "width": 242,
        "height": height,
        "selected": False,
        "data": data,
    }


def edge(source: str, target: str, source_handle: str = "source") -> dict[str, Any]:
    return {
        "id": f"{source}-{source_handle}-{target}",
        "type": "custom",
        "source": source,
        "target": target,
        "sourceHandle": source_handle,
        "targetHandle": "target",
        "data": {"isInIteration": False, "isInLoop": False},
        "zIndex": 0,
    }


def if_else(
    title: str,
    conditions: list[dict[str, Any]],
    logical: str = "and",
) -> dict[str, Any]:
    conds = []
    for c in conditions:
        conds.append(
            {
                "id": str(uuid.uuid4()),
                "varType": c.get("varType", "string"),
                "variable_selector": c["variable_selector"],
                "comparison_operator": c["comparison_operator"],
                "value": c.get("value", ""),
            }
        )
    return {
        "type": "if-else",
        "title": title,
        "desc": "",
        "selected": False,
        "cases": [
            {
                "case_id": "true",
                "logical_operator": logical,
                "conditions": conds,
            }
        ],
        "_targetBranches": [
            {"id": "true", "name": "IF"},
            {"id": "false", "name": "ELSE"},
        ],
        "isInIteration": False,
        "isInLoop": False,
    }


def assigner(title: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "assigner",
        "title": title,
        "desc": "",
        "selected": False,
        "version": "2",
        "items": items,
    }


def assign_item(conv_key: str, value_selector: list[str]) -> dict[str, Any]:
    return {
        "variable_selector": ["conversation", conv_key],
        "input_type": "variable",
        "operation": "over-write",
        "value": value_selector,
    }


def answer_node(title: str, text: str) -> dict[str, Any]:
    return {
        "type": "answer",
        "title": title,
        "desc": "",
        "selected": False,
        "answer": text,
        "variables": [],
    }


def template_node(title: str, source_id: str) -> dict[str, Any]:
    return {
        "type": "template-transform",
        "title": title,
        "desc": "",
        "selected": False,
        "template": "{{ json }}",
        "variables": [{"variable": "json", "value_selector": [source_id, "json"]}],
    }


def llm_node(title: str, prompt: str, memory: bool = True) -> dict[str, Any]:
    return {
        "type": "llm",
        "title": title,
        "desc": "",
        "selected": False,
        "model": {
            "provider": "langgenius/openai/openai",
            "name": "gpt-4.1-mini",
            "mode": "chat",
            "completion_params": {},
        },
        "vision": {"enabled": False},
        "context": {"enabled": True, "variable_selector": ["sys", "query"]},
        "memory": {
            "role_prefix": {"assistant": "", "user": ""},
            "window": {"enabled": memory, "size": 10},
        },
        "prompt_template": [{"id": str(uuid.uuid4()), "role": "system", "text": prompt}],
        "structured_output_enabled": True,
    }


def pe_node(
    title: str,
    instruction: str,
    parameters: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "type": "parameter-extractor",
        "title": title,
        "desc": "",
        "selected": False,
        "query": ["sys", "query"],
        "reasoning_mode": "prompt",
        "model": {
            "provider": "langgenius/openai/openai",
            "name": "gpt-4.1-mini",
            "mode": "chat",
            "completion_params": {"temperature": 0.7},
        },
        "vision": {"enabled": False},
        "instruction": instruction,
        "parameters": parameters,
        "memory": {
            "role_prefix": {"assistant": "", "user": ""},
            "window": {"enabled": True, "size": 10},
        },
    }


def code_node(title: str, code: str, variables: list[dict[str, Any]], outputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "code",
        "title": title,
        "desc": "",
        "selected": False,
        "code_language": "python3",
        "code": code,
        "variables": variables,
        "outputs": outputs,
    }


def clone_tool(base: dict[str, Any], node_id: str, title: str, tool_name: str, tool_label: str, parameters: dict[str, Any]) -> dict[str, Any]:
    data = copy.deepcopy(base)
    data["title"] = title
    data["tool_name"] = tool_name
    data["tool_label"] = tool_label
    data["tool_parameters"] = parameters
    return data


def build_tool_params_products(base_tool: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return preset parameter dicts keyed by action profile."""
    mixed = lambda v: {"type": "mixed", "value": v}
    const = lambda v: {"type": "constant", "value": v}
    return {
        "by_code": {
            "action": const("get_by_code"),
            "code": mixed(f"{{{{#{PE_LOOKUP}.product_code#}}}}"),
            "name": mixed(""),
            "barcode": mixed(""),
            "product_id": const(None),
            "category_id": const(None),
            "base_price": const(None),
            "retail_price": const(None),
            "description": mixed(""),
            "page_size": const(None),
            "current_item": const(None),
            "branch_ids": mixed(""),
        },
        "search": {
            "action": const("search"),
            "code": mixed(""),
            "name": mixed(f"{{{{#{PE_LOOKUP}.product_name#}}}}"),
            "barcode": mixed(""),
            "product_id": const(None),
            "category_id": const(None),
            "base_price": const(None),
            "retail_price": const(None),
            "description": mixed(""),
            "page_size": const(20),
            "current_item": const(0),
            "branch_ids": mixed(""),
        },
        "chot_lookup": {
            "action": const("get_by_code"),
            "code": mixed(f"{{{{#{CODE_RESOLVE}.code#}}}}"),
            "name": mixed(f"{{{{#{PE_CHOT}.product_name#}}}}"),
            "barcode": mixed(""),
            "product_id": const(None),
            "category_id": const(None),
            "base_price": const(None),
            "retail_price": const(None),
            "description": mixed(""),
            "page_size": const(None),
            "current_item": const(None),
            "branch_ids": mixed(""),
        },
    }


def build_kiotviet_tool_nodes(base_tool: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mixed = lambda v: {"type": "mixed", "value": v}
    const = lambda v: {"type": "constant", "value": v}
    profiles = build_tool_params_products(base_tool)

    nodes: dict[str, dict[str, Any]] = {
        KVP_BY_CODE: clone_tool(base_tool, KVP_BY_CODE, "KiotViet Get By Code", "kiotviet_products", "KiotViet Products", profiles["by_code"]),
        KVP_SEARCH: clone_tool(base_tool, KVP_SEARCH, "KiotViet Search", "kiotviet_products", "KiotViet Products", profiles["search"]),
        KVP_CHOT: clone_tool(base_tool, KVP_CHOT, "KiotViet Chốt Lookup", "kiotviet_products", "KiotViet Products", profiles["chot_lookup"]),
        KVC_GET: clone_tool(
            base_tool,
            KVC_GET,
            "KiotViet Get Customer",
            "kiotviet_customers",
            "KiotViet Customers",
            {
                "action": const("get_by_phone"),
                "contact_number": mixed(f"{{{{#{PE_CHOT}.customer_phone#}}}}"),
                "customer_id": const(None),
                "name": mixed(""),
                "email": mixed(""),
                "address": mixed(""),
                "keyword": mixed(""),
                "group_id": const(None),
                "page_size": const(None),
                "current_item": const(None),
            },
        ),
        KVC_CREATE: clone_tool(
            base_tool,
            KVC_CREATE,
            "KiotViet Create Customer",
            "kiotviet_customers",
            "KiotViet Customers",
            {
                "action": const("create"),
                "contact_number": mixed(f"{{{{#{PE_CHOT}.customer_phone#}}}}"),
                "name": mixed(f"{{{{#{PE_CHOT}.customer_name#}}}}"),
                "address": mixed(f"{{{{#{PE_CHOT}.customer_address#}}}}"),
                "customer_id": const(None),
                "email": mixed(""),
                "keyword": mixed(""),
                "group_id": const(None),
                "page_size": const(None),
                "current_item": const(None),
            },
        ),
        KVO_CREATE: clone_tool(
            base_tool,
            KVO_CREATE,
            "KiotViet Create Order",
            "kiotviet_orders",
            "KiotViet Orders",
            {
                "action": const("create"),
                "branch_id": const(1),
                "order_details": mixed(f"{{{{#{CODE_ORDER}.order_details#}}}}"),
                "description": mixed(
                    f"Chatbot PJ Store | {{{{#{PE_CHOT}.customer_name#}}}} | "
                    f"{{{{#{PE_CHOT}.customer_phone#}}}} | {{{{#{PE_CHOT}.customer_address#}}}}"
                ),
                "customer_id": mixed(f"{{{{#{CODE_ORDER}.customer_id#}}}}"),
                "customer_identifier": mixed(f"{{{{#{PE_CHOT}.customer_phone#}}}}"),
                "order_id": const(None),
                "code": mixed(""),
                "discount": const(None),
                "from_date": mixed(""),
                "to_date": mixed(""),
                "status": mixed(""),
                "page_size": const(None),
                "current_item": const(None),
            },
        ),
        KVO_LOOKUP: clone_tool(
            base_tool,
            KVO_LOOKUP,
            "KiotViet Lookup Order",
            "kiotviet_orders",
            "KiotViet Orders",
            {
                "action": const("get_by_customer"),
                "customer_identifier": mixed(f"{{{{#{PE_ORDER}.customer_phone#}}}}"),
                "code": mixed(f"{{{{#{PE_ORDER}.order_code#}}}}"),
                "branch_id": const(None),
                "customer_id": const(None),
                "order_details": mixed(""),
                "description": mixed(""),
                "discount": const(None),
                "from_date": mixed(""),
                "to_date": mixed(""),
                "status": mixed(""),
                "page_size": const(10),
                "current_item": const(0),
                "order_id": const(None),
            },
        ),
        KVO_GET: clone_tool(
            base_tool,
            KVO_GET,
            "KiotViet Get Order",
            "kiotviet_orders",
            "KiotViet Orders",
            {
                "action": const("get_by_code"),
                "code": mixed(f"{{{{#{PE_CANCEL}.order_code#}}}}"),
                "customer_identifier": mixed(f"{{{{#{PE_CANCEL}.customer_phone#}}}}"),
                "branch_id": const(None),
                "customer_id": const(None),
                "order_details": mixed(""),
                "description": mixed(""),
                "discount": const(None),
                "from_date": mixed(""),
                "to_date": mixed(""),
                "status": mixed(""),
                "page_size": const(None),
                "current_item": const(None),
                "order_id": const(None),
            },
        ),
        KVO_CANCEL: clone_tool(
            base_tool,
            KVO_CANCEL,
            "KiotViet Cancel Order",
            "kiotviet_orders",
            "KiotViet Orders",
            {
                "action": const("cancel"),
                "order_id": mixed(f"{{{{#{CODE_ORDER}.order_id#}}}}"),
                "description": mixed("Khách hủy qua chatbot"),
                "code": mixed(""),
                "branch_id": const(None),
                "customer_id": const(None),
                "customer_identifier": mixed(""),
                "order_details": mixed(""),
                "discount": const(None),
                "from_date": mixed(""),
                "to_date": mixed(""),
                "status": mixed(""),
                "page_size": const(None),
                "current_item": const(None),
            },
        ),
    }
    return nodes


ORDER_CODE = '''import json


def main(
    product_code: str,
    product_name: str,
    quantity: float,
    product_json: str,
    customer_json: str,
    conv_product_code: str,
) -> dict:
    code = (product_code or conv_product_code or "").strip()
    name = (product_name or "").strip()
    qty = int(quantity) if quantity else 1

    product_id = None
    price = None
    for raw in (product_json or "",):
        try:
            data = json.loads(raw)
            items = data.get("data") if isinstance(data, dict) else None
            item = items[0] if isinstance(items, list) and items else data
            if isinstance(item, dict):
                product_id = item.get("id") or item.get("productId")
                price = item.get("basePrice") or item.get("retailPrice") or item.get("price")
                if not code:
                    code = item.get("code") or ""
                if not name:
                    name = item.get("name") or ""
        except Exception:
            pass

    detail = {"productCode": code, "productName": name, "quantity": qty}
    if product_id:
        detail["productId"] = product_id
    if price:
        detail["price"] = price

    customer_id = None
    for raw in (customer_json or "",):
        try:
            data = json.loads(raw)
            items = data.get("data") if isinstance(data, dict) else None
            item = items[0] if isinstance(items, list) and items else data
            if isinstance(item, dict):
                customer_id = item.get("id") or item.get("customerId")
        except Exception:
            pass

    return {
        "order_details": json.dumps([detail], ensure_ascii=False),
        "customer_id": customer_id or 0,
        "order_id": 0,
    }
'''

RESOLVE_CODE = '''def main(product_code: str, conv_product_code: str) -> dict:
    code = (product_code or conv_product_code or "").strip()
    return {"code": code}
'''

CANCEL_CODE = '''import json


def main(order_json: str) -> dict:
    order_id = 0
    try:
        data = json.loads(order_json or "{}")
        items = data.get("data") if isinstance(data, dict) else None
        item = items[0] if isinstance(items, list) and items else data
        if isinstance(item, dict):
            order_id = item.get("id") or item.get("orderId") or 0
    except Exception:
        pass
    return {"order_id": order_id or 0}
'''


def transform_graph(graph: dict[str, Any]) -> dict[str, Any]:
    old_nodes = {n["id"]: n for n in graph["nodes"]}
    base_tool = old_nodes.get("1776077032827", {}).get("data") or old_nodes.get(KVP_BY_CODE, {}).get("data")
    if not base_tool:
        raise RuntimeError("Missing KiotViet Products base tool node")

    tool_data = build_kiotviet_tool_nodes(base_tool)

    qc_data = copy.deepcopy(old_nodes[QC]["data"])
    qc_data["classes"] = [
        {"id": CLS_LOOKUP, "name": "Tra cứu kho, tra cứu sản phẩm"},
        {"id": CLS_ADVICE, "name": "Tư vấn chung như: giới thiệu về cửa hàng, địa chỉ, hotline, tiểu sử..."},
        {"id": CLS_HELLO, "name": "Chào hỏi"},
        {"id": CLS_THANKS, "name": "Cám ơn, tạm biệt"},
        {"id": CLS_CHOT, "name": "Nếu khách hàng chốt mua sản phẩm."},
        {"id": CLS_ORDER_LOOKUP, "name": "Tra cứu đơn hàng, hỏi tình trạng giao hàng"},
        {"id": CLS_CANCEL, "name": "Hủy đơn hàng hoặc yêu cầu hủy đơn"},
        {"id": CLS_SUPPLEMENT, "name": "Bổ sung thông tin giao hàng, SĐT, địa chỉ"},
    ]
    qc_data["instructions"] = (
        "Phân loại câu hỏi khách hàng PJ STORE thời trang.\n"
        "- Tra cứu kho/SP: hỏi còn hàng, giá, mã HDxxx/PJxxx.\n"
        "- Chốt mua: khách xác nhận mua, đặt hàng, 'chốt', 'lấy', 'order'.\n"
        "- Tra cứu đơn: hỏi đơn đã đặt, giao chưa, mã đơn.\n"
        "- Hủy đơn: muốn hủy đơn đã đặt.\n"
        "- Bổ sung info: cung cấp SĐT, địa chỉ, tên người nhận.\n"
        "- Tư vấn chung: giới thiệu shop, chính sách.\n"
        "- Chào hỏi / Cám ơn: tương ứng."
    )
    qc_data["memory"] = {
        "window": {"enabled": True, "size": 10},
        "query_prompt_template": "{{#sys.query#}}\n\n{{#sys.files#}}",
    }

    pe_lookup = pe_node(
        "Parameter Extractor",
        old_nodes[PE_LOOKUP]["data"].get("instruction", ""),
        old_nodes[PE_LOOKUP]["data"].get("parameters", []),
    )

    pe_chot = pe_node(
        "Parameter Extractor Chốt",
        (
            "Khách chốt mua. Extract thông tin đơn:\n"
            "- product_code: mã SP (HDxxx, PJxxx). Nếu tin nhắn không có mã, dùng mã đã tra cứu trước đó trong hội thoại.\n"
            "- product_name: tên SP.\n"
            "- quantity: số lượng, mặc định 1.\n"
            "- customer_name, customer_phone, customer_address: thông tin nhận hàng nếu có.\n"
            "Không bịa thông tin."
        ),
        [
            {"name": "product_code", "type": "string", "required": False, "description": "Mã SP chốt mua"},
            {"name": "product_name", "type": "string", "required": False, "description": "Tên SP"},
            {"name": "quantity", "type": "number", "required": False, "description": "Số lượng, mặc định 1"},
            {"name": "customer_name", "type": "string", "required": False, "description": "Tên người nhận"},
            {"name": "customer_phone", "type": "string", "required": False, "description": "SĐT"},
            {"name": "customer_address", "type": "string", "required": False, "description": "Địa chỉ"},
        ],
    )

    pe_order = pe_node(
        "Parameter Extractor Đơn hàng",
        "Extract thông tin tra cứu đơn: order_code (mã đơn), customer_phone (SĐT đặt hàng).",
        [
            {"name": "order_code", "type": "string", "required": False, "description": "Mã đơn hàng"},
            {"name": "customer_phone", "type": "string", "required": False, "description": "SĐT khách hàng"},
        ],
    )

    pe_cancel = pe_node(
        "Parameter Extractor Hủy đơn",
        "Extract order_code và customer_phone để hủy đơn.",
        [
            {"name": "order_code", "type": "string", "required": False, "description": "Mã đơn cần hủy"},
            {"name": "customer_phone", "type": "string", "required": False, "description": "SĐT khách"},
        ],
    )

    pe_supplement = pe_node(
        "Parameter Extractor Bổ sung",
        "Extract thông tin giao hàng khách vừa cung cấp: customer_name, customer_phone, customer_address.",
        [
            {"name": "customer_name", "type": "string", "required": False, "description": "Tên người nhận"},
            {"name": "customer_phone", "type": "string", "required": False, "description": "SĐT"},
            {"name": "customer_address", "type": "string", "required": False, "description": "Địa chỉ"},
        ],
    )

    llm_lookup = llm_node(
        "LLM 3",
        "Dựa vào dữ liệu sản phẩm KiotViet, trả lời tự nhiên về giá, tồn kho, size/màu nếu có.\n"
        "<data>{{#1776150090873.output#}}{{#context#}}</data>",
    )

    llm_chot = llm_node(
        "LLM Chốt",
        "Khách vừa chốt mua. Dựa kết quả KiotViet:\n"
        "- Thành công: xác nhận + mã đơn nếu có + bước tiếp theo.\n"
        "- Thiếu info: nhờ bổ sung tên/SĐT/địa chỉ.\n"
        "- Lỗi: hướng dẫn liên hệ hotline.\n"
        "<data>{{#1779980090874.output#}}{{#context#}}</data>",
    )

    nodes = [
        canvas(START, old_nodes[START]["data"], 0, 200, 115),
        canvas(QC, qc_data, 340, 110, 420),
        canvas(KB, old_nodes[KB]["data"], 704, 168, 134),
        canvas(A_HELLO, old_nodes[A_HELLO]["data"], 704, 312, 148),
        canvas(LLM_ADVICE, old_nodes[LLM_ADVICE]["data"], 1046, 213, 88),
        canvas(A_ADVICE, old_nodes[A_ADVICE]["data"], 1388, 221, 102),
        canvas(A_THANKS, old_nodes[A_THANKS]["data"], 704, 500, 132),
        canvas(PE_LOOKUP, pe_lookup, 704, 0, 88),
        canvas(IF_LOOKUP_CODE, if_else("Có mã SP?", [{"variable_selector": [PE_LOOKUP, "product_code"], "comparison_operator": "not empty"}]), 1046, -40, 140),
        canvas(KVP_BY_CODE, tool_data[KVP_BY_CODE], 1388, -80, 52),
        canvas(KVP_SEARCH, tool_data[KVP_SEARCH], 1388, 40, 52),
        canvas(TMPL_LOOKUP, old_nodes[TMPL_LOOKUP]["data"], 1731, 0, 52),
        canvas(ASSIGN_PRODUCT, assigner("Lưu SP vào hội thoại", [
            assign_item("product_code", [PE_LOOKUP, "product_code"]),
            assign_item("product_name", [PE_LOOKUP, "product_name"]),
        ]), 1980, 0, 86),
        canvas(LLM_LOOKUP, llm_lookup, 2220, 0, 88),
        canvas(A_LOOKUP, old_nodes[A_LOOKUP]["data"], 2560, 0, 102),
        canvas(PE_CHOT, pe_chot, 704, 780, 88),
        canvas(IF_CHOT_PRODUCT, if_else(
            "Chốt có SP?",
            [
                {"variable_selector": [PE_CHOT, "product_code"], "comparison_operator": "not empty"},
                {"variable_selector": ["conversation", "product_code"], "comparison_operator": "not empty"},
            ],
            logical="or",
        ), 1046, 760, 140),
        canvas(CODE_RESOLVE, code_node(
            "Resolve Product Code",
            RESOLVE_CODE,
            [
                {"variable": "product_code", "value_selector": [PE_CHOT, "product_code"]},
                {"variable": "conv_product_code", "value_selector": ["conversation", "product_code"]},
            ],
            {"code": {"type": "string", "children": None}},
        ), 1240, 720, 54),
        canvas(A_CHOT_NO_PRODUCT, answer_node("Answer Thiếu SP", "Anh/chị cho em mã hoặc tên sản phẩm muốn chốt ạ?"), 1388, 900, 120),
        canvas(KVP_CHOT, tool_data[KVP_CHOT], 1388, 720, 52),
        canvas(IF_CHOT_READY, if_else("Đủ info tạo đơn?", [
            {"variable_selector": [PE_CHOT, "customer_phone"], "comparison_operator": "not empty"},
            {"variable_selector": [PE_CHOT, "customer_name"], "comparison_operator": "not empty"},
        ]), 1731, 720, 160),
        canvas(A_CHOT_MISSING, answer_node("Answer Thiếu info", "Anh/chị cho em xin **họ tên, SĐT và địa chỉ nhận hàng** để em tạo đơn ạ."), 2072, 900, 140),
        canvas(KVC_GET, tool_data[KVC_GET], 2072, 680, 52),
        canvas(KVC_CREATE, tool_data[KVC_CREATE], 2410, 760, 52),
        canvas(CODE_ORDER, code_node(
            "Build Order JSON",
            ORDER_CODE,
            [
                {"variable": "product_code", "value_selector": [PE_CHOT, "product_code"]},
                {"variable": "product_name", "value_selector": [PE_CHOT, "product_name"]},
                {"variable": "quantity", "value_selector": [PE_CHOT, "quantity"]},
                {"variable": "product_json", "value_selector": [KVP_CHOT, "json"]},
                {"variable": "customer_json", "value_selector": [KVC_GET, "json"]},
                {"variable": "conv_product_code", "value_selector": ["conversation", "product_code"]},
            ],
            {
                "order_details": {"type": "string", "children": None},
                "customer_id": {"type": "number", "children": None},
                "order_id": {"type": "number", "children": None},
            },
        ), 2410, 680, 54),
        canvas(KVO_CREATE, tool_data[KVO_CREATE], 2750, 680, 52),
        canvas(TMPL_CHOT, old_nodes[TMPL_CHOT]["data"], 3090, 680, 52),
        canvas(LLM_CHOT, llm_chot, 3430, 680, 88),
        canvas(A_CHOT, {"type": "answer", "title": "Answer Chốt", "desc": "", "selected": False, "answer": f"{{{{#{LLM_CHOT}.text#}}}}", "variables": []}, 3770, 680, 102),
        canvas(PE_ORDER, pe_order, 704, 1100, 88),
        canvas(KVO_LOOKUP, tool_data[KVO_LOOKUP], 1046, 1100, 52),
        canvas(TMPL_ORDER, template_node("Template Đơn hàng", KVO_LOOKUP), 1388, 1100, 52),
        canvas(LLM_ORDER, llm_node("LLM Tra cứu đơn", "Trả lời tình trạng đơn hàng dựa dữ liệu KiotViet.\n<data>{{#177999012003.output#}}{{#context#}}</data>"), 1731, 1100, 88),
        canvas(A_ORDER, answer_node("Answer Tra cứu đơn", f"{{{{#{LLM_ORDER}.text#}}}}"), 2072, 1100, 102),
        canvas(PE_CANCEL, pe_cancel, 704, 1400, 88),
        canvas(KVO_GET, tool_data[KVO_GET], 1046, 1400, 52),
        canvas(IF_ORDER_FOUND, if_else("Tìm thấy đơn?", [{"variable_selector": [KVO_GET, "text"], "comparison_operator": "not empty"}]), 1388, 1400, 140),
        canvas(CODE_CANCEL_PARSE, code_node(
            "Parse Order ID",
            CANCEL_CODE,
            [{"variable": "order_json", "value_selector": [KVO_GET, "json"]}],
            {"order_id": {"type": "number", "children": None}},
        ), 1731, 1340, 54),
        canvas(KVO_CANCEL, tool_data[KVO_CANCEL], 2072, 1340, 52),
        canvas(LLM_CANCEL, llm_node("LLM Hủy đơn", "Thông báo kết quả hủy đơn.\n<data>{{#177999013004.text#}}{{#context#}}</data>"), 2410, 1340, 88),
        canvas(A_CANCEL, answer_node("Answer Hủy đơn", f"{{{{#{LLM_CANCEL}.text#}}}}"), 2750, 1340, 102),
        canvas(A_ORDER_NOT_FOUND, answer_node("Answer Không tìm thấy đơn", "Em chưa tìm thấy đơn theo thông tin anh/chị cung cấp. Anh/chị kiểm tra lại mã đơn hoặc SĐT nhé."), 1731, 1480, 140),
        canvas(PE_SUPPLEMENT, pe_supplement, 704, 1700, 88),
        canvas(ASSIGN_CUSTOMER, assigner("Lưu thông tin giao hàng", [
            assign_item("customer_name", [PE_SUPPLEMENT, "customer_name"]),
            assign_item("customer_phone", [PE_SUPPLEMENT, "customer_phone"]),
            assign_item("customer_address", [PE_SUPPLEMENT, "customer_address"]),
        ]), 1046, 1700, 86),
        canvas(IF_SUPPLEMENT_READY, if_else("Đủ info giao hàng?", [
            {"variable_selector": ["conversation", "product_code"], "comparison_operator": "not empty"},
            {"variable_selector": ["conversation", "customer_phone"], "comparison_operator": "not empty"},
            {"variable_selector": ["conversation", "customer_name"], "comparison_operator": "not empty"},
            {"variable_selector": ["conversation", "customer_address"], "comparison_operator": "not empty"},
        ]), 1388, 1700, 180),
        canvas(A_SUPPLEMENT, answer_node(
            "Answer Bổ sung",
            "Em đã ghi nhận thông tin giao hàng. Anh/chị xác nhận **chốt mua {{#conversation.product_name#}}** "
            "(mã {{#conversation.product_code#}}) để em tạo đơn nhé!",
        ), 1731, 1700, 140),
        canvas(A_SUPPLEMENT_WAIT, answer_node(
            "Answer Chờ chốt",
            "Em đã lưu thông tin. Anh/chị vui lòng cho em biết mã/tên sản phẩm muốn mua để em tạo đơn ạ.",
        ), 1731, 1840, 120),
    ]

    # Fix template lookup to accept both KVP paths - use first available; wire from both to same template
    tmpl = next(n for n in nodes if n["id"] == TMPL_LOOKUP)
    tmpl["data"]["variables"] = [{"variable": "json", "value_selector": [KVP_BY_CODE, "json"]}]

    edges = [
        edge(START, QC),
        edge(QC, PE_LOOKUP, CLS_LOOKUP),
        edge(QC, KB, CLS_ADVICE),
        edge(QC, A_HELLO, CLS_HELLO),
        edge(QC, A_THANKS, CLS_THANKS),
        edge(QC, PE_CHOT, CLS_CHOT),
        edge(QC, PE_ORDER, CLS_ORDER_LOOKUP),
        edge(QC, PE_CANCEL, CLS_CANCEL),
        edge(QC, PE_SUPPLEMENT, CLS_SUPPLEMENT),
        edge(KB, LLM_ADVICE),
        edge(LLM_ADVICE, A_ADVICE),
        edge(PE_LOOKUP, IF_LOOKUP_CODE),
        edge(IF_LOOKUP_CODE, KVP_BY_CODE, "true"),
        edge(IF_LOOKUP_CODE, KVP_SEARCH, "false"),
        edge(KVP_BY_CODE, TMPL_LOOKUP),
        edge(KVP_SEARCH, TMPL_LOOKUP),
        edge(TMPL_LOOKUP, ASSIGN_PRODUCT),
        edge(ASSIGN_PRODUCT, LLM_LOOKUP),
        edge(LLM_LOOKUP, A_LOOKUP),
        edge(PE_CHOT, IF_CHOT_PRODUCT),
        edge(IF_CHOT_PRODUCT, CODE_RESOLVE, "true"),
        edge(IF_CHOT_PRODUCT, A_CHOT_NO_PRODUCT, "false"),
        edge(CODE_RESOLVE, KVP_CHOT),
        edge(KVP_CHOT, IF_CHOT_READY),
        edge(IF_CHOT_READY, KVC_GET, "true"),
        edge(IF_CHOT_READY, A_CHOT_MISSING, "false"),
        edge(CODE_ORDER, KVO_CREATE),
        edge(KVO_CREATE, TMPL_CHOT),
        edge(TMPL_CHOT, LLM_CHOT),
        edge(LLM_CHOT, A_CHOT),
        edge(PE_ORDER, KVO_LOOKUP),
        edge(KVO_LOOKUP, TMPL_ORDER),
        edge(TMPL_ORDER, LLM_ORDER),
        edge(LLM_ORDER, A_ORDER),
        edge(PE_CANCEL, KVO_GET),
        edge(KVO_GET, IF_ORDER_FOUND),
        edge(IF_ORDER_FOUND, CODE_CANCEL_PARSE, "true"),
        edge(IF_ORDER_FOUND, A_ORDER_NOT_FOUND, "false"),
        edge(CODE_CANCEL_PARSE, KVO_CANCEL),
        edge(KVO_CANCEL, LLM_CANCEL),
        edge(LLM_CANCEL, A_CANCEL),
        edge(PE_SUPPLEMENT, ASSIGN_CUSTOMER),
        edge(ASSIGN_CUSTOMER, IF_SUPPLEMENT_READY),
        edge(IF_SUPPLEMENT_READY, A_SUPPLEMENT, "true"),
        edge(IF_SUPPLEMENT_READY, A_SUPPLEMENT_WAIT, "false"),
        edge(KVC_GET, IF_CUSTOMER),
        edge(IF_CUSTOMER, CODE_ORDER, "true"),
        edge(IF_CUSTOMER, KVC_CREATE, "false"),
        edge(KVC_CREATE, CODE_ORDER),
    ]

    nodes.append(canvas(IF_CUSTOMER, if_else("KH đã có trên KOV?", [{"variable_selector": [KVC_GET, "text"], "comparison_operator": "not empty"}]), 2240, 680, 140))

    for n in nodes:
        if n["id"] == KVO_CANCEL:
            n["data"]["tool_parameters"]["order_id"]["value"] = f"{{{{#{CODE_CANCEL_PARSE}.order_id#}}}}"
        if n["id"] == LLM_ORDER:
            n["data"]["prompt_template"][0]["text"] = (
                "Trả lời tình trạng đơn hàng dựa dữ liệu KiotViet.\n"
                f"<data>{{{{#{TMPL_ORDER}.output#}}}}{{#context#}}</data>"
            )

    return {
        "nodes": nodes,
        "edges": edges,
        "viewport": graph.get("viewport", {"x": 0, "y": 0, "zoom": 0.7}),
    }


def load_graph(conn, workflow_id: str) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute("SELECT graph FROM workflows WHERE id = %s", (workflow_id,))
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"Workflow {workflow_id} not found")
        return row[0] if isinstance(row[0], dict) else json.loads(row[0])


def save_workflow(conn, workflow_id: str, graph: dict[str, Any]) -> None:
    graph_json = json.dumps(graph, ensure_ascii=False)
    features_json = json.dumps(FEATURES, ensure_ascii=False)
    conv_json = json.dumps(CONV_VARS, ensure_ascii=False)
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE workflows
            SET graph = %s::json,
                features = %s::json,
                conversation_variables = %s::json,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (graph_json, features_json, conv_json, workflow_id),
        )
    conn.commit()


def main() -> None:
    conn = psycopg2.connect(**DB)
    try:
        for wf_id in WORKFLOW_IDS:
            graph = load_graph(conn, wf_id)
            updated = transform_graph(graph)
            save_workflow(conn, wf_id, updated)
            print(f"OK {wf_id}: {len(updated['nodes'])} nodes, {len(updated['edges'])} edges")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
