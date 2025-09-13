"""
Command-line interface for Termania
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .game import run_game


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="termania",
        description="Terminal osu!mania rhythm game"
    )
    
    subparsers = parser.add_subparsers(dest="cmd", required=True, help="Available commands")
    
    # Play command
    play_parser = subparsers.add_parser("play", help="Play a beatmap")
    play_parser.add_argument("osu_path", type=str, help="Path to .osu beatmap file")
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
            osu_path = Path(args.osu_path)
            if not osu_path.exists():
                print(f"Error: Beatmap file not found: {osu_path}", file=sys.stderr)
                sys.exit(1)
            
            # Load configuration
            cfg = load_config(args.config, overrides=args)
            
            # Run the game
            run_game(osu_path, cfg)
            
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.cmd == "calibrate":
        print("Calibration not implemented in v1", file=sys.stderr)
        sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)
