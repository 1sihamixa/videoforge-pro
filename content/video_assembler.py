"""
Video assembler using MoviePy and FFmpeg.
Combines audio + visuals + subtitles into final video.
Supports: faceless (stock footage) and avatar_talking (Wav2Lip output).
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

try:
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, ImageClip,
        TextClip, CompositeVideoClip, concatenate_videoclips,
        ColorClip
    )
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("moviepy not installed. pip install moviepy")


class VideoAssembler:
    """Assembles final video from audio, visuals, and subtitles."""

    def __init__(self, output_dir: str = "output", temp_dir: str = "temp"):
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(temp_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        if not MOVIEPY_AVAILABLE:
            logger.warning("MoviePy not available. Video assembly will use FFmpeg only.")

    def _probe_video(self, path: str) -> dict:
        """Get video metadata using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                str(path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            data = json.loads(result.stdout)
            duration = float(data.get("format", {}).get("duration", 0))
            streams = data.get("streams", [])
            width, height = 1920, 1080
            for s in streams:
                if s.get("codec_type") == "video":
                    width = s.get("width", 1920)
                    height = s.get("height", 1080)
                    break
            return {"duration": duration, "width": width, "height": height}
        except Exception as e:
            logger.warning(f"ffprobe failed: {e}")
            return {"duration": 0, "width": 1920, "height": 1080}

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of an audio file."""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def assemble_faceless(self, audio_paths: List[str],
                          video_paths: List[str],
                          title: str = "",
                          output_filename: str = "final_video.mp4",
                          resolution: tuple = (1080, 1920)) -> str:
        """
        Assemble a faceless video: stock footage + voiceover.
        Loops stock footage to match audio duration.

        Args:
            audio_paths: List of audio segment files
            video_paths: List of stock video clips
            title: Video title (for optional overlay)
            output_filename: Output filename
            resolution: (width, height) tuple

        Returns:
            Path to the assembled video
        """
        if not MOVIEPY_AVAILABLE:
            return self._assemble_ffmpeg(
                audio_paths, video_paths, output_filename
            )

        output_path = self.output_dir / output_filename

        # Calculate total audio duration
        total_duration = sum(self._get_audio_duration(a) for a in audio_paths)
        if total_duration == 0:
            raise ValueError("Total audio duration is 0. Check audio files.")

        logger.info(f"Assembling faceless video: {total_duration:.1f}s audio")

        # Concatenate audio
        from moviepy.editor import concatenate_audioclips
        audio_clips = [AudioFileClip(a) for a in audio_paths if Path(a).exists()]
        if not audio_clips:
            raise ValueError("No valid audio files found")

        final_audio = concatenate_audioclips(audio_clips)

        # Loop video clips to fill duration
        video_clips = []
        for vp in video_paths:
            if Path(vp).exists():
                try:
                    clip = VideoFileClip(vp)
                    if clip.duration > 0:
                        video_clips.append(clip)
                except Exception:
                    continue

        if not video_clips:
            # Fallback: create a solid color background
            logger.warning("No valid video clips, creating solid background")
            background = ColorClip(
                size=resolution, color=(15, 15, 25), duration=total_duration
            )
        else:
            # Loop clips to fill duration
            looped = []
            current_duration = 0
            idx = 0
            while current_duration < total_duration:
                clip = video_clips[idx % len(video_clips)].copy()
                clip = clip.resize(newresolution=resolution)
                looped.append(clip)
                current_duration += clip.duration
                idx += 1
            background = concatenate_videoclips(looped).subclip(0, total_duration)

        # Ensure correct resolution
        background = background.resize(newresolution=resolution)

        # Overlay audio
        final = background.set_audio(final_audio)

        # Write output
        final.write_videofile(
            str(output_path),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None  # Suppress moviepy logger
        )

        # Cleanup
        final_audio.close()
        for c in video_clips:
            try:
                c.close()
            except Exception:
                pass

        logger.info(f"Faceless video assembled: {output_path}")
        return str(output_path)

    def _assemble_ffmpeg(self, audio_paths: List[str],
                         video_paths: List[str],
                         output_filename: str) -> str:
        """
        Fallback assembly using FFmpeg directly when MoviePy is not available.
        """
        output_path = self.output_dir / output_filename

        # Concatenate audio
        audio_list = self.temp_dir / "audio_list.txt"
        with open(audio_list, "w") as f:
            for ap in audio_paths:
                f.write(f"file '{Path(ap).resolve()}'\n")

        merged_audio = self.temp_dir / "merged_audio.mp3"
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(audio_list), "-c", "copy", str(merged_audio)
        ], capture_output=True, timeout=60)

        # Get audio duration
        duration = self._get_audio_duration(str(merged_audio))

        # Use first video clip looped
        if video_paths and Path(video_paths[0]).exists():
            cmd = [
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", video_paths[0],
                "-i", str(merged_audio),
                "-t", str(duration),
                "-c:v", "libx264", "-c:a", "aac",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                "-shortest",
                str(output_path)
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=0x0F0F19:s=1080x1920:d={duration}",
                "-i", str(merged_audio),
                "-c:v", "libx264", "-c:a", "aac",
                "-shortest",
                str(output_path)
            ]

        subprocess.run(cmd, capture_output=True, timeout=120)
        logger.info(f"FFmpeg assembly complete: {output_path}")
        return str(output_path)

    def add_subtitles(self, video_path: str, srt_path: str,
                      output_filename: Optional[str] = None) -> str:
        """Burn subtitles into a video using FFmpeg."""
        output = Path(output_filename or video_path).with_name(
            Path(video_path).stem + "_subtitled.mp4"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"subtitles={srt_path}:force_style='FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2'",
            "-c:v", "libx264", "-c:a", "copy",
            str(output)
        ]
        subprocess.run(cmd, capture_output=True, timeout=120)
        logger.info(f"Subtitles added: {output}")
        return str(output)

    def get_status(self) -> dict:
        return {
            "moviepy_available": MOVIEPY_AVAILABLE,
            "ffmpeg_available": self._check_ffmpeg(),
        }

    def _check_ffmpeg(self) -> bool:
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
