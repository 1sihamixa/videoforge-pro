"""
Instagram publisher placeholder.
Interface prepared for future integration with Instagram Graph API.
"""

import logging
from typing import Dict

from publish.base_publisher import BasePublisher

logger = logging.getLogger(__name__)


class InstagramPublisher(BasePublisher):
    """Instagram publisher - not yet implemented."""

    def __init__(self):
        logger.warning("InstagramPublisher is not yet implemented")

    def upload(self, video_path: str, title: str, description: str,
               tags: list, **kwargs) -> Dict:
        raise NotImplementedError(
            "Instagram Graph API integration not yet implemented. "
            "See: https://developers.facebook.com/docs/instagram-api"
        )

    def schedule(self, video_path: str, publish_at: str,
                 title: str, description: str, tags: list, **kwargs) -> Dict:
        raise NotImplementedError("Instagram scheduling not yet implemented")

    def get_status(self, video_id: str) -> Dict:
        raise NotImplementedError("Instagram status not yet implemented")

    def get_analytics(self, video_id: str) -> Dict:
        raise NotImplementedError("Instagram analytics not yet implemented")
