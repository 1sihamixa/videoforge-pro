"""
Database manager for AutoSystem.
Handles all CRUD operations against the SQLite database.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

import config.settings as settings
from database.models import (
    Base, Channel, Topic, Video, PublishingLog,
    QualityReport, PersonaUsage, APIQuotaUsage,
    TopicStatus, VideoStatus
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages all database operations for AutoSystem."""

    def __init__(self, db_path: Optional[str] = None):
        path = db_path or str(settings.DB_FULL_PATH)
        self.engine = create_engine(f"sqlite:///{path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionFactory = sessionmaker(bind=self.engine)
        logger.info(f"Database initialized at {path}")

    def _session(self) -> Session:
        return self.SessionFactory()

    # ---- Channels ----

    def create_channel(
        self, channel_id: str, name: str,
        content_style: str = "faceless", niche: str = "finance_invest"
    ) -> Channel:
        with self._session() as session:
            existing = session.query(Channel).filter_by(channel_id=channel_id).first()
            if existing:
                logger.warning(f"Channel {channel_id} already exists, returning existing")
                return existing
            ch = Channel(
                channel_id=channel_id, name=name,
                content_style=content_style, niche=niche
            )
            session.add(ch)
            session.commit()
            session.refresh(ch)
            logger.info(f"Created channel: {name} ({channel_id})")
            return ch

    def get_channel(self, channel_id: str) -> Optional[Channel]:
        with self._session() as session:
            return session.query(Channel).filter_by(channel_id=channel_id).first()

    def get_active_channels(self) -> List[Channel]:
        with self._session() as session:
            return session.query(Channel).filter_by(is_active=True).all()

    def list_channels(self) -> List[Channel]:
        with self._session() as session:
            return session.query(Channel).all()

    # ---- Topics ----

    def save_topic(self, keyword: str, niche: str, search_volume: int,
                   competition_score: float, estimated_cpm: float,
                   final_score: float, notes: str = "") -> Topic:
        with self._session() as session:
            existing = session.query(Topic).filter_by(
                keyword=keyword, niche=niche
            ).first()
            if existing:
                existing.search_volume = search_volume
                existing.competition_score = competition_score
                existing.estimated_cpm = estimated_cpm
                existing.final_score = final_score
                existing.notes = notes
                existing.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(existing)
                return existing
            topic = Topic(
                keyword=keyword, niche=niche,
                search_volume=search_volume,
                competition_score=competition_score,
                estimated_cpm=estimated_cpm,
                final_score=final_score,
                notes=notes
            )
            session.add(topic)
            session.commit()
            session.refresh(topic)
            return topic

    def get_approved_topics(self, niche: Optional[str] = None) -> List[Topic]:
        with self._session() as session:
            q = session.query(Topic).filter_by(status=TopicStatus.APPROVED.value)
            if niche:
                q = q.filter_by(niche=niche)
            return q.order_by(Topic.final_score.desc()).all()

    def get_top_unprocessed_topic(self, niche: Optional[str] = None) -> Optional[Topic]:
        """Get the highest-scored approved topic that has no completed video yet."""
        with self._session() as session:
            q = session.query(Topic).filter_by(status=TopicStatus.APPROVED.value)
            if niche:
                q = q.filter_by(niche=niche)
            approved = q.order_by(Topic.final_score.desc()).all()
            for topic in approved:
                video_exists = session.query(Video).filter_by(
                    topic_id=topic.id
                ).filter(Video.status.in_([
                    VideoStatus.PUBLISHED.value,
                    VideoStatus.SCHEDULED.value,
                    VideoStatus.REVIEWING.value
                ])).first()
                if not video_exists:
                    return topic
            return None

    def update_topic_status(self, topic_id: int, status: str) -> bool:
        with self._session() as session:
            topic = session.query(Topic).get(topic_id)
            if not topic:
                return False
            topic.status = status
            topic.updated_at = datetime.utcnow()
            session.commit()
            return True

    def list_topics(self, status: Optional[str] = None, limit: int = 50) -> List[Topic]:
        with self._session() as session:
            q = session.query(Topic)
            if status:
                q = q.filter_by(status=status)
            return q.order_by(Topic.final_score.desc()).limit(limit).all()

    # ---- Videos ----

    def create_video(self, channel_id: int, topic_id: int,
                     title: str = "", description: str = "",
                     tags: str = "", style: str = "faceless") -> Video:
        with self._session() as session:
            video = Video(
                channel_id=channel_id, topic_id=topic_id,
                title=title, description=description,
                tags=tags, style=style,
                status=VideoStatus.DRAFT.value
            )
            session.add(video)
            session.commit()
            session.refresh(video)
            logger.info(f"Created video record id={video.id} for topic_id={topic_id}")
            return video

    def update_video(self, video_id: int, **kwargs) -> bool:
        with self._session() as session:
            video = session.query(Video).get(video_id)
            if not video:
                return False
            for key, value in kwargs.items():
                if hasattr(video, key):
                    setattr(video, key, value)
            video.updated_at = datetime.utcnow()
            session.commit()
            return True

    def get_video(self, video_id: int) -> Optional[Video]:
        with self._session() as session:
            return session.query(Video).get(video_id)

    def get_videos_by_status(self, status: str) -> List[Video]:
        with self._session() as session:
            return session.query(Video).filter_by(status=status).all()

    def list_videos(self, status: Optional[str] = None,
                    channel_id: Optional[int] = None, limit: int = 50) -> List[Video]:
        with self._session() as session:
            q = session.query(Video)
            if status:
                q = q.filter_by(status=status)
            if channel_id:
                q = q.filter_by(channel_id=channel_id)
            return q.order_by(Video.created_at.desc()).limit(limit).all()

    # ---- Publishing Log ----

    def log_publish(self, video_id: int, platform: str, status: str,
                    video_url: str = "", error_message: str = "") -> PublishingLog:
        with self._session() as session:
            log = PublishingLog(
                video_id=video_id, platform=platform,
                status=status, video_url=video_url,
                error_message=error_message
            )
            session.add(log)
            session.commit()
            session.refresh(log)
            return log

    def get_publishing_logs(self, video_id: Optional[int] = None,
                            limit: int = 50) -> List[PublishingLog]:
        with self._session() as session:
            q = session.query(PublishingLog)
            if video_id:
                q = q.filter_by(video_id=video_id)
            return q.order_by(PublishingLog.published_at.desc()).limit(limit).all()

    # ---- Quality Reports ----

    def save_quality_report(self, video_id: int, **checks) -> QualityReport:
        with self._session() as session:
            report = QualityReport(video_id=video_id, **checks)
            session.add(report)
            session.commit()
            session.refresh(report)
            return report

    def get_quality_report(self, video_id: int) -> Optional[QualityReport]:
        with self._session() as session:
            return session.query(QualityReport).filter_by(video_id=video_id).first()

    # ---- Persona Usage ----

    def get_persona_index(self, channel_id: int) -> int:
        with self._session() as session:
            usage = session.query(PersonaUsage).filter_by(channel_id=channel_id).first()
            if not usage:
                return -1
            return usage.last_image_index

    def update_persona_index(self, channel_id: int, index: int, total: int) -> None:
        with self._session() as session:
            usage = session.query(PersonaUsage).filter_by(channel_id=channel_id).first()
            if not usage:
                usage = PersonaUsage(
                    channel_id=channel_id,
                    last_image_index=index,
                    total_images=total
                )
                session.add(usage)
            else:
                usage.last_image_index = index
                usage.total_images = total
                usage.updated_at = datetime.utcnow()
            session.commit()

    # ---- API Quota ----

    def get_quota_usage(self, platform: str, date_str: str) -> int:
        with self._session() as session:
            record = session.query(APIQuotaUsage).filter_by(
                platform=platform, date=date_str
            ).first()
            return record.units_used if record else 0

    def add_quota_usage(self, platform: str, date_str: str, units: int) -> int:
        with self._session() as session:
            record = session.query(APIQuotaUsage).filter_by(
                platform=platform, date=date_str
            ).first()
            if not record:
                record = APIQuotaUsage(
                    platform=platform, date=date_str,
                    units_used=units
                )
                session.add(record)
            else:
                record.units_used += units
                record.updated_at = datetime.utcnow()
            session.commit()
            return record.units_used

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        with self._session() as session:
            return {
                "total_topics": session.query(Topic).count(),
                "approved_topics": session.query(Topic).filter_by(
                    status=TopicStatus.APPROVED.value).count(),
                "total_videos": session.query(Video).count(),
                "published_videos": session.query(Video).filter_by(
                    status=VideoStatus.PUBLISHED.value).count(),
                "scheduled_videos": session.query(Video).filter_by(
                    status=VideoStatus.SCHEDULED.value).count(),
                "failed_videos": session.query(Video).filter_by(
                    status=VideoStatus.FAILED.value).count(),
                "total_channels": session.query(Channel).count(),
            }
