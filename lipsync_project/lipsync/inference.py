"""
Core Wav2Lip inference module.
Wraps the original Wav2Lip inference loop with better logging and error handling.
"""
import os
import sys
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
import torch

logger = logging.getLogger(__name__)

WAV2LIP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "Wav2Lip")
WAV2LIP_DIR = os.path.normpath(WAV2LIP_DIR)
sys.path.insert(0, WAV2LIP_DIR)

try:
    from models import Wav2Lip as Wav2LipModel
    import audio as w2l_audio
except ImportError as e:
    logger.error(f"Failed to import Wav2Lip modules from {WAV2LIP_DIR}: {e}")
    raise

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MEL_STEP_SIZE = 16


def load_model(checkpoint_path: str) -> torch.nn.Module:
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Wav2Lip checkpoint not found: {checkpoint_path}")
    logger.info(f"Loading Wav2Lip model from {checkpoint_path} on {DEVICE}")
    model = Wav2LipModel()
    state = torch.load(checkpoint_path, map_location="cpu")
    state_dict = state.get("state_dict", state)
    state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
    model.load_state_dict(state_dict)
    model = model.to(DEVICE).eval()
    logger.info("Model loaded successfully")
    return model


def _smooth_boxes(boxes: np.ndarray, T: int = 5) -> np.ndarray:
    for i in range(len(boxes)):
        window = boxes[max(0, i): min(len(boxes), i + T)]
        boxes[i] = np.mean(window, axis=0)
    return boxes


def _detect_faces(images: list, pads: list = None) -> list:
    import face_detection
    if pads is None:
        pads = [0, 10, 0, 0]
    detector = face_detection.FaceAlignment(face_detection.LandmarksType._2D, flip_input=False, device=DEVICE)
    batch_size = min(8, len(images))
    results = []
    for i in range(0, len(images), batch_size):
        batch = images[i:i + batch_size]
        preds = detector.get_detections_for_batch(np.array(batch))
        for j, pred in enumerate(preds):
            if pred is None:
                h, w = images[i + j].shape[:2]
                cx, cy = w // 2, h // 2
                box = min(w, h) // 2
                x1, y1, x2, y2 = cx - box // 2, cy - box // 2, cx + box // 2, cy + box // 2
            else:
                x1, y1, x2, y2 = pred
            y1 = max(0, y1 - pads[0])
            y2 = min(images[i + j].shape[0], y2 + pads[1])
            x1 = max(0, x1 - pads[2])
            x2 = min(images[i + j].shape[1], x2 + pads[3])
            results.append([x1, y1, x2, y2])
    boxes = _smooth_boxes(np.array(results), T=5)
    return [
        [image[y1:y2, x1:x2], (y1, y2, x1, x2)]
        for image, (x1, y1, x2, y2) in zip(images, boxes)
    ]


def _detect_faces_haar(images: list, pads: list = None) -> list:
    if pads is None:
        pads = [0, 10, 0, 0]
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    results = []
    for img in images:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(50, 50))
        if len(faces) == 0:
            h, w = img.shape[:2]
            cx, cy = w // 2, h // 2
            box = min(w, h) // 2
            x1, y1, x2, y2 = cx - box // 2, cy - box // 2, cx + box // 2, cy + box // 2
        else:
            x, y, bw, bh = max(faces, key=lambda f: f[2] * f[3])
            x1, y1, x2, y2 = x, y, x + bw, y + bh
        y1 = max(0, y1 - pads[0])
        y2 = min(img.shape[0], y2 + pads[1])
        x1 = max(0, x1 - pads[2])
        x2 = min(img.shape[1], x2 + pads[3])
        results.append([x1, y1, x2, y2])
    return [
        [image[y1:y2, x1:x2], (y1, y2, x1, x2)]
        for image, (x1, y1, x2, y2) in zip(images, results)
    ]


def _data_gen(frames: list, mels: np.ndarray, static: bool,
              img_size: int = 96, batch_size: int = 128, pads: list = None):
    if pads is None:
        pads = [0, 10, 0, 0]
    try:
        face_data = _detect_faces([frames[0]], pads=pads)
    except Exception:
        logger.warning("Wav2Lip face detection failed, falling back to Haar cascade")
        face_data = _detect_faces_haar([frames[0]], pads=pads)
    img_batch, mel_batch, frame_batch, coord_batch = [], [], [], []
    for i, m in enumerate(mels):
        idx = 0 if static else i % len(frames)
        frame = frames[idx].copy()
        face, coords = face_data[idx]
        face = cv2.resize(face, (img_size, img_size))
        img_batch.append(face)
        mel_batch.append(m)
        frame_batch.append(frame)
        coord_batch.append(coords)
        if len(img_batch) >= batch_size:
            imgs = np.asarray(img_batch)
            mels_arr = np.asarray(mel_batch)
            masked = imgs.copy()
            masked[:, img_size // 2:] = 0
            imgs_in = np.concatenate((masked, imgs), axis=3) / 255.0
            mels_arr = mels_arr.reshape(len(mels_arr), mels_arr.shape[1], mels_arr.shape[2], 1)
            yield imgs_in, mels_arr, frame_batch, coord_batch
            img_batch, mel_batch, frame_batch, coord_batch = [], [], [], []
    if img_batch:
        imgs = np.asarray(img_batch)
        mels_arr = np.asarray(mel_batch)
        masked = imgs.copy()
        masked[:, img_size // 2:] = 0
        imgs_in = np.concatenate((masked, imgs), axis=3) / 255.0
        mels_arr = mels_arr.reshape(len(mels_arr), mels_arr.shape[1], mels_arr.shape[2], 1)
        yield imgs_in, mels_arr, frame_batch, coord_batch


def run_inference(model: torch.nn.Module,
                  face_path: str,
                  audio_path: str,
                  output_path: str,
                  pads: list = None,
                  img_size: int = 96,
                  batch_size: int = 128,
                  fps: int = 25,
                  face_detection_method: str = "wav2lip") -> str:
    logger.info(f"Starting inference: face={face_path}, audio={audio_path}")
    if pads is None:
        pads = [20, 10, 10, 10]

    # Read input frames
    if face_path.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
        static = True
        img = cv2.imread(face_path)
        if img is None:
            raise ValueError(f"Cannot read image: {face_path}")
        frames = [img]
        logger.info("Static image mode (single frame)")
    elif face_path.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        static = False
        cap = cv2.VideoCapture(face_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {face_path}")
        orig_fps = cap.get(cv2.CAP_PROP_FPS) or fps
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()
        logger.info(f"Video mode: {len(frames)} frames @ {orig_fps:.2f} fps")
    else:
        raise ValueError(f"Unsupported face file format: {face_path}")

    # Extract mel-spectrogram from audio
    logger.info("Extracting mel-spectrogram from audio...")
    wav_data = w2l_audio.load_wav(audio_path, 16000)
    mel = w2l_audio.melspectrogram(wav_data)
    if mel.shape[1] < MEL_STEP_SIZE:
        raise ValueError(f"Audio too short: {mel.shape[1]} mel frames (need >= {MEL_STEP_SIZE})")
    mel_chunks = []
    mel_idx_multiplier = 80.0 / fps
    i = 0
    while True:
        start_idx = int(i * mel_idx_multiplier)
        if start_idx + MEL_STEP_SIZE > mel.shape[1]:
            break
        mel_chunks.append(mel[:, start_idx: start_idx + MEL_STEP_SIZE])
        i += 1
    logger.info(f"Generated {len(mel_chunks)} mel chunks for {len(frames)} frames")
    total_frames = len(mel_chunks)
    if total_frames > len(frames) and not static:
        logger.warning(f"More audio frames ({total_frames}) than video frames ({len(frames)}), truncating")
        total_frames = len(frames)
        mel_chunks = mel_chunks[:total_frames]

    # Create temp file for raw output
    fd, raw_out = tempfile.mkstemp(suffix=".mp4", dir=os.path.dirname(output_path))
    os.close(fd)
    writer = None

    try:
        gen = _data_gen(frames, mel_chunks, static, img_size=img_size, batch_size=batch_size, pads=pads)
        frame_h, frame_w = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(raw_out, fourcc, fps, (frame_w, frame_h))
        processed = 0

        for img_batch, mel_batch, frame_batch, coord_batch in gen:
            # Wav2Lip expects NCHW (batch, channels, height, width)
            # Our batches are NHWC, so transpose
            img_batch_t = torch.FloatTensor(np.transpose(img_batch, (0, 3, 1, 2))).to(DEVICE)
            mel_batch_t = torch.FloatTensor(np.transpose(mel_batch, (0, 3, 1, 2))).to(DEVICE)
            with torch.no_grad():
                pred = model(mel_batch_t, img_batch_t)
            pred = pred.cpu().numpy().transpose(0, 2, 3, 1) * 255.0
            for pl, f, coords in zip(pred, frame_batch, coord_batch):
                y1, y2, x1, x2 = coords
                pred_face = cv2.resize(pl, (x2 - x1, y2 - y1))
                f[y1:y2, x1:x2] = pred_face
                writer.write(f)
                processed += 1
            pct = processed / total_frames * 100
            logger.debug(f"  {processed}/{total_frames} frames ({pct:.1f}%)")

        writer.release()
        logger.info(f"Raw output: {processed} frames written to {raw_out}")

        if not os.path.exists(raw_out) or os.path.getsize(raw_out) < 1000:
            raise RuntimeError("Raw output is empty or too small")

        # Remux with audio using ffmpeg
        logger.info("Muxing audio with ffmpeg...")
        cmd = [
            "ffmpeg", "-y",
            "-i", raw_out,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg muxing failed: {result.stderr[:200]}")

        if not os.path.exists(output_path) or os.path.getsize(output_path) < 10000:
            raise RuntimeError("Final output is missing or too small")

        logger.info(f"Output saved: {output_path} ({os.path.getsize(output_path)} bytes)")
        return output_path

    except Exception as e:
        logger.error(f"Inference failed: {e}")
        if writer is not None:
            writer.release()
            writer = None
        if os.path.exists(raw_out):
            try:
                os.remove(raw_out)
            except Exception:
                pass
        raise

    finally:
        if writer is not None:
            writer.release()
        if os.path.exists(raw_out):
            try:
                os.remove(raw_out)
            except Exception:
                pass
