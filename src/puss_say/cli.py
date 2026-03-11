#!/usr/bin/env python3
"""CLI interface for puss-say command."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import os
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    import soundfile as sf

AVAILABLE_VOICES = [
    "Bella",
    "Jasper",
    "Luna",
    "Bruno",
    "Rosie",
    "Hugo",
    "Kiki",
    "Leo",
]

DEFAULT_VOICE = "Bella"

AVAILABLE_MODELS = {
    "nano": "KittenML/kitten-tts-nano-0.8",
    "micro": "KittenML/kitten-tts-micro-0.8",
    "mini": "KittenML/kitten-tts-mini-0.8",
}

DEFAULT_MODEL = "micro"
SAMPLE_RATE = 24000


def list_voices() -> None:
    """List all available voices."""
    print("Available voices:")
    for voice in AVAILABLE_VOICES:
        default_marker = " (default)" if voice == DEFAULT_VOICE else ""
        print(f"  {voice}{default_marker}")


def list_models() -> None:
    """List all available models."""
    print("Available models:")
    for name, repo in AVAILABLE_MODELS.items():
        default_marker = " (default)" if name == DEFAULT_MODEL else ""
        print(f"  {name:6s}  {repo}{default_marker}")


MAX_CACHE_ENTRIES = 256


def _cache_dir() -> Path:
    """Return the XDG-compliant cache directory for puss-say."""
    xdg = os.environ.get("XDG_CACHE_HOME", "")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "puss-say"


def _cache_key(text: str, voice: str, model_name: str, speed: float) -> str:
    """Compute a cache key from all parameters that affect audio output."""
    raw = f"{model_name}\0{voice}\0{speed}\0{text}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_lookup(key: str) -> np.ndarray | None:
    """Return cached audio as numpy array, or None on miss.

    Updates the file's mtime on hit so LRU eviction works correctly.
    """
    path = _cache_dir() / f"{key}.wav"
    try:
        if path.exists():
            import soundfile as sf

            path.touch()
            data, _sr = sf.read(path, dtype="float32")
            return data  # type: ignore[return-value]
    except OSError:
        pass
    return None


def _cache_evict() -> None:
    """Evict oldest-accessed entries when cache exceeds MAX_CACHE_ENTRIES."""
    cache = _cache_dir()
    try:
        if not cache.exists():
            return
        entries = sorted(cache.glob("*.wav"), key=lambda p: p.stat().st_mtime)
        while len(entries) > MAX_CACHE_ENTRIES:
            entries.pop(0).unlink(missing_ok=True)
    except OSError:
        pass


def _cache_store(key: str, audio: np.ndarray) -> None:
    """Write audio to the cache atomically, evicting old entries if needed.

    Uses a temp file + rename to avoid leaving corrupt files on disk if
    the write is interrupted or the filesystem is full.
    """
    cache = _cache_dir()
    try:
        cache.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(suffix=".wav", dir=cache)
        os.close(fd)
        try:
            import soundfile as sf

            sf.write(tmp, audio, SAMPLE_RATE)
            os.replace(tmp, cache / f"{key}.wav")
        except BaseException:
            # Clean up the temp file on any failure (full disk, interrupt, etc.)
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise
    except OSError:
        # Cache is best-effort — don't let it break playback
        pass
    _cache_evict()


def say_text(
    text: str,
    voice: str = DEFAULT_VOICE,
    output_file: str | None = None,
    speed: float = 1.0,
    model_name: str = DEFAULT_MODEL,
    *,
    use_cache: bool = True,
) -> None:
    """Generate and play TTS audio."""
    key = _cache_key(text, voice, model_name, speed)
    audio = _cache_lookup(key) if use_cache else None

    if audio is None:
        from kittentts import KittenTTS

        repo_id = AVAILABLE_MODELS[model_name]
        model = KittenTTS(repo_id)

        try:
            audio = model.generate(text, voice=voice, speed=speed)
        except RuntimeError as e:
            print(f"Error generating speech: {e}", file=sys.stderr)
            sys.exit(1)

        if use_cache:
            _cache_store(key, audio)

    # If output file is specified, save to file
    if output_file:
        try:
            import soundfile as sf

            sf.write(output_file, audio, SAMPLE_RATE)
            print(f"Audio saved to: {output_file}")
        except (OSError, RuntimeError) as e:
            print(f"Error saving audio file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Play audio directly
        try:
            import sounddevice as sd

            sd.play(audio, SAMPLE_RATE)
            sd.wait()  # Wait until playback is finished
        except (sd.PortAudioError, RuntimeError) as e:
            print(f"Error playing audio: {e}", file=sys.stderr)
            sys.exit(1)


def main() -> None:
    """Execute the main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Text-to-speech using KittenTTS (similar to macOS say command)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  puss-say "Hello, world!"
  puss-say -v Jasper "Hello from a male voice"
  puss-say -m nano "Use the fastest model"
  puss-say -o output.wav "Save this to a file"
  puss-say -s 0.8 "Speak slowly"
  echo "Pipe text to speech" | puss-say
  puss-say -l  # List available voices
  puss-say --list-models  # List available models
        """,
    )

    parser.add_argument(
        "text",
        nargs="?",
        help="Text to speak (reads from stdin if not provided)",
    )

    parser.add_argument(
        "-v",
        "--voice",
        default=DEFAULT_VOICE,
        choices=AVAILABLE_VOICES,
        help=f"Voice to use (default: {DEFAULT_VOICE})",
    )

    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_MODEL,
        choices=AVAILABLE_MODELS,
        help=f"Model size to use (default: {DEFAULT_MODEL})",
    )

    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Save audio to file instead of playing",
    )

    parser.add_argument(
        "-l",
        "--list-voices",
        action="store_true",
        help="List available voices",
    )

    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models",
    )

    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Interactive mode - keep reading lines from stdin",
    )

    parser.add_argument(
        "-s",
        "--speed",
        type=float,
        default=1.5,
        metavar="SPEED",
        help="Speech speed (default: 1.5, range: 0.5-2.0)",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass the audio cache",
    )

    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the audio cache and exit",
    )

    args = parser.parse_args()

    # Handle clear cache
    if args.clear_cache:
        cache = _cache_dir()
        if cache.exists():
            import shutil

            shutil.rmtree(cache)
            print(f"Cache cleared: {cache}")
        else:
            print("Cache is already empty.")
        return

    # Handle list voices
    if args.list_voices:
        list_voices()
        return

    # Handle list models
    if args.list_models:
        list_models()
        return

    # Handle interactive mode
    if args.interactive:
        print("Interactive mode. Type text and press Enter to speak. Ctrl+D to exit.")
        try:
            while True:
                try:
                    text = input("> ")
                    if text.strip():
                        say_text(text, voice=args.voice, speed=args.speed, model_name=args.model, use_cache=not args.no_cache)
                except EOFError:
                    print("\nExiting...")
                    break
        except KeyboardInterrupt:
            print("\nInterrupted!")
            sys.exit(1)
        return

    # Get text from argument or stdin
    if args.text:
        text = args.text
    else:
        # Read from stdin
        text = sys.stdin.read().strip()
        if not text:
            parser.error("No text provided. Use --help for usage information.")

    # Generate and play/save speech
    say_text(text, voice=args.voice, output_file=args.output, speed=args.speed, model_name=args.model, use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
