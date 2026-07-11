"""
Application settings loaded from .env file with safe defaults.
All secrets are read from environment variables, never hardcoded.
"""

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _bool(val: Optional[str], default: bool = False) -> bool:
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes")


def _int(val: Optional[str], default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _list(val: Optional[str], default: Optional[List[str]] = None) -> List[str]:
    if val is None:
        return default or []
    return [item.strip() for item in val.split(",") if item.strip()]


# =============================================================================
# API Keys (secrets)
# =============================================================================
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

YOUTUBE_CLIENT_ID: str = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET: str = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_ACCESS_TOKEN: str = os.getenv("YOUTUBE_ACCESS_TOKEN", "")
YOUTUBE_REFRESH_TOKEN: str = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
YOUTUBE_TOKEN_URI: str = os.getenv("YOUTUBE_TOKEN_URI", "https://oauth2.googleapis.com/token")

PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY: str = os.getenv("PIXABAY_API_KEY", "")

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# =============================================================================
# Application Settings
# =============================================================================
AUTO_PUBLISH: bool = _bool(os.getenv("AUTO_PUBLISH"), False)
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "autosystem.db")
OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "output")
TEMP_DIR: str = os.getenv("TEMP_DIR", "temp")
DASHBOARD_PORT: int = _int(os.getenv("DASHBOARD_PORT"), 8000)

# =============================================================================
# TTS Settings
# =============================================================================
TTS_ENGINE: str = os.getenv("TTS_ENGINE", "edge-tts")
TTS_VOICE_POOL: List[str] = _list(
    os.getenv("TTS_VOICE_POOL"),
    ["en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural"],
)

# =============================================================================
# Content Settings
# =============================================================================
DEFAULT_VIDEO_STYLE: str = os.getenv("DEFAULT_VIDEO_STYLE", "faceless")
SCHEDULER_ENABLED: bool = _bool(os.getenv("SCHEDULER_ENABLED"), True)
SCHEDULER_FREQUENCY_HOURS: int = _int(os.getenv("SCHEDULER_FREQUENCY_HOURS"), 24)

# =============================================================================
# Derived Paths
# =============================================================================
DB_FULL_PATH: Path = PROJECT_ROOT / DATABASE_PATH
OUTPUT_FULL_PATH: Path = PROJECT_ROOT / OUTPUT_DIR
TEMP_FULL_PATH: Path = PROJECT_ROOT / TEMP_DIR
PERSONA_ASSETS_DIR: Path = PROJECT_ROOT / "content" / "persona_assets"

# =============================================================================
# YouTube API Quota
# =============================================================================
YOUTUBE_API_QUOTA_LIMIT: int = 10000  # Daily units
YOUTUBE_API_COST_SEARCH: int = 100    # cost per search.list call
YOUTUBE_API_COST_VIDEOS: int = 1      # cost per videos.list call

# =============================================================================
# Quality Review Thresholds
# =============================================================================
MIN_VIDEO_DURATION_SECONDS: int = 15
MAX_VIDEO_DURATION_SECONDS: int = 600  # 10 minutes
MIN_VIDEO_WIDTH: int = 1080
MIN_VIDEO_HEIGHT: int = 720

# =============================================================================
# Retry Settings
# =============================================================================
MAX_RETRIES: int = 3
RETRY_DELAY_SECONDS: int = 5

# =============================================================================
# Validation helper
# =============================================================================
def validate_required_keys() -> List[str]:
    """Return list of missing required API keys."""
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not YOUTUBE_CLIENT_ID:
        missing.append("YOUTUBE_CLIENT_ID")
    if not YOUTUBE_CLIENT_SECRET:
        missing.append("YOUTUBE_CLIENT_SECRET")
    if not PEXELS_API_KEY:
        missing.append("PEXELS_API_KEY")
    if not PIXABAY_API_KEY:
        missing.append("PIXABAY_API_KEY")
    return missing
