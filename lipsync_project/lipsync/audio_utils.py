"""
Audio processing utilities for lip-sync pipeline.
"""
import os
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_audio_duration(path: str) -> float:
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path
        ], capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Could not get audio duration: {e}")
        return 0.0


def convert_to_wav(input_path: str, output_path: str, sample_rate: int = 16000) -> Optional[str]:
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-ar", str(sample_rate), "-ac", "1",
            "-c:a", "pcm_s16le",
            output_path
        ], capture_output=True, text=True, timeout=60)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            return output_path
    except Exception as e:
        logger.error(f"Audio conversion failed: {e}")
    return None


def validate_audio(path: str) -> bool:
    if not os.path.exists(path):
        logger.error(f"Audio file not found: {path}")
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"):
        logger.warning(f"Unsupported audio format: {ext}")
    duration = get_audio_duration(path)
    if duration < 0.5:
        logger.error(f"Audio too short: {duration:.2f}s")
        return False
    logger.info(f"Audio OK: {path} ({duration:.1f}s)")
    return True
