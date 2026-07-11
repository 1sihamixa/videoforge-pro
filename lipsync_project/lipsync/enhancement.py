"""
Optional face enhancement after Wav2Lip using GFPGAN or CodeFormer.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy imports to avoid requiring heavy deps unless needed
_GFPGAN_AVAILABLE = False


def is_gfpgan_available() -> bool:
    global _GFPGAN_AVAILABLE
    if not _GFPGAN_AVAILABLE:
        try:
            import gfpgan  # noqa
            _GFPGAN_AVAILABLE = True
        except ImportError:
            pass
    return _GFPGAN_AVAILABLE


def enhance_with_gfpgan(input_video: str, output_video: str, upscale: int = 1) -> Optional[str]:
    """
    Enhance face regions in video frames using GFPGAN.
    Falls back to copying input if GFPGAN is not installed.
    """
    if not is_gfpgan_available():
        logger.warning("GFPGAN not installed, skipping enhancement. "
                       "Install with: pip install gfpgan")
        return None

    logger.info(f"Starting GFPGAN enhancement: {input_video} -> {output_video}")
    try:
        from gfpgan import GFPGANer
        import cv2
        import subprocess
        import tempfile

        # Extract frames to temp directory
        frame_dir = tempfile.mkdtemp(prefix="gfpgan_frames_")
        pattern = os.path.join(frame_dir, "frame_%06d.png")
        subprocess.run([
            "ffmpeg", "-y", "-i", input_video,
            "-q:v", "2", pattern
        ], capture_output=True, text=True, timeout=300)

        # Initialize GFPGAN
        model_path = None
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "checkpoints", "GFPGANv1.4.pth"),
            os.path.expanduser("~/.cache/gfpgan/GFPGANv1.4.pth"),
        ]
        for p in possible_paths:
            if os.path.exists(os.path.normpath(p)):
                model_path = os.path.normpath(p)
                break

        enhancer = GFPGANer(
            model_path=model_path,
            upscale=upscale,
            arch="clean",
            channel_multiplier=2,
            bg_upsampler=None,
        )

        out_frame_dir = tempfile.mkdtemp(prefix="gfpgan_enhanced_")
        frame_files = sorted(os.listdir(frame_dir))
        total = len(frame_files)
        logger.info(f"Enhancing {total} frames...")

        for i, fname in enumerate(frame_files):
            in_path = os.path.join(frame_dir, fname)
            img = cv2.imread(in_path, cv2.IMREAD_COLOR)
            if img is None:
                continue
            _, _, enhanced = enhancer.enhance(img, has_aligned=False, only_center_face=False, paste_back=True)
            out_path = os.path.join(out_frame_dir, fname)
            cv2.imwrite(out_path, enhanced)
            if (i + 1) % 50 == 0:
                logger.debug(f"  {i + 1}/{total} frames")

        # Reassemble video
        fps = 25
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", os.path.join(out_frame_dir, "frame_%06d.png"),
            "-i", input_video,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            "-shortest", "-movflags", "+faststart",
            output_video
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        # Cleanup
        for d in [frame_dir, out_frame_dir]:
            for f in os.listdir(d):
                try:
                    os.remove(os.path.join(d, f))
                except Exception:
                    pass
            try:
                os.rmdir(d)
            except Exception:
                pass

        if os.path.exists(output_video) and os.path.getsize(output_video) > 10000:
            logger.info(f"Enhanced video saved: {output_video}")
            return output_video
        return None

    except Exception as e:
        logger.error(f"GFPGAN enhancement failed: {e}")
        return None


def enhance_video(input_video: str, output_video: str, method: str = "gfpgan", upscale: int = 1) -> Optional[str]:
    if method == "gfpgan":
        return enhance_with_gfpgan(input_video, output_video, upscale)
    logger.warning(f"Unknown enhancement method: {method}")
    return None
