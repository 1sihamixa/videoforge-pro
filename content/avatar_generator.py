"""
Avatar video generator using Wav2Lip (optional, requires GPU).
Takes a face image + audio and produces a talking head video.

NOTE: This module is optional and requires:
- torch + torchvision (GPU recommended)
- Wav2Lip model weights
- The user is responsible for ensuring persona images are owned/licensed.
"""

import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

WAV2LIP_CHECKPOINT = Path(__file__).resolve().parent.parent / "Wav2Lip" / "checkpoints" / "wav2lip_gan.pth"
WAV2LIP_SCRIPT = Path(__file__).resolve().parent.parent / "Wav2Lip" / "inference.py"


def is_gpu_available() -> bool:
    """Check if CUDA GPU is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def is_wav2lip_available() -> bool:
    """Check if Wav2Lip model and dependencies are available."""
    return (
        WAV2LIP_CHECKPOINT.exists() and
        WAV2LIP_SCRIPT.exists() and
        is_gpu_available()
    )


class AvatarGenerator:
    """
    Generates talking head videos using Wav2Lip.
    Only functional when GPU is available and Wav2Lip is installed.
    """

    def __init__(self, output_dir: str = "temp"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.gpu_available = is_gpu_available()
        self.wav2lip_ready = is_wav2lip_available()

        if not self.gpu_available:
            logger.warning(
                "GPU not available. AvatarGenerator will not function. "
                "Use 'faceless' video style instead."
            )
        if self.gpu_available and not self.wav2lip_ready:
            logger.warning(
                "GPU available but Wav2Lip not found. "
                f"Expected checkpoint at: {WAV2LIP_CHECKPOINT}"
            )

    def generate(self, face_image_path: str, audio_path: str,
                 output_filename: Optional[str] = None) -> str:
        """
        Generate a talking head video from a face image and audio.

        Args:
            face_image_path: Path to the face image (jpg/png)
            audio_path: Path to the audio file (wav/mp3)
            output_filename: Custom output filename (optional)

        Returns:
            Path to the generated video file.

        Raises:
            RuntimeError: If GPU or Wav2Lip is not available.
        """
        if not self.gpu_available:
            raise RuntimeError(
                "Cannot generate avatar video: GPU not available. "
                "Use 'faceless' content style or install CUDA-capable GPU."
            )
        if not self.wav2lip_ready:
            raise RuntimeError(
                "Cannot generate avatar video: Wav2Lip not found. "
                f"Ensure checkpoint exists at: {WAV2LIP_CHECKPOINT}"
            )

        face_path = Path(face_image_path)
        audio = Path(audio_path)

        if not face_path.exists():
            raise FileNotFoundError(f"Face image not found: {face_path}")
        if not audio.exists():
            raise FileNotFoundError(f"Audio file not found: {audio}")

        out_name = output_filename or f"avatar_{face_path.stem}_{audio.stem}.mp4"
        output_path = self.output_dir / out_name

        logger.info(f"Generating avatar video: {face_path.name} + {audio.name}")

        try:
            cmd = [
                "python", str(WAV2LIP_SCRIPT),
                "--checkpoint_path", str(WAV2LIP_CHECKPOINT),
                "--face", str(face_path),
                "--audio", str(audio),
                "--outfile", str(output_path),
                "--nosmooth",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(WAV2LIP_CHECKPOINT.parent.parent),
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Wav2Lip failed: {result.stderr[:500]}"
                )

            if not output_path.exists():
                raise RuntimeError("Wav2Lip completed but output file not created")

            logger.info(f"Avatar video generated: {output_path}")
            return str(output_path)

        except subprocess.TimeoutExpired:
            raise RuntimeError("Wav2Lip timed out after 300 seconds")
        except Exception as e:
            logger.error(f"Avatar generation failed: {e}")
            raise

    def get_status(self) -> dict:
        """Get the status of avatar generation capability."""
        return {
            "gpu_available": self.gpu_available,
            "wav2lip_checkpoint_exists": WAV2LIP_CHECKPOINT.exists(),
            "wav2lip_script_exists": WAV2LIP_SCRIPT.exists,
            "ready": self.wav2lip_ready and self.gpu_available,
            "checkpoint_path": str(WAV2LIP_CHECKPOINT),
        }
