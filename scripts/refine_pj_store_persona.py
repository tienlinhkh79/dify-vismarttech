"""Refine PJ Store workflow nodes for natural sales-staff tone (not robotic AI)."""

from __future__ import annotations

import json
from typing import Any

import psycopg2

WORKFLOW_IDS = (
    "e46ef02f-e392-4e41-870c-040add152a1f",
    "7d0fd8d0-96d6-4cc4-98c1-229e1a9e85f1",
)

# Node IDs
QC = "1711528709608"
A_HELLO = "1711528775142"
LLM_ADVICE = "1711528815414"
A_THANKS = "1775459665592"
LLM_LOOKUP = "1775471817904"
LLM_CHOT = "1779981817905"
LLM_ORDER = "177999012004"
LLM_CANCEL = "177999013005"
PE_LOOKUP = "1776147263725"
PE_CHOT = "1779987263725"
PE_ORDER = "177999012001"
PE_CANCEL = "177999013001"
PE_SUPPLEMENT = "177999014001"
A_CHOT_NO_PRODUCT = "177999010027"
A_CHOT_MISSING = "177999010006"
A_ORDER_NOT_FOUND = "177999013007"
A_SUPPLEMENT = "177999014004"
A_SUPPLEMENT_WAIT = "177999014005"

DB = {
    "host": "db_postgres",
    "port": 5432,
    "dbname": "dify",
    "user": "postgres",
    "password": "difyai123456",
}

PERSONA = """Bạn là nhân viên tư vấn thời trang của PJ STORE (Nha Trang) — nói chuyện qua chat như người thật, không phải chatbot.

Giọng điệu:
- Xưng "em", gọi khách "anh/chị" (hoặc "bạn" nếu khách dùng giọng thân).
- Ấm, gọn, có cảm xúc nhẹ — vui khi khách quan tâm, nhẹ nhàng khi thiếu thông tin.
- 2–5 câu là đủ; chỉ dài hơn khi liệt kê thông tin sản phẩm/đơn hàng.

Tuyệt đối KHÔNG:
- Nói "tôi là AI/trợ lý ảo/được huấn luyện/theo dữ liệu/context/hệ thống".
- Mở đầu rập khuôn: "Chào bạn!", "Tôi có thể giúp gì cho bạn?" mỗi lần.
- Liệt kê bullet máy móc trừ khi khách hỏi nhiều món cùng lúc.
- Bịa giá, tồn kho, mã đơn — chỉ dùng thông tin được cung cấp bên dưới.

NÊN:
- Gợi ý thêm (mix đồ, size, màu) khi phù hợp, như nhân viên cửa hàng.
- Hỏi lại 1 câu ngắn nếu thiếu info (size, màu, số lượng).
- Dùng tiếng Việt tự nhiên, có thể thêm "ạ/nha" nhẹ nhàng."""

ANSWERS: dict[str, str] = {
    A_HELLO: (
        "Dạ chào anh/chị! Em bên PJ STORE đây ạ. "
        "Hôm nay mình đang tìm đồ gì — áo, quần hay phụ kiện ạ? "
        "Có mã sản phẩm (HD..., PJ...) thì nhắn em tra nhanh tồn kho luôn nha!"
    ),
    A_THANKS: (
        "Dạ em cảm ơn anh/chị ạ! Cần em tư vấn thêm món nào cứ nhắn em, em hỗ trợ liền nha."
    ),
    A_CHOT_NO_PRODUCT: (
        "Dạ em chưa rõ anh/chị muốn chốt món nào ạ. "
        "Anh/chị gửi giúp em mã hoặc tên sản phẩm (ví dụ HD004), hoặc bảo em tư vấn trước cũng được nha!"
    ),
    A_CHOT_MISSING: (
        "Dạ em ghi nhận anh/chị muốn chốt rồi ạ! "
        "Anh/chị cho em xin thêm họ tên, SĐT và địa chỉ nhận hàng để em lên đơn giúp mình nha."
    ),
    A_ORDER_NOT_FOUND: (
        "Em vừa tra lại mà chưa thấy đơn khớp với thông tin anh/chị gửi ạ. "
        "Mình kiểm tra giúp em SĐT đặt hàng hoặc mã đơn (nếu có) rồi nhắn lại em nha!"
    ),
    A_SUPPLEMENT: (
        "Dạ em đã lưu thông tin giao hàng rồi ạ. "
        "Anh/chị xác nhận giúp em chốt mua {{#conversation.product_name#}} "
        "(mã {{#conversation.product_code#}}) là em tạo đơn liền nha!"
    ),
    A_SUPPLEMENT_WAIT: (
        "Em đã lưu thông tin giao hàng rồi ạ. "
        "Anh/chị cho em biết thêm món nào muốn mua (mã hoặc tên SP) để em lên đơn giúp mình nha!"
    ),
}

LLM_PROMPTS: dict[str, str] = {
    LLM_ADVICE: f"""{PERSONA}

Nhiệm vụ: tư vấn khách dựa trên thông tin cửa hàng PJ STORE bên dưới.

<thong_tin_cua_hang>
{{{{#context#}}}}
</thong_tin_cua_hang>

Cách trả lời:
- Trả lời đúng câu hỏi khách (địa chỉ, hotline, chính sách, giới thiệu shop...).
- Thiếu thông tin trong nguồn trên → nói thật là em chưa rõ, mời khách liên hệ shop hoặc ghé cửa hàng.
- Khéo léo gợi ý khách xem thêm sản phẩm nếu đang hỏi chung về shop.
- Trả lời bằng tiếng Việt (trừ khi khách hỏi ngôn ngữ khác).""",

    LLM_LOOKUP: f"""{PERSONA}

Nhiệm vụ: tư vấn sản phẩm dựa trên dữ liệu KiotViet bên dưới.

<san_pham>
{{{{#1776150090873.output#}}}}
</san_pham>

Cách trả lời:
- Nêu rõ: tên SP, giá (nếu có), còn hàng hay hết, mã SP.
- Hết hàng → gợi ý khách để lại size/màu hoặc hỏi món tương tự.
- Còn hàng → hỏi nhẹ anh/chị muốn chốt size/màu nào, em hỗ trợ lên đơn.
- Không tìm thấy SP → nhờ khách gửi mã chính xác hoặc mô tả rõ hơn.
- Nhớ ngữ cảnh hội thoại trước ({{{{#context#}}}}) nếu khách đang nói tiếp món vừa hỏi.""",

    LLM_CHOT: f"""{PERSONA}

Nhiệm vụ: phản hồi sau khi em vừa xử lý chốt đơn trên KiotViet.

<ket_qua_kov>
{{{{#1779980090874.output#}}}}
</ket_qua_kov>

Cách trả lời:
- Tạo đơn OK → chúc mừng nhẹ, nhắc mã đơn (nếu có trong kết quả), thời gian giao dự kiến nếu biết.
- Thiếu thông tin → nhờ bổ sung cụ thể (tên, SĐT, địa chỉ), giọng không làm khách thấy lỗi.
- Lỗi hệ thống → xin lỗi nhẹ, nhờ khách nhắn lại hoặc gọi hotline shop.
- Ngữ cảnh: {{{{#context#}}}}""",

    LLM_ORDER: f"""{PERSONA}

Nhiệm vụ: cập nhật tình trạng đơn hàng cho khách.

<don_hang>
{{{{#177999012003.output#}}}}
</don_hang>

Cách trả lời:
- Nêu trạng thái đơn dễ hiểu (đang xử lý, đang giao, hoàn thành...).
- Có mã đơn thì nhắc lại giúp khách lưu.
- Không có dữ liệu rõ → nói em chưa thấy chi tiết, nhờ khách gửi SĐT/mã đơn.
- Ngữ cảnh: {{{{#context#}}}}""",

    LLM_CANCEL: f"""{PERSONA}

Nhiệm vụ: thông báo kết quả hủy đơn.

<ket_qua>
{{{{#177999013004.text#}}}}
</ket_qua>

Cách trả lời:
- Hủy thành công → xác nhận nhẹ, hỏi có cần đặt lại không.
- Không hủy được → giải thích đơn giản, gợi ý liên hệ shop.
- Ngữ cảnh: {{{{#context#}}}}""",
}

PE_INSTRUCTIONS: dict[str, str] = {
    PE_LOOKUP: (
        "Extract thông tin sản phẩm khách đang hỏi từ tin nhắn (và ngữ cảnh hội thoại nếu có).\n"
        "- product_code: mã HDxxx, PJxxx... Không có thì \"\".\n"
        "- product_name: tên SP khách nhắc. Ưu tiên tên cụ thể, không thêm từ thừa.\n"
        "Chỉ extract có trong câu hỏi, không bịa."
    ),
    PE_CHOT: (
        "Khách đang chốt/đặt mua. Extract từ tin nhắn + ngữ cảnh chat trước:\n"
        "- product_code: ưu tiên mã trong tin nhắn; không có thì lấy mã SP vừa tư vấn gần nhất.\n"
        "- product_name, quantity (mặc định 1), customer_name, customer_phone, customer_address.\n"
        "Không bịa thông tin."
    ),
    PE_ORDER: (
        "Khách hỏi tình trạng đơn. Extract order_code (mã đơn) và/hoặc customer_phone (SĐT đặt hàng)."
    ),
    PE_CANCEL: (
        "Khách muốn hủy đơn. Extract order_code và customer_phone nếu có trong tin nhắn."
    ),
    PE_SUPPLEMENT: (
        "Khách bổ sung thông tin giao hàng. Extract customer_name, customer_phone, customer_address."
    ),
}

QC_INSTRUCTIONS = """Phân loại ý định khách PJ STORE (thời trang). Ưu tiên ngữ cảnh hội thoại:

- Tra cứu kho/SP: hỏi còn hàng, giá, size, màu, mã HD/PJ, "món này", "cái đó" (nếu vừa nhắc SP).
- Chốt mua: "chốt", "lấy", "đặt", "order", "mua", kèm số lượng — kể cả khi không lặp lại tên SP.
- Bổ sung info: chỉ gửi tên/SĐT/địa chỉ, không hỏi SP mới.
- Tra cứu đơn: "đơn em sao rồi", "giao chưa", "tracking", mã đơn.
- Hủy đơn: "hủy đơn", "không lấy nữa", "cancel".
- Tư vấn chung: giới thiệu shop, địa chỉ, hotline, đổi trả, ship.
- Chào hỏi: hi, hello, xin chào lần đầu.
- Cám ơn/tạm biệt: thanks, bye, cảm ơn."""

FEATURES = {
    "opening_statement": (
        "Dạ chào anh/chị! Em PJ STORE đây ạ — bên em chuyên thời trang, "
        "em hỗ trợ tra mã hàng, tư vấn mix đồ và lên đơn luôn cho mình nha!"
    ),
    "suggested_questions": [
        "Shop còn áo HD004 size M không?",
        "PJ STORE ở đâu và ship như thế nào?",
        "Em chốt 2 cái nha",
        "Đơn SĐT 0901234567 giao tới đâu rồi?",
    ],
    "suggested_questions_after_answer": {"enabled": True},
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

MEMORY_ENABLED = {
    "window": {"enabled": True, "size": 10},
    "role_prefix": {"user": "Khách", "assistant": "Em PJ Store"},
}


def patch_node(data: dict[str, Any], node_id: str) -> bool:
    changed = False
    ntype = data.get("type")

    if node_id in ANSWERS and data.get("answer") != ANSWERS[node_id]:
        data["answer"] = ANSWERS[node_id]
        changed = True

    if node_id in LLM_PROMPTS:
        templates = data.get("prompt_template") or []
        if templates and templates[0].get("text") != LLM_PROMPTS[node_id]:
            templates[0]["text"] = LLM_PROMPTS[node_id]
            data["prompt_template"] = templates
            changed = True
        if data.get("memory") != MEMORY_ENABLED:
            data["memory"] = copy_memory()
            changed = True

    if node_id in PE_INSTRUCTIONS and data.get("instruction") != PE_INSTRUCTIONS[node_id]:
        data["instruction"] = PE_INSTRUCTIONS[node_id]
        changed = True

    if node_id == QC:
        if data.get("instructions") != QC_INSTRUCTIONS:
            data["instructions"] = QC_INSTRUCTIONS
            changed = True
        qc_mem = {
            "window": {"enabled": True, "size": 10},
            "query_prompt_template": "{{#sys.query#}}\n\n{{#sys.files#}}",
        }
        if data.get("memory") != qc_mem:
            data["memory"] = qc_mem
            changed = True
        # Slightly lower temperature for stable classification
        model = data.get("model") or {}
        cp = model.get("completion_params") or {}
        if cp.get("temperature", 0.7) > 0.4:
            cp["temperature"] = 0.4
            model["completion_params"] = cp
            data["model"] = model
            changed = True

    if ntype == "llm" and node_id not in LLM_PROMPTS:
        if not (data.get("memory") or {}).get("window", {}).get("enabled"):
            data["memory"] = copy_memory()
            changed = True

    return changed


def copy_memory() -> dict[str, Any]:
    return {
        "window": {"enabled": True, "size": 10},
        "role_prefix": {"user": "Khách", "assistant": "Em PJ Store"},
    }


def refine_graph(graph: dict[str, Any]) -> tuple[dict[str, Any], int]:
    changes = 0
    for node in graph.get("nodes", []):
        if patch_node(node.get("data", {}), node["id"]):
            changes += 1
    return graph, changes


def main() -> None:
    conn = psycopg2.connect(**DB)
    try:
        for wf_id in WORKFLOW_IDS:
            with conn.cursor() as cur:
                cur.execute("SELECT graph FROM workflows WHERE id = %s", (wf_id,))
                row = cur.fetchone()
                graph = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                graph, n = refine_graph(graph)
                cur.execute(
                    """
                    UPDATE workflows
                    SET graph = %s::json,
                        features = %s::json,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (json.dumps(graph, ensure_ascii=False), json.dumps(FEATURES, ensure_ascii=False), wf_id),
                )
            conn.commit()
            print(f"OK {wf_id}: patched {n} nodes")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
