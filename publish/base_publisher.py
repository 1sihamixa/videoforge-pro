"""
Abstract base publisher interface.
All platform publishers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional


class BasePublisher(ABC):
    """Abstract base class for content publishers."""

    @abstractmethod
    def upload(self, video_path: str, title: str, description: str,
               tags: list, **kwargs) -> Dict:
        """
        Upload video to the platform.

        Returns:
            Dict with: success (bool), video_id (str), video_url (str), error (str)
        """
        pass

    @abstractmethod
    def schedule(self, video_path: str, publish_at: str,
                 title: str, description: str, tags: list, **kwargs) -> Dict:
        """
        Schedule video for future publication.

        Args:
            publish_at: ISO 8601 datetime string for scheduled publish time

        Returns:
            Dict with: success (bool), scheduled_id (str), error (str)
        """
        pass

    @abstractmethod
    def get_status(self, video_id: str) -> Dict:
        """Get the status of a published/scheduled video."""
        pass

    @abstractmethod
    def get_analytics(self, video_id: str) -> Dict:
        """Get analytics data for a video."""
        pass
