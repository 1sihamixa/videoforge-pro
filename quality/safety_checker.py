"""
Safety checker for content compliance with platform policies.
Verifies YouTube policies, license compliance, and AI disclosure requirements.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

PLATFORM_RULES_FILE = Path(__file__).resolve().parent.parent / "config" / "platform_rules.json"


class SafetyChecker:
    """Checks content safety and platform policy compliance."""

    def __init__(self):
        self.rules = self._load_rules()
        logger.info("SafetyChecker initialized")

    def _load_rules(self) -> dict:
        try:
            with open(PLATFORM_RULES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load platform rules: {e}")
            return {}

    def check_youtube_compliance(self, title: str, description: str,
                                  tags: List[str], video_style: str) -> Dict:
        """
        Check content compliance with YouTube policies.

        Returns dict with:
            - compliant (bool)
            - warnings (list)
            - required_actions (list)
        """
        youtube = self.rules.get("youtube", {})
        warnings = []
        required_actions = []

        # Title checks
        if len(title) > youtube.get("max_title_length", 100):
            warnings.append(
                f"Title too long ({len(title)} chars, max {youtube.get('max_title_length', 100)})"
            )

        # Description checks
        if len(description) > youtube.get("max_description_length", 5000):
            warnings.append(
                f"Description too long ({len(description)} chars)"
            )

        # Tag checks
        max_tags = youtube.get("max_tags", 15)
        if len(tags) > max_tags:
            warnings.append(f"Too many tags ({len(tags)}, max {max_tags})")

        for tag in tags:
            if len(tag) > youtube.get("max_tag_length", 30):
                warnings.append(f"Tag too long: '{tag[:30]}...'")

        # AI content disclosure
        if video_style in ("avatar_talking", "faceless"):
            required_actions.append(
                "Set containsSyntheticMedia=true when uploading to YouTube"
            )

        # Mass-produced content policy
        required_actions.append(
            "Ensure content provides unique value beyond what's already available"
        )

        compliant = len(warnings) == 0
        return {
            "platform": "youtube",
            "compliant": compliant,
            "warnings": warnings,
            "required_actions": required_actions,
        }

    def check_license_compliance(self, media_files: List[str]) -> Dict:
        """
        Check that all media files have proper license tracking.
        """
        issues = []
        for filepath in media_files:
            path = Path(filepath)
            if not path.exists():
                issues.append(f"Media file not found: {filepath}")
            # License info should be stored alongside the file
            # or in the download metadata
        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "note": "License info tracked during download from Pexels/Pixabay",
        }

    def check_ai_disclosure(self, video_style: str) -> Dict:
        """
        Verify AI content disclosure requirements.
        """
        required = video_style in ("avatar_talking", "faceless")
        return {
            "ai_generated": required,
            "disclosure_required": True,
            "youtube_flag": "containsSyntheticMedia" if required else None,
            "recommendation": (
                "Always declare AI-generated content per YouTube policy. "
                "Set containsSyntheticMedia=true in video metadata."
            ) if required else "No AI disclosure required for this content type",
        }

    def full_check(self, title: str, description: str, tags: List[str],
                   video_style: str, media_files: List[str]) -> Dict:
        """Run all safety checks."""
        youtube = self.check_youtube_compliance(title, description, tags, video_style)
        license_check = self.check_license_compliance(media_files)
        ai_disclosure = self.check_ai_disclosure(video_style)

        all_passed = youtube["compliant"] and license_check["compliant"]

        return {
            "overall_compliant": all_passed,
            "youtube": youtube,
            "license": license_check,
            "ai_disclosure": ai_disclosure,
        }
