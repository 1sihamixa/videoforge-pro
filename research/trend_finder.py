"""
Google Trends integration for trend discovery.
Uses pytrends to fetch trending keywords by region.
"""

import logging
import time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False
    logger.warning("pytrends not installed. Install with: pip install pytrends")


class TrendFinder:
    """Discovers trending topics via Google Trends."""

    def __init__(self, hl: str = "en-US", tz: str = 360):
        if not PYTRENDS_AVAILABLE:
            raise ImportError("pytrends is required. pip install pytrends")
        self.pytrends = TrendReq(hl=hl, tz=tz)
        logger.info("TrendFinder initialized")

    def get_related_queries(self, keyword: str, geo: str = "US") -> List[Dict]:
        """
        Get related rising/top queries for a keyword.
        Returns list of dicts: [{"query": str, "value": int}, ...]
        """
        try:
            self.pytrends.build_payload(
                kw_list=[keyword],
                cat=0,
                timeframe="today 12-m",
                geo=geo
            )
            related = self.pytrends.related_queries()
            results = []
            if keyword in related:
                rising = related[keyword].get("rising")
                top = related[keyword].get("top")
                if rising is not None and not rising.empty:
                    for _, row in rising.head(10).iterrows():
                        results.append({
                            "query": row.get("query", ""),
                            "value": int(row.get("value", 0)),
                            "type": "rising"
                        })
                if top is not None and not top.empty:
                    for _, row in top.head(10).iterrows():
                        results.append({
                            "query": row.get("query", ""),
                            "value": int(row.get("value", 0)),
                            "type": "top"
                        })
            return results
        except Exception as e:
            logger.error(f"Error fetching related queries for '{keyword}': {e}")
            return []

    def get_interest_over_time(self, keyword: str, geo: str = "US") -> Dict:
        """
        Get search interest over time for a keyword.
        Returns dict with current_interest and avg_interest.
        """
        try:
            self.pytrends.build_payload(
                kw_list=[keyword],
                cat=0,
                timeframe="today 3-m",
                geo=geo
            )
            data = self.pytrends.interest_over_time()
            if data.empty or keyword not in data.columns:
                return {"current_interest": 0, "avg_interest": 0, "trend": "stable"}

            values = data[keyword].tolist()
            current = values[-1] if values else 0
            avg = sum(values) / len(values) if values else 0
            recent_avg = sum(values[-4:]) / 4 if len(values) >= 4 else avg

            if recent_avg > avg * 1.2:
                trend = "rising"
            elif recent_avg < avg * 0.8:
                trend = "falling"
            else:
                trend = "stable"

            return {
                "current_interest": current,
                "avg_interest": round(avg, 1),
                "trend": trend
            }
        except Exception as e:
            logger.error(f"Error fetching interest for '{keyword}': {e}")
            return {"current_interest": 0, "avg_interest": 0, "trend": "unknown"}

    def get_suggestions(self, keyword: str) -> List[str]:
        """Get autocomplete suggestions for a keyword."""
        try:
            suggestions = self.pytrends.suggestions(keyword=keyword)
            return [s.get("title", "") for s in suggestions if s.get("title")]
        except Exception as e:
            logger.error(f"Error getting suggestions for '{keyword}': {e}")
            return []

    def batch_trend_analysis(self, keywords: List[str],
                             geo: str = "US") -> List[Dict]:
        """
        Analyze trends for multiple keywords.
        Returns list with trend data for each keyword.
        """
        results = []
        for keyword in keywords:
            interest = self.get_interest_over_time(keyword, geo)
            suggestions = self.get_suggestions(keyword)
            results.append({
                "keyword": keyword,
                "geo": geo,
                **interest,
                "suggestions": suggestions[:5]
            })
            # Rate limit: pytrends allows ~10 requests/minute
            time.sleep(6)
        logger.info(f"Analyzed trends for {len(keywords)} keywords")
        return results
