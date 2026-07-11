"""
Persona rotation manager.
Manages persona images per channel using round-robin scheduling.
Images are stored in content/persona_assets/<channel_id>/
"""

import logging
from pathlib import Path
from typing import List, Optional

import config.settings as settings
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class PersonaManager:
    """Manages persona image rotation per channel."""

    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()
        self.assets_dir = settings.PERSONA_ASSETS_DIR

    def _get_channel_dir(self, channel_id: str) -> Path:
        """Get the persona assets directory for a channel."""
        channel_dir = self.assets_dir / str(channel_id)
        channel_dir.mkdir(parents=True, exist_ok=True)
        return channel_dir

    def _list_images(self, channel_id: str) -> List[Path]:
        """List all valid image files for a channel, sorted by name."""
        channel_dir = self._get_channel_dir(channel_id)
        images = [
            f for f in sorted(channel_dir.iterdir())
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        return images

    def get_next_image(self, channel_id: str) -> Path:
        """
        Get the next persona image for a channel using round-robin.
        Raises FileNotFoundError if no images exist for the channel.
        """
        images = self._list_images(channel_id)
        if not images:
            raise FileNotFoundError(
                f"No persona images found for channel '{channel_id}'. "
                f"Add images to: {self.assets_dir / channel_id}"
            )

        # Get DB channel id from string channel_id
        from database.models import Channel
        with self.db._session() as session:
            db_channel = session.query(Channel).filter_by(
                channel_id=channel_id
            ).first()
            if not db_channel:
                raise ValueError(f"Channel '{channel_id}' not found in database")

            db_channel_id = db_channel.id

        # Get last used index
        last_index = self.db.get_persona_index(db_channel_id)
        total = len(images)

        # Round-robin: next index
        next_index = (last_index + 1) % total

        # Update DB
        self.db.update_persona_index(db_channel_id, next_index, total)

        selected = images[next_index]
        logger.info(
            f"Persona image for channel '{channel_id}': "
            f"{selected.name} (index {next_index}/{total - 1})"
        )
        return selected

    def get_image_count(self, channel_id: str) -> int:
        """Get the number of persona images for a channel."""
        return len(self._list_images(channel_id))

    def list_all_channels(self) -> List[str]:
        """List all channel IDs that have persona assets."""
        if not self.assets_dir.exists():
            return []
        return [
            d.name for d in self.assets_dir.iterdir()
            if d.is_dir() and any(
                f.suffix.lower() in SUPPORTED_EXTENSIONS
                for f in d.iterdir() if f.is_file()
            )
        ]

    def validate_channel_assets(self, channel_id: str) -> dict:
        """
        Validate persona assets for a channel.
        Returns validation report.
        """
        images = self._list_images(channel_id)
        return {
            "channel_id": channel_id,
            "image_count": len(images),
            "images": [img.name for img in images],
            "is_valid": len(images) > 0,
            "directory": str(self._get_channel_dir(channel_id)),
        }
