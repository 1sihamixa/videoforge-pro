"""
VideoForge Pro - Wav2Lip Talking Avatar Generator
Unified Flask application with ad monetization ready.
"""
import os, sys, uuid, threading, time, json, io, asyncio, subprocess, shutil, re
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, abort

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")
GALLERY_FILE  = os.path.join(BASE_DIR, "gallery.json")
STATS_FILE    = os.path.join(BASE_DIR, "stats.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024
app.secret_key = os.environ.get("SECRET_KEY", "videoforge-pro-secret-2026")

# ─── i18n (Bilingual: Arabic/English) ───
from translations import setup_i18n, t, get_language
setup_i18n(app)

# ─── Configuration ───
SYNC_API_KEY = os.environ.get("SYNC_API_KEY", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
GA_TRACKING_ID = os.environ.get("GA_TRACKING_ID", "")
ADSENSE_CLIENT = os.environ.get("ADSENSE_CLIENT", "")

def _valid_slot(val):
    """Return val only if it looks like a real AdSense slot ID (numeric, not placeholder)."""
    if not val: return ""
    s = val.strip()
    if s in ("", "1234567890", "xxxxxxxxxxxxxx"): return ""
    if not s.isdigit(): return ""
    if len(s) < 8: return ""
    return s

ADSENSE_SLOT_TOP = _valid_slot(os.environ.get("ADSENSE_SLOT_TOP", ""))
ADSENSE_SLOT_SIDEBAR = _valid_slot(os.environ.get("ADSENSE_SLOT_SIDEBAR", ""))
ADSENSE_SLOT_IN_ARTICLE = _valid_slot(os.environ.get("ADSENSE_SLOT_IN_ARTICLE", ""))
ADSENSE_SLOT_VIDEO = _valid_slot(os.environ.get("ADSENSE_SLOT_VIDEO", ""))
# Quick flag so templates know manual ads are ready
ADS_MANUAL_READY = bool(ADSENSE_SLOT_TOP or ADSENSE_SLOT_SIDEBAR or ADSENSE_SLOT_IN_ARTICLE or ADSENSE_SLOT_VIDEO)

# Load from config.json if exists
_cfg_path = os.path.join(BASE_DIR, "config.json")
if os.path.exists(_cfg_path):
    try:
        with open(_cfg_path, encoding="utf-8") as f:
            _cfg = json.load(f)
        SYNC_API_KEY = _cfg.get("avatar_settings", {}).get("sync_api_key", SYNC_API_KEY)
        if not PEXELS_API_KEY:
            PEXELS_API_KEY = _cfg.get("pexels_api_key", "")
    except: pass

# ─── Wav2Lip Model Check ───
# Removed: local Wav2Lip model check — cloud-only mode via sync.so
def check_model():
    return False

# ─── Jobs Store ───
jobs = {}

# ─── Gallery & Stats ───
def load_gallery():
    if os.path.exists(GALLERY_FILE):
        try:
            with open(GALLERY_FILE, encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return []

def save_gallery(gallery):
    with open(GALLERY_FILE, "w", encoding="utf-8") as f:
        json.dump(gallery, f, ensure_ascii=False, indent=2)

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"total_videos": 0, "today": 0, "active_channels": 1, "last_date": ""}

def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def add_to_gallery(video_path, title=""):
    gallery = load_gallery()
    today = datetime.now().strftime("%Y-%m-%d")
    gallery.insert(0, {
        "path": video_path,
        "name": title or "فيديو Wav2Lip",
        "date": today,
        "created": datetime.now().isoformat()
    })
    if len(gallery) > 50:
        gallery = gallery[:50]
    save_gallery(gallery)

    stats = load_stats()
    stats["total_videos"] = stats.get("total_videos", 0) + 1
    if stats.get("last_date") == today:
        stats["today"] = stats.get("today", 0) + 1
    else:
        stats["today"] = 1
        stats["last_date"] = today
    save_stats(stats)

# ─── Sync.so Models ───
SYNC_MODELS = {
    "sync-3":       {"free": True,  "max_sec": 15, "image": True,  "desc": "أفضل جودة, يدعم الصور مباشرة"},
    "lipsync-2":    {"free": True,  "max_sec": 20, "image": False, "desc": "سريع وجودة جيدة"},
    "lipsync-2-pro":{"free": True,  "max_sec": 20, "image": False, "desc": "جودة عالية"},
    "react-1":      {"free": False, "max_sec": 15, "image": False, "desc": "تعابير وجه + حركات رأس"},
}

# ─── Wav2Lip Generators ───
def run_local_generate(job_id, image_path, audio_path, output_path):
    try:
        jobs[job_id]["status"] = "processing"
        _buf = io.StringIO()
        _old_stdout = sys.stdout
        sys.stdout = _buf
        try:
            from avatar_engine import generate_video as gen_local
            result = gen_local(image_path, audio_path, output_path, checkpoint_path=MODEL_PATH if MODEL_READY else None)
        finally:
            sys.stdout = _old_stdout
        _log = _buf.getvalue()
        print(_log, end="")
        if result and os.path.exists(result):
            size = os.path.getsize(result)
            rel_path = "/output/" + os.path.basename(result)
            jobs[job_id]["status"] = "done"
            jobs[job_id]["output"] = rel_path
            jobs[job_id]["output_size"] = size
            add_to_gallery(rel_path)
        else:
            err_lines = [l for l in _log.splitlines() if "ERROR" in l or "Traceback" in l or "Error" in l]
            err_msg = err_lines[-1] if err_lines else "فشل في إنشاء الفيديو محلياً"
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = err_msg
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)

def run_cloud_generate(job_id, image_path, audio_path, output_path, api_key, model, model_mode):
    try:
        jobs[job_id]["status"] = "processing"
        from sync_api import generate_video as gen_cloud
        result, err = gen_cloud(image_path, audio_path, output_path, api_key, model, model_mode)
        if result and os.path.exists(result):
            rel_path = "/output/" + os.path.basename(result)
            jobs[job_id]["status"] = "done"
            jobs[job_id]["output"] = rel_path
            jobs[job_id]["output_size"] = os.path.getsize(result)
            add_to_gallery(rel_path)
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = err or "فشل في إنشاء الفيديو سحابياً"
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)

# ══════════════════════════════════════════════
#  Routes
# ══════════════════════════════════════════════

@app.route("/")
def index():
    lang = get_language()
    return render_template("video_creator.html",
        lang=lang,
        dir="rtl" if lang == "ar" else "ltr",
        model_ready=False,
        sync_api_key=SYNC_API_KEY,
        models=SYNC_MODELS,
        adsense_client=ADSENSE_CLIENT,
        adsense_slot_top=ADSENSE_SLOT_TOP,
        adsense_slot_sidebar=ADSENSE_SLOT_SIDEBAR,
        adsense_slot_in_article=ADSENSE_SLOT_IN_ARTICLE,
        adsense_slot_video=ADSENSE_SLOT_VIDEO,
        ga_tracking_id=GA_TRACKING_ID,
    )

@app.route("/api/status")
def api_status():
    return jsonify({
        "model_ready": check_model(),
        "total_videos": load_stats().get("total_videos", 0),
        "today": load_stats().get("today", 0),
        "status": "online",
        "version": "2.0"
    })

# ─── File Upload ───
@app.route("/api/wav2lip/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "لم يتم رفع ملف"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "الملف فارغ"}), 400
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "png"
    fid = uuid.uuid4().hex
    fname = f"{fid}.{ext}"
    fpath = os.path.join(UPLOAD_FOLDER, fname)
    file.save(fpath)
    img_exts = {"jpg","jpeg","png","webp","gif"}
    ftype = "image" if ext in img_exts else "audio"
    return jsonify({
        "path": f"/static/uploads/{fname}",
        "type": ftype,
        "name": file.filename
    })

# ─── Generate ───
@app.route("/api/wav2lip/generate", methods=["POST"])
def start_generate():
    data = request.json or {}
    image = data.get("image", "")
    audio = data.get("audio", "")
    text = data.get("text", "")
    mode = data.get("mode", "local")
    api_key = data.get("api_key", "")
    model = data.get("model", "lipsync-2")
    model_mode = data.get("model_mode", "")

    if not image:
        return jsonify({"error": "يرجى رفع صورة للوجه"}), 400

    image_path = os.path.join(BASE_DIR, image.lstrip("/"))
    if not os.path.exists(image_path):
        return jsonify({"error": "ملف الصورة غير موجود"}), 400

    audio_path = None
    if audio:
        audio_path = os.path.join(BASE_DIR, audio.lstrip("/"))
        if not os.path.exists(audio_path):
            return jsonify({"error": "ملف الصوت غير موجود"}), 400
    elif text:
        try:
            import edge_tts
            audio_fname = f"tts_{uuid.uuid4().hex}.mp3"
            audio_path = os.path.join(UPLOAD_FOLDER, audio_fname)
            has_ar = bool(re.search(r'[\u0600-\u06FF]', text))
            voice_map = {"ar": "ar-SA-HamedNeural", "en": "en-US-AriaNeural"}
            voice = voice_map["ar"] if has_ar else voice_map["en"]
            async def _tts():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(audio_path)
            asyncio.run(_tts())
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 100:
                raise Exception("ملف الصوت الناتج صغير جداً")
        except Exception as e:
            return jsonify({"error": f"فشل توليد الصوت: {e}"}), 500
    else:
        return jsonify({"error": "يرجى رفع ملف صوتي أو كتابة نص"}), 400

    # Force cloud-only: use env API key, ignore user input
    if not SYNC_API_KEY:
        return jsonify({"error": "مفتاح API السحابي غير مضبوط في الخادم"}), 400

    job_id = uuid.uuid4().hex
    out_fname = f"wav2lip_{job_id}.mp4"
    output_path = os.path.join(OUTPUT_FOLDER, out_fname)

    jobs[job_id] = {"status": "queued", "output": None, "error": None, "progress": 0}

    t = threading.Thread(target=run_cloud_generate,
        args=(job_id, image_path, audio_path, output_path, SYNC_API_KEY, model, model_mode))
    t.daemon = True
    t.start()

    return jsonify({"job_id": job_id})

@app.route("/api/wav2lip/job/<job_id>")
def get_job(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "المهمة غير موجودة"}), 404
    return jsonify({
        "status": job.get("status", "unknown"),
        "output": job.get("output"),
        "error": job.get("error"),
        "progress": job.get("progress", 0),
        "output_size": job.get("output_size", 0),
    })

# ─── Gallery ───
@app.route("/api/gallery")
def get_gallery():
    gallery = load_gallery()
    return jsonify(gallery)

@app.route("/api/stats")
def get_stats():
    return jsonify(load_stats())

# ─── Serve Output Files ───
@app.route("/output/<path:filename>")
def serve_output(filename):
    full_path = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(full_path):
        return send_file(full_path, as_attachment=False, mimetype="video/mp4")
    return jsonify({"error": "الملف غير موجود"}), 404

@app.route("/api/download/<path:filepath>")
def download_file(filepath):
    full_path = os.path.join(BASE_DIR, filepath.lstrip("/"))
    if os.path.exists(full_path):
        return send_file(full_path, as_attachment=True)
    full_path = os.path.join(OUTPUT_FOLDER, filepath.lstrip("/"))
    if os.path.exists(full_path):
        return send_file(full_path, as_attachment=True)
    return jsonify({"error": "الملف غير موجود"}), 404

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_file(os.path.join(BASE_DIR, "static", filename))

# ─── Admin / Dashboard (simple) ───
@app.route("/admin")
def admin_panel():
    stats = load_stats()
    gallery = load_gallery()
    lang = get_language()
    is_en = lang == "en"
    html_lang = "en" if is_en else "ar"
    html_dir = "ltr" if is_en else "rtl"
    title = "VideoForge Pro - Dashboard" if is_en else "VideoForge Pro - لوحة التحكم"
    lbl_total = "Total Videos" if is_en else "إجمالي الفيديوهات"
    lbl_today = "Today's Videos" if is_en else "فيديو اليوم"
    lbl_gallery_count = "In Gallery" if is_en else "في المعرض"
    lbl_model_status = "Local Model" if is_en else "النموذج المحلي"
    lbl_active_jobs = "Active Jobs" if is_en else "المهام قيد التنفيذ"
    lbl_latest = "Latest Videos" if is_en else "آخر الفيديوهات"
    lbl_settings = "Environment Settings" if is_en else "إعدادات البيئة"
    lbl_configured = "Configured" if is_en else "مضبوط"
    lbl_not_configured = "Not configured" if is_en else "غير مضبوط"
    lbl_ready = "Ready" if is_en else "جاهز"
    lbl_not_found = "Not found" if is_en else "غير موجود"
    lbl_files_uploaded = "Uploaded files" if is_en else "الملفات المرفوعة"
    lbl_files_produced = "Produced files" if is_en else "الملفات المنتجة"
    lbl_back_home = "Back to Home" if is_en else "العودة للرئيسية"
    lbl_switch_lang = "العربية" if is_en else "English"
    switch_lang_code = "ar" if is_en else "en"
    link_prefix = "/switch-language/" + switch_lang_code
    name_label = "Name" if is_en else "الاسم"
    date_label = "Date" if is_en else "التاريخ"
    link_label = "Link" if is_en else "رابط"
    preview_label = "Preview" if is_en else "معاينة"
    return f"""
    <!DOCTYPE html><html lang="{html_lang}" dir="{html_dir}"><head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Cairo',sans-serif;background:#0b0b1a;color:#e0e0f0;padding:30px}}
    h1{{font-size:28px;margin-bottom:20px}} h1 span{{color:#6c5ce7}}
    .stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:30px}}
    .stat-card{{background:#13132e;border:1px solid #1e1e44;border-radius:12px;padding:20px;text-align:center}}
    .stat-card .num{{font-size:32px;font-weight:900;color:#6c5ce7}}
    .stat-card .lbl{{font-size:13px;color:#8888aa;margin-top:4px}}
    table{{width:100%;border-collapse:collapse;background:#13132e;border-radius:12px;overflow:hidden}}
    th,td{{padding:12px 16px;text-align:right;border-bottom:1px solid #1e1e44;font-size:13px}}
    th{{background:#1a1a3a;color:#6c5ce7;font-weight:700}}
    td{{color:#ccc}} a{{color:#6c5ce7;text-decoration:none}} a:hover{{text-decoration:underline}}
    .badge{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700}}
    .badge.green{{background:#00c85320;color:#00c853}}
    .env-section{{background:#13132e;border:1px solid #1e1e44;border-radius:12px;padding:20px;margin-top:20px}}
    .env-section h3{{margin-bottom:12px;color:#6c5ce7}}
    code{{display:block;background:#0b0b1a;padding:12px;border-radius:8px;font-size:12px;color:#aaa;line-height:1.8}}
    </style></head><body>
    <h1>🎬 VideoForge <span>Pro</span> - {title}</h1>
    <div class="stats">
      <div class="stat-card"><div class="num">{stats.get('total_videos',0)}</div><div class="lbl">{lbl_total}</div></div>
      <div class="stat-card"><div class="num">{stats.get('today',0)}</div><div class="lbl">{lbl_today}</div></div>
      <div class="stat-card"><div class="num">{len(gallery)}</div><div class="lbl">{lbl_gallery_count}</div></div>
      <div class="stat-card"><div class="num">{'✅'}</div><div class="lbl">API Status</div></div>
      <div class="stat-card"><div class="num">{len(jobs)}</div><div class="lbl">{lbl_active_jobs}</div></div>
    </div>
    <h3 style="margin-bottom:12px;color:#8888aa">📹 {lbl_latest}</h3>
    <table>
    <tr><th>#</th><th>{name_label}</th><th>{date_label}</th><th>{link_label}</th></tr>
    {"".join(f'<tr><td>{i+1}</td><td>{v.get("name","Video" if is_en else "فيديو")}</td><td>{v.get("date","")}</td><td><a href="{v["path"]}" target="_blank">▶ {preview_label}</a></td></tr>' for i,v in enumerate(gallery[:20]))}
    </table>
    <div class="env-section">
      <h3>⚙️ {lbl_settings}</h3>
      <code>SYNC_API_KEY={'✅ ' + lbl_configured if SYNC_API_KEY else '⚠️ ' + lbl_not_configured}\\nPEXELS_API_KEY={'✅ ' + lbl_configured if PEXELS_API_KEY else '⚠️ ' + lbl_not_configured}\\nADSENSE_CLIENT={ADSENSE_CLIENT or '⚠️ ' + lbl_not_configured}\\nGA_TRACKING_ID={GA_TRACKING_ID or '⚠️ ' + lbl_not_configured}\\n{lbl_files_uploaded}: {len(os.listdir(UPLOAD_FOLDER)) if os.path.exists(UPLOAD_FOLDER) else 0}\\n{lbl_files_produced}: {len(os.listdir(OUTPUT_FOLDER)) if os.path.exists(OUTPUT_FOLDER) else 0}</code>
    </div>
    <div style="margin-top:20px;font-size:12px;color:#555;text-align:center">
      <a href="{link_prefix}" style="color:#6c5ce7;text-decoration:none;margin-left:12px">🔄 {lbl_switch_lang}</a>
      VideoForge Pro v2.0 | <a href="/">{lbl_back_home}</a>
    </div>
    </body></html>
    """

# ══════════════════════════════════════════════
#  SEO Routes (sitemap.xml, robots.txt, etc.)
# ══════════════════════════════════════════════

@app.route("/sitemap.xml")
def sitemap_xml():
    domain = "https://videoforge-pro.com"
    today = datetime.now().strftime("%Y-%m-%d")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>{domain}/</loc>
    <xhtml:link rel="alternate" hreflang="ar" href="{domain}/" />
    <xhtml:link rel="alternate" hreflang="en" href="{domain}/en" />
    <xhtml:link rel="alternate" hreflang="x-default" href="{domain}/" />
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{domain}/en</loc>
    <xhtml:link rel="alternate" hreflang="ar" href="{domain}/" />
    <xhtml:link rel="alternate" hreflang="en" href="{domain}/en" />
    <xhtml:link rel="alternate" hreflang="x-default" href="{domain}/" />
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>{domain}/admin</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.3</priority>
  </url>
</urlset>""", 200, {"Content-Type": "application/xml"}

@app.route("/robots.txt")
def robots_txt():
    return f"""User-agent: *
Allow: /
Disallow: /admin
Disallow: /api/

Sitemap: https://videoforge-pro.com/sitemap.xml
""", 200, {"Content-Type": "text/plain"}

@app.route("/sitemap")
def sitemap_html():
    stats = load_stats()
    total = stats.get("total_videos", 0)
    today = stats.get("today", 0)
    gallery = load_gallery()
    gallery_count = len(gallery)
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>خريطة الموقع - VideoForge Pro</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Cairo',sans-serif;background:#0b0b1a;color:#e0e0f0;padding:40px;max-width:800px;margin:0 auto}}h1{{font-size:28px;color:#6c5ce7;margin-bottom:20px}}a{{color:#6c5ce7;text-decoration:none;display:block;padding:10px 16px;background:#13132e;border:1px solid #1e1e44;border-radius:10px;margin-bottom:8px;transition:all 0.3s}}a:hover{{border-color:#6c5ce7;transform:translateX(-4px)}}a small{{display:block;color:#8888aa;font-size:12px;margin-top:2px}}.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:30px}}.stat{{background:#13132e;border:1px solid #1e1e44;border-radius:10px;padding:16px;text-align:center}}.stat .num{{font-size:24px;font-weight:900;color:#6c5ce7}}.stat .lbl{{font-size:12px;color:#8888aa}}p{{color:#8888aa;font-size:13px;margin-bottom:20px}}</style></head>
<body>
<h1>🗺️ خريطة الموقع - VideoForge Pro</h1>
<p>جميع صفحات الموقع المتاحة للفهرسة. إجمالي الفيديوهات: {total} | اليوم: {today} | في المعرض: {gallery_count}</p>
<div class="stats">
  <div class="stat"><div class="num">{total}</div><div class="lbl">فيديو منتج</div></div>
  <div class="stat"><div class="num">{today}</div><div class="lbl">اليوم</div></div>
  <div class="stat"><div class="num">{gallery_count}</div><div class="lbl">بالمعرض</div></div>
</div>
<a href="/">🏠 الصفحة الرئيسية <small>VideoForge Pro - Wav2Lip لتوليد فيديوهات ناطقة</small></a>
<a href="/?lang=en">🇬🇧 English Version <small>VideoForge Pro - AI Talking Avatar Generator</small></a>
<a href="/admin">📊 لوحة التحكم <small>إحصائيات وإدارة الموقع</small></a>
<p style="margin-top:30px;font-size:12px;color:#555;text-align:center">VideoForge Pro © 2026 | <a href="/sitemap.xml" style="display:inline;padding:0;background:none;border:none;color:#6c5ce7">XML Sitemap</a></p>
</body></html>"""

@app.route("/googleads.html")
def google_ads_verify():
    return "google-site-verification: google3830862702445100.html", 200

@app.route("/ads.txt")
def ads_txt():
    from flask import Response
    return Response("google.com, pub-3830862702445100, DIRECT, f08c47fec0942fa0\n", mimetype="text/plain")

@app.route("/en")
def index_en():
    return redirect("/?lang=en")

# ══════════════════════════════════════════════
#  Legal Pages (Privacy & Terms)
# ══════════════════════════════════════════════

@app.route("/privacy")
def privacy():
    lang = get_language()
    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{'rtl' if lang == 'ar' else 'ltr'}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{t('page_privacy_title')}</title>
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://videoforge-pro.com/privacy">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Cairo',sans-serif;background:#0b0b1a;color:#e0e0f0;padding:40px 20px;line-height:1.8}}.container{{max-width:800px;margin:0 auto}}h1{{font-size:32px;color:#6c5ce7;margin-bottom:24px;text-align:center}}h2{{font-size:22px;color:#f0c040;margin:30px 0 12px}}p{{font-size:15px;color:#ccc;margin-bottom:12px}}a{{color:#6c5ce7;text-decoration:none}}.btn{{display:inline-block;padding:10px 24px;background:#6c5ce7;color:#fff;border-radius:8px;margin-top:20px;text-decoration:none}}.btn:hover{{background:#5a4bd1}}hr{{border:none;border-top:1px solid #1e1e44;margin:30px 0}}.lang-bar{{text-align:{'left' if lang == 'ar' else 'right'};margin-bottom:20px}}.lang-bar a{{color:#8888aa;font-size:14px}}</style>
</head>
<body>
<div class="container">
<div class="lang-bar"><a href="?lang={'en' if lang == 'ar' else 'ar'}">{'🇸🇦 العربية' if lang == 'en' else '🇬🇧 English'}</a></div>
<h1>{t('page_privacy_title')}</h1>
<p>{t('privacy_intro')}</p>
<h2>{t('privacy_data_collect_title')}</h2>
<p>{t('privacy_data_collect')}</p>
<h2>{t('privacy_cookies_title')}</h2>
<p>{t('privacy_cookies')}</p>
<h2>{t('privacy_third_party_title')}</h2>
<p>{t('privacy_third_party')}</p>
<h2>{t('privacy_rights_title')}</h2>
<p>{t('privacy_rights')}</p>
<h2>{t('privacy_contact_title')}</h2>
<p>{t('privacy_contact')}</p>
<hr>
<div style="text-align:center"><a href="/" class="btn">{t('privacy_back')}</a></div>
<p style="text-align:center;font-size:12px;color:#555;margin-top:30px">VideoForge Pro © 2026</p>
</div>
</body>
</html>"""

@app.route("/terms")
def terms():
    lang = get_language()
    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{'rtl' if lang == 'ar' else 'ltr'}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{t('page_terms_title')}</title>
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://videoforge-pro.com/terms">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Cairo',sans-serif;background:#0b0b1a;color:#e0e0f0;padding:40px 20px;line-height:1.8}}.container{{max-width:800px;margin:0 auto}}h1{{font-size:32px;color:#6c5ce7;margin-bottom:24px;text-align:center}}h2{{font-size:22px;color:#f0c040;margin:30px 0 12px}}p{{font-size:15px;color:#ccc;margin-bottom:12px}}a{{color:#6c5ce7;text-decoration:none}}.btn{{display:inline-block;padding:10px 24px;background:#6c5ce7;color:#fff;border-radius:8px;margin-top:20px;text-decoration:none}}.btn:hover{{background:#5a4bd1}}hr{{border:none;border-top:1px solid #1e1e44;margin:30px 0}}.lang-bar{{text-align:{'left' if lang == 'ar' else 'right'};margin-bottom:20px}}.lang-bar a{{color:#8888aa;font-size:14px}}</style>
</head>
<body>
<div class="container">
<div class="lang-bar"><a href="?lang={'en' if lang == 'ar' else 'ar'}">{'🇸🇦 العربية' if lang == 'en' else '🇬🇧 English'}</a></div>
<h1>{t('page_terms_title')}</h1>
<p>{t('terms_intro')}</p>
<h2>{t('terms_service_title')}</h2>
<p>{t('terms_service')}</p>
<h2>{t('terms_usage_title')}</h2>
<p>{t('terms_usage')}</p>
<h2>{t('terms_content_title')}</h2>
<p>{t('terms_content')}</p>
<h2>{t('terms_ads_title')}</h2>
<p>{t('terms_ads')}</p>
<h2>{t('terms_changes_title')}</h2>
<p>{t('terms_changes')}</p>
<hr>
<div style="text-align:center"><a href="/" class="btn">{t('terms_back')}</a></div>
<p style="text-align:center;font-size:12px;color:#555;margin-top:30px">VideoForge Pro © 2026</p>
</div>
</body>
</html>"""

# ─── Error Handlers ───
@app.errorhandler(404)
def not_found(e):
    lang = get_language()
    msg = "الصفحة غير موجودة" if lang == "ar" else "Page not found"
    return jsonify({"error": msg}), 404

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "الملف كبير جداً. الحد الأقصى 200MB"}), 413

@app.errorhandler(500)
def server_error(e):
    lang = get_language()
    msg = "خطأ في الخادم" if lang == "ar" else "Server error"
    return jsonify({"error": msg}), 500

# ══════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 55)
    print("  VideoForge Pro - Wav2Lip Avatar Generator")
    print("=" * 55)
    print(f"  الموقع: http://0.0.0.0:{port}")
    print(f"  لوحة التحكم: http://0.0.0.0:{port}/admin")
    print(f"  API سحابي (sync.so): {'✅ مضبوط' if SYNC_API_KEY else '⚠️ غير مضبوط'}")
    print(f"  رفع الملفات: {UPLOAD_FOLDER}")
    print(f"  إنتاج الفيديو: {OUTPUT_FOLDER}")
    print("=" * 55)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
