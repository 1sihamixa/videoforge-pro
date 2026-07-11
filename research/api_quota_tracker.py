"""
YouTube API quota tracker.
Prevents exceeding the daily quota limit (default: 10,000 units).
"""

import logging
from datetime import datetime

import config.settings as settings
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class QuotaTracker:
    """Tracks and enforces YouTube API daily quota limits."""

    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()
        self.platform = "youtube"
        self.limit = settings.YOUTUBE_API_QUOTA_LIMIT

    @property
    def today(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d")

    def get_usage(self) -> int:
        """Get total units used today."""
        return self.db.get_quota_usage(self.platform, self.today)

    def can_afford(self, units: int) -> bool:
        """Check if we can afford the given number of units."""
        current = self.get_usage()
        remaining = self.limit - current
        if remaining < units:
            logger.warning(
                f"YouTube API quota low: {remaining} units remaining "
                f"(requested {units})"
            )
            return False
        return True

    def add_usage(self, units: int) -> int:
        """Record usage and return new total."""
        new_total = self.db.add_quota_usage(self.platform, self.today, units)
        remaining = self.limit - new_total
        if remaining < 500:
            logger.warning(
                f"YouTube API quota critical: only {remaining} units remaining"
            )
        return new_total

    def get_status(self) -> dict:
        """Get current quota status."""
        used = self.get_usage()
        return {
            "platform": self.platform,
            "date": self.today,
            "used": used,
            "limit": self.limit,
            "remaining": self.limit - used,
            "percent_used": round((used / self.limit) * 100, 1) if self.limit > 0 else 0,
        }
