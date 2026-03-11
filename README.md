# puss-say

A command-line text-to-speech tool that mimics macOS's `say` command, powered by [KittenTTS](https://github.com/KittenML/KittenTTS).

## Features

- High-quality text-to-speech using KittenTTS
- Multiple voice options (male and female)
- Adjustable speech speed
- Save output to WAV files
- Interactive mode for continuous speech
- Pipe text from stdin
- No GPU required - runs on CPU

## Installation

### Using Nix

```bash
# Run directly
nix run github:Mic92/puss-say -- "Hello, world!"

# Build and run locally
nix build
./result/bin/puss-say "Hello, world!"
```

### Using uvx

```bash
# Run directly from GitHub (requires PortAudio installed)
uvx --from 'git+https://github.com/Mic92/puss-say' puss-say "Hello, world!"
```

### Development

```bash
# Enter development shell with all dependencies
nix develop

# puss-say is now available in your PATH
puss-say "Hello from the development shell!"

# Or use uv directly for Python package management
uv sync
uv run puss-say "Hello from uv!"
# Note: uv run requires PortAudio to be installed on your system
# For a complete environment with all dependencies, use 'nix develop'
```

## Usage

Basic usage:
```bash
puss-say "Hello, world!"
```

Choose a different voice:
```bash
puss-say -v Jasper "Hello from a male voice"
```

Save to file:
```bash
puss-say -o output.wav "Save this speech to a file"
```

Adjust speech speed:
```bash
puss-say -s 0.8 "Speak more slowly"
puss-say -s 1.5 "Speak faster"
```

Pipe text:
```bash
echo "This text is piped" | puss-say
```

Interactive mode:
```bash
puss-say -i
# Type text and press Enter to hear it spoken
# Press Ctrl+D to exit
```

List available voices:
```bash
puss-say --list-voices
```

## Available Voices

- `expr-voice-2-m` - Male voice 2
- `expr-voice-2-f` - Female voice 2 [default]
- `expr-voice-3-m` - Male voice 3
- `expr-voice-3-f` - Female voice 3
- `expr-voice-4-m` - Male voice 4
- `expr-voice-4-f` - Female voice 4
- `expr-voice-5-m` - Male voice 5
- `expr-voice-5-f` - Female voice 5

## Requirements

- Nix with flakes enabled (for Nix installation)
- Python 3.13+ (for manual installation)
- PortAudio (automatically provided by Nix)
- No GPU required - CPU inference only

## License

MIT

## Acknowledgments

- [KittenTTS](https://github.com/KittenML/KittenTTS) for the excellent TTS model
- [uv2nix](https://github.com/pyproject-nix/uv2nix) for seamless Python packaging in Nix
