import os, sys, tempfile, shutil, subprocess
import numpy as np
import cv2
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Wav2Lip"))
from models import Wav2Lip
import audio as wav2lip_audio

device = "cpu"
mel_step_size = 16
CHECKPOINT_PATH = os.path.join(os.path.dirname(__file__), "Wav2Lip", "checkpoints", "wav2lip_gan.pth")


def load_model(path):
    model = Wav2Lip()
    checkpoint = torch.load(path, map_location=lambda storage, loc: storage)
    s = checkpoint["state_dict"]
    s = {k.replace("module.", ""): v for k, v in s.items()}
    model.load_state_dict(s)
    return model.to(device).eval()


def get_smoothened_boxes(boxes, T):
    for i in range(len(boxes)):
        if i + T > len(boxes):
            window = boxes[len(boxes) - T:]
        else:
            window = boxes[i: i + T]
        boxes[i] = np.mean(window, axis=0)
    return boxes


def face_detect_haar(images, pads=[0, 10, 0, 0]):
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
    boxes = np.array(results)
    boxes = get_smoothened_boxes(boxes, T=5)
    return [[image[y1:y2, x1:x2], (y1, y2, x1, x2)] for image, (x1, y1, x2, y2) in zip(images, boxes)]


def datagen(frames, mels, static, img_size=96, batch_size=128, pads=None):
    if pads is None:
        pads = [0, 10, 0, 0]
    img_batch, mel_batch, frame_batch, coords_batch = [], [], [], []
    face_det_results = face_detect_haar([frames[0]], pads=pads)
    for i, m in enumerate(mels):
        idx = 0 if static else i % len(frames)
        frame_to_save = frames[idx].copy()
        face, coords = face_det_results[idx].copy()
        face = cv2.resize(face, (img_size, img_size))
        img_batch.append(face)
        mel_batch.append(m)
        frame_batch.append(frame_to_save)
        coords_batch.append(coords)
        if len(img_batch) >= batch_size:
            img_batch, mel_batch = np.asarray(img_batch), np.asarray(mel_batch)
            img_masked = img_batch.copy()
            img_masked[:, img_size // 2:] = 0
            img_batch = np.concatenate((img_masked, img_batch), axis=3) / 255.0
            mel_batch = np.reshape(mel_batch, [len(mel_batch), mel_batch.shape[1], mel_batch.shape[2], 1])
            yield img_batch, mel_batch, frame_batch, coords_batch
            img_batch, mel_batch, frame_batch, coords_batch = [], [], [], []
    if len(img_batch) > 0:
        img_batch, mel_batch = np.asarray(img_batch), np.asarray(mel_batch)
        img_masked = img_batch.copy()
        img_masked[:, img_size // 2:] = 0
        img_batch = np.concatenate((img_masked, img_batch), axis=3) / 255.0
        mel_batch = np.reshape(mel_batch, [len(mel_batch), mel_batch.shape[1], mel_batch.shape[2], 1])
        yield img_batch, mel_batch, frame_batch, coords_batch


def generate_video(image_path, audio_path, output_path, fps=25, checkpoint_path=None, pads=None):
    if pads is None:
        pads = [0, 10, 0, 0]
    if not os.path.exists(image_path):
        print(f"ERROR: Image not found: {image_path}")
        return None
    if not os.path.exists(audio_path):
        print(f"ERROR: Audio not found: {audio_path}")
        return None
    if not checkpoint_path:
        checkpoint_path = CHECKPOINT_PATH
    if not os.path.exists(checkpoint_path):
        alt = checkpoint_path.replace(".pth", ".pt")
        if os.path.exists(alt):
            checkpoint_path = alt
        else:
            alt2 = checkpoint_path.replace("wav2lip_gan.pth", "wav2lip.pth")
            if os.path.exists(alt2):
                checkpoint_path = alt2
            else:
                print(f"ERROR: Model not found at {checkpoint_path}")
                return None

    temp_dir = tempfile.mkdtemp(prefix="wav2lip_")
    try:
        print("[1/4] Loading image...")
        frame = cv2.imread(image_path)
        if frame is None:
            print("ERROR: Could not read image")
            return None
        h, w = frame.shape[:2]
        max_dim = 1024
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h))
            h, w = frame.shape[:2]
            print(f"  Resized: {w}x{h} (was {w//scale}x{h//scale})")
        else:
            print(f"  Image: {w}x{h}")

        print("[2/4] Preparing audio and mel spectrograms...")
        if not audio_path.endswith(".wav"):
            wav_path = os.path.join(temp_dir, "temp.wav")
            subprocess.run(["ffmpeg", "-y", "-i", audio_path, "-strict", "-2", wav_path],
                          capture_output=True, check=True)
            audio_path_wav = wav_path
        else:
            audio_path_wav = audio_path

        wav_data = wav2lip_audio.load_wav(audio_path_wav, 16000)
        mel = wav2lip_audio.melspectrogram(wav_data)
        if np.isnan(mel.reshape(-1)).sum() > 0:
            mel = np.nan_to_num(mel)
        mel_chunks = []
        mel_idx_multiplier = 80.0 / fps
        i = 0
        while True:
            start_idx = int(i * mel_idx_multiplier)
            if start_idx + mel_step_size > len(mel[0]):
                mel_chunks.append(mel[:, len(mel[0]) - mel_step_size:])
                break
            mel_chunks.append(mel[:, start_idx: start_idx + mel_step_size])
            i += 1
        print(f"  Mel chunks: {len(mel_chunks)}")

        full_frames = [frame] * len(mel_chunks)
        if len(full_frames) == 0:
            print("ERROR: No frames")
            return None

        gen = datagen(full_frames.copy(), mel_chunks, static=True, pads=pads)
        model = load_model(checkpoint_path)
        print("[3/4] Generating Wav2Lip video...")

        avi_path = os.path.join(temp_dir, "result.avi")
        out = cv2.VideoWriter(avi_path, cv2.VideoWriter_fourcc(*"DIVX"), fps, (w, h))
        frame_idx = 0

        for img_batch, mel_batch, frames, coords in gen:
            t = torch.FloatTensor(np.transpose(img_batch, (0, 3, 1, 2))).to(device)
            m = torch.FloatTensor(np.transpose(mel_batch, (0, 3, 1, 2))).to(device)
            with torch.no_grad():
                pred = model(m, t)
            pred = pred.cpu().numpy().transpose(0, 2, 3, 1) * 255.0
            for p, f, c in zip(pred, frames, coords):
                y1, y2, x1, x2 = c
                p = cv2.resize(p.astype(np.uint8), (x2 - x1, y2 - y1))
                f[y1:y2, x1:x2] = p
                out.write(f)
                frame_idx += 1

        out.release()
        print(f"  Wrote {frame_idx} frames")

        print("[4/4] Muxing audio...")
        subprocess.run([
            "ffmpeg", "-y", "-i", audio_path, "-i", avi_path,
            "-strict", "-2", "-q:v", "1", output_path
        ], capture_output=True, check=True)
        print(f"Done: {output_path}")
        return output_path

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Wav2Lip - تحريك الشفاه فقط")
    parser.add_argument("image", help="صورة الوجه")
    parser.add_argument("audio", help="ملف الصوت")
    parser.add_argument("output", help="ملف الفيديو الناتج")
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--pads", type=int, nargs=4, default=[0, 10, 0, 0],
                        metavar=("TOP", "BOTTOM", "LEFT", "RIGHT"),
                        help="Padding حول الوجه (بكسل) — default: 0 10 0 0")
    args = parser.parse_args()
    result = generate_video(args.image, args.audio, args.output, fps=args.fps, pads=args.pads)
    if not result:
        sys.exit(1)
