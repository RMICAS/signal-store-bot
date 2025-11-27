import logging
import re
from typing import Optional

def setup_logging(level: str = "INFO"):
    """Set up logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    # Basic E.164 format validation
    pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone))

def format_currency(amount: float) -> str:
    """Format currency amount"""
    return f"${amount:.2f}"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def safe_int(value: str, default: int = 0) -> int:
    """Safely convert to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value: str, default: float = 0.0) -> float:
    """Safely convert to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default