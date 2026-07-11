"""
Main pipeline orchestrator for Wav2Lip lip-sync video generation.
"""
import os
import sys
import uuid
import logging
from typing import Optional, Tuple

from . import inference
from . import audio_utils
from . import video_utils
from . import enhancement

logger = logging.getLogger(__name__)

# Path to Wav2Lip checkpoint (reuse existing if available)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CHECKPOINT = os.path.join(BASE_DIR, "..", "Wav2Lip", "checkpoints", "wav2lip_gan.pth")
DEFAULT_CHECKPOINT = os.path.normpath(DEFAULT_CHECKPOINT)
FALLBACK_CHECKPOINT = os.path.join(BASE_DIR, "checkpoints", "wav2lip_gan.pth")


def _resolve_checkpoint(custom_path: Optional[str] = None) -> str:
    if custom_path and os.path.exists(custom_path):
        return custom_path
    if os.path.exists(DEFAULT_CHECKPOINT):
        return DEFAULT_CHECKPOINT
    if os.path.exists(FALLBACK_CHECKPOINT):
        return FALLBACK_CHECKPOINT
    return FALLBACK_CHECKPOINT  # will trigger download


def download_checkpoint(target_path: str) -> bool:
    """Download Wav2Lip checkpoint if not present."""
    if os.path.exists(target_path):
        logger.info(f"Checkpoint already exists: {target_path}")
        return True
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    url = "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0.0/wav2lip_gan.pth"
    logger.info(f"Downloading checkpoint from {url}...")
    try:
        import urllib.request
        urllib.request.urlretrieve(url, target_path)
        if os.path.exists(target_path) and os.path.getsize(target_path) > 1_000_000:
            logger.info(f"Downloaded: {target_path} ({os.path.getsize(target_path)} bytes)")
            return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
    return False


class LipSyncPipeline:
    def __init__(self, checkpoint_path: Optional[str] = None, config: Optional[dict] = None):
        self.config = config or {}
        ckpt = _resolve_checkpoint(checkpoint_path)
        if not os.path.exists(ckpt):
            logger.info("Checkpoint not found, attempting download...")
            download_checkpoint(ckpt)
        self.checkpoint_path = ckpt
        self.model = None

    def _load_model(self):
        if self.model is None:
            self.model = inference.load_model(self.checkpoint_path)

    def generate(self, face_path: str, audio_path: str,
                 output_dir: Optional[str] = None,
                 pads: Optional[list] = None,
                 fps: int = 25,
                 enable_enhancement: bool = False,
                 enhancement_method: str = "gfpgan") -> Tuple[Optional[str], Optional[str]]:
        """
        Generate lip-sync video from face image/video and audio.

        Args:
            face_path: Path to face image or video
            audio_path: Path to audio file (mp3, wav, etc.)
            output_dir: Directory for output video (default: static/videos/)
            pads: Face detection padding [top, bottom, left, right]
            fps: Output video frame rate
            enable_enhancement: Apply GFPGAN face enhancement after Wav2Lip
            enhancement_method: "gfpgan" or "codeformer"

        Returns:
            (output_path, error_message)
        """
        # Validate inputs
        logger.info("=" * 60)
        logger.info("LipSync Pipeline started")
        logger.info(f"  Face: {face_path}")
        logger.info(f"  Audio: {audio_path}")
        logger.info("=" * 60)

        if not audio_utils.validate_audio(audio_path):
            return None, f"Invalid audio file: {audio_path}"

        if not video_utils.validate_face_image(face_path):
            return None, f"Invalid face file: {face_path}"

        # Resolve output directory
        out_dir = output_dir or os.path.join(BASE_DIR, "static", "videos")
        os.makedirs(out_dir, exist_ok=True)

        output_filename = f"wav2lip_alternate_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(out_dir, output_filename)

        # Prepare temp paths
        temp_dir = os.path.join(BASE_DIR, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        raw_output = os.path.join(temp_dir, f"raw_{uuid.uuid4().hex[:8]}.mp4")
        enhanced_output = os.path.join(temp_dir, f"enhanced_{uuid.uuid4().hex[:8]}.mp4")

        try:
            # Load model
            self._load_model()

            # Run Wav2Lip inference
            logger.info("Step 1/3: Running Wav2Lip inference...")
            inference.run_inference(
                model=self.model,
                face_path=face_path,
                audio_path=audio_path,
                output_path=output_path,
                pads=pads or self.config.get("face_detection", {}).get("pads", [20, 10, 10, 10]),
                fps=fps
            )
            logger.info(f"Step 1/3 complete: {output_path}")

            # Optional enhancement
            if enable_enhancement:
                logger.info("Step 2/3: Running face enhancement...")
                enh_result = enhancement.enhance_video(
                    output_path, enhanced_output,
                    method=enhancement_method,
                    upscale=self.config.get("enhancement", {}).get("upscale", 1)
                )
                if enh_result and os.path.exists(enhanced_output):
                    os.replace(enhanced_output, output_path)
                    logger.info("Step 2/3 complete: enhancement applied")
                else:
                    logger.info("Step 2/3 skipped: enhancement unavailable")
            else:
                logger.info("Step 2/3 skipped: enhancement disabled")

            # Verify final output
            if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
                logger.info("Step 3/3: Pipeline complete")
                info = video_utils.get_video_info(output_path)
                if info:
                    logger.info(f"  Resolution: {info.get('width')}x{info.get('height')}")
                    logger.info(f"  FPS: {info.get('r_frame_rate')}")
                logger.info(f"  Size: {os.path.getsize(output_path)} bytes")
                logger.info(f"  Output: {output_path}")
                return output_path, None

            return None, "Output file is missing or too small"

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            # Cleanup partial output
            for p in [output_path, raw_output, enhanced_output]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            return None, str(e)

        finally:
            # Cleanup temp files
            for p in [raw_output, enhanced_output]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
