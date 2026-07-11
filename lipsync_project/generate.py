#!/usr/bin/env python3
"""
CLI entry point for Wav2Lip lip-sync video generation.

Usage:
    python generate.py --face samples/face.jpg --audio samples/audio.mp3
    python generate.py --face samples/face.mp4 --audio samples/audio.wav --enhance
"""
import os
import sys
import argparse
import logging
import yaml

from lipsync import LipSyncPipeline


def load_config(path: str = "config.yaml") -> dict:
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def setup_logging(level: str = "INFO", log_file: str = None):
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO),
                        format=fmt, handlers=handlers)


def main():
    parser = argparse.ArgumentParser(
        description="Wav2Lip Lip-Sync Video Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate.py --face face.jpg --audio speech.mp3
  python generate.py --face video.mp4 --audio audio.wav --output ./my_video.mp4
  python generate.py --face face.jpg --audio speech.mp3 --enhance --fps 30
        """
    )
    parser.add_argument("--face", required=True, help="Path to face image or video")
    parser.add_argument("--audio", required=True, help="Path to audio file (mp3/wav)")
    parser.add_argument("--output", "-o", help="Output path (default: static/videos/wav2lip_alternate_<uuid>.mp4)")
    parser.add_argument("--output-dir", help="Output directory (default: static/videos/)")
    parser.add_argument("--fps", type=int, default=25, help="Output frame rate (default: 25)")
    parser.add_argument("--pads", nargs=4, type=int, default=[20, 10, 10, 10],
                        help="Face detection padding: top bottom left right")
    parser.add_argument("--enhance", action="store_true", help="Apply GFPGAN face enhancement")
    parser.add_argument("--enhance-method", default="gfpgan", choices=["gfpgan"],
                        help="Enhancement method (default: gfpgan)")
    parser.add_argument("--checkpoint", help="Path to Wav2Lip checkpoint file")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging level (default: INFO)")
    args = parser.parse_args()

    cfg = load_config()
    log_cfg = cfg.get("logging", {})
    setup_logging(args.log_level or log_cfg.get("level", "INFO"),
                  log_cfg.get("file"))

    logging.getLogger().info("Starting Wav2Lip generation...")
    logging.getLogger().info(f"Arguments: face={args.face}, audio={args.audio}")

    pipeline = LipSyncPipeline(checkpoint_path=args.checkpoint, config=cfg)

    output_path, error = pipeline.generate(
        face_path=args.face,
        audio_path=args.audio,
        output_dir=args.output_dir,
        pads=args.pads,
        fps=args.fps,
        enable_enhancement=args.enhance,
        enhancement_method=args.enhance_method,
    )

    if error:
        logging.getLogger().error(f"Failed: {error}")
        sys.exit(1)
    else:
        logging.getLogger().info(f"Success: {output_path}")
        print(f"\n✅ Video generated: {output_path}")


if __name__ == "__main__":
    main()
