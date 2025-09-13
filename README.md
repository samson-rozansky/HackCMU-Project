# Termania

A terminal-based rhythm game that plays osu!mania beatmaps with falling notes, accurate timing judgments, and synchronized audio.

## Features

- **osu!mania Support**: Plays `.osu` beatmap files with 4K, 5K, 6K, and 7K key layouts
- **Terminal Rendering**: Smooth falling notes rendered in ASCII characters
- **Audio Synchronization**: Music plays in sync with gameplay using pygame
- **Accurate Timing**: Precise judgment windows (MARV, PERF, GREAT, GOOD, OK, MISS)
- **Health System**: Health drains on misses, gains on good hits
- **Scoring**: Combo-based scoring with accuracy tracking
- **Configurable**: Customizable keybinds, timing windows, and visual settings

## Installation

1. Install Python 3.10 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

```bash
# Play a beatmap
python -m termania play path/to/beatmap.osu

# Use custom config
python -m termania play path/to/beatmap.osu --config examples/config.yaml
```

### Command Line Options

- `--config`: Path to config YAML file
- `--lead-in`: Lead-in time in milliseconds
- `--offset`: Audio offset in milliseconds  
- `--scroll`: Scroll speed in rows per second
- `--fps`: Target FPS

### Configuration

Edit `examples/config.yaml` to customize:

- **Audio**: Volume levels and timing offset
- **Gameplay**: Judgment windows, health system, scoring
- **Visual**: Character symbols, scroll speed, FPS
- **Input**: Keybind mappings for different key counts

### Keybinds

Default keybinds are in `examples/keybinds.yaml`:

- **4K**: D F J K
- **5K**: D F Space J K  
- **6K**: S D F J K L
- **7K**: S D F J K L ;

## File Structure

```
termania/
├── termania/           # Main package
│   ├── __init__.py
│   ├── __main__.py     # CLI entrypoint
│   ├── cli.py          # Command-line interface
│   ├── config.py       # Configuration models
│   ├── audio.py        # Audio subsystem
│   ├── beatmap.py      # .osu parser
│   ├── timing.py       # Timing calculations
│   ├── input.py        # Keyboard input
│   ├── render.py       # Terminal renderer
│   ├── scoring.py      # Scoring engine
│   └── game.py         # Game engine
├── tests/              # Unit tests
├── examples/          # Sample files
│   ├── config.yaml    # Default configuration
│   ├── keybinds.yaml  # Default keybinds
│   └── sample.osu     # Sample beatmap
└── requirements.txt   # Dependencies
```

## Testing

Run the test suite:

```bash
pytest tests/
```

## Requirements

- Python 3.10+
- Terminal with ANSI escape support
- Audio file formats: OGG, MP3, WAV

## Limitations (v1)

- No mouse support
- No skinning/themes beyond ASCII
- No storyboard/video backgrounds
- No online leaderboards
- No speed modifications (rate must be 1.0x)

## License

This project is licensed under the MIT License.
