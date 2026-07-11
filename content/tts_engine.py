"""
TTS (Text-to-Speech) engine.
Currently supports edge-tts (free) with configurable voice pool.
Architecture allows future switch to ElevenLabs via config.
"""

import asyncio
import logging
import random
import hashlib
from pathlib import Path
from typing import Optional, List

import config.settings as settings

logger = logging.getLogger(__name__)

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts not installed. pip install edge-tts")


class TTSEngine:
    """
    Text-to-Speech engine supporting edge-tts and (future) ElevenLabs.
    Voice selection: random from pool, or deterministic by content hash.
    """

    def __init__(self, engine: str = None, output_dir: str = "temp"):
        self.engine = engine or settings.TTS_ENGINE
        self.voice_pool = settings.TTS_VOICE_POOL
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._voice_index = 0

        if self.engine == "edge-tts" and not EDGE_TTS_AVAILABLE:
            raise ImportError("edge-tts is required. pip install edge-tts")

        logger.info(f"TTSEngine initialized: {self.engine}, pool={self.voice_pool}")

    def _select_voice(self, deterministic_key: Optional[str] = None) -> str:
        """
        Select a voice from the pool.
        If deterministic_key is provided, always returns the same voice for the same key.
        Otherwise, cycles through the pool sequentially.
        """
        if not self.voice_pool:
            raise ValueError("No voices in TTS_VOICE_POOL")

        if deterministic_key:
            idx = int(hashlib.md5(deterministic_key.encode()).hexdigest(), 16) % len(self.voice_pool)
            return self.voice_pool[idx]

        voice = self.voice_pool[self._voice_index % len(self.voice_pool)]
        self._voice_index += 1
        return voice

    def _generate_edge_tts(self, text: str, voice: str, output_path: str,
                           rate: str = "+0%", pitch: str = "+0Hz") -> str:
        """Generate speech using edge-tts."""
        async def _generate():
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch
            )
            await communicate.save(output_path)
            return output_path

        return asyncio.run(_generate())

    def generate(self, text: str, output_filename: Optional[str] = None,
                 voice: Optional[str] = None,
                 deterministic_key: Optional[str] = None,
                 rate: str = "+0%", pitch: str = "+0Hz") -> str:
        """
        Generate speech audio from text.

        Args:
            text: Text to convert to speech
            output_filename: Custom filename (auto-generated if None)
            voice: Specific voice name (auto-selected if None)
            deterministic_key: Key for deterministic voice selection
            rate: Speech rate adjustment (e.g., "+10%", "-5%")
            pitch: Pitch adjustment (e.g., "+2Hz", "-3Hz")

        Returns:
            Path to the generated audio file
        """
        selected_voice = voice or self._select_voice(deterministic_key)

        if not output_filename:
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            output_filename = f"tts_{text_hash}.mp3"

        output_path = str(self.output_dir / output_filename)

        logger.info(f"Generating TTS: voice={selected_voice}, text_len={len(text)}")

        if self.engine == "edge-tts":
            try:
                result = self._generate_edge_tts(
                    text, selected_voice, output_path, rate, pitch
                )
                logger.info(f"TTS generated: {result}")
                return result
            except Exception as e:
                logger.error(f"Edge-TTS failed: {e}")
                raise

        elif self.engine == "elevenlabs":
            # Future implementation
            raise NotImplementedError(
                "ElevenLabs TTS not yet implemented. "
                "Set TTS_ENGINE=edge-tts in .env"
            )
        else:
            raise ValueError(f"Unknown TTS engine: {self.engine}")

    def generate_segments(self, segments: List[dict],
                          output_prefix: str = "segment") -> List[str]:
        """
        Generate audio for multiple script segments.
        Each segment dict: {"text": str, "duration_seconds": float}
        Returns list of audio file paths.
        """
        paths = []
        for i, segment in enumerate(segments):
            text = segment.get("text", "")
            if not text.strip():
                continue
            filename = f"{output_prefix}_{i:03d}.mp3"
            path = self.generate(
                text=text,
                output_filename=filename,
                deterministic_key=f"{output_prefix}_{i}"
            )
            paths.append(path)
        return paths

    def list_voices(self) -> List[str]:
        """List all voices in the current pool."""
        return list(self.voice_pool)

    def get_status(self) -> dict:
        """Get TTS engine status."""
        return {
            "engine": self.engine,
            "edge_tts_available": EDGE_TTS_AVAILABLE,
            "voice_pool": self.voice_pool,
            "voice_count": len(self.voice_pool),
        }
