"""
Scoring and ranking module.
Combines search volume, competition, and CPM into a final score.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class TopicScorer:
    """Calculates final opportunity score for topics and ranks them."""

    # Scoring weights (adjustable)
    WEIGHT_SEARCH_VOLUME = 0.4
    WEIGHT_INVERSE_COMPETITION = 0.35
    WEIGHT_CPM = 0.25

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def calculate_score(self, search_volume: int, competition_score: float,
                        estimated_cpm: float, max_volume: int = 10000,
                        max_cpm: float = 30.0) -> float:
        """
        Calculate final opportunity score (0-100).

        Args:
            search_volume: Monthly search volume estimate
            competition_score: 0-1 (0 = no competition, 1 = saturated)
            estimated_cpm: Estimated CPM in USD
            max_volume: Normalization cap for search volume
            max_cpm: Normalization cap for CPM
        """
        # Normalize search volume (0-1)
        vol_normalized = min(search_volume / max_volume, 1.0)

        # Inverse competition (0-1, higher = less competition = better)
        inv_competition = 1.0 - competition_score

        # Normalize CPM (0-1)
        cpm_normalized = min(estimated_cpm / max_cpm, 1.0)

        score = (
            vol_normalized * self.WEIGHT_SEARCH_VOLUME +
            inv_competition * self.WEIGHT_INVERSE_COMPETITION +
            cpm_normalized * self.WEIGHT_CPM
        ) * 100

        return round(score, 2)

    def rank_topics(self, topics: List[Dict]) -> List[Dict]:
        """
        Score and rank a list of topic dicts.
        Each dict must have: keyword, search_volume, competition_score, estimated_cpm
        Returns sorted list (highest score first).
        """
        scored = []
        max_volume = max((t.get("search_volume", 0) for t in topics), default=1) or 1

        for topic in topics:
            score = self.calculate_score(
                search_volume=topic.get("search_volume", 0),
                competition_score=topic.get("competition_score", 0.5),
                estimated_cpm=topic.get("estimated_cpm", 5.0),
                max_volume=max_volume
            )
            scored.append({**topic, "final_score": score})

        scored.sort(key=lambda x: x["final_score"], reverse=True)
        logger.info(f"Ranked {len(scored)} topics, top score: {scored[0]['final_score'] if scored else 0}")
        return scored

    def export_csv(self, topics: List[Dict], filename: str = "topics_report.csv") -> str:
        """
        Export ranked topics to CSV file.
        Returns the file path.
        """
        filepath = self.output_dir / filename
        fieldnames = [
            "keyword", "niche", "search_volume", "competition_score",
            "estimated_cpm", "final_score", "status"
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for topic in topics:
                writer.writerow(topic)

        logger.info(f"Exported {len(topics)} topics to {filepath}")
        return str(filepath)

    def export_json(self, topics: List[Dict],
                    filename: str = "topics_report.json") -> str:
        """
        Export ranked topics to JSON file.
        Returns the file path.
        """
        filepath = self.output_dir / filename
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_topics": len(topics),
            "topics": topics
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported {len(topics)} topics to {filepath}")
        return str(filepath)

    def get_summary(self, topics: List[Dict]) -> Dict:
        """Get summary statistics for ranked topics."""
        if not topics:
            return {"count": 0, "avg_score": 0, "top_keyword": ""}

        scores = [t.get("final_score", 0) for t in topics]
        return {
            "count": len(topics),
            "avg_score": round(sum(scores) / len(scores), 2),
            "max_score": max(scores),
            "min_score": min(scores),
            "top_keyword": topics[0].get("keyword", "") if topics else "",
        }
