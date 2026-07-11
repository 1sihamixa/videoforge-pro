"""
Job scheduler using APScheduler.
Orchestrates periodic pipeline runs per channel.
"""

import logging
from datetime import datetime
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config.settings as settings

logger = logging.getLogger(__name__)


class JobScheduler:
    """Manages scheduled pipeline runs using APScheduler."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._running = False
        logger.info("JobScheduler initialized")

    def start_pipeline_job(self, pipeline_func: Callable,
                           channel_id: Optional[str] = None,
                           interval_hours: int = None):
        """
        Schedule a pipeline job to run at regular intervals.

        Args:
            pipeline_func: Function to call each cycle
            channel_id: Optional channel ID to filter
            interval_hours: Override default frequency
        """
        hours = interval_hours or settings.SCHEDULER_FREQUENCY_HOURS
        job_id = f"pipeline_{channel_id or 'all'}"

        # Remove existing job with same ID
        existing = self.scheduler.get_job(job_id)
        if existing:
            self.scheduler.remove_job(job_id)

        self.scheduler.add_job(
            func=self._run_pipeline,
            trigger=IntervalTrigger(hours=hours),
            args=[pipeline_func, channel_id],
            id=job_id,
            name=f"Pipeline: {channel_id or 'all channels'}",
            replace_existing=True,
        )
        logger.info(
            f"Scheduled pipeline job '{job_id}' every {hours}h"
        )

    def _run_pipeline(self, pipeline_func: Callable,
                      channel_id: Optional[str] = None):
        """Execute a pipeline run with error handling."""
        start = datetime.now()
        logger.info(f"Pipeline started: channel={channel_id}, time={start}")
        try:
            pipeline_func(channel_id=channel_id)
            elapsed = (datetime.now() - start).total_seconds()
            logger.info(f"Pipeline completed in {elapsed:.1f}s")
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)

    def start(self):
        """Start the scheduler."""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown()
            self._running = False
            logger.info("Scheduler stopped")

    def list_jobs(self) -> list:
        """List all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
            })
        return jobs

    def run_now(self, pipeline_func: Callable,
                channel_id: Optional[str] = None):
        """Immediately run a pipeline job (for testing)."""
        self._run_pipeline(pipeline_func, channel_id)
