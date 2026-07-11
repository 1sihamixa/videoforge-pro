"""
Telegram notification bot.
Sends notifications about pipeline events (video ready, published, errors).
"""

import logging
from typing import Optional

import httpx

import config.settings as settings

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends notifications via Telegram bot."""

    def __init__(self, bot_token: Optional[str] = None,
                 chat_id: Optional[str] = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            logger.info("Telegram notifications disabled (missing token or chat_id)")

    def send(self, message: str) -> bool:
        """
        Send a message via Telegram.
        Returns True if sent successfully, False otherwise.
        """
        if not self.enabled:
            logger.debug(f"Telegram disabled, message: {message[:100]}")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }

            with httpx.Client(timeout=10) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()

            logger.info(f"Telegram notification sent: {message[:80]}...")
            return True

        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

    def send_video_ready(self, title: str, file_path: str,
                         preview_url: Optional[str] = None) -> bool:
        """Send notification that a video is ready for review."""
        msg = (
            f"*Video Ready for Review*\n\n"
            f"*Title:* {title}\n"
            f"*File:* `{file_path}`\n"
        )
        if preview_url:
            msg += f"*Preview:* {preview_url}\n"
        msg += f"\nReview at: http://localhost:{settings.DASHBOARD_PORT}"
        return self.send(msg)

    def send_published(self, title: str, video_url: str) -> bool:
        """Send notification that a video was published."""
        msg = (
            f"*Video Published*\n\n"
            f"*Title:* {title}\n"
            f"*URL:* {video_url}"
        )
        return self.send(msg)

    def send_error(self, error: str) -> bool:
        """Send error notification."""
        msg = f"*Pipeline Error*\n\n`{error[:500]}`"
        return self.send(msg)

    def send_quota_warning(self, remaining: int) -> bool:
        """Send quota warning."""
        msg = f"*YouTube API Quota Warning*\n\nRemaining units: {remaining}"
        return self.send(msg)

    def get_status(self) -> dict:
        return {
            "enabled": self.enabled,
            "chat_id": self.chat_id[:5] + "..." if self.chat_id else None,
        }
