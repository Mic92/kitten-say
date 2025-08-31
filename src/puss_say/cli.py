#!/usr/bin/env python3
"""CLI interface for puss-say command."""

import argparse
import sys

import sounddevice as sd
import soundfile as sf
from kittentts import KittenTTS

AVAILABLE_VOICES = [
    "expr-voice-2-m",
    "expr-voice-2-f",
    "expr-voice-3-m",
    "expr-voice-3-f",
    "expr-voice-4-m",
    "expr-voice-4-f",
    "expr-voice-5-m",
    "expr-voice-5-f",
]

DEFAULT_VOICE = "expr-voice-2-f"
DEFAULT_MODEL = "KittenML/kitten-tts-nano-0.2"
SAMPLE_RATE = 24000


def list_voices() -> None:
    """List all available voices."""
    print("Available voices:")
    for voice in AVAILABLE_VOICES:
        default_marker = " (default)" if voice == DEFAULT_VOICE else ""
        print(f"  {voice}{default_marker}")


def say_text(
    text: str,
    voice: str = DEFAULT_VOICE,
    output_file: str | None = None,
    speed: float = 1.0,
) -> None:
    """Generate and play TTS audio."""
    # Initialize the model
    model = KittenTTS(DEFAULT_MODEL)

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
  puss-say -v expr-voice-3-m "Hello from a male voice"
  puss-say -o output.wav "Save this to a file"
  puss-say -s 0.8 "Speak slowly"
  puss-say -s 1.5 "Speak faster"
  echo "Pipe text to speech" | puss-say
  puss-say -l  # List available voices
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

    # Handle interactive mode
    if args.interactive:
        print("Interactive mode. Type text and press Enter to speak. Ctrl+D to exit.")
        try:
            while True:
                try:
                    text = input("> ")
                    if text.strip():
                        say_text(text, voice=args.voice, speed=args.speed)
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
    say_text(text, voice=args.voice, output_file=args.output, speed=args.speed)


if __name__ == "__main__":
    main()
