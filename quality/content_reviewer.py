"""
Automated content quality reviewer.
Checks text, audio, and video against quality standards before publishing.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import config.settings as settings

logger = logging.getLogger(__name__)


class ContentReviewer:
    """Automated quality review for generated content."""

    # Common problematic patterns
    MEDICAL_CLAIMS = re.compile(
        r"\b(cure|treat|diagnose|prevention of disease|guaranteed results|"
        r"proven to|medical advice|consult your doctor)\b",
        re.IGNORECASE
    )
    FINANCIAL_CLAIMS = re.compile(
        r"\b(guaranteed returns|risk-free investment|get rich|"
        r"double your money|no risk|100% profit)\b",
        re.IGNORECASE
    )
    MISLEADING = re.compile(
        r"\b(secret trick|they don't want you to know|"
        r"doctors hate this|one weird trick)\b",
        re.IGNORECASE
    )

    def __init__(self):
        logger.info("ContentReviewer initialized")

    def review_text(self, text: str, title: str = "") -> Dict:
        """
        Review script text for quality and compliance issues.
        Returns dict with passed (bool) and issues (list).
        """
        issues = []
        full_text = f"{title} {text}"

        # Check for prohibited patterns
        if self.MEDICAL_CLAIMS.search(full_text):
            issues.append("Potential medical claims detected - add disclaimer")
        if self.FINANCIAL_CLAIMS.search(full_text):
            issues.append("Potential misleading financial claims - review before publishing")
        if self.MISLEADING.search(full_text):
            issues.append("Clickbait/dishonest language detected")

        # Check length
        word_count = len(full_text.split())
        if word_count < 50:
            issues.append(f"Text too short ({word_count} words, minimum 50)")
        if word_count > 5000:
            issues.append(f"Text too long ({word_count} words, maximum 5000)")

        # Check for repeated sentences
        sentences = re.split(r'[.!?]+', text)
        unique_sentences = set(s.strip().lower() for s in sentences if s.strip())
        if len(sentences) > 5 and len(unique_sentences) < len(sentences) * 0.7:
            issues.append("Text appears to have excessive repetition")

        passed = len(issues) == 0
        return {"passed": passed, "issues": issues, "word_count": word_count}

    def review_audio(self, audio_path: str) -> Dict:
        """
        Basic audio quality check.
        Verifies file exists, is not empty, and has reasonable duration.
        """
        issues = []
        path = Path(audio_path)

        if not path.exists():
            return {"passed": False, "issues": ["Audio file does not exist"]}

        size = path.stat().st_size
        if size == 0:
            issues.append("Audio file is empty")
        elif size < 10000:  # Less than 10KB is suspicious
            issues.append(f"Audio file very small ({size} bytes) - may be corrupted")

        # Check duration via ffprobe
        duration = self._get_duration(str(path))
        if duration < settings.MIN_VIDEO_DURATION_SECONDS:
            issues.append(f"Audio too short ({duration:.1f}s, minimum {settings.MIN_VIDEO_DURATION_SECONDS}s)")
        if duration > settings.MAX_VIDEO_DURATION_SECONDS:
            issues.append(f"Audio too long ({duration:.1f}s, maximum {settings.MAX_VIDEO_DURATION_SECONDS}s)")

        return {"passed": len(issues) == 0, "issues": issues, "duration": duration}

    def review_video(self, video_path: str) -> Dict:
        """
        Basic video quality check.
        Verifies resolution, duration, and file integrity.
        """
        issues = []
        path = Path(video_path)

        if not path.exists():
            return {"passed": False, "issues": ["Video file does not exist"]}

        size = path.stat().st_size
        if size == 0:
            return {"passed": False, "issues": ["Video file is empty"]}

        # Check with ffprobe
        info = self._probe_video(str(path))
        duration = info.get("duration", 0)
        width = info.get("width", 0)
        height = info.get("height", 0)

        if duration < settings.MIN_VIDEO_DURATION_SECONDS:
            issues.append(f"Video too short ({duration:.1f}s)")
        if duration > settings.MAX_VIDEO_DURATION_SECONDS:
            issues.append(f"Video too long ({duration:.1f}s)")
        if width < settings.MIN_VIDEO_WIDTH:
            issues.append(f"Width too small ({width}px, minimum {settings.MIN_VIDEO_WIDTH}px)")
        if height < settings.MIN_VIDEO_HEIGHT:
            issues.append(f"Height too small ({height}px, minimum {settings.MIN_VIDEO_HEIGHT}px)")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "duration": duration,
            "width": width,
            "height": height,
        }

    def _get_duration(self, path: str) -> float:
        """Get media file duration using ffprobe."""
        import subprocess
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def _probe_video(self, path: str) -> dict:
        """Get video info using ffprobe."""
        import subprocess
        import json
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            data = json.loads(result.stdout)
            duration = float(data.get("format", {}).get("duration", 0))
            for s in data.get("streams", []):
                if s.get("codec_type") == "video":
                    return {
                        "duration": duration,
                        "width": s.get("width", 0),
                        "height": s.get("height", 0)
                    }
            return {"duration": duration, "width": 0, "height": 0}
        except Exception:
            return {"duration": 0, "width": 0, "height": 0}

    def full_review(self, script_data: Dict, audio_path: str,
                    video_path: str, title: str = "") -> Dict:
        """
        Run complete quality review on all components.
        Returns comprehensive review report.
        """
        script_text = script_data.get("script", {}).get("full_text", "")
        if not script_text:
            # Build from sections
            sections = script_data.get("script", {}).get("sections", [])
            script_text = " ".join(s.get("narration", "") for s in sections)

        text_review = self.review_text(script_text, title)
        audio_review = self.review_audio(audio_path)
        video_review = self.review_video(video_path)

        overall_passed = (
            text_review["passed"] and
            audio_review["passed"] and
            video_review["passed"]
        )

        report = {
            "overall_passed": overall_passed,
            "text_review": text_review,
            "audio_review": audio_review,
            "video_review": video_review,
        }

        if not overall_passed:
            logger.warning(f"Quality review FAILED: {report}")

        return report
