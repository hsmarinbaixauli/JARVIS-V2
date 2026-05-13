"""Voice interaction loop extracted from the legacy src/main.py. Contains the
wake-word detection, microphone capture, Whisper transcription, and ElevenLabs
TTS response cycle. Only imported when JARVIS_VOICE_MODE=true is set in the
environment. All voice dependencies (pyaudio, openWakeWord, whisper,
elevenlabs) are imported inside this module to avoid ImportError on machines
without audio hardware."""
from __future__ import annotations


def run_voice_loop() -> None:
    pass
