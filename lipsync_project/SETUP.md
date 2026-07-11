# Wav2Lip Lip-Sync Project - Setup Guide

## Project Structure

```
lipsync_project/
├── config.yaml              # Configuration file
├── requirements.txt         # Python dependencies
├── generate.py              # CLI entry point
├── api_server.py            # FastAPI server
├── test_run.py              # Quick test script
├── lipsync/
│   ├── __init__.py
│   ├── pipeline.py          # Main pipeline orchestrator
│   ├── inference.py         # Wav2Lip model inference
│   ├── audio_utils.py       # Audio processing utilities
│   ├── video_utils.py       # Video processing utilities
│   └── enhancement.py       # GFPGAN optional enhancement
├── checkpoints/             # Model weights (auto-downloaded)
├── static/videos/           # Output video directory
├── temp/                    # Temporary working files
└── samples/                 # Sample input files
```

## Setup Instructions (Windows)

### 1. Install Python 3.8+ and FFmpeg

```powershell
# Check Python
python --version

# Check FFmpeg
ffmpeg -version
```

If FFmpeg is not installed, download from https://ffmpeg.org/download.html and add to PATH.

### 2. Create Virtual Environment (Recommended)

```powershell
cd C:\autosystem\lipsync_project
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Download Wav2Lip Checkpoint

The checkpoint will auto-download on first run, or manually:
```powershell
python -c "from lipsync.pipeline import download_checkpoint; download_checkpoint('checkpoints/wav2lip_gan.pth')"
```

The project also detects the existing checkpoint at `C:\autosystem\Wav2Lip\checkpoints\wav2lip_gan.pth`.

## Usage

### CLI (Command Line)

```powershell
# Basic usage with image
python generate.py --face samples\face.jpg --audio samples\audio.mp3

# With video input
python generate.py --face input_video.mp4 --audio speech.mp3

# With GFPGAN enhancement
python generate.py --face face.jpg --audio speech.mp3 --enhance

# Custom output directory
python generate.py --face face.jpg --audio speech.mp3 --output-dir C:\my_videos

# Custom face detection padding
python generate.py --face face.jpg --audio speech.mp3 --pads 30 20 20 20

# Change output frame rate
python generate.py --face face.jpg --audio speech.mp3 --fps 30
```

### API Server

```powershell
# Start the FastAPI server
python api_server.py

# Server runs on http://localhost:8000
# API docs at http://localhost:8000/docs
```

**API Endpoints:**

- `POST /generate` - Upload face and audio files (multipart form)
  ```powershell
  curl -X POST http://localhost:8000/generate ^
    -F "face=@face.jpg" ^
    -F "audio=@speech.mp3" ^
    -F "enhance=false" ^
    -F "fps=25"
  ```

- `POST /generate/json` - Generate from local file paths
  ```powershell
  curl -X POST http://localhost:8000/generate/json ^
    -H "Content-Type: application/json" ^
    -d "{\"face_path\":\"C:/face.jpg\",\"audio_path\":\"C:/audio.mp3\"}"
  ```

- `GET /video/{filename}` - Serve generated video

### Test

```powershell
# Download samples and run test
python test_run.py

# Test with custom files
python test_run.py --face my_face.jpg --audio my_audio.mp3

# Test with enhancement
python test_run.py --enhance
```

## Model Replacement Guide

To replace Wav2Lip with a newer model:

1. Place the new model checkpoint in `checkpoints/` directory
2. Modify `lipsync/inference.py`:
   - Update `load_model()` to load the new model architecture
   - Update the `run_inference()` function if the new model has different input/output format
3. Update the checkpoint path in `config.yaml` or via `--checkpoint` flag

### Alternative Models

| Model | Pros | Cons |
|-------|------|------|
| **Wav2Lip** | Fast, accurate lip-sync | Low resolution mouth region, needs enhancement |
| **Wav2Lip-HD** | Better quality (GAN), 720p | Heavier, slower |
| **SadTalker** | Full head animation, 512x512 | Doesn't handle video input, slower |
| **VideoReTalking** | Full face restoration | Complex setup, needs multiple models |
| **MuseTalk** | Real-time, high quality | Requires GPU, new/less tested |

To use SadTalker instead:
```python
# In pipeline.py, replace the inference call:
# from sadtalker import SadTalker
# result = sadtalker.generate(face_path, audio_path)
```

## Output

- Videos saved to: `static/videos/wav2lip_alternate_<uuid>.mp4`
- Default resolution: 1920x1080
- Default frame rate: 25 fps
- Video codec: H.264 (libx264) CRF 18
- Audio codec: AAC 128kbps
