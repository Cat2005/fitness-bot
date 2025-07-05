"""
Configuration module for the fitness coach bot.

This module handles all configuration settings including API keys,
chat IDs, and other environment-specific variables.
"""

from __future__ import annotations

import os
from typing import Final

# Telegram Bot Configuration
TELEGRAM_TOKEN: Final[str] = os.getenv("TELEGRAM_TOKEN", "")
USER_CHAT_ID: Final[int] = int(os.getenv("USER_CHAT_ID", "0"))

# Claude API Configuration
CLAUDE_API_KEY: Final[str] = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL: Final[str] = os.getenv("CLAUDE_MODEL", "claude-3-7-sonnet-20250219")

# Google Docs Configuration
DOC_ID: Final[str] = os.getenv("GOOGLE_DOC_ID", "")
STRETCH_DOC_ID: Final[str] = os.getenv("STRETCH_DOC_ID", "")
GOOGLE_CREDENTIALS_PATH: Final[str] = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")

# Timezone Configuration
TZ: Final[str] = os.getenv("TIMEZONE", "Europe/London")

# Retry Configuration
MAX_RETRIES: Final[int] = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY: Final[float] = float(os.getenv("RETRY_DELAY", "1.0"))
RETRY_BACKOFF: Final[float] = float(os.getenv("RETRY_BACKOFF", "2.0"))

# Logging Configuration
LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")


def validate_config() -> None:
    """
    Validate that all required configuration values are set.
    
    Raises:
        ValueError: If any required configuration is missing.
    """
    required_configs = {
        "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
        "USER_CHAT_ID": USER_CHAT_ID,
        "CLAUDE_API_KEY": CLAUDE_API_KEY,
        "GOOGLE_DOC_ID": DOC_ID,
        "STRETCH_DOC_ID": STRETCH_DOC_ID,
    }
    
    missing_configs = [
        name for name, value in required_configs.items()
        if not value or (name == "USER_CHAT_ID" and value == 0)
    ]
    
    if missing_configs:
        raise ValueError(
            f"Missing required configuration: {', '.join(missing_configs)}. "
            "Please set the corresponding environment variables."
        )


def get_config_summary() -> dict[str, str]:
    """
    Get a summary of current configuration (without exposing sensitive data).
    
    Returns:
        dict: Configuration summary with masked sensitive values.
    """
    return {
        "telegram_token_set": bool(TELEGRAM_TOKEN),
        "user_chat_id": str(USER_CHAT_ID) if USER_CHAT_ID else "Not set",
        "claude_api_key_set": bool(CLAUDE_API_KEY),
        "claude_model": CLAUDE_MODEL,
        "google_doc_id_set": bool(DOC_ID),
        "stretch_doc_id_set": bool(STRETCH_DOC_ID),
        "timezone": TZ,
        "max_retries": str(MAX_RETRIES),
        "retry_delay": str(RETRY_DELAY),
        "log_level": LOG_LEVEL,
    } 