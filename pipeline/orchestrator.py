"""
Pipeline orchestrator.
Coordinates the full workflow: research → select topic → generate content → quality check → publish.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

import config.settings as settings
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


def _lazy_import_trend_finder():
    from research.trend_finder import TrendFinder
    return TrendFinder()


def _lazy_import_youtube_analyzer():
    from research.youtube_analyzer import YouTubeAnalyzer
    return YouTubeAnalyzer()


def _lazy_import_cpm_estimator():
    from research.cpm_estimator import CPMEstimator
    return CPMEstimator()


def _lazy_import_scorer():
    from research.scorer import TopicScorer
    return TopicScorer()


def _lazy_import_script_gen():
    from content.script_generator import ScriptGenerator
    return ScriptGenerator()


def _lazy_import_tts():
    from content.tts_engine import TTSEngine
    return TTSEngine()


def _lazy_import_media():
    from content.media_fetcher import MediaFetcher
    return MediaFetcher()


def _lazy_import_video_asm():
    from content.video_assembler import VideoAssembler
    return VideoAssembler()


def _lazy_import_subtitle():
    from content.subtitle_generator import SubtitleGenerator
    return SubtitleGenerator()


def _lazy_import_thumbnail():
    from content.thumbnail_generator import ThumbnailGenerator
    return ThumbnailGenerator()


def _lazy_import_reviewer():
    from quality.content_reviewer import ContentReviewer
    return ContentReviewer()


def _lazy_import_safety():
    from quality.safety_checker import SafetyChecker
    return SafetyChecker()


def _lazy_import_publisher():
    from publish.youtube_publisher import YouTubePublisher
    return YouTubePublisher()


def _lazy_import_notifier():
    from notifications.telegram_bot import TelegramNotifier
    return TelegramNotifier()


class PipelineOrchestrator:
    """Orchestrates the full content pipeline."""

    def __init__(self, channel_id: Optional[str] = None):
        self.db = DatabaseManager()
        self.channel_id = channel_id
        self.trend_finder = None
        self.youtube_analyzer = None
        self.cpm_estimator = _lazy_import_cpm_estimator()
        self.scorer = _lazy_import_scorer()
        self.notifier = _lazy_import_notifier()

        # Lazy-init modules that need API keys
        self._script_gen = None
        self._tts = None
        self._media = None
        self._video_asm = None
        self._subtitle_gen = None
        self._thumbnail_gen = None
        self._persona_mgr = None
        self._avatar_gen = None
        self._reviewer = _lazy_import_reviewer()
        self._safety = _lazy_import_safety()
        self._publisher = None

    def run(self, channel_id: Optional[str] = None):
        """Run the full pipeline for one cycle."""
        ch_id = channel_id or self.channel_id
        logger.info(f"=== Pipeline Cycle Started: channel={ch_id} ===")

        try:
            # Step 1: Research
            topic = self._step_research(ch_id)
            if not topic:
                logger.info("No suitable topic found. Pipeline cycle complete.")
                return

            # Step 2: Generate content
            video_data = self._step_generate(topic, ch_id)
            if not video_data:
                logger.error("Content generation failed.")
                return

            # Step 3: Quality check
            passed = self._step_quality_check(video_data)
            if not passed:
                logger.warning("Quality check failed.")
                return

            # Step 4: Publish or notify
            self._step_publish(video_data)

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            self.notifier.send(f"Pipeline error: {e}")
        finally:
            logger.info("=== Pipeline Cycle Complete ===")

    def _step_research(self, channel_id: Optional[str] = None) -> Optional[object]:
        """Step 1: Find and select the best topic."""
        logger.info("Step 1: Research")

        # Get active channels or use provided channel_id
        channels = self.db.get_active_channels()
        if not channels:
            logger.warning("No active channels configured")
            return None

        # Use first active channel or the specified one
        if channel_id:
            channel = self.db.get_channel(channel_id)
        else:
            channel = channels[0]

        niche = channel.niche if channel else "finance_invest"
        style = channel.content_style if channel else "faceless"

        # Get top unprocessed topic
        topic = self.db.get_top_unprocessed_topic(niche=niche)
        if topic:
            logger.info(f"Selected topic: {topic.keyword} (score={topic.final_score})")
            return topic

        # If no topics available, try to discover new ones
        self._discover_topics(niche)
        topic = self.db.get_top_unprocessed_topic(niche=niche)
        return topic

    def _discover_topics(self, niche: str):
        """Discover new topics for a niche."""
        try:
            # Initialize trend analyzer
            if self.trend_finder is None:
                self.trend_finder = _lazy_import_trend_finder()

            if self.youtube_analyzer is None:
                self.youtube_analyzer = _lazy_import_youtube_analyzer()

            # Get keywords for this niche
            keywords = self.cpm_estimator.get_niche_keywords(niche)
            if not keywords:
                logger.warning(f"No keywords defined for niche: {niche}")
                return

            # Analyze each keyword
            for keyword in keywords[:10]:  # Limit per cycle
                try:
                    # Get YouTube competition data
                    competition = self.youtube_analyzer.analyze_competition(keyword)

                    # Estimate CPM
                    cpm_data = self.cpm_estimator.estimate(niche)

                    # Map competition level to score
                    competition_map = {"low": 0.2, "medium": 0.5, "high": 0.8}
                    comp_score = competition_map.get(
                        competition.get("competition_level", "medium"), 0.5
                    )

                    # Calculate final score
                    final_score = self.scorer.calculate_score(
                        search_volume=competition.get("avg_views", 0),
                        competition_score=comp_score,
                        estimated_cpm=cpm_data.get("adjusted_cpm", 5.0),
                    )

                    # Save to database
                    self.db.save_topic(
                        keyword=keyword,
                        niche=niche,
                        search_volume=competition.get("avg_views", 0),
                        competition_score=comp_score,
                        estimated_cpm=cpm_data.get("adjusted_cpm", 5.0),
                        final_score=final_score,
                        notes=f"Competition: {competition.get('competition_level')}, "
                              f"Avg views: {competition.get('avg_views')}"
                    )

                    time.sleep(2)  # Rate limit

                except Exception as e:
                    logger.warning(f"Failed to analyze '{keyword}': {e}")
                    continue

        except ImportError as e:
            logger.error(f"Missing dependency for research: {e}")
        except Exception as e:
            logger.error(f"Research failed: {e}", exc_info=True)

    def _step_generate(self, topic, channel_id: str = None) -> Optional[Dict]:
        """Step 2: Generate script, audio, video."""
        logger.info(f"Step 2: Generate content for '{topic.keyword}'")

        channel = self.db.get_channel(channel_id) if channel_id else None
        style = channel.content_style if channel else settings.DEFAULT_VIDEO_STYLE

        # Generate script
        if self._script_gen is None:
            self._script_gen = _lazy_import_script_gen()

        script = self._script_gen.generate_script(
            keyword=topic.keyword,
            niche=topic.niche,
            video_style=style,
            duration="short"  # Default to shorts
        )

        # Generate audio
        if self._tts is None:
            self._tts = _lazy_import_tts()

        sections = script.get("script", {}).get("sections", [])
        narration_texts = [s.get("narration", "") for s in sections if s.get("narration")]
        full_text = " ".join(narration_texts)

        audio_path = self._tts.generate(
            text=full_text,
            deterministic_key=topic.keyword
        )

        # Create video record
        channel_obj = self.db.get_channel(channel_id) if channel_id else None
        if not channel_obj:
            channels = self.db.get_active_channels()
            channel_obj = channels[0] if channels else None

        video = self.db.create_video(
            channel_id=channel_obj.id if channel_obj else 1,
            topic_id=topic.id,
            title=script.get("title", topic.keyword),
            description=script.get("description", ""),
            tags=",".join(script.get("tags", [])),
            style=style
        )

        # Assemble video
        if self._media is None:
            self._media = _lazy_import_media()
        if self._video_asm is None:
            self._video_asm = _lazy_import_video_asm()

        video_files = self._media.fetch_and_download_videos(topic.keyword, count=3)

        video_path = self._video_asm.assemble_faceless(
            audio_paths=[audio_path],
            video_paths=video_files,
            title=script.get("title", ""),
            output_filename=f"video_{video.id}.mp4"
        )

        # Generate subtitles
        if self._subtitle_gen is None:
            self._subtitle_gen = _lazy_import_subtitle()

        srt_path = self._subtitle_gen.generate_srt(audio_path)
        subtitled_path = self._video_asm.add_subtitles(video_path, srt_path)

        # Generate thumbnail
        if self._thumbnail_gen is None:
            self._thumbnail_gen = _lazy_import_thumbnail()

        thumb_path = self._thumbnail_gen.generate(
            title=script.get("title", topic.keyword),
            background_image=video_files[0] if video_files else None
        )

        # Update video record
        self.db.update_video(
            video.id,
            file_path=subtitled_path,
            status="reviewing"
        )

        # Mark topic as in-progress
        self.db.update_topic_status(topic.id, "in_progress")

        logger.info(f"Content generated: {subtitled_path}")
        return {
            "video_id": video.id,
            "topic": topic,
            "script": script,
            "audio_path": audio_path,
            "video_path": subtitled_path,
            "srt_path": srt_path,
            "thumbnail_path": thumb_path,
            "channel": channel_obj,
            "style": style,
        }

    def _step_quality_check(self, video_data: Dict) -> bool:
        """Step 3: Run quality checks."""
        logger.info("Step 3: Quality check")

        # Run content review
        review = self._reviewer.full_review(
            script_data=video_data["script"],
            audio_path=video_data["audio_path"],
            video_path=video_data["video_path"],
            title=video_data["script"].get("title", "")
        )

        # Run safety check
        safety = self._safety.full_check(
            title=video_data["script"].get("title", ""),
            description=video_data["script"].get("description", ""),
            tags=video_data["script"].get("tags", []),
            video_style=video_data["style"],
            media_files=[video_data["video_path"]]
        )

        # Save quality report
        self.db.save_quality_report(
            video_data["video_id"],
            text_check_passed=review["text_review"]["passed"],
            text_issues="; ".join(review["text_review"]["issues"]),
            audio_check_passed=review["audio_review"]["passed"],
            audio_issues="; ".join(review["audio_review"]["issues"]),
            video_check_passed=review["video_review"]["passed"],
            video_issues="; ".join(review["video_review"]["issues"]),
            safety_check_passed=safety["overall_compliant"],
            safety_issues="; ".join(safety.get("youtube", {}).get("warnings", [])),
            overall_passed=review["overall_passed"] and safety["overall_compliant"],
        )

        if review["overall_passed"] and safety["overall_compliant"]:
            self.db.update_video(video_data["video_id"], status="reviewed")
            logger.info("Quality check PASSED")
            return True
        else:
            self.db.update_video(video_data["video_id"], status="failed")
            logger.warning("Quality check FAILED")
            return False

    def _step_publish(self, video_data: Dict):
        """Step 4: Publish or notify for review."""
        logger.info("Step 4: Publish")

        if settings.AUTO_PUBLISH:
            # Direct publish
            self._do_publish(video_data)
        else:
            # Notify for manual review
            self.notifier.send(
                f"Video ready for review:\n"
                f"Title: {video_data['script'].get('title', '')}\n"
                f"File: {video_data['video_path']}\n"
                f"Dashboard: http://localhost:{settings.DASHBOARD_PORT}"
            )
            logger.info("Notification sent for manual review")

    def _do_publish(self, video_data: Dict):
        """Actually publish the video."""
        if self._publisher is None:
            self._publisher = _lazy_import_publisher()

        # Schedule for tomorrow at best time
        tomorrow = datetime.now() + timedelta(days=1)
        schedule_time = tomorrow.replace(
            hour=18, minute=0, second=0, microsecond=0
        )
        publish_at = schedule_time.isoformat()

        result = self._publisher.schedule(
            video_path=video_data["video_path"],
            publish_at=publish_at,
            title=video_data["script"].get("title", ""),
            description=video_data["script"].get("description", ""),
            tags=video_data["script"].get("tags", []),
            is_ai_generated=True,
        )

        if result["success"]:
            self.db.update_video(
                video_data["video_id"],
                youtube_video_id=result.get("video_id", ""),
                status="scheduled",
                publish_at=schedule_time
            )
            self.db.log_publish(
                video_data["video_id"],
                "youtube", "success",
                video_url=f"https://youtube.com/watch?v={result.get('video_id', '')}"
            )
            self.notifier.send(
                f"Video scheduled for publication:\n"
                f"Title: {video_data['script'].get('title', '')}\n"
                f"Scheduled: {publish_at}\n"
                f"URL: https://youtube.com/watch?v={result.get('video_id', '')}"
            )
        else:
            self.db.update_video(video_data["video_id"], status="failed")
            self.db.log_publish(
                video_data["video_id"],
                "youtube", "failed",
                error_message=result.get("error", "Unknown error")
            )
            self.notifier.send(
                f"Video publication FAILED:\n"
                f"Error: {result.get('error', 'Unknown')}"
            )
