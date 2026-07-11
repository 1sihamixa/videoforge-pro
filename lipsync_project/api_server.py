#!/usr/bin/env python3
"""
FastAPI server for Wav2Lip lip-sync video generation.

Usage:
    python api_server.py
    # POST /generate with multipart form: face=<file>, audio=<file>

    # Or with JSON:
    # POST /generate/json -d '{"face_path": "...", "audio_path": "..."}'
"""
import os
import sys
import uuid
import logging
import shutil
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from lipsync import LipSyncPipeline

app = FastAPI(title="Wav2Lip Lip-Sync API", version="1.0.0")

BASE_DIR = Path(__file__).parent.absolute()
STATIC_DIR = BASE_DIR / "static"
VIDEOS_DIR = STATIC_DIR / "videos"
TEMP_DIR = BASE_DIR / "temp"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files for serving generated videos
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Pipeline instance (lazy-loaded)
_pipeline = None


def get_pipeline() -> LipSyncPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = LipSyncPipeline()
    return _pipeline


@app.get("/")
def root():
    return {
        "name": "Wav2Lip Lip-Sync API",
        "version": "1.0.0",
        "endpoints": {
            "POST /generate": "Upload face and audio files (multipart/form-data)",
            "POST /generate/json": "Generate from local file paths (JSON body)",
            "GET /video/{filename}": "Serve generated video file",
            "GET /health": "Health check"
        }
    }


@app.get("/health")
def health():
    cuda = False
    try:
        import torch
        cuda = torch.cuda.is_available()
    except ImportError:
        pass
    return {
        "status": "ok",
        "device": "cuda" if cuda else "cpu",
        "checkpoint_exists": os.path.exists(
            os.path.join(BASE_DIR, "..", "Wav2Lip", "checkpoints", "wav2lip_gan.pth")
        ) or os.path.exists(os.path.join(BASE_DIR, "checkpoints", "wav2lip_gan.pth"))
    }


@app.post("/generate", summary="Upload face + audio and generate lip-sync video")
async def generate_upload(
    face: UploadFile = File(..., description="Face image or video file"),
    audio: UploadFile = File(..., description="Audio file (mp3/wav)"),
    enhance: bool = Form(False, description="Apply GFPGAN face enhancement"),
    fps: int = Form(25, description="Output frame rate"),
):
    # Validate file types
    face_ext = os.path.splitext(face.filename or "")[1].lower()
    audio_ext = os.path.splitext(audio.filename or "")[1].lower()
    valid_face = (".jpg", ".jpeg", ".png", ".bmp", ".mp4", ".avi", ".mov", ".mkv")
    valid_audio = (".mp3", ".wav", ".m4a", ".aac", ".ogg")

    if face_ext not in valid_face:
        raise HTTPException(400, f"Unsupported face file format: {face_ext}")
    if audio_ext not in valid_audio:
        raise HTTPException(400, f"Unsupported audio file format: {audio_ext}")

    # Save uploaded files to temp
    uid = uuid.uuid4().hex[:8]
    face_path = TEMP_DIR / f"face_{uid}{face_ext}"
    audio_path = TEMP_DIR / f"audio_{uid}{audio_ext}"

    try:
        with open(face_path, "wb") as f:
            shutil.copyfileobj(face.file, f)
        with open(audio_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)
    except Exception as e:
        raise HTTPException(500, f"Failed to save uploaded files: {e}")
    finally:
        face.file.close()
        audio.file.close()

    # Run pipeline
    try:
        pipeline = get_pipeline()
        output_path, error = pipeline.generate(
            face_path=str(face_path),
            audio_path=str(audio_path),
            enable_enhancement=enhance,
            fps=fps,
        )
    except Exception as e:
        error = str(e)
        output_path = None

    # Cleanup temp files
    for p in [face_path, audio_path]:
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    if error:
        raise HTTPException(500, detail=error)

    # Return download link
    rel_path = os.path.relpath(str(output_path), str(STATIC_DIR))
    download_url = f"/static/{rel_path.replace(os.sep, '/')}"
    return {
        "success": True,
        "video_url": download_url,
        "filename": os.path.basename(str(output_path)),
        "filesize": os.path.getsize(str(output_path)),
    }


@app.post("/generate/json", summary="Generate from local file paths")
async def generate_json(
    face_path: str = Form(..., description="Absolute path to face image/video"),
    audio_path: str = Form(..., description="Absolute path to audio file"),
    enhance: bool = Form(False),
    fps: int = Form(25),
):
    if not os.path.exists(face_path):
        raise HTTPException(400, f"Face file not found: {face_path}")
    if not os.path.exists(audio_path):
        raise HTTPException(400, f"Audio file not found: {audio_path}")

    pipeline = get_pipeline()
    output_path, error = pipeline.generate(
        face_path=face_path,
        audio_path=audio_path,
        enable_enhancement=enhance,
        fps=fps,
    )

    if error:
        raise HTTPException(500, detail=error)

    rel_path = os.path.relpath(str(output_path), str(STATIC_DIR))
    download_url = f"/static/{rel_path.replace(os.sep, '/')}"
    return {
        "success": True,
        "video_url": download_url,
        "filename": os.path.basename(str(output_path)),
        "filesize": os.path.getsize(str(output_path)),
    }


@app.get("/video/{filename:path}")
def serve_video(filename: str):
    file_path = VIDEOS_DIR / filename
    if not file_path.exists():
        raise HTTPException(404, "Video not found")
    return FileResponse(str(file_path), media_type="video/mp4",
                        filename=filename,
                        headers={"Content-Disposition": f"inline; filename={filename}"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
