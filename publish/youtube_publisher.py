"""
YouTube publisher using YouTube Data API v3.
Handles OAuth2 authentication, video upload, scheduling,
and automatic containsSyntheticMedia flag for AI-generated content.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import config.settings as settings
from publish.base_publisher import BasePublisher

logger = logging.getLogger(__name__)

# YouTube API scopes
SCOPES = settings.YOUTUBE_API_SCOPES if hasattr(settings, 'YOUTUBE_API_SCOPES') else [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


class YouTubePublisher(BasePublisher):
    """Publishes videos to YouTube via Data API v3."""

    def __init__(self):
        self.credentials = self._load_credentials()
        self.youtube = build("youtube", "v3", credentials=self.credentials)
        logger.info("YouTubePublisher initialized")

    def _load_credentials(self) -> Credentials:
        """Load OAuth2 credentials from settings, refreshing if needed."""
        creds = Credentials(
            token=settings.YOUTUBE_ACCESS_TOKEN,
            refresh_token=settings.YOUTUBE_REFRESH_TOKEN,
            token_uri=settings.YOUTUBE_TOKEN_URI,
            client_id=settings.YOUTUBE_CLIENT_ID,
            client_secret=settings.YOUTUBE_CLIENT_SECRET,
            scopes=SCOPES,
        )
        # Refresh if expired
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("YouTube OAuth tokens refreshed")
            except Exception as e:
                logger.error(f"Failed to refresh YouTube tokens: {e}")
        return creds

    def upload(self, video_path: str, title: str, description: str,
               tags: list, category_id: str = "28",
               privacy_status: str = "public",
               is_ai_generated: bool = True,
               **kwargs) -> Dict:
        """
        Upload a video to YouTube.

        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags
            category_id: YouTube category ID (28 = Science & Technology)
            privacy_status: "public", "private", or "unlisted"
            is_ai_generated: Set containsSyntheticMedia flag

        Returns:
            Dict with: success, video_id, video_url, error
        """
        path = Path(video_path)
        if not path.exists():
            return {"success": False, "error": f"Video file not found: {video_path}"}

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:15],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
                # YouTube's AI content disclosure
                "containsSyntheticMedia": is_ai_generated,
            },
        }

        media = MediaFileUpload(
            str(path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,  # 10MB chunks
        )

        try:
            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"Upload progress: {progress}%")

            video_id = response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            logger.info(f"Video uploaded successfully: {video_url}")
            return {
                "success": True,
                "video_id": video_id,
                "video_url": video_url,
            }

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {"success": False, "error": str(e)}

    def schedule(self, video_path: str, publish_at: str,
                 title: str, description: str, tags: list,
                 category_id: str = "28",
                 is_ai_generated: bool = True,
                 **kwargs) -> Dict:
        """
        Upload and schedule a video for future publication.

        Args:
            publish_at: ISO 8601 datetime string (e.g., "2026-07-10T18:00:00Z")
        """
        path = Path(video_path)
        if not path.exists():
            return {"success": False, "error": f"Video file not found: {video_path}"}

        # Parse and validate publish time
        try:
            pub_time = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
            if pub_time < datetime.now(pub_time.tzinfo):
                # If time is in the past, schedule for tomorrow at the same time
                pub_time = pub_time + timedelta(days=1)
                publish_at = pub_time.isoformat()
        except ValueError:
            return {"success": False, "error": f"Invalid publish_at format: {publish_at}"}

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:15],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": "private",  # Upload as private first
                "selfDeclaredMadeForKids": False,
                "containsSyntheticMedia": is_ai_generated,
                "publishAt": publish_at,
                "privacyStatusUnlisted": False,
            },
        }

        media = MediaFileUpload(
            str(path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,
        )

        try:
            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()

            video_id = response["id"]
            logger.info(f"Video scheduled: {video_id} at {publish_at}")

            return {
                "success": True,
                "video_id": video_id,
                "scheduled_at": publish_at,
            }

        except Exception as e:
            logger.error(f"Scheduling failed: {e}")
            return {"success": False, "error": str(e)}

    def get_status(self, video_id: str) -> Dict:
        """Get video status."""
        try:
            response = self.youtube.videos().list(
                part="status,statistics",
                id=video_id
            ).execute()

            if response.get("items"):
                item = response["items"][0]
                return {
                    "video_id": video_id,
                    "privacy_status": item.get("status", {}).get("privacyStatus"),
                    "upload_status": item.get("status", {}).get("uploadStatus"),
                    "publish_at": item.get("status", {}).get("publishAt"),
                    "stats": item.get("statistics", {}),
                }
            return {"error": "Video not found"}
        except Exception as e:
            return {"error": str(e)}

    def get_analytics(self, video_id: str) -> Dict:
        """Get basic analytics for a video."""
        try:
            response = self.youtube.videos().list(
                part="statistics",
                id=video_id
            ).execute()

            if response.get("items"):
                stats = response["items"][0].get("statistics", {})
                return {
                    "video_id": video_id,
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                }
            return {"video_id": video_id, "error": "Video not found"}
        except Exception as e:
            return {"video_id": video_id, "error": str(e)}

    def get_channel_videos(self, max_results: int = 10) -> list:
        """Get recent videos from the authenticated channel."""
        try:
            response = self.youtube.channels().list(
                part="contentDetails",
                mine=True
            ).execute()

            if not response.get("items"):
                return []

            uploads_playlist = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

            videos_response = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist,
                maxResults=max_results
            ).execute()

            return [
                {
                    "video_id": item["snippet"]["resourceId"]["videoId"],
                    "title": item["snippet"]["title"],
                    "published_at": item["snippet"]["publishedAt"],
                }
                for item in videos_response.get("items", [])
            ]
        except Exception as e:
            logger.error(f"Failed to get channel videos: {e}")
            return []
