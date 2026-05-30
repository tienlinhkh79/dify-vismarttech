"""Full workflow migration for Vieclamtop recruitment assistant (756d906f…)."""

from __future__ import annotations

import copy
import json
import uuid
from typing import Any

import psycopg2

APP_ID = "756d906f-3b82-4087-a6dd-e45e9745d04f"
DATASET_ID = "ef72fd07-79fc-4c48-89da-4ec9081330a4"
WORKFLOW_IDS = (
    "2441f8bf-f16e-4668-bed8-cb8aeb784a46",  # draft
    "ce1caf06-f391-4e01-976b-3c92b86f237b",  # published
)

START = "1711528914102"
KB_GENERAL = "1711528915811"

QC = "178100001001"
CLS_HELLO = "178100001002"
CLS_THANKS = "178100001003"
CLS_JOB_SEARCH = "178100001004"
CLS_JOB_DETAIL = "178100001005"
CLS_FAQ = "178100001006"
CLS_CV = "178100001007"
CLS_EMPLOYER = "178100001008"
CLS_LEAD = "178100001009"
CLS_GENERAL = "178100001010"

A_HELLO = "178100002001"
A_THANKS = "178100002002"

PE_JOB = "178100003001"
PE_DETAIL = "178100003002"
PE_EMPLOYER = "178100003003"
PE_LEAD = "178100003004"

ASSIGN_JOB = "178100004001"
ASSIGN_LEAD = "178100004002"
ASSIGN_EMP = "178100004003"
ASSIGN_DETAIL = "178100004004"

IF_JOB_READY = "178100005001"
IF_LEAD_READY = "178100005002"

A_JOB_ASK = "178100006001"
A_LEAD_ASK = "178100006002"

KB_JOB = "178100007001"
KB_FAQ = "178100007002"
KB_DETAIL = "178100007003"
KB_EMP = "178100007004"

LLM_JOB = "178100008001"
LLM_FAQ = "178100008002"
LLM_DETAIL = "178100008003"
LLM_CV = "178100008004"
LLM_EMP = "178100008005"
LLM_GENERAL = "1711528917469"

A_JOB = "178100009001"
A_FAQ = "178100009002"
A_DETAIL = "178100009003"
A_CV = "178100009004"
A_EMP = "178100009005"
A_LEAD = "178100009006"
A_GENERAL = "1711528919501"

DB = {
    "host": "db_postgres",
    "port": 5432,
    "dbname": "dify",
    "user": "postgres",
    "password": "difyai123456",
}

CONV_VARS = {
    "user_type": {
        "id": "a1b2c3d4-e001-4001-8001-000000000001",
        "name": "user_type",
        "value_type": "string",
        "value": "",
        "description": "candidate | employer | unknown",
        "selector": ["conversation", "user_type"],
    },
    "full_name": {
        "id": "a1b2c3d4-e001-4001-8001-000000000002",
        "name": "full_name",
        "value_type": "string",
        "value": "",
        "description": "Họ tên người dùng",
        "selector": ["conversation", "full_name"],
    },
    "phone": {
        "id": "a1b2c3d4-e001-4001-8001-000000000003",
        "name": "phone",
        "value_type": "string",
        "value": "",
        "description": "SĐT liên hệ",
        "selector": ["conversation", "phone"],
    },
    "email": {
        "id": "a1b2c3d4-e001-4001-8001-000000000004",
        "name": "email",
        "value_type": "string",
        "value": "",
        "description": "Email",
        "selector": ["conversation", "email"],
    },
    "desired_role": {
        "id": "a1b2c3d4-e001-4001-8001-000000000005",
        "name": "desired_role",
        "value_type": "string",
        "value": "",
        "description": "Vị trí/việc mong muốn",
        "selector": ["conversation", "desired_role"],
    },
    "location": {
        "id": "a1b2c3d4-e001-4001-8001-000000000006",
        "name": "location",
        "value_type": "string",
        "value": "",
        "description": "Địa điểm làm việc mong muốn",
        "selector": ["conversation", "location"],
    },
    "experience_years": {
        "id": "a1b2c3d4-e001-4001-8001-000000000007",
        "name": "experience_years",
        "value_type": "string",
        "value": "",
        "description": "Số năm kinh nghiệm",
        "selector": ["conversation", "experience_years"],
    },
    "japanese_level": {
        "id": "a1b2c3d4-e001-4001-8001-000000000008",
        "name": "japanese_level",
        "value_type": "string",
        "value": "",
        "description": "Trình độ tiếng Nhật (N5–N1)",
        "selector": ["conversation", "japanese_level"],
    },
    "salary_expectation": {
        "id": "a1b2c3d4-e001-4001-8001-000000000009",
        "name": "salary_expectation",
        "value_type": "string",
        "value": "",
        "description": "Mức lương mong muốn",
        "selector": ["conversation", "salary_expectation"],
    },
    "job_title_interest": {
        "id": "a1b2c3d4-e001-4001-8001-00000000000a",
        "name": "job_title_interest",
        "value_type": "string",
        "value": "",
        "description": "Tin/vị trí đang quan tâm",
        "selector": ["conversation", "job_title_interest"],
    },
    "company_name": {
        "id": "a1b2c3d4-e001-4001-8001-00000000000b",
        "name": "company_name",
        "value_type": "string",
        "value": "",
        "description": "Tên công ty (NTD)",
        "selector": ["conversation", "company_name"],
    },
}

FEATURES = {
    "opening_statement": (
        "Xin chào! Em là trợ lý tuyển dụng Vieclamtop. Em có thể giúp anh/chị:\n"
        "• Tìm việc làm phù hợp (Việt Nam, Nhật Bản, Đài Loan…)\n"
        "• Tư vấn thủ tục, visa, phỏng vấn\n"
        "• Hướng dẫn viết CV / hồ sơ\n"
        "• Hỗ trợ nhà tuyển dụng đăng tin\n"
        "Anh/chị cần em hỗ trợ điều gì ạ?"
    ),
    "suggested_questions": [
        "Em muốn tìm việc làm tại Nhật, cần điều kiện gì?",
        "Có tin tuyển kỹ sư xây dựng tại Fukuoka không?",
        "Hướng dẫn em viết CV xin việc Nhật",
        "Công ty em muốn đăng tin tuyển dụng",
    ],
    "suggested_questions_after_answer": {"enabled": True},
    "text_to_speech": {"enabled": False, "language": "", "voice": ""},
    "speech_to_text": {"enabled": True},
    "retriever_resource": {"enabled": True},
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

PERSONA = """Bạn là nhân viên tư vấn tuyển dụng Vieclamtop (vieclamtop.vn) — nói chuyện qua chat như người thật.

Giọng điệu:
- Xưng "em", gọi khách "anh/chị" (hoặc "bạn" nếu khách dùng giọng thân).
- Ấm, gọn, chuyên nghiệp — 2–6 câu, bullet khi liệt kê tin việc.

Tuyệt đối KHÔNG:
- Nói "tôi là AI/trợ lý ảo/theo dữ liệu/context/hệ thống".
- Bịa lương, yêu cầu tuyển, link tin — chỉ dùng thông tin được cung cấp.
- Mở đầu rập khuôn mỗi lượt chat.

NÊN:
- Gợi ý bước tiếp theo (xem tin, để lại SĐT, nộp hồ sơ).
- Hỏi lại 1 câu ngắn nếu thiếu thông tin quan trọng.
- Nếu không có trong dữ liệu: "Thông tin này em chưa có trong hệ thống Vieclamtop, anh/chị liên hệ hotline hoặc để lại SĐT để em chuyển tư vấn viên nhé."
- Link tin dùng markdown: [tên tin](URL) nếu có URL trong context."""


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


def if_else(title: str, conditions: list[dict[str, Any]], logical: str = "and") -> dict[str, Any]:
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
        "cases": [{"case_id": "true", "logical_operator": logical, "conditions": conds}],
        "_targetBranches": [{"id": "true", "name": "IF"}, {"id": "false", "name": "ELSE"}],
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
        "write_mode": "over-write",
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


def kb_node(title: str, base_kb: dict[str, Any], kb_id: str) -> dict[str, Any]:
    data = copy.deepcopy(base_kb)
    data["title"] = title
    data["dataset_ids"] = [DATASET_ID]
    data["query_variable_selector"] = ["sys", "query"]
    return data


def llm_node(title: str, prompt: str, context_selector: list[str], memory: bool = True) -> dict[str, Any]:
    return {
        "type": "llm",
        "title": title,
        "desc": "",
        "selected": False,
        "model": {
            "provider": "langgenius/openai/openai",
            "name": "gpt-4.1",
            "mode": "chat",
            "completion_params": {
                "temperature": 0.7,
                "top_p": 1,
                "presence_penalty": 0,
                "frequency_penalty": 0,
                "max_tokens": 4096,
            },
        },
        "vision": {"enabled": False},
        "context": {"enabled": True, "variable_selector": context_selector},
        "memory": {
            "role_prefix": {"assistant": "", "user": ""},
            "window": {"enabled": memory, "size": 12},
            "query_prompt_template": "{{#sys.query#}}",
        },
        "prompt_template": [{"id": str(uuid.uuid4()), "role": "system", "text": prompt, "edition_type": "basic"}],
        "prompt_config": {"jinja2_variables": []},
        "structured_output_enabled": False,
        "reasoning_format": "tagged",
        "variables": [],
    }


def pe_node(title: str, instruction: str, parameters: list[dict[str, Any]]) -> dict[str, Any]:
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
            "completion_params": {"temperature": 0.3},
        },
        "vision": {"enabled": False},
        "instruction": instruction,
        "parameters": parameters,
        "memory": {
            "role_prefix": {"assistant": "", "user": ""},
            "window": {"enabled": True, "size": 10},
        },
    }


def qc_node() -> dict[str, Any]:
    return {
        "type": "question-classifier",
        "title": "Question Classifier",
        "desc": "",
        "selected": False,
        "classes": [
            {"id": CLS_HELLO, "name": "Chào hỏi, xin chào, bắt đầu trò chuyện"},
            {"id": CLS_THANKS, "name": "Cảm ơn, tạm biệt, kết thúc"},
            {"id": CLS_JOB_SEARCH, "name": "Tìm việc, gợi ý việc làm phù hợp theo ngành/địa điểm/lương"},
            {"id": CLS_JOB_DETAIL, "name": "Hỏi chi tiết một tin tuyển dụng cụ thể (tên vị trí, công ty, địa điểm)"},
            {"id": CLS_FAQ, "name": "Thủ tục, visa, phỏng vấn, kinh nghiệm làm việc Nhật/Đài/nước ngoài"},
            {"id": CLS_CV, "name": "Hướng dẫn viết CV, hồ sơ xin việc"},
            {"id": CLS_EMPLOYER, "name": "Nhà tuyển dụng: đăng tin, tìm ứng viên, quy trình tuyển dụng"},
            {"id": CLS_LEAD, "name": "Đăng ký tư vấn, nộp hồ sơ, để lại SĐT, gặp tư vấn viên"},
            {"id": CLS_GENERAL, "name": "Giới thiệu Vieclamtop, hỏi chung về website/dịch vụ"},
        ],
        "instructions": (
            "Phân loại câu hỏi khách Vieclamtop (ứng viên hoặc nhà tuyển dụng).\n"
            "- Tìm việc: muốn tìm job, hỏi việc làm theo ngành/địa điểm/lương.\n"
            "- Chi tiết tin: hỏi về 1 tin cụ thể (kỹ sư Fukuoka, điều dưỡng Nhật…).\n"
            "- FAQ: visa, thủ tục, phỏng vấn, xuất cảnh, kinh nghiệm.\n"
            "- CV: cách viết CV/hồ sơ.\n"
            "- NTD: công ty muốn đăng tin, tuyển người.\n"
            "- Lead: muốn đăng ký, để SĐT, nộp hồ sơ, gặp tư vấn.\n"
            "- Chào/Cảm ơn/ Giới thiệu chung: tương ứng."
        ),
        "model": {
            "provider": "langgenius/openai/openai",
            "name": "gpt-4.1-mini",
            "mode": "chat",
            "completion_params": {"temperature": 0.3, "max_tokens": 512},
        },
        "query_variable_selector": [START, "sys.query"],
        "topics": [],
        "memory": {
            "window": {"enabled": True, "size": 10},
            "query_prompt_template": "{{#sys.query#}}",
        },
    }


def transform_graph(graph: dict[str, Any]) -> dict[str, Any]:
    old_nodes = {n["id"]: n for n in graph["nodes"]}
    if START not in old_nodes or KB_GENERAL not in old_nodes:
        raise RuntimeError("Expected Start/KB nodes not found in graph")

    base_kb = old_nodes[KB_GENERAL]["data"]
    old_llm = old_nodes.get(LLM_GENERAL, {}).get("data", {})

    general_prompt = (
        f"{PERSONA}\n\n"
        "Nhiệm vụ: giới thiệu Vieclamtop và trả lời câu hỏi chung dựa trên dữ liệu website.\n"
        "<context>\n{{#context#}}\n</context>\n"
        "Thông tin hồ sơ đã biết (nếu có): "
        "vị trí={{#conversation.desired_role#}}, địa điểm={{#conversation.location#}}, "
        "SĐT={{#conversation.phone#}}."
    )

    job_prompt = (
        f"{PERSONA}\n\n"
        "Nhiệm vụ: gợi ý việc làm phù hợp từ dữ liệu Vieclamtop.\n"
        "<context>\n{{#context#}}\n</context>\n"
        "Hồ sơ ứng viên:\n"
        "- Vị trí: {{#conversation.desired_role#}}\n"
        "- Địa điểm: {{#conversation.location#}}\n"
        "- Kinh nghiệm: {{#conversation.experience_years#}} năm\n"
        "- Tiếng Nhật: {{#conversation.japanese_level#}}\n"
        "- Lương mong muốn: {{#conversation.salary_expectation#}}\n\n"
        "Liệt kê 1–3 tin phù hợp nhất (tên, địa điểm, yêu cầu chính, link nếu có). "
        "Cuối cùng gợi ý để lại SĐT để em chuyển tư vấn viên."
    )

    detail_prompt = (
        f"{PERSONA}\n\n"
        "Nhiệm vụ: trả lời chi tiết về tin tuyển dụng khách đang hỏi.\n"
        "<context>\n{{#context#}}\n</context>\n"
        "Tin quan tâm: {{#conversation.job_title_interest#}}\n"
        "Tóm tắt rõ: vị trí, địa điểm, yêu cầu, quyền lợi (nếu có trong context). "
        "Kết thúc bằng CTA: anh/chị muốn nộp hồ sơ thì gửi tên + SĐT cho em nhé."
    )

    faq_prompt = (
        f"{PERSONA}\n\n"
        "Nhiệm vụ: giải đáp thủ tục, visa, phỏng vấn, kinh nghiệm từ bài viết Vieclamtop.\n"
        "<context>\n{{#context#}}\n</context>"
    )

    cv_prompt = (
        f"{PERSONA}\n\n"
        "Nhiệm vụ: hướng dẫn viết CV/hồ sơ xin việc (ưu tiên xuất khẩu lao động/Nhật nếu khách hỏi).\n"
        "Ngành/vị trí khách quan tâm: {{#conversation.desired_role#}}.\n"
        "Đưa cấu trúc CV gọn, mục nên có, lưu ý theo ngành. Không cần dữ liệu KB."
    )

    emp_prompt = (
        f"{PERSONA}\n\n"
        "Nhiệm vụ: hỗ trợ nhà tuyển dụng.\n"
        "<context>\n{{#context#}}\n</context>\n"
        "Công ty: {{#conversation.company_name#}}, SĐT: {{#conversation.phone#}}.\n"
        "Hướng dẫn đăng tin trên Vieclamtop, quy trình tuyển dụng. "
        "Mời để lại SĐT/email nếu cần bộ phận sales liên hệ."
    )

    llm_general_data = copy.deepcopy(old_llm) if old_llm else llm_node("LLM Tư vấn chung", general_prompt, [KB_GENERAL, "result"])
    llm_general_data["title"] = "LLM Tư vấn chung"
    llm_general_data.setdefault("memory", {})["window"] = {"enabled": True, "size": 12}
    llm_general_data["context"] = {"enabled": True, "variable_selector": [KB_GENERAL, "result"]}
    llm_general_data["prompt_template"] = [
        {"id": str(uuid.uuid4()), "role": "system", "text": general_prompt, "edition_type": "basic"}
    ]

    nodes = [
        canvas(START, old_nodes[START]["data"], 0, 280, 73),
        canvas(QC, qc_node(), 320, 200, 380),
        canvas(A_HELLO, answer_node(
            "Answer Chào",
            "Dạ chào anh/chị! Em bên Vieclamtop đây ạ. "
            "Hôm nay mình đang tìm việc ở đâu (Nhật, Đài, trong nước) hay cần tư vấn thủ tục/CV ạ? "
            "Có tin cụ thể nào đang quan tâm thì nhắn em tra giúp luôn nha!",
        ), 680, 40, 148),
        canvas(A_THANKS, answer_node(
            "Answer Cảm ơn",
            "Dạ em cảm ơn anh/chị ạ! Cần tư vấn thêm việc làm hay thủ tục cứ nhắn em, em hỗ trợ liền nha.",
        ), 680, 180, 120),
        canvas(PE_JOB, pe_node(
            "Extract Tìm việc",
            "Extract thông tin tìm việc từ tin nhắn. Không bịa. Dùng thông tin đã có trong hội thoại nếu tin nhắn hiện tại thiếu.",
            [
                {"name": "desired_role", "type": "string", "required": False, "description": "Vị trí/ngành nghề"},
                {"name": "location", "type": "string", "required": False, "description": "Địa điểm làm việc"},
                {"name": "experience_years", "type": "string", "required": False, "description": "Số năm KN"},
                {"name": "japanese_level", "type": "string", "required": False, "description": "N5–N1 hoặc trống"},
                {"name": "salary_expectation", "type": "string", "required": False, "description": "Mức lương mong muốn"},
            ],
        ), 680, 340, 88),
        canvas(ASSIGN_JOB, assigner("Lưu hồ sơ tìm việc", [
            assign_item("user_type", [PE_JOB, "desired_role"]),  # placeholder overwritten below
            assign_item("desired_role", [PE_JOB, "desired_role"]),
            assign_item("location", [PE_JOB, "location"]),
            assign_item("experience_years", [PE_JOB, "experience_years"]),
            assign_item("japanese_level", [PE_JOB, "japanese_level"]),
            assign_item("salary_expectation", [PE_JOB, "salary_expectation"]),
        ]), 1020, 340, 86),
        canvas(IF_JOB_READY, if_else("Đủ info tìm việc?", [
            {"variable_selector": [PE_JOB, "desired_role"], "comparison_operator": "not empty"},
            {"variable_selector": [PE_JOB, "location"], "comparison_operator": "not empty"},
        ], logical="or"), 1360, 340, 140),
        canvas(A_JOB_ASK, answer_node(
            "Answer Hỏi thêm tìm việc",
            "Dạ để em gợi ý tin phù hợp, anh/chị cho em biết thêm:\n"
            "• Anh/chị muốn làm **vị trí/ngành** gì?\n"
            "• **Địa điểm** mong muốn (Nhật, Đài, tỉnh thành VN…)?\n"
            "(Có thêm kinh nghiệm, tiếng Nhật, mức lương thì em lọc chính xác hơn ạ!)",
        ), 1700, 480, 160),
        canvas(KB_JOB, kb_node("KB Tìm việc", base_kb, KB_JOB), 1700, 300, 134),
        canvas(LLM_JOB, llm_node("LLM Gợi ý việc", job_prompt, [KB_JOB, "result"]), 2040, 300, 148),
        canvas(A_JOB, answer_node("Answer Gợi ý việc", f"{{{{#{LLM_JOB}.text#}}}}"), 2380, 300, 102),
        canvas(PE_DETAIL, pe_node(
            "Extract Tin cụ thể",
            "Extract tên tin/vị trí/công ty/địa điểm khách đang hỏi chi tiết.",
            [{"name": "job_title_interest", "type": "string", "required": False, "description": "Tên tin hoặc vị trí"}],
        ), 680, 560, 88),
        canvas(ASSIGN_DETAIL, assigner("Lưu tin quan tâm", [
            assign_item("job_title_interest", [PE_DETAIL, "job_title_interest"]),
        ]), 1020, 560, 86),
        canvas(KB_DETAIL, kb_node("KB Chi tiết tin", base_kb, KB_DETAIL), 1360, 560, 134),
        canvas(LLM_DETAIL, llm_node("LLM Chi tiết tin", detail_prompt, [KB_DETAIL, "result"]), 1700, 560, 148),
        canvas(A_DETAIL, answer_node("Answer Chi tiết tin", f"{{{{#{LLM_DETAIL}.text#}}}}"), 2040, 560, 102),
        canvas(KB_FAQ, kb_node("KB FAQ", base_kb, KB_FAQ), 680, 720, 134),
        canvas(LLM_FAQ, llm_node("LLM FAQ", faq_prompt, [KB_FAQ, "result"]), 1020, 720, 148),
        canvas(A_FAQ, answer_node("Answer FAQ", f"{{{{#{LLM_FAQ}.text#}}}}"), 1360, 720, 102),
        canvas(LLM_CV, {
            **llm_node("LLM CV", cv_prompt, ["sys", "query"], memory=True),
            "context": {"enabled": False, "variable_selector": []},
        }, 680, 880, 148),
        canvas(A_CV, answer_node("Answer CV", f"{{{{#{LLM_CV}.text#}}}}"), 1020, 880, 102),
        canvas(PE_EMPLOYER, pe_node(
            "Extract NTD",
            "Extract thông tin nhà tuyển dụng: company_name, phone, email nếu có.",
            [
                {"name": "company_name", "type": "string", "required": False, "description": "Tên công ty"},
                {"name": "phone", "type": "string", "required": False, "description": "SĐT liên hệ"},
                {"name": "email", "type": "string", "required": False, "description": "Email"},
            ],
        ), 680, 1040, 88),
        canvas(ASSIGN_EMP, assigner("Lưu NTD", [
            assign_item("user_type", [PE_EMPLOYER, "company_name"]),
            assign_item("company_name", [PE_EMPLOYER, "company_name"]),
            assign_item("phone", [PE_EMPLOYER, "phone"]),
            assign_item("email", [PE_EMPLOYER, "email"]),
        ]), 1020, 1040, 86),
        canvas(KB_EMP, kb_node("KB NTD", base_kb, KB_EMP), 1360, 1040, 134),
        canvas(LLM_EMP, llm_node("LLM NTD", emp_prompt, [KB_EMP, "result"]), 1700, 1040, 148),
        canvas(A_EMP, answer_node("Answer NTD", f"{{{{#{LLM_EMP}.text#}}}}"), 2040, 1040, 102),
        canvas(PE_LEAD, pe_node(
            "Extract Lead",
            "Extract thông tin đăng ký tư vấn/nộp hồ sơ: full_name, phone, email, desired_role.",
            [
                {"name": "full_name", "type": "string", "required": False, "description": "Họ tên"},
                {"name": "phone", "type": "string", "required": False, "description": "SĐT"},
                {"name": "email", "type": "string", "required": False, "description": "Email"},
                {"name": "desired_role", "type": "string", "required": False, "description": "Vị trí quan tâm"},
            ],
        ), 680, 1200, 88),
        canvas(ASSIGN_LEAD, assigner("Lưu lead", [
            assign_item("full_name", [PE_LEAD, "full_name"]),
            assign_item("phone", [PE_LEAD, "phone"]),
            assign_item("email", [PE_LEAD, "email"]),
            assign_item("desired_role", [PE_LEAD, "desired_role"]),
        ]), 1020, 1200, 86),
        canvas(IF_LEAD_READY, if_else("Đủ lead?", [
            {"variable_selector": [PE_LEAD, "phone"], "comparison_operator": "not empty"},
            {"variable_selector": [PE_LEAD, "full_name"], "comparison_operator": "not empty"},
        ]), 1360, 1200, 140),
        canvas(A_LEAD_ASK, answer_node(
            "Answer Hỏi lead",
            "Dạ em ghi nhận anh/chị muốn đăng ký tư vấn ạ! "
            "Anh/chị cho em xin **họ tên** và **SĐT** để em chuyển tư vấn viên Vieclamtop liên hệ trong giờ hành chính nha.",
        ), 1700, 1320, 140),
        canvas(A_LEAD, answer_node(
            "Answer Xác nhận lead",
            "Dạ em đã ghi nhận thông tin:\n"
            "• Họ tên: {{#conversation.full_name#}}\n"
            "• SĐT: {{#conversation.phone#}}\n"
            "• Vị trí quan tâm: {{#conversation.desired_role#}}\n\n"
            "Tư vấn viên Vieclamtop sẽ liên hệ anh/chị sớm nhất. "
            "Anh/chị cần hỗ trợ thêm gì cứ nhắn em nhé!",
        ), 1700, 1180, 160),
        canvas(KB_GENERAL, kb_node("KB Tư vấn chung", base_kb, KB_GENERAL), 680, 1360, 134),
        canvas(LLM_GENERAL, llm_general_data, 1020, 1360, 148),
        canvas(A_GENERAL, answer_node("Answer Tư vấn chung", f"{{{{#{LLM_GENERAL}.text#}}}}"), 1360, 1360, 102),
    ]

    # Fix assign user_type for job branch — set constant via separate assign not supported; use desired_role only
    for n in nodes:
        if n["id"] == ASSIGN_JOB:
            n["data"]["items"] = [
                assign_item("desired_role", [PE_JOB, "desired_role"]),
                assign_item("location", [PE_JOB, "location"]),
                assign_item("experience_years", [PE_JOB, "experience_years"]),
                assign_item("japanese_level", [PE_JOB, "japanese_level"]),
                assign_item("salary_expectation", [PE_JOB, "salary_expectation"]),
            ]
        if n["id"] == ASSIGN_EMP:
            n["data"]["items"] = [
                assign_item("company_name", [PE_EMPLOYER, "company_name"]),
                assign_item("phone", [PE_EMPLOYER, "phone"]),
                assign_item("email", [PE_EMPLOYER, "email"]),
            ]

    edges = [
        edge(START, QC),
        edge(QC, A_HELLO, CLS_HELLO),
        edge(QC, A_THANKS, CLS_THANKS),
        edge(QC, PE_JOB, CLS_JOB_SEARCH),
        edge(QC, PE_DETAIL, CLS_JOB_DETAIL),
        edge(QC, KB_FAQ, CLS_FAQ),
        edge(QC, LLM_CV, CLS_CV),
        edge(QC, PE_EMPLOYER, CLS_EMPLOYER),
        edge(QC, PE_LEAD, CLS_LEAD),
        edge(QC, KB_GENERAL, CLS_GENERAL),
        edge(PE_JOB, ASSIGN_JOB),
        edge(ASSIGN_JOB, IF_JOB_READY),
        edge(IF_JOB_READY, KB_JOB, "true"),
        edge(IF_JOB_READY, A_JOB_ASK, "false"),
        edge(KB_JOB, LLM_JOB),
        edge(LLM_JOB, A_JOB),
        edge(PE_DETAIL, ASSIGN_DETAIL),
        edge(ASSIGN_DETAIL, KB_DETAIL),
        edge(KB_DETAIL, LLM_DETAIL),
        edge(LLM_DETAIL, A_DETAIL),
        edge(KB_FAQ, LLM_FAQ),
        edge(LLM_FAQ, A_FAQ),
        edge(LLM_CV, A_CV),
        edge(PE_EMPLOYER, ASSIGN_EMP),
        edge(ASSIGN_EMP, KB_EMP),
        edge(KB_EMP, LLM_EMP),
        edge(LLM_EMP, A_EMP),
        edge(PE_LEAD, ASSIGN_LEAD),
        edge(ASSIGN_LEAD, IF_LEAD_READY),
        edge(IF_LEAD_READY, A_LEAD, "true"),
        edge(IF_LEAD_READY, A_LEAD_ASK, "false"),
        edge(KB_GENERAL, LLM_GENERAL),
        edge(LLM_GENERAL, A_GENERAL),
    ]

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
