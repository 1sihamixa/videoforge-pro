import os, time, tempfile, subprocess, mimetypes, socket, json as _json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://api.sync.so/v2"

# DNS multi-resolution: try local, fallback to Google DoH
def _resolve_sync():
    ips = []
    try:
        ips = list(set([
            info[4][0] for info in socket.getaddrinfo("api.sync.so", 443, socket.AF_INET)
        ]))
    except:
        pass
    if not ips:
        try:
            import urllib.request
            doh = urllib.request.urlopen("https://dns.google/resolve?name=api.sync.so&type=A", timeout=5)
            data = _json.loads(doh.read().decode())
            ips = [a["data"] for a in data.get("Answer", []) if a.get("type") == 1]
        except:
            pass
    if not ips:
        ips = ["104.18.22.221", "104.18.23.221"]
    return ips

_sync_ips = _resolve_sync()
_HOST_HEADER = "api.sync.so"

def _make_session(retries=3, backoff=2):
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["POST", "PUT", "GET"])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=5, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

_SESSION = _make_session()

MODELS = {
    "sync-3":       {"free": True,  "max_sec": 15, "image": True,  "desc": "أفضل جودة, يدعم الصور مباشرة (مجاني 1/شهر)"},
    "lipsync-2":    {"free": True,  "max_sec": 20, "image": False, "desc": "سريع وجودة جيدة (مجاني 3/شهر)"},
    "lipsync-2-pro":{"free": True,  "max_sec": 20, "image": False, "desc": "جودة عالية (مجاني 3/شهر)"},
    "react-1":      {"free": False, "max_sec": 15, "image": False, "desc": "تعابير وجه + حركات رأس (مدفوع)"},
}

def _request(method, url, **kwargs):
    """Try request; if DNS fails, retry with IP + Host header."""
    try:
        return _SESSION.request(method, url, **kwargs)
    except requests.exceptions.ConnectionError:
        if not _sync_ips:
            raise
        for ip in _sync_ips:
            try:
                ip_url = url.replace("api.sync.so", ip)
                h = dict(kwargs.get("headers", {}))
                h["Host"] = _HOST_HEADER
                kwargs["headers"] = h
                return _SESSION.request(method, ip_url, **kwargs)
            except:
                continue
        raise

def _upload_asset(api_key, file_path, content_type):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    resp = _request("POST", f"{BASE_URL}/assets/upload",
                    headers=headers,
                    json={"fileName": file_name, "contentType": content_type, "size": file_size},
                    timeout=45)
    if resp.status_code not in (200, 201):
        return None, f"فشل رفع الملف: {resp.text}"
    data = resp.json()
    upload_url = data["uploadUrl"]
    asset_url = data["url"]
    with open(file_path, "rb") as f:
        put_resp = _SESSION.put(upload_url, data=f, timeout=180)
    if put_resp.status_code not in (200, 201):
        return None, f"فشل رفع الملف: HTTP {put_resp.status_code}"
    reg_resp = _request("POST", f"{BASE_URL}/assets", headers=headers,
                         json={"url": asset_url, "contentType": content_type}, timeout=30)
    if reg_resp.status_code not in (200, 201):
        return None, f"فشل تسجيل الملف: {reg_resp.text}"
    asset_id = reg_resp.json()["id"]
    return {"id": asset_id, "url": asset_url}, None


def generate_video(image_path, audio_path, output_path, api_key, model="lipsync-2", model_mode=None):
    if not os.path.exists(image_path):
        return None, "الصورة غير موجودة"
    if not os.path.exists(audio_path):
        return None, "الملف الصوتي غير موجود"
    if not api_key:
        return None, "مطلوب API Key من sync.so"
    if model not in MODELS:
        return None, f"نموذج غير معروف: {model}"

    temp_dir = tempfile.mkdtemp(prefix="sync_")
    try:
        print("[1/5] تجهيز الصورة...")
        model_info = MODELS[model]
        if model_info["image"]:
            vid_path = image_path
            vid_ct = "image/" + ("png" if image_path.endswith(".png") else "jpeg")
        else:
            vid_path = os.path.join(temp_dir, "input.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-loop", "1", "-i", image_path,
                "-c:v", "libx264", "-t", "30", "-pix_fmt", "yuv420p",
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                vid_path
            ], capture_output=True, check=True)
            vid_ct = "video/mp4"

        print("[2/5] تحميل الملفات إلى sync.so...")
        vid_asset, err = _upload_asset(api_key, vid_path, vid_ct)
        if err:
            return None, err
        aud_ct = "audio/mpeg"
        if audio_path.endswith(".wav"):
            aud_ct = "audio/wav"
        aud_asset, err = _upload_asset(api_key, audio_path, aud_ct)
        if err:
            return None, err

        input_type = "image" if model_info["image"] else "video"
        payload = {
            "model": model,
            "input": [
                {"type": input_type, "assetId": vid_asset["id"]},
                {"type": "audio", "assetId": aud_asset["id"]}
            ]
        }
        if model == "react-1":
            opts = {}
            if model_mode:
                opts["model_mode"] = model_mode
            if opts:
                payload["options"] = opts

        print("[3/5] إرسال إلى sync.so API...")
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        resp = _request("POST", f"{BASE_URL}/generate", json=payload, headers=headers, timeout=60)
        if resp.status_code not in (200, 201):
            return None, f"API خطأ: {resp.text}"
        gen_id = resp.json()["id"]
        print(f"  Generation ID: {gen_id}")

        print("[4/5] انتظار النتيجة...")
        for i in range(60):
            time.sleep(5)
            try:
                status_resp = _request("GET", f"{BASE_URL}/generate/{gen_id}", headers=headers, timeout=20)
                data = status_resp.json()
                status = data.get("status")
            except:
                continue
            if i % 6 == 0:
                print(f"  Status: {status}")
            if status == "COMPLETED":
                output_url = data.get("outputUrl")
                if not output_url:
                    return None, "تم الإكمال ولكن لا يوجد رابط"
                break
            elif status in ("FAILED", "REJECTED"):
                err_msg = data.get("error", "فشل غير معروف")
                return None, f"فشل API: {err_msg}"
        else:
            return None, "انتهت مهلة الانتظار (5 دقائق)"

        print("[5/5] تحميل النتيجة...")
        vid_resp = _SESSION.get(output_url, timeout=180)
        with open(output_path, "wb") as f:
            f.write(vid_resp.content)
        print(f"تم: {output_path}")
        return output_path, None

    except Exception as e:
        return None, str(e)
    finally:
        for f in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, f))
            except:
                pass
        try:
            os.rmdir(temp_dir)
        except:
            pass
