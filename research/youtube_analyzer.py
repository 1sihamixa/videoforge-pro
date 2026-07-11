"""
YouTube Data API v3 analyzer for competition assessment.
Uses the official YouTube Data API v3 via google-api-python-client.
"""

import logging
from typing import List, Dict, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config.settings as settings
from research.api_quota_tracker import QuotaTracker

logger = logging.getLogger(__name__)


class YouTubeAnalyzer:
    """Analyzes YouTube competition for given keywords."""

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.YOUTUBE_CLIENT_ID
        # We use API key for public search (no OAuth needed for search.list)
        # For upload, we need OAuth2 - handled separately in youtube_publisher.py
        self.youtube = build("youtube", "v3", developerKey=key)
        self.quota = QuotaTracker()
        logger.info("YouTubeAnalyzer initialized")

    def search_videos(self, query: str, max_results: int = 10,
                      order: str = "relevance",
                      region_code: str = "US") -> List[Dict]:
        """
        Search YouTube for videos matching a query.
        Returns list of video metadata.
        """
        cost = settings.YOUTUBE_API_COST_SEARCH
        if not self.quota.can_afford(cost):
            logger.warning("YouTube API quota exhausted, skipping search")
            return []

        try:
            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=max_results,
                order=order,
                regionCode=region_code,
                relevanceLanguage="en"
            )
            response = request.execute()
            self.quota.add_usage(cost)

            videos = []
            for item in response.get("items", []):
                videos.append({
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "channel_id": item["snippet"]["channelId"],
                    "channel_title": item["snippet"]["channelTitle"],
                    "description": item["snippet"].get("description", ""),
                    "published_at": item["snippet"]["publishedAt"],
                })
            return videos
        except HttpError as e:
            logger.error(f"YouTube API error for query '{query}': {e}")
            return []

    def get_video_stats(self, video_ids: List[str]) -> List[Dict]:
        """
        Get statistics for specific videos.
        Returns views, likes, comments counts.
        """
        if not video_ids:
            return []

        cost = settings.YOUTUBE_API_COST_VIDEOS * len(video_ids)
        if not self.quota.can_afford(cost):
            logger.warning("YouTube API quota insufficient for video stats")
            return []

        try:
            request = self.youtube.videos().list(
                part="statistics,contentDetails",
                id=",".join(video_ids[:50])  # API limit: 50 IDs per call
            )
            response = request.execute()
            self.quota.add_usage(cost)

            stats = []
            for item in response.get("items", []):
                stat = item.get("statistics", {})
                stats.append({
                    "video_id": item["id"],
                    "view_count": int(stat.get("viewCount", 0)),
                    "like_count": int(stat.get("likeCount", 0)),
                    "comment_count": int(stat.get("commentCount", 0)),
                    "duration": item.get("contentDetails", {}).get("duration", "PT0S"),
                })
            return stats
        except HttpError as e:
            logger.error(f"YouTube API error fetching stats: {e}")
            return []

    def get_channel_stats(self, channel_id: str) -> Dict:
        """
        Get channel statistics (subscriber count, total views).
        """
        cost = settings.YOUTUBE_API_COST_VIDEOS
        if not self.quota.can_afford(cost):
            return {}

        try:
            request = self.youtube.channels().list(
                part="statistics",
                id=channel_id
            )
            response = request.execute()
            self.quota.add_usage(cost)

            if response.get("items"):
                stat = response["items"][0].get("statistics", {})
                return {
                    "subscriber_count": int(stat.get("subscriberCount", 0)),
                    "video_count": int(stat.get("videoCount", 0)),
                    "view_count": int(stat.get("viewCount", 0)),
                }
            return {}
        except HttpError as e:
            logger.error(f"YouTube API error fetching channel {channel_id}: {e}")
            return {}

    def analyze_competition(self, keyword: str,
                            region_code: str = "US") -> Dict:
        """
        Comprehensive competition analysis for a keyword.
        Returns dict with competition metrics.
        """
        logger.info(f"Analyzing competition for: {keyword}")

        # Step 1: Search for videos
        videos = self.search_videos(keyword, max_results=15, region_code=region_code)
        if not videos:
            return {
                "video_count": 0,
                "avg_views": 0,
                "avg_likes": 0,
                "avg_comments": 0,
                "avg_channel_subs": 0,
                "competition_level": "unknown",
                "large_channels_count": 0
            }

        # Step 2: Get video stats
        video_ids = [v["video_id"] for v in videos]
        stats = self.get_video_stats(video_ids)

        # Step 3: Get channel stats for each video
        channel_ids = list(set(v["channel_id"] for v in videos))
        channel_stats = []
        for cid in channel_ids[:10]:  # Limit to avoid quota explosion
            cs = self.get_channel_stats(cid)
            if cs:
                channel_stats.append(cs)

        # Step 4: Calculate metrics
        total_views = sum(s.get("view_count", 0) for s in stats)
        total_likes = sum(s.get("like_count", 0) for s in stats)
        total_comments = sum(s.get("comment_count", 0) for s in stats)
        count = len(stats) or 1

        large_channels = sum(
            1 for cs in channel_stats
            if cs.get("subscriber_count", 0) > 100000
        )

        avg_subs = (
            sum(cs.get("subscriber_count", 0) for cs in channel_stats) / len(channel_stats)
            if channel_stats else 0
        )

        # Determine competition level
        if large_channels >= 5:
            level = "high"
        elif large_channels >= 2:
            level = "medium"
        else:
            level = "low"

        result = {
            "video_count": len(videos),
            "avg_views": total_views // count,
            "avg_likes": total_likes // count,
            "avg_comments": total_comments // count,
            "avg_channel_subs": int(avg_subs),
            "competition_level": level,
            "large_channels_count": large_channels
        }

        logger.info(
            f"Competition for '{keyword}': {level} "
            f"(avg_views={result['avg_views']}, large_channels={large_channels})"
        )
        return result
