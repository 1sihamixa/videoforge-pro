"""
TikTok publisher placeholder.
Interface prepared for future integration with TikTok Content Posting API.
"""

import logging
from typing import Dict

from publish.base_publisher import BasePublisher

logger = logging.getLogger(__name__)


class TikTokPublisher(BasePublisher):
    """TikTok publisher - not yet implemented."""

    def __init__(self):
        logger.warning("TikTokPublisher is not yet implemented")

    def upload(self, video_path: str, title: str, description: str,
               tags: list, **kwargs) -> Dict:
        raise NotImplementedError(
            "TikTok Content Posting API integration not yet implemented. "
            "See: https://developers.tiktok.com/doc/content-posting-api"
        )

    def schedule(self, video_path: str, publish_at: str,
                 title: str, description: str, tags: list, **kwargs) -> Dict:
        raise NotImplementedError("TikTok scheduling not yet implemented")

    def get_status(self, video_id: str) -> Dict:
        raise NotImplementedError("TikTok status not yet implemented")

    def get_analytics(self, video_id: str) -> Dict:
        raise NotImplementedError("TikTok analytics not yet implemented")
