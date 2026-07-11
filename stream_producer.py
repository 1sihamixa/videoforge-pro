#!/usr/bin/env python3
"""
Stream Producer Pro v1.0
برنامج مستقل لصناعة ونشر البثوث المباشرة (STREAMS) على منصات التواصل الاجتماعي
يدعم: YouTube Live, Facebook Live, Twitch
"""
import os, sys, json, re, random, uuid, subprocess, threading, time, shutil, io, socket
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "stream_workspace")
os.makedirs(TEMP_DIR, exist_ok=True)
for sub in ["thumbnails", "overlays", "scheduled", "logs"]:
    os.makedirs(os.path.join(TEMP_DIR, sub), exist_ok=True)

SCHEDULE_FILE = os.path.join(TEMP_DIR, "stream_schedule.json")
STREAM_LOG = os.path.join(TEMP_DIR, "stream_log.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
FFMPEG_PATH = "ffmpeg"

# قوالب عناوين ونصوص البثوث
STREAM_CATEGORIES = {
    "educational": {
        "titles": [
            "بث مباشر: {topic} - شرح كامل ومباشر",
            "تعلم {topic} في بث مباشر مع الخبراء",
            "{topic} - جلسة تعليمية مفتوحة",
            "مباشر: كل ما تريد معرفته عن {topic}",
        ],
        "descriptions": [
            "بث مباشر تعليمي شامل عن {topic}\n\n"
            "في هذا البث المباشر سنغطي:\n"
            "• المفاهيم الأساسية\n"
            "• تطبيقات عملية\n"
            "• إجابات على أسئلتكم\n\n"
            "انضموا إلينا مباشرة واطرحوا أسئلتكم في التعليقات\n\n"
            "#بث_مباشر #{topic_slug} #تعليم #مباشر",
        ],
    },
    "entertainment": {
        "titles": [
            "بث مباشر: {topic} - لن تصدق ما سيحدث!",
            "مباشر مع المشتركين: {topic}",
            "{topic} - بث حصري ومباشر",
            "لا يفوتك: {topic} بث مباشر الليلة",
        ],
        "descriptions": [
            "بث مباشر ترفيهي: {topic}\n\n"
            "انضموا إلينا في هذا البث المباشر الممتع\n"
            "ننتظر تفاعلكم وتعليقاتكم\n\n"
            "شاركوا البث مع أصدقائكم\n\n"
            "#بث_مباشر #{topic_slug} #ترفيه #مباشر",
        ],
    },
    "talk": {
        "titles": [
            "بث مباشر: حوار مفتوح عن {topic}",
            "تعالوا نتكلم عن {topic} - بث مباشر",
            "{topic} - رأيكم يهمنا | بث مباشر",
            "نقاش مباشر: {topic} مع المشتركين",
        ],
        "descriptions": [
            "بث مباشر - حوار ونقاش عن {topic}\n\n"
            "مواضيع النقاش:\n"
            "• رأيكم في {topic}\n"
            "• تجاربكم الشخصية\n"
            "• أسئلة وأجوبة مفتوحة\n\n"
            "شاركونا آراءكم في التعليقات\n\n"
            "#بث_مباشر #{topic_slug} #نقاش #حوار",
        ],
    },
    "gaming": {
        "titles": [
            "بث مباشر: {topic} - العب مع المشتركين",
            "مباشر الآن: {topic}",
            "{topic} - بث مباشر وتحديات",
            "شاهدوني وأنا ألعب {topic} - بث مباشر",
        ],
        "descriptions": [
            "بث مباشر: {topic}\n\n"
            "انضموا للعب المباشر وتفاعلوا معنا\n"
            "تحديات وأسئلة أثناء البث\n\n"
            "اشتركوا وفعلوا الجرس\n\n"
            "#بث_مباشر #{topic_slug} #قيمنق #مباشر",
        ],
    },
}

# منصات البث المباشر المدعومة
PLATFORMS = {
    "youtube": {
        "name": "YouTube Live",
        "rtmp_template": "rtmp://a.rtmp.youtube.com/live2/{stream_key}",
        "url_template": "https://youtube.com/live/{stream_id}",
    },
    "facebook": {
        "name": "Facebook Live",
        "rtmp_template": "rtmp://live-api-s.facebook.com:80/rtmp/{stream_key}",
        "url_template": "https://facebook.com/live/{stream_id}",
    },
    "twitch": {
        "name": "Twitch",
        "rtmp_template": "rtmp://live.twitch.tv/app/{stream_key}",
        "url_template": "https://twitch.tv/{channel_name}",
    },
    "tiktok": {
        "name": "TikTok Live",
        "rtmp_template": "rtmp://live.tiktok.com/live/{stream_key}",
        "url_template": "https://tiktok.com/@channel/live",
    },
    "instagram": {
        "name": "Instagram Live",
        "rtmp_template": "rtmp://live-upload.instagram.com:443/rtmp/{stream_key}",
        "url_template": "https://instagram.com/{channel_name}/live",
    },
}

# قوالب الصور المصغرة
THUMBNAIL_TEMPLATES = {
    "default": {
        "overlay_text": "بث مباشر",
        "colors": [(200, 40, 40), (255, 100, 0)],
    },
    "educational": {
        "overlay_text": "بث تعليمي",
        "colors": [(20, 80, 180), (0, 150, 255)],
    },
    "gaming": {
        "overlay_text": "بث قيمنق",
        "colors": [(100, 20, 150), (200, 0, 100)],
    },
}

# ─── إدارة الإعدادات ───

def load_config():
    cfg = {
        "streams": {},
        "platforms": {},
        "default_duration": 60,
        "auto_stream": False,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                cfg.update({k: v for k, v in saved.items() if k in cfg or k.startswith("stream_")})
                if "streams" in saved:
                    cfg["streams"] = saved["streams"]
                if "platforms" in saved:
                    cfg["platforms"] = saved["platforms"]
        except:
            pass
    return cfg

def save_config(cfg):
    full = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                full = json.load(f)
        except:
            pass
    full["streams"] = cfg.get("streams", {})
    full["platforms"] = cfg.get("platforms", {})
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(full, f, ensure_ascii=False, indent=2)
    print(f"  تم حفظ إعدادات البث")

def load_schedule():
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"streams": [], "total": 0}

def save_schedule(data):
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_log():
    if os.path.exists(STREAM_LOG):
        try:
            with open(STREAM_LOG, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"streams": [], "total": 0}

def save_log(data):
    with open(STREAM_LOG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── توليد محتوى البث ───

def generate_stream_metadata(topic, category="educational"):
    vid_num = load_schedule().get("total", 0)
    rng = random.Random(vid_num * 9973 + 7)
    cats = STREAM_CATEGORIES.get(category, STREAM_CATEGORIES["educational"])
    title = rng.choice(cats["titles"]).format(topic=topic, topic_slug=topic.replace(" ", "_")[:20])
    desc = rng.choice(cats["descriptions"]).format(topic=topic, topic_slug=topic.replace(" ", "_")[:20])

    tags = [topic, topic.replace(" ", "_"), "بث مباشر", "مباشر", category, "محتوى عربي", "live stream"]
    schedule_time = datetime.now() + timedelta(minutes=30)
    estimated_duration = rng.randint(30, 120)
    return {
        "title": title,
        "description": desc,
        "tags": tags,
        "suggested_schedule": schedule_time.isoformat(),
        "estimated_minutes": estimated_duration,
        "category": category,
    }

# ─── إدارة البثوث المجدولة ───

def create_stream(topic, category="educational", platform=None, schedule_time=None):
    meta = generate_stream_metadata(topic, category)
    stream_id = uuid.uuid4().hex[:8]
    stream = {
        "id": stream_id,
        "topic": topic,
        "category": category,
        "title": meta["title"],
        "description": meta["description"],
        "tags": meta["tags"],
        "estimated_minutes": meta["estimated_minutes"],
        "created_at": datetime.now().isoformat(),
        "scheduled_for": schedule_time or meta["suggested_schedule"],
        "platforms": platform or ["youtube"],
        "status": "scheduled",
        "thumbnail": None,
        "stream_key": None,
        "rtmp_url": None,
        "started_at": None,
        "ended_at": None,
        "viewers_peak": 0,
    }
    schedule = load_schedule()
    schedule["streams"].append(stream)
    schedule["total"] = len(schedule["streams"])
    save_schedule(schedule)
    print(f"  تم إنشاء بث مباشر: {stream['title']}")
    print(f"  المعرف: {stream_id}")
    print(f"  الوقت: {stream['scheduled_for']}")
    return stream

def list_streams(status=None):
    schedule = load_schedule()
    streams = schedule.get("streams", [])
    if status:
        streams = [s for s in streams if s.get("status") == status]
    return streams

def get_stream(stream_id):
    schedule = load_schedule()
    for s in schedule.get("streams", []):
        if s["id"] == stream_id:
            return s
    return None

def delete_stream(stream_id):
    schedule = load_schedule()
    initial = len(schedule["streams"])
    schedule["streams"] = [s for s in schedule["streams"] if s["id"] != stream_id]
    if len(schedule["streams"]) < initial:
        schedule["total"] = len(schedule["streams"])
        save_schedule(schedule)
        print(f"  تم حذف البث {stream_id}")
        return True
    print(f"  البث {stream_id} غير موجود")
    return False

def update_stream(stream_id, updates):
    schedule = load_schedule()
    for s in schedule["streams"]:
        if s["id"] == stream_id:
            s.update(updates)
            save_schedule(schedule)
            print(f"  تم تحديث البث {stream_id}")
            return s
    return None

# ─── توليد الصور المصغرة للبث ───

def generate_thumbnail(title, category="default"):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  PIL غير متوفر - تخطي الصور المصغرة")
        return None
    vid_num = load_schedule().get("total", 0)
    uid = uuid.uuid4().hex[:8]
    font_paths = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
    ]
    font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 60)
                break
            except:
                pass
    if not font:
        font = ImageFont.load_default()
    thumb_data = THUMBNAIL_TEMPLATES.get(category, THUMBNAIL_TEMPLATES["default"])
    try:
        W, H = 1280, 720
        c1, c2 = thumb_data["colors"]
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)
        for row in range(H):
            r = row / H
            color = (int(c1[0] * (1 - r) + c2[0] * r),
                     int(c1[1] * (1 - r) + c2[1] * r),
                     int(c1[2] * (1 - r) + c2[2] * r))
            draw.line([(0, row), (W, row)], fill=color)
        draw.rectangle([(0, 0), (W, 80)], fill=(255, 50, 50))
        bb = draw.textbbox((0, 0), thumb_data["overlay_text"], font=font)
        draw.text(((W - (bb[2] - bb[0])) // 2, 15), thumb_data["overlay_text"], font=font, fill=(255, 255, 255))
        y = 200
        words = title.split()
        lines = []
        cur = ""
        for w in words:
            if len(cur) + len(w) + 1 <= 18:
                cur = (cur + " " + w).strip()
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        for line in lines[:3]:
            bb = draw.textbbox((0, 0), line, font=font)
            x = (W - (bb[2] - bb[0])) // 2
            draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0))
            draw.text((x, y), line, font=font, fill=(255, 255, 255))
            y += (bb[3] - bb[1]) + 10
        draw.rectangle([(W // 2 - 100, H - 120), (W // 2 + 100, H - 70)], fill=(255, 50, 50))
        bb = draw.textbbox((0, 0), "مباشر", font=font)
        draw.text(((W - (bb[2] - bb[0])) // 2, H - 115), "مباشر", font=font, fill=(255, 255, 255))
        out = os.path.join(TEMP_DIR, "thumbnails", f"stream_{uid}.jpg")
        img.save(out, "JPEG", quality=92)
        print(f"  صورة مصغرة: {out}")
        return out
    except Exception as e:
        print(f"  فشل توليد الصورة: {e}")
        return None

# ─── إدارة مفاتيح البث (Stream Keys) ───

def configure_platform(platform, **params):
    cfg = load_config()
    if "platforms" not in cfg:
        cfg["platforms"] = {}
    cfg["platforms"][platform] = params
    save_config(cfg)
    print(f"  تم إعداد {PLATFORMS.get(platform, {}).get('name', platform)}")

def get_rtmp_url(platform, stream_key, channel_name=""):
    platform_info = PLATFORMS.get(platform)
    if not platform_info:
        print(f"  المنصة {platform} غير مدعومة")
        return None, None
    rtmp = platform_info["rtmp_template"].format(stream_key=stream_key)
    url = platform_info["url_template"].format(stream_key=stream_key, channel_name=channel_name, stream_id=stream_key[:8])
    return rtmp, url

# ─── البث المباشر عبر FFmpeg ───

class StreamBroadcaster:
    def __init__(self):
        self.processes = {}
        self.running = threading.Event()

    def start_stream(self, stream_id, video_source, platforms_config):
        """بدء بث مباشر إلى منصة واحدة أو عدة منصات"""
        if stream_id in self.processes:
            print(f"  البث {stream_id} قيد التشغيل بالفعل")
            return False
        rtmg_urls = []
        for platform, config in platforms_config.items():
            if platform not in PLATFORMS:
                print(f"  {platform} غير مدعومة")
                continue
            rtmp, url = get_rtmp_url(platform, config.get("stream_key", ""), config.get("channel_name", ""))
            if rtmp:
                rtmg_urls.append((platform, rtmp, url))
        if not rtmg_urls:
            print("  لا توجد منصات صالحة للبث")
            return False
        print(f"  بدء البث إلى {len(rtmg_urls)} منصة...")
        threads = []
        for platform, rtmp, url in rtmg_urls:
            t = threading.Thread(target=self._broadcast_to_platform, args=(stream_id, video_source, rtmp, platform, url), daemon=True)
            t.start()
            threads.append(t)
        self.processes[stream_id] = {
            "platforms": rtmg_urls,
            "threads": threads,
            "started_at": datetime.now().isoformat(),
            "video_source": video_source,
        }
        return True

    def _broadcast_to_platform(self, stream_id, video_source, rtmp_url, platform, public_url):
        print(f"  بث إلى {PLATFORMS.get(platform, {}).get('name', platform)}...")
        log_file = os.path.join(TEMP_DIR, "logs", f"stream_{stream_id}_{platform}.log")
        cmd = [
            FFMPEG_PATH, "-re", "-i", video_source,
            "-c:v", "libx264", "-preset", "veryfast", "-b:v", "3000k",
            "-maxrate", "3000k", "-bufsize", "6000k",
            "-pix_fmt", "yuv420p", "-g", "60",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-f", "flv", "-flvflags", "no_duration_filesize",
            rtmp_url,
        ]
        with open(log_file, "w", encoding="utf-8") as log:
            proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, text=False)
            self.processes[stream_id][platform] = proc
            proc.wait()
        print(f"  انتهى البث إلى {PLATFORMS.get(platform, {}).get('name', platform)} (الكود: {proc.returncode})")

    def stop_stream(self, stream_id):
        if stream_id not in self.processes:
            print(f"  لا يوجد بث نشط بالمعرف {stream_id}")
            return False
        print(f"  إيقاف البث {stream_id}...")
        proc_info = self.processes[stream_id]
        for key, val in list(proc_info.items()):
            if isinstance(val, subprocess.Popen):
                try:
                    val.terminate()
                    val.wait(timeout=5)
                except:
                    try: val.kill()
                    except: pass
        del self.processes[stream_id]
        log_entry = load_log()
        log_entry["streams"].append({
            "id": stream_id,
            "stopped_at": datetime.now().isoformat(),
            "duration": str(datetime.now() - datetime.fromisoformat(proc_info.get("started_at", datetime.now().isoformat()))),
        })
        log_entry["total"] = len(log_entry["streams"])
        save_log(log_entry)
        print(f"  تم إيقاف البث {stream_id}")
        return True

    def stream_status(self, stream_id):
        return self.processes.get(stream_id)

broadcaster = StreamBroadcaster()

# ─── بث من ملف فيديو ───

def stream_video_file(video_path, stream_id=None, platforms_config=None, loop=False):
    if not os.path.exists(video_path):
        print(f"  ملف الفيديو غير موجود: {video_path}")
        return None
    if not stream_id:
        stream_id = uuid.uuid4().hex[:8]
    if not platforms_config:
        cfg = load_config()
        platforms_config = cfg.get("platforms", {})
    if not platforms_config:
        print("  لم يتم إعداد أي منصة. استخدم --configure أولاً")
        return None
    if loop:
        video_source = video_path
    else:
        video_source = video_path
    ok = broadcaster.start_stream(stream_id, video_source, platforms_config)
    if ok:
        update = {"status": "live", "started_at": datetime.now().isoformat(), "stream_key": list(platforms_config.values())[0].get("stream_key", "") if platforms_config else ""}
        update_stream(stream_id, update)
        print(f"  البث المباشر نشط: {stream_id}")
        print(f"  المصدر: {video_path}")
        for platform, config in platforms_config.items():
            _, url = get_rtmp_url(platform, config.get("stream_key", ""), config.get("channel_name", ""))
            if url:
                print(f"  {PLATFORMS.get(platform, {}).get('name', platform)}: {url}")
    return stream_id

# ─── بث الشاشة (Screen Capture) ───

def stream_screen(stream_id=None, platforms_config=None, region="desktop"):
    if not stream_id:
        stream_id = uuid.uuid4().hex[:8]
    if not platforms_config:
        cfg = load_config()
        platforms_config = cfg.get("platforms", {})
    if not platforms_config:
        print("  لم يتم إعداد أي منصة")
        return None
    rtmg_urls = []
    for platform, config in platforms_config.items():
        rtmp, url = get_rtmp_url(platform, config.get("stream_key", ""), config.get("channel_name", ""))
        if rtmp:
            rtmg_urls.append((platform, rtmp, url))
    if not rtmg_urls:
        return None
    print(f"  بدء بث الشاشة إلى {len(rtmg_urls)} منصة...")
    log_file = os.path.join(TEMP_DIR, "logs", f"screen_stream_{stream_id}.log")
    input_device = "desktop" if region == "desktop" else f"title={region}"
    threads = []
    for platform, rtmp, url in rtmg_urls:
        t = threading.Thread(target=_stream_screen_to, args=(stream_id, rtmp, platform, url, input_device, log_file), daemon=True)
        t.start()
        threads.append(t)
    broadcaster.processes[stream_id] = {"platforms": rtmg_urls, "threads": threads, "started_at": datetime.now().isoformat(), "type": "screen"}
    return stream_id

def _stream_screen_to(stream_id, rtmp_url, platform, public_url, input_device, log_file):
    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "gdigrab", "-framerate", "30",
        "-i", input_device,
        "-f", "dshow", "-i", "audio=virtual-audio-capturer",
        "-c:v", "libx264", "-preset", "veryfast", "-b:v", "3000k",
        "-maxrate", "3000k", "-bufsize", "6000k",
        "-pix_fmt", "yuv420p", "-g", "60",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-f", "flv", rtmp_url,
    ]
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n--- Screen stream to {platform} ---\n")
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        proc.wait()

# ─── بث مباشر من كاميرا الويب ───

def stream_webcam(stream_id=None, platforms_config=None):
    if not stream_id:
        stream_id = uuid.uuid4().hex[:8]
    if not platforms_config:
        cfg = load_config()
        platforms_config = cfg.get("platforms", {})
    if not platforms_config:
        print("  لم يتم إعداد أي منصة")
        return None
    rtmg_urls = []
    for platform, config in platforms_config.items():
        rtmp, url = get_rtmp_url(platform, config.get("stream_key", ""), config.get("channel_name", ""))
        if rtmp:
            rtmg_urls.append((platform, rtmp, url))
    if not rtmg_urls:
        return None
    print(f"  بدء بث الكاميرا إلى {len(rtmg_urls)} منصة...")
    log_file = os.path.join(TEMP_DIR, "logs", f"cam_stream_{stream_id}.log")
    threads = []
    for platform, rtmp, url in rtmg_urls:
        t = threading.Thread(target=_stream_webcam_to, args=(stream_id, rtmp, platform, url, log_file), daemon=True)
        t.start()
        threads.append(t)
    broadcaster.processes[stream_id] = {"platforms": rtmg_urls, "threads": threads, "started_at": datetime.now().isoformat(), "type": "webcam"}
    return stream_id

def _stream_webcam_to(stream_id, rtmp_url, platform, public_url, log_file):
    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "dshow", "-i", "video=HD Webcam",
        "-f", "dshow", "-i", "audio=virtual-audio-capturer",
        "-c:v", "libx264", "-preset", "veryfast", "-b:v", "2000k",
        "-maxrate", "2000k", "-bufsize", "4000k",
        "-pix_fmt", "yuv420p", "-g", "60",
        "-c:a", "aac", "-b:a", "96k", "-ar", "44100",
        "-f", "flv", rtmp_url,
    ]
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n--- Webcam stream to {platform} ---\n")
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        proc.wait()

# ─── إحصائيات البث ───

def stream_stats():
    schedule = load_schedule()
    log = load_log()
    active = len(broadcaster.processes)
    total_scheduled = schedule.get("total", 0)
    total_streamed = log.get("total", 0)
    return {
        "active_streams": active,
        "total_scheduled": total_scheduled,
        "total_streamed": total_streamed,
        "upcoming": len([s for s in schedule.get("streams", []) if s.get("status") == "scheduled"]),
        "live": len([s for s in schedule.get("streams", []) if s.get("status") == "live"]),
    }

# ─── معالج الإعداد ───

def setup_wizard():
    print("\n" + "=" * 50)
    print("  إعداد Stream Producer Pro")
    print("=" * 50)
    cfg = load_config()
    if "platforms" not in cfg:
        cfg["platforms"] = {}
    print("\n  [1] YouTube Live")
    key = input(f"  مفتاح البث (Stream Key) > {cfg['platforms'].get('youtube', {}).get('stream_key', '')} ").strip()
    if key: cfg["platforms"].setdefault("youtube", {})["stream_key"] = key
    print("\n  [2] Facebook Live")
    key = input(f"  مفتاح البث (Stream Key) > {cfg['platforms'].get('facebook', {}).get('stream_key', '')} ").strip()
    if key: cfg["platforms"].setdefault("facebook", {})["stream_key"] = key
    print("\n  [3] Twitch")
    key = input(f"  مفتاح البث (Stream Key) > {cfg['platforms'].get('twitch', {}).get('stream_key', '')} ").strip()
    if key: cfg["platforms"].setdefault("twitch", {})["stream_key"] = key
    ch = input(f"  اسم القناة > {cfg['platforms'].get('twitch', {}).get('channel_name', '')} ").strip()
    if ch: cfg["platforms"].setdefault("twitch", {})["channel_name"] = ch
    print("\n  [4] TikTok Live")
    key = input(f"  مفتاح البث (Stream Key) > {cfg['platforms'].get('tiktok', {}).get('stream_key', '')} ").strip()
    if key: cfg["platforms"].setdefault("tiktok", {})["stream_key"] = key
    print("\n  [5] Instagram Live")
    key = input(f"  مفتاح البث (Stream Key) > {cfg['platforms'].get('instagram', {}).get('stream_key', '')} ").strip()
    if key: cfg["platforms"].setdefault("instagram", {})["stream_key"] = key
    save_config(cfg)
    print("\n  ✅ تم إعداد المنصات بنجاح!")
    return cfg

# ─── معالج الأسئلة التفاعلي لإنشاء بث ───

def interactive_create():
    print("\n" + "=" * 50)
    print("  إنشاء بث مباشر جديد")
    print("=" * 50)
    topic = input("\n  موضوع البث: ").strip()
    if not topic:
        print("  الموضوع مطلوب")
        return None
    print("\n  التصنيفات:")
    cats = list(STREAM_CATEGORIES.keys())
    for i, c in enumerate(cats):
        print(f"  {i+1}. {c}")
    try:
        ci = int(input(f"  اختر تصنيف (1-{len(cats)}) [1]: ").strip() or "1") - 1
        category = cats[max(0, min(ci, len(cats)-1))]
    except:
        category = "educational"
    print("\n  المنصات المتاحة:")
    plats = list(PLATFORMS.keys())
    selected = []
    for i, p in enumerate(plats):
        ans = input(f"  {i+1}. {PLATFORMS[p]['name']}? (y/n) [y]: ").strip().lower()
        if ans in ("", "y", "yes"):
            selected.append(p)
    if not selected:
        selected = ["youtube"]
    stream = create_stream(topic, category, selected)
    print(f"\n  ✅ تم إنشاء البث!")
    print(f"  العنوان: {stream['title']}")
    print(f"  المعرف: {stream['id']}")
    return stream

# ─── خادم REST API (Flask) ───

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    accept = request.headers.get("Accept", "")
    if "text/html" in accept:
        return dashboard_html()
    return jsonify({"name": "Stream Producer Pro", "version": "1.0", "status": "running"})

@app.route("/dashboard", methods=["GET"])
def dashboard_page():
    return dashboard_html()

def dashboard_html():
    return """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stream Producer Pro</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<style>
body { background: #0f0f23; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, sans-serif; }
.sidebar { background: #1a1a3e; min-height: 100vh; border-left: 1px solid #2a2a5e; }
.sidebar .nav-link { color: #a0a0c0; padding: 12px 20px; border-radius: 8px; margin: 2px 8px; transition: all 0.2s; }
.sidebar .nav-link:hover, .sidebar .nav-link.active { background: #2a2a5e; color: #fff; }
.sidebar .nav-link i { margin-left: 10px; }
.card { background: #1a1a3e; border: 1px solid #2a2a5e; border-radius: 12px; }
.card-header { background: #22225a; border-bottom: 1px solid #2a2a5e; color: #ffd700; font-weight: bold; }
.stat-card { background: linear-gradient(135deg, #1a1a3e, #252570); border: 1px solid #3a3a7e; border-radius: 12px; padding: 20px; text-align: center; }
.stat-card .num { font-size: 2.2rem; font-weight: bold; color: #ffd700; }
.stat-card .label { color: #a0a0c0; font-size: 0.85rem; }
.badge-live { background: #ff4444; color: #fff; animation: pulse 1.5s infinite; }
.badge-scheduled { background: #ffa500; color: #000; }
.badge-ended { background: #444; color: #aaa; }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
.table { color: #e0e0e0; }
.table th { color: #ffd700; border-color: #2a2a5e; }
.table td { border-color: #2a2a5e; vertical-align: middle; }
.form-control, .form-select { background: #0f0f23; border: 1px solid #2a2a5e; color: #e0e0e0; }
.form-control:focus, .form-select:focus { background: #0f0f23; color: #e0e0e0; border-color: #ffd700; box-shadow: 0 0 0 0.2rem rgba(255,215,0,0.15); }
.btn-gold { background: #ffd700; color: #000; font-weight: bold; }
.btn-gold:hover { background: #ffed4a; color: #000; }
.btn-outline-gold { border: 1px solid #ffd700; color: #ffd700; }
.btn-outline-gold:hover { background: #ffd700; color: #000; }
.toast-container { position: fixed; bottom: 20px; left: 20px; z-index: 9999; }
</style>
</head>
<body>
<div class="container-fluid">
<div class="row">
  <!-- Sidebar -->
  <div class="col-md-2 sidebar p-3">
    <h4 class="text-center mb-4" style="color:#ffd700;"><i class="bi bi-broadcast"></i> Stream Pro</h4>
    <hr style="border-color:#2a2a5e;">
    <nav class="nav flex-column">
      <a class="nav-link active" href="javascript:void(0)" onclick="showTab('dashboard', this)"><i class="bi bi-speedometer2"></i> لوحة التحكم</a>
      <a class="nav-link" href="javascript:void(0)" onclick="showTab('streams', this)"><i class="bi bi-collection-play"></i> البثوث</a>
      <a class="nav-link" href="javascript:void(0)" onclick="showTab('create', this)"><i class="bi bi-plus-circle"></i> إنشاء بث</a>
      <a class="nav-link" href="javascript:void(0)" onclick="showTab('platforms', this)"><i class="bi bi-gear"></i> المنصات</a>
    </nav>
    <hr style="border-color:#2a2a5e;">
    <div class="text-center mt-3">
      <button class="btn btn-outline-gold btn-sm" onclick="refreshAll()"><i class="bi bi-arrow-clockwise"></i> تحديث</button>
    </div>
  </div>

  <!-- Main Content -->
  <div class="col-md-10 p-4">
    <!-- Dashboard Tab -->
    <div id="tab-dashboard" class="tab-content">
      <h3><i class="bi bi-speedometer2"></i> لوحة التحكم</h3>
      <div class="row mt-4" id="statsRow">
        <div class="col-md-3 mb-3"><div class="stat-card"><div class="num" id="statUpcoming">0</div><div class="label">بثوث قادمة</div></div></div>
        <div class="col-md-3 mb-3"><div class="stat-card"><div class="num" id="statLive">0</div><div class="label">مباشرة الآن</div></div></div>
        <div class="col-md-3 mb-3"><div class="stat-card"><div class="num" id="statTotal">0</div><div class="label">إجمالي البثوث</div></div></div>
        <div class="col-md-3 mb-3"><div class="stat-card"><div class="num" id="statPlatforms">0</div><div class="label">منصات مفعلة</div></div></div>
      </div>
      <div class="card mt-4"><div class="card-header"><i class="bi bi-clock-history"></i> آخر البثوث</div>
      <div class="card-body" id="recentStreams"><p class="text-muted text-center">جاري التحميل...</p></div></div>
    </div>

    <!-- Streams Tab -->
    <div id="tab-streams" class="tab-content" style="display:none">
      <h3><i class="bi bi-collection-play"></i> كل البثوث</h3>
      <div class="mt-3"><table class="table table-hover"><thead><tr><th>#</th><th>العنوان</th><th>التصنيف</th><th>الحالة</th><th>الموعد</th><th>إجراءات</th></tr></thead><tbody id="streamsTable"></tbody></table></div>
    </div>

    <!-- Create Tab -->
    <div id="tab-create" class="tab-content" style="display:none">
      <h3><i class="bi bi-plus-circle"></i> إنشاء بث مباشر جديد</h3>
      <div class="card mt-3"><div class="card-body">
        <div class="mb-3"><label class="form-label">الموضوع</label><input id="newTopic" class="form-control" placeholder="أدخل موضوع البث"></div>
        <div class="mb-3"><label class="form-label">التصنيف</label><select id="newCategory" class="form-select"><option value="educational">تعليمي</option><option value="entertainment">ترفيهي</option><option value="talk">نقاش</option><option value="gaming">قيمنق</option></select></div>
        <div class="mb-3"><label class="form-label">المنصات</label><div id="platformCheckboxes"></div></div>
        <button class="btn btn-gold" onclick="createStream()"><i class="bi bi-send"></i> إنشاء البث</button>
      </div></div>
    </div>

    <!-- Platforms Tab -->
    <div id="tab-platforms" class="tab-content" style="display:none">
      <h3><i class="bi bi-gear"></i> إعداد المنصات</h3>
      <div class="card mt-3"><div class="card-body" id="platformsConfig"><p class="text-muted text-center">جاري التحميل...</p></div></div>
    </div>
  </div>
</div>
</div>

<!-- Toast -->
<div class="toast-container"><div id="toast" class="toast align-items-center text-bg-dark border-0"><div class="d-flex"><div class="toast-body" id="toastMsg"></div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div></div></div>

<script>
const API = '';
function showTab(name, el) {
  document.querySelectorAll('.tab-content').forEach(function(t) { t.style.display = 'none'; });
  var tab = document.getElementById('tab-' + name);
  if (tab) tab.style.display = 'block';
  document.querySelectorAll('.sidebar .nav-link').forEach(function(l) { l.classList.remove('active'); });
  if (el) el.classList.add('active');
  if (name === 'dashboard') loadDashboard();
  if (name === 'streams') loadStreams();
  if (name === 'platforms') loadPlatforms();
}
function toast(msg) {
  var el = document.getElementById('toastMsg');
  if (el) el.textContent = msg;
  var t = document.getElementById('toast');
  if (t) { t.classList.add('show'); setTimeout(function() { t.classList.remove('show'); }, 3000); }
}
function refreshAll() { loadDashboard(); }

function api(path, opts) {
  opts = opts || {};
  return fetch(API + path, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    method: opts.method || 'GET',
    body: opts.body || null
  }).then(function(r) { return r.json(); }).catch(function(e) { console.error('API error:', e); toast('خطأ في الاتصال'); });
}

function loadStats() {
  api('/stats').then(function(s) {
    document.getElementById('statUpcoming').textContent = s.upcoming || 0;
    document.getElementById('statLive').textContent = s.live || 0;
    document.getElementById('statTotal').textContent = s.total_scheduled || 0;
  });
}

function loadDashboard() {
  loadStats();
  api('/platforms').then(function(plats) {
    document.getElementById('statPlatforms').textContent = Object.keys(plats).length || 0;
  });
  api('/streams').then(function(streams) {
    var recent = streams.slice(-5).reverse();
    var html = '';
    if (recent.length) {
      recent.forEach(function(s) {
        var badge = s.status === 'live' ? 'badge-live' : s.status === 'scheduled' ? 'badge-scheduled' : 'badge-ended';
        var date = s.scheduled_for ? new Date(s.scheduled_for).toLocaleString('ar-SA') : '';
        html += '<div class="d-flex justify-content-between align-items-center p-2 border-bottom" style="border-color:#2a2a5e!important"><span><span class="badge ' + badge + ' ms-2">' + s.status + '</span> ' + s.title + '</span><small class="text-muted">' + date + '</small></div>';
      });
    } else {
      html = '<p class="text-muted text-center">لا توجد بثوث</p>';
    }
    document.getElementById('recentStreams').innerHTML = html;
  });
}

function loadStreams() {
  api('/streams').then(function(streams) {
    var html = '';
    streams.forEach(function(s, i) {
      var badge = s.status === 'live' ? 'badge-live' : s.status === 'scheduled' ? 'badge-scheduled' : 'badge-ended';
      var date = s.scheduled_for ? new Date(s.scheduled_for).toLocaleString('ar-SA') : '-';
      html += '<tr><td>' + (i+1) + '</td><td>' + s.title + '</td><td>' + s.category + '</td><td><span class="badge ' + badge + '">' + s.status + '</span></td><td>' + date + '</td><td><button class="btn btn-sm btn-outline-gold" onclick="viewStream(\'' + s.id + '\')"><i class="bi bi-eye"></i></button> <button class="btn btn-sm btn-outline-danger" onclick="deleteStream(\'' + s.id + '\')"><i class="bi bi-trash"></i></button></td></tr>';
    });
    document.getElementById('streamsTable').innerHTML = html || '<tr><td colspan="6" class="text-center text-muted">لا توجد بثوث</td></tr>';
  });
}

function viewStream(id) {
  api('/streams/' + id).then(function(s) {
    toast(JSON.stringify(s, null, 2).slice(0, 100) + '...');
  });
}

function deleteStream(id) {
  if (!confirm('حذف البث ' + id + '?')) return;
  api('/streams/' + id, { method: 'DELETE' }).then(function() {
    toast('تم حذف البث');
    loadStreams();
    loadStats();
  });
}

function createStream() {
  var topic = document.getElementById('newTopic').value.trim();
  if (!topic) { toast('الرجاء إدخال الموضوع'); return; }
  var category = document.getElementById('newCategory').value;
  var checks = document.querySelectorAll('#platformCheckboxes input:checked');
  var platforms = [];
  checks.forEach(function(c) { platforms.push(c.value); });
  if (!platforms.length) platforms = ['youtube'];
  api('/streams', { method: 'POST', body: JSON.stringify({ topic: topic, category: category, platforms: platforms }) }).then(function() {
    toast('تم إنشاء البث: ' + topic);
    document.getElementById('newTopic').value = '';
    loadStreams();
    loadStats();
  });
}

function loadPlatforms() {
  api('/platforms').then(function(plats) {
    var names = { youtube: 'YouTube Live', facebook: 'Facebook Live', twitch: 'Twitch', tiktok: 'TikTok Live', instagram: 'Instagram Live' };
    var html = '<div class="row">';
    var keys = Object.keys(plats || {});
    keys.forEach(function(key) {
      var val = plats[key];
      var icon = key === 'youtube' ? 'youtube' : key === 'facebook' ? 'facebook' : key === 'twitch' ? 'twitch' : 'camera-reels';
      var keyDisplay = val.stream_key ? val.stream_key.slice(0, 16) + '...' : 'غير مضبوط';
      html += '<div class="col-md-6 mb-3"><div class="card"><div class="card-body"><h5><i class="bi bi-' + icon + '"></i> ' + (names[key] || key) + '</h5><p class="mb-1"><small>مفتاح البث: ' + keyDisplay + '</small></p><span class="badge bg-success">مفعل</span></div></div></div>';
    });
    if (!keys.length) html += '<p class="text-muted text-center">لم يتم إعداد أي منصة. استخدم: python stream_producer.py --configure</p>';
    html += '</div>';
    document.getElementById('platformsConfig').innerHTML = html;
    var chkHtml = '';
    keys.forEach(function(p) {
      chkHtml += '<div class="form-check form-check-inline"><input class="form-check-input" type="checkbox" id="chk_' + p + '" value="' + p + '" checked><label class="form-check-label" for="chk_' + p + '">' + (names[p] || p) + '</label></div>';
    });
    document.getElementById('platformCheckboxes').innerHTML = chkHtml || '<p class="text-muted">أضف منصة أولاً</p>';
  });
}

loadDashboard();
</script>
</body>
</html>"""

@app.route("/health", methods=["GET"])
def health():
    stats = stream_stats()
    return jsonify({"status": "ok", **stats})

@app.route("/streams", methods=["GET"])
def api_list_streams():
    status = request.args.get("status")
    return jsonify(list_streams(status))

@app.route("/streams/<stream_id>", methods=["GET"])
def api_get_stream(stream_id):
    s = get_stream(stream_id)
    if not s:
        return jsonify({"error": "not found"}), 404
    return jsonify(s)

@app.route("/streams", methods=["POST"])
def api_create_stream():
    data = request.json or {}
    topic = data.get("topic", "")
    if not topic:
        return jsonify({"error": "topic required"}), 400
    category = data.get("category", "educational")
    platform = data.get("platforms")
    stream = create_stream(topic, category, platform)
    return jsonify(stream), 201

@app.route("/streams/<stream_id>", methods=["DELETE"])
def api_delete_stream(stream_id):
    ok = delete_stream(stream_id)
    return jsonify({"deleted": ok}), 200 if ok else 404

@app.route("/streams/<stream_id>/start", methods=["POST"])
def api_start_stream(stream_id):
    data = request.json or {}
    video = data.get("video")
    cfg = load_config()
    platforms_config = cfg.get("platforms", {})
    if video:
        sid = stream_video_file(video, stream_id, platforms_config)
    else:
        update_stream(stream_id, {"status": "live", "started_at": datetime.now().isoformat()})
    return jsonify({"status": "started", "stream_id": stream_id})

@app.route("/streams/<stream_id>/stop", methods=["POST"])
def api_stop_stream(stream_id):
    broadcaster.stop_stream(stream_id)
    update_stream(stream_id, {"status": "ended", "ended_at": datetime.now().isoformat()})
    return jsonify({"status": "stopped", "stream_id": stream_id})

@app.route("/streams/<stream_id>/thumbnail", methods=["POST"])
def api_generate_thumbnail(stream_id):
    s = get_stream(stream_id)
    if not s:
        return jsonify({"error": "not found"}), 404
    thumb = generate_thumbnail(s["title"], s.get("category", "default"))
    if thumb:
        update_stream(stream_id, {"thumbnail": thumb})
        return jsonify({"thumbnail": thumb})
    return jsonify({"error": "failed"}), 500

@app.route("/stats", methods=["GET"])
def api_stats():
    return jsonify(stream_stats())

@app.route("/platforms", methods=["GET"])
def api_platforms():
    cfg = load_config()
    return jsonify(cfg.get("platforms", {}))

@app.route("/platforms", methods=["POST"])
def api_configure_platform():
    data = request.json or {}
    platform = data.get("platform", "")
    if not platform:
        return jsonify({"error": "platform required"}), 400
    configure_platform(platform, **{k: v for k, v in data.items() if k != "platform"})
    return jsonify({"configured": platform})

# ─── واجهة سطر الأوامر ───

def print_help():
    print("""
Stream Producer Pro v1.0

الاستخدام:
  --create             إنشاء بث مباشر جديد (وضع تفاعلي)
  --list               عرض كل البثوث المجدولة
  --list-upcoming      عرض البثوث القادمة
  --list-live          عرض البثوث النشطة
  --info <id>          عرض تفاصيل بث
  --delete <id>        حذف بث
  --start <id>         بدء بث مباشر (من ملف فيديو)
  --stop <id>          إيقاف بث مباشر
  --screen             بث الشاشة مباشرة
  --webcam             بث الكاميرا مباشرة
  --configure          إعداد مفاتيح البث للمنصات
  --config             عرض الإعدادات الحالية
  --stats              إحصائيات البث
  --thumbnail <id>     توليد صورة مصغرة للبث
  --server [PORT]      تشغيل خادم REST API (المنفذ الافتراضي 5002)
  --topic "موضوع"      إنشاء بث سريع (بدون تفاعل)
  --category TYPE      تصنيف البث (educational, entertainment, talk, gaming)
  --platform PLATFORM  المنصة (youtube, facebook, twitch, tiktok, instagram)
  --video FILE         ملف فيديو للبث

أمثلة:
  python stream_producer.py --configure
  python stream_producer.py --create
  python stream_producer.py --topic "الذكاء الاصطناعي" --category educational
  python stream_producer.py --start <id> --video video.mp4
  python stream_producer.py --screen
  python stream_producer.py --stats
    """)

def main():
    if "--server" in sys.argv:
        port = int(sys.argv[sys.argv.index("--server") + 1]) if "--server" in sys.argv and sys.argv[sys.argv.index("--server") + 1].isdigit() else 5002
        print(f"  تشغيل خادم API على http://0.0.0.0:{port}")
        app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
        sys.exit(0)

    if "--help" in sys.argv or len(sys.argv) == 1:
        print_help()
        sys.exit(0)
    if "--configure" in sys.argv:
        setup_wizard()
        sys.exit(0)
    if "--config" in sys.argv:
        cfg = load_config()
        print(json.dumps(cfg.get("platforms", {}), ensure_ascii=False, indent=2))
        sys.exit(0)
    if "--create" in sys.argv:
        interactive_create()
        sys.exit(0)
    if "--list" in sys.argv:
        streams = list_streams()
        if not streams:
            print("  لا توجد بثوث")
        else:
            print(f"\n  البثوث ({len(streams)}):")
            for s in streams:
                print(f"  [{s['status']}] {s['id']}: {s['title']} - {s.get('scheduled_for', 'N/A')}")
        sys.exit(0)
    if "--list-upcoming" in sys.argv:
        streams = list_streams("scheduled")
        if not streams:
            print("  لا توجد بثوث قادمة")
        else:
            print(f"\n  البثوث القادمة ({len(streams)}):")
            for s in streams:
                print(f"  {s['id']}: {s['title']} - {s.get('scheduled_for', 'N/A')}")
        sys.exit(0)
    if "--list-live" in sys.argv:
        streams = list_streams("live")
        active = broadcaster.processes
        if not streams and not active:
            print("  لا توجد بثوث نشطة")
        else:
            print(f"\n  البثوث النشطة:")
            for s in streams:
                print(f"  {s['id']}: {s['title']}")
            for sid in active:
                print(f"  [بث مباشر] {sid}")
        sys.exit(0)
    if "--stats" in sys.argv:
        stats = stream_stats()
        print(f"\n  إحصائيات البث:")
        print(f"  بثوث نشطة: {stats['active_streams']}")
        print(f"  مجدولة: {stats['upcoming']}")
        print(f"  مباشرة الآن: {stats['live']}")
        print(f"  تم البث سابقاً: {stats['total_streamed']}")
        sys.exit(0)
    if "--info" in sys.argv:
        idx = sys.argv.index("--info")
        if idx + 1 < len(sys.argv):
            sid = sys.argv[idx + 1]
            s = get_stream(sid)
            if s:
                print(json.dumps(s, ensure_ascii=False, indent=2))
            else:
                print(f"  البث {sid} غير موجود")
        sys.exit(0)
    if "--delete" in sys.argv:
        idx = sys.argv.index("--delete")
        if idx + 1 < len(sys.argv):
            delete_stream(sys.argv[idx + 1])
        sys.exit(0)
    if "--thumbnail" in sys.argv:
        idx = sys.argv.index("--thumbnail")
        if idx + 1 < len(sys.argv):
            sid = sys.argv[idx + 1]
            s = get_stream(sid)
            if s:
                thumb = generate_thumbnail(s["title"], s.get("category", "default"))
                if thumb:
                    update_stream(sid, {"thumbnail": thumb})
            else:
                print(f"  البث {sid} غير موجود")
        sys.exit(0)
    if "--start" in sys.argv:
        idx = sys.argv.index("--start")
        sid = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
        video = None
        if "--video" in sys.argv:
            vi = sys.argv.index("--video")
            video = sys.argv[vi + 1] if vi + 1 < len(sys.argv) else None
        if sid:
            cfg = load_config()
            platforms_config = cfg.get("platforms", {})
            if video:
                stream_video_file(video, sid, platforms_config)
            else:
                s = get_stream(sid)
                if s:
                    print(f"  تم تفعيل البث {sid}")
                    update_stream(sid, {"status": "live", "started_at": datetime.now().isoformat()})
                else:
                    print(f"  البث {sid} غير موجود")
        sys.exit(0)
    if "--stop" in sys.argv:
        idx = sys.argv.index("--stop")
        sid = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
        if sid:
            broadcaster.stop_stream(sid)
            update_stream(sid, {"status": "ended", "ended_at": datetime.now().isoformat()})
        sys.exit(0)
    if "--screen" in sys.argv:
        cfg = load_config()
        stream_screen(platforms_config=cfg.get("platforms", {}))
        print("  بث الشاشة بدأ. استخدم --stop مع المعرف للإيقاف")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            print("\n  إيقاف...")
            for sid in list(broadcaster.processes.keys()):
                broadcaster.stop_stream(sid)
        sys.exit(0)
    if "--webcam" in sys.argv:
        cfg = load_config()
        stream_webcam(platforms_config=cfg.get("platforms", {}))
        print("  بث الكاميرا بدأ. استخدم Ctrl+C للإيقاف")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            print("\n  إيقاف...")
            for sid in list(broadcaster.processes.keys()):
                broadcaster.stop_stream(sid)
        sys.exit(0)
    if "--topic" in sys.argv:
        idx = sys.argv.index("--topic")
        topic = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if not topic:
            print("  الرجاء إدخال موضوع")
            sys.exit(1)
        category = "educational"
        if "--category" in sys.argv:
            ci = sys.argv.index("--category")
            if ci + 1 < len(sys.argv):
                category = sys.argv[ci + 1]
        platform = None
        if "--platform" in sys.argv:
            pi = sys.argv.index("--platform")
            if pi + 1 < len(sys.argv):
                platform = [sys.argv[pi + 1]]
        create_stream(topic, category, platform)
        sys.exit(0)

if __name__ == "__main__":
    main()
