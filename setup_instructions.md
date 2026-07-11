# AutoSystem - Setup Instructions

## Overview
AutoSystem is a semi-automated video content production and publishing system for social media platforms. It researches trending topics, generates scripts via Claude AI, creates videos with TTS voiceover and stock footage, and publishes to YouTube.

## Prerequisites

### System Requirements
- **Python 3.10+**
- **FFmpeg** installed and in PATH
  - Windows: Download from https://ffmpeg.org/download.html, add to PATH
  - Or install via: `winget install FFmpeg`
- **Git** (for cloning)

### Optional: GPU for Avatar Mode
If you want avatar_talking videos (Wav2Lip):
- NVIDIA GPU with CUDA support
- PyTorch with CUDA: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`

## Step 1: Install Python Dependencies

```bash
cd C:\autosystem
pip install -r requirements.txt
```

## Step 2: Configure API Keys

Copy the example environment file and fill in your keys:

```bash
copy .env.example .env
```

Then edit `.env` with your actual API keys:

### Getting Each API Key

#### 1. Anthropic (Claude API)
- Go to https://console.anthropic.com/
- Create an account or sign in
- Go to API Keys section
- Create a new API key
- Set `ANTHROPIC_API_KEY=sk-ant-...` in `.env`

#### 2. YouTube Data API v3 (OAuth2)
- Go to https://console.cloud.google.com/
- Create a new project or select existing
- Enable "YouTube Data API v3"
- Go to Credentials > Create Credentials > OAuth 2.0 Client ID
- Set application type to "Desktop app"
- Download credentials
- Set `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET` in `.env`
- For initial token generation, run: `python -c "from publish.youtube_publisher import YouTubePublisher; YouTubePublisher()"`

#### 3. Pexels API
- Go to https://www.pexels.com/api/
- Create a free account
- Get your API key
- Set `PEXELS_API_KEY=...` in `.env`

#### 4. Pixabay API
- Go to https://pixabay.com/api/docs/
- Register for free
- Get your API key
- Set `PIXABAY_API_KEY=...` in `.env`

#### 5. Telegram Bot (Optional)
- Open Telegram, search for @BotFather
- Create a new bot with /newbot
- Get the bot token
- Get your chat ID (message the bot, then visit https://api.telegram.org/bot<TOKEN>/getUpdates)
- Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`

## Step 3: Initialize Database

The database is created automatically on first run. No manual setup needed.

## Step 4: Add Channels

### Option A: Via Dashboard
1. Start dashboard: `python run_dashboard.py`
2. Open http://localhost:8000
3. Go to Channels tab
4. Add your YouTube channel with Channel ID

### Option B: Via Code
```python
from database.db_manager import DatabaseManager
db = DatabaseManager()
db.create_channel("UCxxxxxxxx", "My Channel", "faceless", "finance_invest")
```

## Step 5: Run

### Manual Single Run (Testing)
```bash
python main.py
```

### Dashboard Only
```bash
python run_dashboard.py
```
Open http://localhost:8000

### Scheduler (Automatic Runs)
```bash
python run_scheduler.py
```
Runs pipeline every 24 hours (configurable in `.env`).

### Run Everything
Open 3 terminals:
```bash
# Terminal 1: Dashboard
python run_dashboard.py

# Terminal 2: Scheduler
python run_scheduler.py
```

## Configuration Options (in .env)

| Variable | Default | Description |
|---|---|---|
| `AUTO_PUBLISH` | `false` | Auto-publish after quality check |
| `TTS_ENGINE` | `edge-tts` | TTS engine (`edge-tts` or `elevenlabs`) |
| `TTS_VOICE_POOL` | `en-US-AriaNeural,...` | Comma-separated voice names |
| `DEFAULT_VIDEO_STYLE` | `faceless` | `faceless` or `avatar_talking` |
| `SCHEDULER_FREQUENCY_HOURS` | `24` | Hours between pipeline runs |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DASHBOARD_PORT` | `8000` | Dashboard web port |

## Avatar Mode (Optional)

To enable avatar_talking videos:

1. Place face images in `content/persona_assets/<channel_id>/`
2. Ensure GPU is available (run `python -c "import torch; print(torch.cuda.is_available())"`)
3. Ensure Wav2Lip checkpoint exists at `Wav2Lip/checkpoints/wav2lip_gan.pth`
4. Set `DEFAULT_VIDEO_STYLE=avatar_talking` in `.env`

**Important**: You are responsible for ensuring persona images are owned by you or properly licensed.

## Troubleshooting

### "ModuleNotFoundError"
Run: `pip install -r requirements.txt`

### "ffmpeg not found"
Install FFmpeg and ensure it's in your system PATH.

### YouTube API Quota Exceeded
The system tracks API quota automatically. Wait until midnight (UTC) for quota reset.

### Edge-TTS Connection Error
Check internet connection. Edge-TTS requires network access to Microsoft servers.

### Dashboard shows "No channels configured"
Add a channel via the dashboard Channels tab or via code.
