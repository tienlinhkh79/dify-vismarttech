"""Shared graph builders for US Restaurant / Nail omnichannel chatbots."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from add_omnichannel_rich_reply_nodes import code_node_data

SCRIPTS_DIR = Path(__file__).resolve().parent
KB_DIR = SCRIPTS_DIR / "kb"

STRUCTURED_SCHEMA: dict[str, Any] = {
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "display_type": {
                "type": "string",
                "description": "service_cards | product_grid | actions",
            },
            "ai_reply": {"type": "string"},
            "products": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "product_name": {"type": "string"},
                        "price": {"type": "string"},
                        "image_url": {"type": "string"},
                        "detail_url": {"type": "string"},
                    },
                },
            },
            "quick_replies": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["ai_reply"],
    }
}

STRUCTURED_SUFFIX_RESTAURANT = (
    "\n\nMessenger structured output (use structured fields — do NOT put JSON in plain text):\n"
    "- FAQ / menu / hours: display_type=service_cards, ai_reply=1-3 short friendly English sentences, "
    "quick_replies=2-4 SHORT options (max 20 chars): View Menu, Hours, Reserve, Call Us.\n"
    "- Specific dishes with prices from context: display_type=product_grid, products with "
    "product_name and price; quick_replies=2-3 follow-ups.\n"
    "- Always include quick_replies when possible for Messenger buttons."
)

STRUCTURED_SUFFIX_NAIL = (
    "\n\nMessenger structured output (use structured fields — do NOT put JSON in plain text):\n"
    "- Services / pricing / policies: display_type=service_cards, ai_reply=1-3 short English sentences, "
    "quick_replies=2-4 SHORT options (max 20 chars): Book Now, Services, Prices, Hours.\n"
    "- Specific services with prices: display_type=product_grid, products with product_name and price.\n"
    "- Always include quick_replies when possible for Messenger buttons."
)


@dataclass(frozen=True)
class VerticalSpec:
    key: str
    app_name: str
    app_icon: str
    dataset_name: str
    kb_filename: str
    id_prefix: str
    opening_statement: str
    suggested_questions: tuple[str, ...]
    persona: str
    classifier_instructions: str
    cls_faq: str
    cls_greet: str
    cls_thanks: str
    cls_lead: str
    lead_instruction: str
    lead_parameters: tuple[dict[str, Any], ...]
    crm_tags: str
    notes_template: str
    lead_confirm_system: str
    answer_greet: str
    answer_thanks: str
    answer_need_info: str
    structured_suffix: str

    @property
    def kb_path(self) -> Path:
        return KB_DIR / self.kb_filename

    def nid(self, suffix: int) -> str:
        return f"{self.id_prefix}{suffix:04d}"


RESTAURANT_SPEC = VerticalSpec(
    key="restaurant",
    app_name="US Restaurant Omnichannel Bot",
    app_icon="🍜",
    dataset_name="US Restaurant KB",
    kb_filename="quyen_us_restaurant_kb.md",
    id_prefix="179001",
    opening_statement=(
        "Hi! I'm the assistant for Golden Dragon Restaurant. "
        "I can help with our menu, hours, promotions, and table reservations. What can I help you with today?"
    ),
    suggested_questions=(
        "What's on the menu?",
        "What are your hours?",
        "I'd like to make a reservation",
        "Do you have vegetarian options?",
    ),
    persona=(
        "You are a friendly host at Golden Dragon Restaurant (Houston, TX). "
        "Speak natural American English — warm, concise, 2-5 sentences. "
        "Never say you are an AI. Only use facts from the knowledge context; "
        "if unsure, invite the guest to call (713) 555-0188 or leave name + phone for a callback."
    ),
    classifier_instructions=(
        "Classify the customer message (including button postback payloads).\n"
        "- FAQ: menu, prices, hours, location, promotions, dietary, delivery, general questions.\n"
        "- Greet: hi, hello, start, first message.\n"
        "- Thanks: thank you, bye, done.\n"
        "- Lead: reservation, book a table, party, catering, leave phone/email, talk to staff, "
        "contact, callback. Includes buttons: Reserve, Book, Contact."
    ),
    cls_faq="Menu, prices, hours, location, promotions, dietary options, delivery, general FAQ",
    cls_greet="Greetings: hi, hello, hey, getting started",
    cls_thanks="Thanks, goodbye, conversation ending",
    cls_lead="Reservation, book table, party, catering, leave contact info, speak to staff",
    lead_instruction=(
        "Guest wants a reservation or to leave contact info. Extract from message and recent context:\n"
        "- customer_name\n"
        "- customer_phone (US phone, 10 digits)\n"
        "- customer_email (if any)\n"
        "- party_size (number of guests)\n"
        "- reservation_datetime (date/time text as guest said it)\n"
        "- service_interest (e.g. dine-in reservation, catering, private room)\n"
        "Do not invent information not in the conversation."
    ),
    lead_parameters=(
        {"name": "customer_name", "type": "string", "required": False, "description": "Guest name"},
        {"name": "customer_phone", "type": "string", "required": False, "description": "Phone number"},
        {"name": "customer_email", "type": "string", "required": False, "description": "Email"},
        {"name": "party_size", "type": "string", "required": False, "description": "Party size"},
        {
            "name": "reservation_datetime",
            "type": "string",
            "required": False,
            "description": "Requested date/time",
        },
        {"name": "service_interest", "type": "string", "required": False, "description": "Reservation type"},
    ),
    crm_tags="Reservation,Restaurant",
    notes_template=(
        "Chatbot lead — {{#sys.query#}} | "
        "Party: {{#{{EXTRACT}}.party_size#}} | "
        "When: {{#{{EXTRACT}}.reservation_datetime#}} | "
        "Type: {{#{{EXTRACT}}.service_interest#}} | "
        "Name: {{#{{EXTRACT}}.customer_name#}}"
    ),
    lead_confirm_system=(
        "You are the host at Golden Dragon Restaurant. The guest just shared contact details.\n"
        "Name: {{#{{EXTRACT}}.customer_name#}}\n"
        "Phone: {{#{{EXTRACT}}.customer_phone#}}\n"
        "Email: {{#{{EXTRACT}}.customer_email#}}\n"
        "Party: {{#{{EXTRACT}}.party_size#}}\n"
        "When: {{#{{EXTRACT}}.reservation_datetime#}}\n"
        "CRM saved the lead. Reply in 2-3 warm English sentences: thank them, confirm we received the request, "
        "and say the team will call/text to confirm the reservation soon."
    ),
    answer_greet=(
        "Hi there! Welcome to **Golden Dragon Restaurant**. "
        "I can help with our menu, hours, promotions, or a table reservation. What would you like to know?"
    ),
    answer_thanks=(
        "You're welcome! Hope to see you at Golden Dragon soon. "
        "Message anytime if you need menu info or want to book a table."
    ),
    answer_need_info=(
        "I'd love to help with your reservation! Please share your **name** and **phone number**, "
        "plus your preferred **date, time**, and **party size** — our team will confirm shortly."
    ),
    structured_suffix=STRUCTURED_SUFFIX_RESTAURANT,
)

NAIL_SPEC = VerticalSpec(
    key="nail",
    app_name="US Nail Salon Omnichannel Bot",
    app_icon="💅",
    dataset_name="US Nail Salon KB",
    kb_filename="quyen_us_nail_kb.md",
    id_prefix="179002",
    opening_statement=(
        "Hi! I'm the assistant for Luxe Nails Studio. "
        "I can help with services, pricing, policies, and booking an appointment. How can I help?"
    ),
    suggested_questions=(
        "What services do you offer?",
        "How much is a gel manicure?",
        "I'd like to book an appointment",
        "What are your hours?",
    ),
    persona=(
        "You are a friendly front-desk coordinator at Luxe Nails Studio (Dallas, TX). "
        "Speak natural American English — warm, concise, 2-5 sentences. "
        "Never say you are an AI. Only use facts from the knowledge context; "
        "if unsure, invite them to call (214) 555-0142 or leave name + phone to book."
    ),
    classifier_instructions=(
        "Classify the customer message (including button postback payloads).\n"
        "- FAQ: services, prices, hours, policies, promotions, waxing, general questions.\n"
        "- Greet: hi, hello, start.\n"
        "- Thanks: thank you, bye.\n"
        "- Lead: book appointment, schedule, leave phone, callback, specific date/time for service. "
        "Buttons: Book Now, Book, Contact."
    ),
    cls_faq="Services, pricing, hours, location, policies, promotions, waxing, general FAQ",
    cls_greet="Greetings: hi, hello, hey",
    cls_thanks="Thanks, goodbye, end of chat",
    cls_lead="Book appointment, schedule service, leave contact, request callback",
    lead_instruction=(
        "Guest wants to book an appointment or leave contact info. Extract:\n"
        "- customer_name\n"
        "- customer_phone (US phone)\n"
        "- customer_email (if any)\n"
        "- service_name (manicure, pedicure, gel, etc.)\n"
        "- appointment_datetime (date/time as guest said)\n"
        "- notes (special requests)\n"
        "Do not invent information."
    ),
    lead_parameters=(
        {"name": "customer_name", "type": "string", "required": False, "description": "Client name"},
        {"name": "customer_phone", "type": "string", "required": False, "description": "Phone"},
        {"name": "customer_email", "type": "string", "required": False, "description": "Email"},
        {"name": "service_name", "type": "string", "required": False, "description": "Requested service"},
        {
            "name": "appointment_datetime",
            "type": "string",
            "required": False,
            "description": "Preferred date/time",
        },
        {"name": "notes", "type": "string", "required": False, "description": "Special requests"},
    ),
    crm_tags="Booking,Nail",
    notes_template=(
        "[BOOKING] {{#{{EXTRACT}}.appointment_datetime#}} | "
        "{{#{{EXTRACT}}.service_name#}} | "
        "Phone: {{#{{EXTRACT}}.customer_phone#}} | "
        "{{#sys.query#}} | "
        "Notes: {{#{{EXTRACT}}.notes#}} | "
        "Name: {{#{{EXTRACT}}.customer_name#}}"
    ),
    lead_confirm_system=(
        "You are the coordinator at Luxe Nails Studio. The client shared booking details.\n"
        "Name: {{#{{EXTRACT}}.customer_name#}}\n"
        "Phone: {{#{{EXTRACT}}.customer_phone#}}\n"
        "Service: {{#{{EXTRACT}}.service_name#}}\n"
        "When: {{#{{EXTRACT}}.appointment_datetime#}}\n"
        "Notes: {{#{{EXTRACT}}.notes#}}\n"
        "CRM saved the booking request. Reply in 2-3 friendly English sentences: thank them, "
        "confirm we received the request, and say we'll text/call to confirm the appointment."
    ),
    answer_greet=(
        "Hi! Welcome to **Luxe Nails Studio**. "
        "Ask me about services, prices, or book your next appointment — happy to help!"
    ),
    answer_thanks=(
        "Thanks for chatting! We look forward to seeing you at Luxe Nails. "
        "Message anytime to check services or book again."
    ),
    answer_need_info=(
        "Happy to get you booked! Please send your **name**, **phone number**, "
        "preferred **service**, and **date/time** — we'll confirm your appointment shortly."
    ),
    structured_suffix=STRUCTURED_SUFFIX_NAIL,
)

VERTICALS: tuple[VerticalSpec, ...] = (RESTAURANT_SPEC, NAIL_SPEC)


def canvas_node(
    node_id: str,
    data: dict[str, Any],
    x: float,
    y: float,
    *,
    width: int = 242,
    height: int = 54,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": "custom",
        "position": {"x": x, "y": y},
        "positionAbsolute": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
        "width": width,
        "height": height,
        "selected": False,
        "data": data,
    }


def edge(
    source: str,
    target: str,
    *,
    source_type: str,
    target_type: str,
    source_handle: str = "source",
) -> dict[str, Any]:
    return {
        "id": f"{source}-{source_handle}-{target}-target",
        "type": "custom",
        "source": source,
        "sourceHandle": source_handle,
        "target": target,
        "targetHandle": "target",
        "data": {
            "sourceType": source_type,
            "targetType": target_type,
            "isInIteration": False,
            "isInLoop": False,
        },
        "zIndex": 0,
    }


def workflow_features(spec: VerticalSpec) -> dict[str, Any]:
    return {
        "opening_statement": spec.opening_statement,
        "suggested_questions": list(spec.suggested_questions),
        "suggested_questions_after_answer": {"enabled": True},
        "text_to_speech": {"enabled": False, "language": "", "voice": ""},
        "speech_to_text": {"enabled": False},
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


def _subst(node_id: str, template: str) -> str:
    return template.replace("{{EXTRACT}}", node_id)


def build_graph(spec: VerticalSpec, dataset_id: str, model: dict[str, Any]) -> dict[str, Any]:
    start = spec.nid(1)
    classifier = spec.nid(101)
    cls_faq = spec.nid(102)
    cls_greet = spec.nid(103)
    cls_thanks = spec.nid(104)
    cls_lead = spec.nid(105)
    kb = spec.nid(201)
    llm_faq = spec.nid(202)
    code = spec.nid(203)
    answer_main = spec.nid(204)
    answer_greet = spec.nid(301)
    answer_thanks = spec.nid(302)
    lead_extract = spec.nid(401)
    lead_if = spec.nid(402)
    crm_tool = spec.nid(403)
    llm_lead = spec.nid(404)
    answer_need_info = spec.nid(405)
    answer_lead = spec.nid(406)

    faq_prompt = (
        f"{spec.persona}\n\n"
        "Answer using the knowledge base context below.\n"
        "<context>\n{{#context#}}\n</context>\n"
        f"{spec.structured_suffix}"
    )

    nodes = [
        canvas_node(
            start,
            {
                "type": "start",
                "title": "Start",
                "desc": "",
                "selected": False,
                "variables": [],
            },
            0,
            280,
            height=54,
        ),
        canvas_node(
            classifier,
            {
                "type": "question-classifier",
                "title": "Question Classifier",
                "desc": "",
                "selected": False,
                "classes": [
                    {"id": cls_faq, "name": spec.cls_faq},
                    {"id": cls_greet, "name": spec.cls_greet},
                    {"id": cls_thanks, "name": spec.cls_thanks},
                    {"id": cls_lead, "name": spec.cls_lead},
                ],
                "query_variable_selector": [start, "sys.query"],
                "instructions": spec.classifier_instructions,
                "topics": [],
                "model": model,
                "memory": {
                    "role_prefix": {"assistant": "", "user": ""},
                    "window": {"enabled": True, "size": 10},
                    "query_prompt_template": "{{#sys.query#}}",
                },
                "vision": {"enabled": False},
            },
            342,
            280,
            height=320,
        ),
        canvas_node(
            kb,
            {
                "type": "knowledge-retrieval",
                "title": "Knowledge Retrieval",
                "desc": "",
                "selected": False,
                "query_variable_selector": [start, "sys.query"],
                "query_attachment_selector": [],
                "dataset_ids": [dataset_id],
                "retrieval_mode": "multiple",
                "multiple_retrieval_config": {
                    "top_k": 4,
                    "score_threshold": None,
                    "reranking_enable": False,
                    "reranking_mode": "weighted_score",
                    "reranking_model": {
                        "provider": "",
                        "model": "",
                    },
                    "weights": {
                        "weight_type": "customized",
                        "vector_setting": {
                            "vector_weight": 0.0,
                            "embedding_provider_name": "",
                            "embedding_model_name": "",
                        },
                        "keyword_setting": {"keyword_weight": 1.0},
                    },
                },
                "metadata_filtering_mode": "disabled",
            },
            680,
            280,
            height=88,
        ),
        canvas_node(
            llm_faq,
            {
                "type": "llm",
                "title": "LLM FAQ",
                "desc": "",
                "selected": False,
                "model": model,
                "prompt_template": [
                    {
                        "id": str(uuid.uuid4()),
                        "role": "system",
                        "text": faq_prompt,
                        "edition_type": "basic",
                    }
                ],
                "context": {"enabled": True, "variable_selector": [kb, "result"]},
                "memory": {
                    "query_prompt_template": "{{#sys.query#}}",
                    "role_prefix": {"assistant": "", "user": ""},
                    "window": {"enabled": True, "size": 10},
                },
                "vision": {"enabled": False},
                "structured_output_enabled": True,
                "structured_output": STRUCTURED_SCHEMA,
                "prompt_config": {"jinja2_variables": []},
            },
            980,
            280,
            height=146,
        ),
        canvas_node(
            code,
            code_node_data(
                llm_node_id=llm_faq,
                title="Format Rich Reply",
                use_structured_fields=True,
            ),
            1280,
            280,
            height=88,
        ),
        canvas_node(
            answer_main,
            {
                "type": "answer",
                "title": "Answer FAQ",
                "desc": "",
                "selected": False,
                "answer": f"{{{{#{code}.reply#}}}}",
                "variables": [],
            },
            1580,
            280,
            height=105,
        ),
        canvas_node(
            answer_greet,
            {
                "type": "answer",
                "title": "Answer Greet",
                "desc": "",
                "selected": False,
                "answer": spec.answer_greet,
                "variables": [],
            },
            980,
            40,
            height=120,
        ),
        canvas_node(
            answer_thanks,
            {
                "type": "answer",
                "title": "Answer Thanks",
                "desc": "",
                "selected": False,
                "answer": spec.answer_thanks,
                "variables": [],
            },
            980,
            160,
            height=120,
        ),
        canvas_node(
            lead_extract,
            {
                "type": "parameter-extractor",
                "title": "Extract Lead",
                "desc": "",
                "selected": False,
                "query": ["sys", "query"],
                "reasoning_mode": "prompt",
                "model": model,
                "vision": {"enabled": False},
                "instruction": spec.lead_instruction,
                "parameters": list(spec.lead_parameters),
                "memory": {
                    "role_prefix": {"assistant": "", "user": ""},
                    "window": {"enabled": True, "size": 8},
                },
            },
            680,
            520,
            height=88,
        ),
        canvas_node(
            lead_if,
            {
                "type": "if-else",
                "title": "Has phone?",
                "desc": "",
                "selected": False,
                "cases": [
                    {
                        "id": "true",
                        "case_id": "true",
                        "logical_operator": "and",
                        "conditions": [
                            {
                                "id": str(uuid.uuid4()),
                                "varType": "string",
                                "variable_selector": [lead_extract, "customer_phone"],
                                "comparison_operator": "not empty",
                                "value": "",
                            }
                        ],
                    }
                ],
                "_targetBranches": [{"id": "true", "name": "IF"}, {"id": "false", "name": "ELSE"}],
                "isInIteration": False,
                "isInLoop": False,
            },
            980,
            520,
            height=124,
        ),
        canvas_node(
            crm_tool,
            {
                "type": "tool",
                "title": "Save CRM Lead",
                "desc": "",
                "selected": False,
                "provider_id": "mini_crm",
                "provider_type": "builtin",
                "provider_name": "mini_crm",
                "tool_name": "update_crm_lead",
                "tool_label": "Save CRM Lead",
                "tool_node_version": "2",
                "tool_configurations": {},
                "tool_parameters": {
                    "stage": {"type": "constant", "value": "qualified"},
                    "contact_phone": {
                        "type": "mixed",
                        "value": f"{{{{#{lead_extract}.customer_phone#}}}}",
                    },
                    "contact_email": {
                        "type": "mixed",
                        "value": f"{{{{#{lead_extract}.customer_email#}}}}",
                    },
                    "tags": {"type": "constant", "value": spec.crm_tags},
                    "notes_append": {
                        "type": "mixed",
                        "value": _subst(lead_extract, spec.notes_template),
                    },
                },
                "params": {},
                "paramSchemas": [],
                "is_team_authorization": True,
                "plugin_id": None,
                "plugin_unique_identifier": "",
                "provider_icon": "/console/api/workspaces/current/tool-provider/builtin/mini_crm/icon",
            },
            1280,
            480,
            height=88,
        ),
        canvas_node(
            llm_lead,
            {
                "type": "llm",
                "title": "LLM Confirm Lead",
                "desc": "",
                "selected": False,
                "model": model,
                "prompt_template": [
                    {
                        "id": str(uuid.uuid4()),
                        "role": "system",
                        "text": _subst(lead_extract, spec.lead_confirm_system),
                        "edition_type": "basic",
                    }
                ],
                "context": {"enabled": False, "variable_selector": []},
                "memory": {
                    "query_prompt_template": "{{#sys.query#}}",
                    "role_prefix": {"assistant": "", "user": ""},
                    "window": {"enabled": False, "size": 10},
                },
                "vision": {"enabled": False},
                "structured_output_enabled": False,
                "prompt_config": {"jinja2_variables": []},
            },
            1580,
            480,
            height=146,
        ),
        canvas_node(
            answer_need_info,
            {
                "type": "answer",
                "title": "Answer Need Info",
                "desc": "",
                "selected": False,
                "answer": spec.answer_need_info,
                "variables": [],
            },
            1280,
            640,
            height=120,
        ),
        canvas_node(
            answer_lead,
            {
                "type": "answer",
                "title": "Answer Lead",
                "desc": "",
                "selected": False,
                "answer": f"{{{{#{llm_lead}.text#}}}}",
                "variables": [],
            },
            1880,
            480,
            height=105,
        ),
    ]

    edges = [
        edge(start, classifier, source_type="start", target_type="question-classifier"),
        edge(
            classifier,
            kb,
            source_type="question-classifier",
            target_type="knowledge-retrieval",
            source_handle=cls_faq,
        ),
        edge(
            classifier,
            answer_greet,
            source_type="question-classifier",
            target_type="answer",
            source_handle=cls_greet,
        ),
        edge(
            classifier,
            answer_thanks,
            source_type="question-classifier",
            target_type="answer",
            source_handle=cls_thanks,
        ),
        edge(
            classifier,
            lead_extract,
            source_type="question-classifier",
            target_type="parameter-extractor",
            source_handle=cls_lead,
        ),
        edge(kb, llm_faq, source_type="knowledge-retrieval", target_type="llm"),
        edge(llm_faq, code, source_type="llm", target_type="code"),
        edge(code, answer_main, source_type="code", target_type="answer"),
        edge(lead_extract, lead_if, source_type="parameter-extractor", target_type="if-else"),
        edge(
            lead_if,
            crm_tool,
            source_type="if-else",
            target_type="tool",
            source_handle="true",
        ),
        edge(
            lead_if,
            answer_need_info,
            source_type="if-else",
            target_type="answer",
            source_handle="false",
        ),
        edge(crm_tool, llm_lead, source_type="tool", target_type="llm"),
        edge(llm_lead, answer_lead, source_type="llm", target_type="answer"),
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "viewport": {"x": -40, "y": 120, "zoom": 0.55},
    }


def binding_instructions(spec: VerticalSpec, app_id: str, dataset_id: str) -> str:
    return (
        f"\n=== {spec.app_name} ===\n"
        f"  App ID: {app_id}\n"
        f"  Dataset ID: {dataset_id}\n"
        f"  Mini CRM vertical: {spec.key}\n"
        f"  Channel binding: Studio → Settings → Channels → set App = this app, "
        f"Mini CRM business line = {spec.key}\n"
    )
