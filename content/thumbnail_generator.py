"""
Thumbnail generator for video content.
Creates eye-catching thumbnails with text overlays.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not installed. pip install Pillow")


class ThumbnailGenerator:
    """Generates video thumbnails with text overlays."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = 1280
        self.height = 720

    def generate(self, title: str, background_image: Optional[str] = None,
                 output_filename: Optional[str] = None) -> str:
        """
        Generate a thumbnail image.

        Args:
            title: Title text to overlay
            background_image: Optional background image path
            output_filename: Custom output filename

        Returns:
            Path to the generated thumbnail
        """
        if not PIL_AVAILABLE:
            raise ImportError("Pillow is required. pip install Pillow")

        if not output_filename:
            title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
            output_filename = f"thumb_{title_hash}.png"

        output_path = self.output_dir / output_filename

        # Create or load background
        if background_image and Path(background_image).exists():
            img = Image.open(background_image).convert("RGB")
            img = img.resize((self.width, self.height), Image.LANCZOS)
            # Add dark overlay for text readability
            overlay = Image.new("RGB", (self.width, self.height), (0, 0, 0))
            img = Image.blend(img, overlay, alpha=0.4)
        else:
            # Create gradient-like background
            img = Image.new("RGB", (self.width, self.height), (15, 15, 35))

        draw = ImageDraw.Draw(img)

        # Try to use a system font, fallback to default
        font_large = self._get_font(64)
        font_small = self._get_font(28)

        # Word wrap title
        lines = self._wrap_text(title, font_large, self.width - 100)

        # Calculate vertical centering
        total_text_height = len(lines) * 75
        start_y = (self.height - total_text_height) // 2

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font_large)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            y = start_y + i * 75

            # Draw shadow
            draw.text((x + 3, y + 3), line, fill=(0, 0, 0), font=font_large)
            # Draw text
            draw.text((x, y), line, fill=(255, 255, 255), font=font_large)

        # Add branding text at bottom
        brand_text = "AutoSystem"
        draw.text(
            (self.width - 200, self.height - 40),
            brand_text,
            fill=(150, 150, 150),
            font=font_small
        )

        img.save(str(output_path), quality=95)
        logger.info(f"Thumbnail generated: {output_path}")
        return str(output_path)

    def _get_font(self, size: int):
        """Get a font, trying system fonts first."""
        font_paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for fp in font_paths:
            try:
                return ImageFont.truetype(fp, size)
            except (IOError, OSError):
                continue
        return ImageFont.load_default()

    def _wrap_text(self, text: str, font, max_width: int) -> list:
        """Word-wrap text to fit within max_width pixels."""
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            # Estimate text width
            try:
                from PIL import ImageDraw
                dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
                bbox = dummy.textbbox((0, 0), test_line, font=font)
                width = bbox[2] - bbox[0]
            except Exception:
                width = len(test_line) * 12  # rough estimate

            if width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines[:4]  # Max 4 lines
