"""
Command-line interface for Termania
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .beatmap import extract_osz
from .config import load_config
from .game import run_game


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="termania",
        description="Terminal osu!mania rhythm game - supports .osu and .osz files"
    )
    
    subparsers = parser.add_subparsers(dest="cmd", required=True, help="Available commands")
    
    # Play command
    play_parser = subparsers.add_parser("play", help="Play a beatmap")
    play_parser.add_argument("beatmap_path", type=str, help="Path to .osu or .osz beatmap file")
    play_parser.add_argument("--config", type=str, default=None, help="Path to config YAML file")
    play_parser.add_argument("--rate", type=float, default=1.0, help="Playback rate (must be 1.0 in v1)")
    play_parser.add_argument("--lead-in", type=int, default=None, help="Lead-in time in milliseconds")
    play_parser.add_argument("--offset", type=int, default=None, help="Audio offset in milliseconds")
    play_parser.add_argument("--scroll", type=float, default=None, help="Scroll speed in rows per second")
    play_parser.add_argument("--fps", type=int, default=None, help="Target FPS")
    
    # Calibrate command (placeholder for future)
    calibrate_parser = subparsers.add_parser("calibrate", help="Calibrate input timing (not implemented in v1)")
    
    args = parser.parse_args()
    
    if args.cmd == "play":
        try:
            # Validate beatmap path
            beatmap_path = Path(args.beatmap_path)
            if not beatmap_path.exists():
                print(f"Error: Beatmap file not found: {beatmap_path}", file=sys.stderr)
                sys.exit(1)
            
            # Handle .osz files by extracting them
            temp_dir = None
            if beatmap_path.suffix.lower() == '.osz':
                print(f"Extracting .osz file: {beatmap_path}")
                osu_path, temp_dir = extract_osz(beatmap_path)
                print(f"Found .osu file: {osu_path}")
            else:
                osu_path = beatmap_path
            
            # Load configuration
            cfg = load_config(args.config, overrides=args)
            
            # Run the game
            run_game(osu_path, cfg)
            
            # Clean up temporary directory if we extracted an .osz file
            if temp_dir:
                temp_dir.cleanup()
            
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            # Clean up temporary directory on error
            if 'temp_dir' in locals() and temp_dir:
                temp_dir.cleanup()
            sys.exit(1)
    
    elif args.cmd == "calibrate":
        print("Calibration not implemented in v1", file=sys.stderr)
        sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)
