"""
Main game engine with state management and game loop
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from pathlib import Path
from typing import Optional

from blessed import Terminal

from .audio import AudioPlayer
from .beatmap import parse_osu
from .config import AppConfig, get_keybinds_for_keycount, load_keybinds
from .input import InputHandler
from .render import Renderer
from .scoring import ScoringEngine


class GameState(Enum):
    INIT = "INIT"
    LEAD_IN = "LEAD_IN"
    PLAYING = "PLAYING"
    RESULTS = "RESULTS"
    FAILED = "FAILED"


def run_game(osu_path: Path, cfg: AppConfig) -> None:
    """
    High-level orchestration:
    - parse beatmap
    - load keybinds for key_count
    - setup audio, input, renderer, scoring
    - main loop across states
    - print results and exit
    """
    logging.basicConfig(level=getattr(logging, cfg.logging.level))
    
    try:
        # Parse beatmap
        logging.info(f"Loading beatmap: {osu_path}")
        beatmap = parse_osu(osu_path)
        
        # Log beatmap info
        logging.info(f"Beatmap: {beatmap.title} - {beatmap.artist}")
        logging.info(f"Version: {beatmap.version}")
        logging.info(f"Creator: {beatmap.creator}")
        logging.info(f"Key Count: {beatmap.key_count}")
        logging.info(f"Notes: {len(beatmap.notes)}")
        logging.info(f"Audio: {beatmap.audio_path}")
        logging.info(f"Lead-in: {beatmap.audio_lead_in_ms}ms")
        
        # Load keybinds
        keybinds_path = Path(cfg.input.keybinds_file)
        keybinds = load_keybinds(keybinds_path)
        keymap = get_keybinds_for_keycount(keybinds, beatmap.key_count)
        
        logging.info(f"Keybinds: {keymap}")
        
        # Initialize terminal
        term = Terminal()
        
        # Initialize components
        audio_player = AudioPlayer(
            beatmap.audio_path,
            cfg.audio.master_volume,
            cfg.audio.music_volume
        )
        
        input_handler = InputHandler(term, keymap)
        renderer = Renderer(term, beatmap, cfg)
        scoring_engine = ScoringEngine(beatmap, cfg.gameplay)
        
        # Run game loop
        _run_game_loop(term, audio_player, input_handler, renderer, scoring_engine, cfg, beatmap)
        
    except Exception as e:
        logging.error(f"Game failed: {e}")
        raise
    finally:
        # Cleanup
        try:
            audio_player.cleanup()
        except Exception as e:
            logging.warning(f"Audio cleanup error: {e}")


def _run_game_loop(
    term: Terminal,
    audio_player: AudioPlayer,
    input_handler: InputHandler,
    renderer: Renderer,
    scoring_engine: ScoringEngine,
    cfg: AppConfig,
    beatmap
) -> None:
    """Run the main game loop."""
    state = GameState.INIT
    fps_target = cfg.visual.fps_target
    frame_time = 1.0 / fps_target
    
    # Calculate timing
    lead_in_ms = cfg.gameplay.lead_in_ms
    audio_offset_ms = cfg.audio.offset_ms + beatmap.audio_lead_in_ms
    
    # Game start time
    t_game_start = time.perf_counter() + lead_in_ms / 1000.0
    
    # Load and prepare audio
    audio_player.load_music()
    
    # Enter raw mode
    with term.cbreak(), term.hidden_cursor():
        state = GameState.LEAD_IN
        
        # Lead-in phase
        while state == GameState.LEAD_IN:
            frame_start = time.perf_counter()
            
            # Calculate current time
            t_now_ms = int((time.perf_counter() - t_game_start) * 1000)
            
            # Check if lead-in is over
            if t_now_ms >= 0:
                # Start music
                audio_player.start()
                state = GameState.PLAYING
                logging.info("Game started - music playing")
                break
            
            # Render lead-in screen
            _render_lead_in(term, renderer, t_now_ms, lead_in_ms)
            
            # Frame pacing
            _sleep_for_frame(frame_start, frame_time)
        
        # Playing phase
        while state == GameState.PLAYING:
            frame_start = time.perf_counter()
            
            # Calculate current time
            t_now_ms = int((time.perf_counter() - t_game_start) * 1000)
            
            # Handle input
            input_events = input_handler.poll()
            for key_label, is_press, event_time_ms in input_events:
                # Find lane for this key
                lane = _find_lane_for_key(key_label, input_handler.keymap)
                if lane is not None:
                    if is_press:
                        scoring_engine.on_key_press(lane, event_time_ms)
                    else:
                        scoring_engine.on_key_release(lane, event_time_ms)
            
            # Update scoring (auto-miss overdue notes)
            scoring_engine.update_for_time(t_now_ms)
            
            # Render frame
            renderer.draw_frame(t_now_ms, scoring_engine.state)
            
            # Check for fail condition
            if cfg.gameplay.fail_enabled and scoring_engine.state.health <= cfg.gameplay.fail_threshold:
                state = GameState.FAILED
                logging.info("Game failed - health too low")
                break
            
            # Check for completion
            if t_now_ms >= beatmap.total_length_ms:
                # Check if all notes have been judged
                total_notes = len(beatmap.notes)
                judged_notes = scoring_engine.state.judged_count
                
                # For hold notes, we need to count both head and tail
                hold_notes = sum(1 for note in beatmap.notes if note.type.value == "HOLD")
                expected_judgments = total_notes + hold_notes  # Each hold counts as 2 judgments
                
                if judged_notes >= expected_judgments:
                    state = GameState.RESULTS
                    logging.info("Game completed successfully")
                    break
            
            # Frame pacing
            _sleep_for_frame(frame_start, frame_time)
        
        # Results phase
        if state == GameState.RESULTS:
            results = scoring_engine.results()
            renderer.draw_results(results)
            
            # Wait for user input to exit
            logging.info("Game completed. Press any key to exit...")
            term.inkey()
            
        elif state == GameState.FAILED:
            _render_failed_screen(term, renderer)
            logging.info("Game failed. Press any key to exit...")
            term.inkey()


def _render_lead_in(term: Terminal, renderer: Renderer, t_now_ms: int, lead_in_ms: int):
    """Render lead-in countdown screen."""
    print(term.clear, end='')
    
    # Calculate countdown
    remaining_ms = lead_in_ms + t_now_ms
    remaining_seconds = max(0, remaining_ms / 1000.0)
    
    # Center the countdown
    center_y = term.height // 2
    center_x = term.width // 2
    
    # Title
    title = "TERMANIA"
    print(term.move(center_y - 2, center_x - len(title) // 2) + term.bold + title + term.normal)
    
    # Countdown
    if remaining_seconds > 0:
        countdown = f"{remaining_seconds:.1f}"
        print(term.move(center_y, center_x - len(countdown) // 2) + term.bright_blue + countdown + term.normal)
    else:
        print(term.move(center_y, center_x - 3) + term.bright_green + "GO!" + term.normal)
    
    print(end='', flush=True)


def _render_failed_screen(term: Terminal, renderer: Renderer):
    """Render failed screen."""
    print(term.clear, end='')
    
    # Center the failed message
    center_y = term.height // 2
    center_x = term.width // 2
    
    failed_text = "FAILED"
    print(term.move(center_y, center_x - len(failed_text) // 2) + term.bright_red + term.bold + failed_text + term.normal)
    
    print(end='', flush=True)


def _find_lane_for_key(key_label: str, keymap: list) -> Optional[int]:
    """Find lane index for given key label."""
    try:
        return keymap.index(key_label.lower())
    except ValueError:
        return None


def _sleep_for_frame(frame_start: float, frame_time: float):
    """Sleep to maintain target FPS."""
    elapsed = time.perf_counter() - frame_start
    sleep_time = max(0.0, frame_time - elapsed)
    if sleep_time > 0:
        time.sleep(sleep_time)
