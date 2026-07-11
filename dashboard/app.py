"""
Dashboard application using FastAPI.
Bilingual (Arabic/English) web interface for managing content pipeline.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config.settings as settings
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

app = FastAPI(title="AutoSystem Dashboard")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
db = DatabaseManager()


def _get_orchestrator():
    """Lazy import of PipelineOrchestrator to avoid heavy deps at startup."""
    from pipeline.orchestrator import PipelineOrchestrator
    return PipelineOrchestrator()


def _base_context(**extra):
    """Build base template context with stats always present."""
    ctx = {"stats": db.get_stats(), "auto_publish": settings.AUTO_PUBLISH}
    ctx.update(extra)
    return ctx


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse(
        request=request, name="index.html",
        context=_base_context(
            channels=db.list_channels(),
            videos=db.list_videos(limit=20),
            topics=db.list_topics(limit=20),
        ),
    )


@app.get("/channels", response_class=HTMLResponse)
async def channels(request: Request):
    """Channels management page."""
    return templates.TemplateResponse(
        request=request, name="index.html",
        context=_base_context(
            view="channels",
            channels=db.list_channels(),
        ),
    )


@app.post("/channels/add")
async def add_channel(
    channel_id: str = Form(...),
    name: str = Form(...),
    content_style: str = Form("faceless"),
    niche: str = Form("finance_invest"),
):
    """Add a new channel."""
    db.create_channel(channel_id, name, content_style, niche)
    return RedirectResponse("/channels", status_code=303)


@app.get("/topics", response_class=HTMLResponse)
async def topics(request: Request, status: Optional[str] = Query(None)):
    """Topics list page."""
    return templates.TemplateResponse(
        request=request, name="index.html",
        context=_base_context(
            view="topics",
            topics=db.list_topics(status=status),
            current_status=status,
        ),
    )


@app.post("/topics/{topic_id}/approve")
async def approve_topic(topic_id: int):
    """Approve a topic for content generation."""
    db.update_topic_status(topic_id, "approved")
    return RedirectResponse("/topics", status_code=303)


@app.post("/topics/{topic_id}/reject")
async def reject_topic(topic_id: int):
    """Reject a topic."""
    db.update_topic_status(topic_id, "rejected")
    return RedirectResponse("/topics", status_code=303)


@app.get("/videos", response_class=HTMLResponse)
async def videos(request: Request, status: Optional[str] = Query(None)):
    """Videos list page."""
    return templates.TemplateResponse(
        request=request, name="index.html",
        context=_base_context(
            view="videos",
            videos=db.list_videos(status=status),
            current_status=status,
        ),
    )


@app.post("/videos/{video_id}/publish")
async def publish_video(video_id: int):
    """Manually trigger video publication."""
    video = db.get_video(video_id)
    if not video:
        return RedirectResponse("/videos", status_code=303)

    orchestrator = _get_orchestrator()
    orchestrator._do_publish({
        "video_id": video.id,
        "video_path": video.file_path,
        "script": {
            "title": video.title,
            "description": video.description,
            "tags": video.tags.split(",") if video.tags else [],
        },
        "style": video.style,
    })
    return RedirectResponse("/videos", status_code=303)


@app.post("/videos/{video_id}/approve")
async def approve_video(video_id: int):
    """Approve video for publication (when AUTO_PUBLISH=False)."""
    db.update_video(video_id, status="reviewed")
    return RedirectResponse("/videos", status_code=303)


@app.post("/videos/{video_id}/reject")
async def reject_video(video_id: int):
    """Reject a video."""
    db.update_video(video_id, status="failed")
    return RedirectResponse("/videos", status_code=303)


@app.get("/videos/{video_id}/stream")
async def stream_video(video_id: int):
    """Serve a video file for playback."""
    video = db.get_video(video_id)
    if not video or not video.file_path:
        return RedirectResponse("/", status_code=303)
    video_path = video.file_path
    if not os.path.isabs(video_path):
        video_path = str(Path(__file__).parent.parent / video_path)
    if not os.path.exists(video_path):
        return RedirectResponse("/", status_code=303)
    return FileResponse(video_path, media_type="video/mp4", filename=os.path.basename(video_path))


@app.get("/api/stats")
async def api_stats():
    """API endpoint for stats."""
    return db.get_stats()


@app.get("/api/videos")
async def api_videos(status: Optional[str] = None):
    """API endpoint for videos."""
    videos = db.list_videos(status=status)
    return [
        {
            "id": v.id,
            "title": v.title,
            "status": v.status,
            "file_path": v.file_path,
            "youtube_video_id": v.youtube_video_id,
            "created_at": str(v.created_at),
        }
        for v in videos
    ]


@app.post("/pipeline/run")
async def run_pipeline():
    """Trigger a pipeline run manually."""
    orchestrator = _get_orchestrator()
    orchestrator.run()
    return RedirectResponse("/", status_code=303)
