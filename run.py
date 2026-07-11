#!/usr/bin/env python3
"""
VideoForge Pro - Wav2Lip Avatar Generator
تشغيل موقع VideoForge Pro على الخادم المحلي أو السحابي

الاستخدام:
    python run.py               # تشغيل عادي
    python run.py --port 8080   # تغيير المنفذ
    python run.py --host 0.0.0.0  # استماع على كل الواجهات
"""
import os
import sys
import argparse

# Fix Windows console encoding for Arabic/emoji
if sys.platform == "win32":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VideoForge Pro Server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)),
                       help="منفذ الخادم (افتراضي: 5000)")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                       help="المضيف (افتراضي: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true",
                       help="وضع التصحيح")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv()

    from app import app

    print("=" * 60)
    print("  VideoForge Pro v2.0 - Wav2Lip Talking Avatar")
    print("=" * 60)
    print(f"  [WEB] http://{args.host}:{args.port}")
    print(f"  [ADMIN] http://{args.host}:{args.port}/admin")
    print(f"  [DEPLOY] gunicorn app:app")
    print("=" * 60)

    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
