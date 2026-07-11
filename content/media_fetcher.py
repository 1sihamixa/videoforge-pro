"""
Stock media fetcher using Pexels and Pixabay APIs.
Downloads free stock photos and videos for faceless content.
"""

import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

import requests

import config.settings as settings

logger = logging.getLogger(__name__)


class MediaFetcher:
    """Fetches stock photos and videos from Pexels and Pixabay."""

    def __init__(self, output_dir: str = "temp"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pexels_key = settings.PEXELS_API_KEY
        self.pixabay_key = settings.PIXABAY_API_KEY
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "AutoSystem/1.0"})
        logger.info("MediaFetcher initialized")

    # ---- Pexels ----

    def _pexels_search_videos(self, query: str, per_page: int = 5,
                               orientation: str = "portrait") -> List[Dict]:
        """Search Pexels for videos."""
        if not self.pexels_key:
            return []
        try:
            resp = self._session.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": self.pexels_key},
                params={"query": query, "per_page": per_page, "orientation": orientation},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for video in data.get("videos", []):
                files = video.get("video_files", [])
                # Pick the best quality HD file
                best = None
                for f in files:
                    if f.get("quality") == "hd" and f.get("file_type") == "video/mp4":
                        best = f
                        break
                if not best and files:
                    best = files[0]
                if best:
                    results.append({
                        "id": video.get("id"),
                        "url": best.get("link"),
                        "width": best.get("width"),
                        "height": best.get("height"),
                        "duration": video.get("duration"),
                        "source": "pexels",
                        "license": "Pexels License (free for commercial use)",
                    })
            return results
        except Exception as e:
            logger.error(f"Pexels video search failed: {e}")
            return []

    def _pexels_search_photos(self, query: str, per_page: int = 5,
                               orientation: str = "portrait") -> List[Dict]:
        """Search Pexels for photos."""
        if not self.pexels_key:
            return []
        try:
            resp = self._session.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": self.pexels_key},
                params={"query": query, "per_page": per_page, "orientation": orientation},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for photo in data.get("photos", []):
                results.append({
                    "id": photo.get("id"),
                    "url": photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large"),
                    "width": photo.get("width"),
                    "height": photo.get("height"),
                    "source": "pexels",
                    "photographer": photo.get("photographer", ""),
                    "license": "Pexels License (free for commercial use)",
                })
            return results
        except Exception as e:
            logger.error(f"Pexels photo search failed: {e}")
            return []

    # ---- Pixabay ----

    def _pixabay_search_videos(self, query: str, per_page: int = 5) -> List[Dict]:
        """Search Pixabay for videos."""
        if not self.pixabay_key:
            return []
        try:
            resp = self._session.get(
                "https://pixabay.com/api/videos/",
                params={
                    "key": self.pixabay_key,
                    "q": query,
                    "per_page": per_page,
                    "video_type": "film",
                },
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for hit in data.get("hits", []):
                videos = hit.get("videos", {})
                medium = videos.get("medium") or videos.get("small")
                if medium:
                    results.append({
                        "id": hit.get("id"),
                        "url": medium.get("url"),
                        "width": medium.get("width"),
                        "height": medium.get("height"),
                        "duration": hit.get("duration"),
                        "source": "pixabay",
                        "license": "Pixabay License (free for commercial use)",
                    })
            return results
        except Exception as e:
            logger.error(f"Pixabay video search failed: {e}")
            return []

    def _pixabay_search_photos(self, query: str, per_page: int = 5) -> List[Dict]:
        """Search Pixabay for photos."""
        if not self.pixabay_key:
            return []
        try:
            resp = self._session.get(
                "https://pixabay.com/api/",
                params={
                    "key": self.pixabay_key,
                    "q": query,
                    "per_page": per_page,
                    "image_type": "photo",
                },
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for hit in data.get("hits", []):
                results.append({
                    "id": hit.get("id"),
                    "url": hit.get("largeImageURL"),
                    "width": hit.get("imageWidth"),
                    "height": hit.get("imageHeight"),
                    "source": "pixabay",
                    "photographer": hit.get("user", ""),
                    "license": "Pixabay License (free for commercial use)",
                })
            return results
        except Exception as e:
            logger.error(f"Pixabay photo search failed: {e}")
            return []

    # ---- Public API ----

    def search_videos(self, query: str, count: int = 5,
                      orientation: str = "portrait") -> List[Dict]:
        """
        Search both Pexels and Pixabay for videos.
        Merges results, prioritizes Pexels.
        """
        pexels = self._pexels_search_videos(query, count, orientation)
        pixabay = self._pixabay_search_videos(query, count)
        combined = pexels + pixabay
        return combined[:count]

    def search_photos(self, query: str, count: int = 5,
                      orientation: str = "portrait") -> List[Dict]:
        """Search both Pexels and Pixabay for photos."""
        pexels = self._pexels_search_photos(query, count, orientation)
        pixabay = self._pixabay_search_photos(query, count)
        combined = pexels + pixabay
        return combined[:count]

    def download(self, url: str, filename: Optional[str] = None) -> str:
        """
        Download a media file from URL.
        Returns path to downloaded file.
        """
        if not filename:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            ext = url.split("?")[0].split(".")[-1][:4]
            filename = f"media_{url_hash}.{ext}"

        output_path = self.output_dir / filename

        try:
            resp = self._session.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Downloaded: {filename} ({output_path.stat().st_size} bytes)")
            return str(output_path)
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            raise

    def fetch_and_download_videos(self, query: str, count: int = 3) -> List[str]:
        """Search and download videos. Returns list of local file paths."""
        results = self.search_videos(query, count)
        paths = []
        for item in results:
            try:
                path = self.download(item["url"])
                paths.append(path)
            except Exception:
                continue
        return paths

    def get_status(self) -> dict:
        """Get media fetcher status."""
        return {
            "pexels_configured": bool(self.pexels_key),
            "pixabay_configured": bool(self.pixabay_key),
        }
