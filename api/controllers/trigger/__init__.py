from flask import Blueprint

# Create trigger blueprint
bp = Blueprint("trigger", __name__, url_prefix="/triggers")

# Import routes after blueprint creation to avoid circular imports
from . import messenger, tiktok, trigger, webhook, zalo, zalo_personal

__all__ = [
    "messenger",
    "tiktok",
    "trigger",
    "webhook",
    "zalo",
    "zalo_personal",
]
