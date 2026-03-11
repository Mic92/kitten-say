#!/usr/bin/env python3
"""CLI interface for puss-say command."""

import argparse
import sys

import sounddevice as sd
import soundfile as sf
from kittentts import KittenTTS

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


def say_text(
    text: str,
    voice: str = DEFAULT_VOICE,
    output_file: str | None = None,
    speed: float = 1.0,
    model_name: str = DEFAULT_MODEL,
) -> None:
    """Generate and play TTS audio."""
    repo_id = AVAILABLE_MODELS[model_name]
    model = KittenTTS(repo_id)

    # Generate audio
    try:
        audio = model.generate(text, voice=voice, speed=speed)
    except RuntimeError as e:
        print(f"Error generating speech: {e}", file=sys.stderr)
        sys.exit(1)

    # If output file is specified, save to file
    if output_file:
        try:
            sf.write(output_file, audio, SAMPLE_RATE)
            print(f"Audio saved to: {output_file}")
        except (OSError, RuntimeError) as e:
            print(f"Error saving audio file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Play audio directly
        try:
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
        default=1.0,
        metavar="SPEED",
        help="Speech speed (default: 1.0, range: 0.5-2.0)",
    )

    args = parser.parse_args()

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
                        say_text(text, voice=args.voice, speed=args.speed, model_name=args.model)
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
    say_text(text, voice=args.voice, output_file=args.output, speed=args.speed, model_name=args.model)


if __name__ == "__main__":
    main()
