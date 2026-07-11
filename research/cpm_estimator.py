"""
CPM (Cost Per Mille) estimation module.
Estimates approximate CPM based on niche, geography, and season.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

NICHES_FILE = Path(__file__).resolve().parent.parent / "config" / "niches.json"


class CPMEstimator:
    """Estimates CPM based on niche, geo, and seasonal factors."""

    def __init__(self):
        self.data = self._load_niches()
        logger.info("CPMEstimator initialized")

    def _load_niches(self) -> Dict:
        try:
            with open(NICHES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load niches config: {e}")
            return {"niches": {}, "cpm_adjustments": {}}

    def _get_season_key(self) -> str:
        month = datetime.now().month
        if month <= 3:
            return "season_q1"
        elif month <= 6:
            return "season_q2"
        elif month <= 9:
            return "season_q3"
        else:
            return "season_q4"

    def _get_geo_key(self, geo: str) -> str:
        geo_upper = geo.upper()
        mapping = {
            "US": "geo_us",
            "UNITED STATES": "geo_us",
            "UK": "geo_uk",
            "UNITED KINGDOM": "geo_uk",
            "GB": "geo_uk",
            "CA": "geo_ca",
            "CANADA": "geo_ca",
        }
        return mapping.get(geo_upper, "geo_other")

    def estimate(self, niche: str, geo: str = "US",
                 is_short: bool = False) -> Dict:
        """
        Estimate CPM for a given niche and geo.
        Returns dict with raw_cpm, adjusted_cpm, and factors used.
        """
        niches = self.data.get("niches", {})
        adjustments = self.data.get("cpm_adjustments", {})

        niche_data = niches.get(niche, {})
        base_cpm = niche_data.get("cpm_estimate_usd", 5.0)
        niche_multiplier = niche_data.get("cpm_multiplier", 0.5)

        geo_key = self._get_geo_key(geo)
        geo_factor = adjustments.get(geo_key, 0.5)

        season_key = self._get_season_key()
        season_factor = adjustments.get(season_key, 1.0)

        video_type_key = "short_video" if is_short else "long_video"
        video_type_factor = adjustments.get(video_type_key, 1.0)

        raw_cpm = base_cpm
        adjusted_cpm = (
            base_cpm * niche_multiplier * geo_factor * season_factor * video_type_factor
        )

        result = {
            "raw_cpm": round(raw_cpm, 2),
            "adjusted_cpm": round(adjusted_cpm, 2),
            "base_cpm": base_cpm,
            "niche_multiplier": niche_multiplier,
            "geo_factor": geo_factor,
            "season_factor": season_factor,
            "video_type_factor": video_type_factor,
            "niche_label": niche_data.get("label_ar", niche),
        }

        logger.debug(f"CPM for {niche}/{geo}: ${adjusted_cpm:.2f}")
        return result

    def get_niche_keywords(self, niche: str) -> list:
        """Get keywords for a specific niche."""
        niches = self.data.get("niches", {})
        return niches.get(niche, {}).get("keywords", [])

    def list_niches(self) -> list:
        """List all available niches with their CPM estimates."""
        niches = self.data.get("niches", {})
        result = []
        for key, data in niches.items():
            result.append({
                "key": key,
                "label": data.get("label_ar", key),
                "base_cpm": data.get("cpm_estimate_usd", 0),
                "keyword_count": len(data.get("keywords", [])),
            })
        return result
