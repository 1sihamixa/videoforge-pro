"""
Video processing utilities for lip-sync pipeline.
"""
import os
import subprocess
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def get_video_info(path: str) -> Optional[dict]:
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,codec_name",
            "-of", "json",
            path
        ], capture_output=True, text=True, timeout=30)
        import json
        info = json.loads(result.stdout)
        streams = info.get("streams", [])
        if streams:
            return streams[0]
    except Exception as e:
        logger.debug(f"Could not get video info: {e}")
    return None


def validate_face_image(path: str) -> bool:
    if not os.path.exists(path):
        logger.error(f"Face file not found: {path}")
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg", ".png", ".bmp", ".mp4", ".avi", ".mov", ".mkv"):
        if ext in (".mp4", ".avi", ".mov", ".mkv"):
            info = get_video_info(path)
            if info and int(info.get("width", 0)) > 0 and int(info.get("height", 0)) > 0:
                logger.info(f"Face video OK: {path} ({info['width']}x{info['height']})")
                return True
            logger.error(f"Cannot read video: {path}")
            return False
        import cv2
        img = cv2.imread(path)
        if img is None:
            logger.error(f"Cannot read image: {path}")
            return False
        h, w = img.shape[:2]
        if w < 50 or h < 50:
            logger.error(f"Image too small: {w}x{h}")
            return False
        logger.info(f"Face image OK: {path} ({w}x{h})")
        return True
    logger.error(f"Unsupported face file format: {ext}")
    return False


def scale_video(input_path: str, output_path: str,
                width: int, height: int, fps: int = 25,
                crf: int = 18) -> Optional[str]:
    try:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                   f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-r", str(fps),
            "-c:a", "copy", output_path
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
            return output_path
    except Exception as e:
        logger.error(f"Video scaling failed: {e}")
    return None
