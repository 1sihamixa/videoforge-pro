"""
Subtitle generator using faster-whisper.
Transcribes audio and generates SRT subtitle files.
"""

import logging
import re
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not installed. pip install faster-whisper")


class SubtitleGenerator:
    """Generates SRT subtitles from audio using faster-whisper."""

    def __init__(self, model_size: str = "base", device: str = "auto"):
        self.model_size = model_size
        self.device = device
        self._model = None

        if not WHISPER_AVAILABLE:
            logger.warning("faster-whisper not available. Subtitle generation disabled.")

    def _load_model(self):
        """Lazy-load the whisper model."""
        if self._model is None:
            if not WHISPER_AVAILABLE:
                raise ImportError("faster-whisper required. pip install faster-whisper")
            logger.info(f"Loading whisper model: {self.model_size}")
            self._model = WhisperModel(self.model_size, device=self.device)
            logger.info("Whisper model loaded")

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def generate_srt(self, audio_path: str, output_path: Optional[str] = None,
                     max_chars_per_line: int = 42) -> str:
        """
        Generate SRT subtitle file from audio.

        Args:
            audio_path: Path to audio file
            output_path: Output SRT path (auto-generated if None)
            max_chars_per_line: Max characters per subtitle line

        Returns:
            Path to the generated SRT file
        """
        self._load_model()

        audio = Path(audio_path)
        if not audio.exists():
            raise FileNotFoundError(f"Audio file not found: {audio}")

        if not output_path:
            output_path = str(audio.with_suffix(".srt"))

        logger.info(f"Transcribing: {audio.name}")

        segments, info = self._model.transcribe(
            str(audio),
            beam_size=5,
            language="en",
            vad_filter=True,
        )

        srt_lines = []
        idx = 1
        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue

            # Split long text into multiple lines
            words = text.split()
            lines = []
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 > max_chars_per_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    current_line = f"{current_line} {word}".strip()
            if current_line:
                lines.append(current_line)

            display_text = "\n".join(lines)

            srt_lines.append(f"{idx}")
            srt_lines.append(
                f"{self._format_timestamp(segment.start)} --> "
                f"{self._format_timestamp(segment.end)}"
            )
            srt_lines.append(display_text)
            srt_lines.append("")
            idx += 1

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_lines))

        logger.info(f"SRT generated: {output_path} ({idx - 1} segments)")
        return output_path

    def generate_segments(self, audio_path: str) -> List[Dict]:
        """
        Transcribe audio and return structured segments.
        Returns list of dicts: {"start": float, "end": float, "text": str}
        """
        self._load_model()

        segments, _ = self._model.transcribe(
            audio_path,
            beam_size=5,
            language="en",
            vad_filter=True,
        )

        result = []
        for seg in segments:
            if seg.text.strip():
                result.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                })
        return result

    def get_status(self) -> dict:
        return {
            "faster_whisper_available": WHISPER_AVAILABLE,
            "model_size": self.model_size,
        }
