"""
Terminal renderer for lanes, notes, and HUD
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional

from blessed import Terminal

from .beatmap import ManiaBeatmap, ManiaNote, ManiaNoteType
from .config import AppConfig
from .scoring import ScoreState


class Renderer:
    """Terminal renderer for the rhythm game."""
    
    def __init__(self, term: Terminal, beatmap: ManiaBeatmap, cfg: AppConfig, keymap: list = None):
        """
        Initialize renderer.
        
        Args:
            term: Blessed terminal instance
            beatmap: Parsed beatmap data
            cfg: Application configuration
            keymap: List of key labels for each lane
        """
        self.term = term
        self.beatmap = beatmap
        self.cfg = cfg
        self.keymap = keymap or []
        
        # Calculate lane positions
        self._calculate_lane_positions()
        
        # Calculate hit line row
        self.hit_line_row = term.height - cfg.gameplay.hit_line_row_from_bottom
        
        logging.info(f"Renderer initialized: {term.width}x{term.height}, hit line at row {self.hit_line_row}")
    
    def draw_frame(self, t_ms: int, state: ScoreState) -> None:
        """
        Draw a complete frame.
        
        Args:
            t_ms: Current time in milliseconds
            state: Current scoring state
        """
        # Properly clear the entire terminal screen
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # Draw HUD at top
        self._draw_hud(t_ms, state)
        
        # Draw lanes and notes
        self._draw_lanes_and_notes(t_ms)
        
        # Draw hit line
        self._draw_hit_line()
        
        # Draw key labels
        self._draw_key_labels()
        
        # Draw HUD at bottom
        self._draw_bottom_hud(state)
        
        # Final flush for smooth animation
        print(end='', flush=True)
    
    def draw_results(self, results: Dict[str, float | int | str]) -> None:
        """
        Draw results screen.
        
        Args:
            results: Results dictionary from scoring engine
        """
        # Properly clear the entire terminal screen
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # Center the results
        center_y = self.term.height // 2
        center_x = self.term.width // 2
        
        # Title
        title = "RESULTS"
        print(self.term.move(center_y - 6, center_x - len(title) // 2) + self.term.bold + title + self.term.normal)
        
        # Grade
        grade = str(results['grade'])
        print(self.term.move(center_y - 4, center_x - len(grade) // 2) + self.term.bright_blue + grade + self.term.normal)
        
        # Accuracy
        accuracy = f"{results['accuracy']:.2f}%"
        print(self.term.move(center_y - 2, center_x - len(accuracy) // 2) + accuracy)
        
        # Score
        score = f"Score: {results['score']:,}"
        print(self.term.move(center_y, center_x - len(score) // 2) + score)
        
        # Max Combo
        max_combo = f"Max Combo: {results['max_combo']}"
        print(self.term.move(center_y + 2, center_x - len(max_combo) // 2) + max_combo)
        
        # Judgment counts
        y_offset = center_y + 4
        judgment_counts = results['judgment_counts']
        for judgment in ['MARV', 'PERF', 'GREAT', 'GOOD', 'OK', 'MISS']:
            count = judgment_counts.get(judgment, 0)
            text = f"{judgment}: {count}"
            print(self.term.move(y_offset, center_x - len(text) // 2) + text)
            y_offset += 1
        
        print(end='', flush=True)
    
    def _calculate_lane_positions(self):
        """Calculate x positions for each lane."""
        key_count = self.beatmap.key_count
        lane_spacing = self.cfg.visual.lane_spacing
        
        # Total width needed
        total_lane_width = key_count + lane_spacing * (key_count - 1)
        
        # Center the lanes
        x0 = (self.term.width - total_lane_width) // 2
        
        # Calculate position for each lane
        self.lane_x_positions = []
        for c in range(key_count):
            x = x0 + c * (1 + lane_spacing)
            self.lane_x_positions.append(x)
    
    def _draw_hud(self, t_ms: int, state: ScoreState):
        """Draw top HUD."""
        # Title and artist
        title = f"{self.beatmap.title} - {self.beatmap.artist}"
        version = f"[{self.beatmap.version}]"
        
        # Center the title
        title_x = (self.term.width - len(title)) // 2
        print(self.term.move(0, title_x) + self.term.bold + title + self.term.normal)
        
        # Version below title
        version_x = (self.term.width - len(version)) // 2
        print(self.term.move(1, version_x) + version)
        
        # Timer (top right)
        minutes = t_ms // 60000
        seconds = (t_ms % 60000) // 1000
        timer = f"{minutes:02d}:{seconds:02d}"
        print(self.term.move(0, self.term.width - len(timer)) + timer)
    
    def _draw_lanes_and_notes(self, t_ms: int):
        """Draw lanes and falling notes."""
        key_count = self.beatmap.key_count
        
        # Draw lane dividers
        for row in range(2, self.hit_line_row):
            for lane_idx in range(key_count):
                x = self.lane_x_positions[lane_idx]
                print(self.term.move(row, x) + self.cfg.visual.lanes_char_vertical)
        
        # Draw notes
        visible_notes = self._get_visible_notes(t_ms)
        
        for note in visible_notes:
            self._draw_note(note, t_ms)
    
    def _draw_note(self, note: ManiaNote, t_ms: int):
        """Draw a single note."""
        # Calculate row position
        row = self._time_to_row(note.start_time_ms, t_ms)
        
        if row < 2 or row >= self.hit_line_row:
            return  # Outside visible area
        
        x = self.lane_x_positions[note.column]
        
        if note.type == ManiaNoteType.TAP:
            # Draw tap note
            print(self.term.move(row, x) + self.cfg.visual.note_char)
        else:
            # Draw hold note
            # Head
            print(self.term.move(row, x) + self.cfg.visual.long_note_head_char)
            
            # Body (if visible)
            if note.end_time_ms:
                end_row = self._time_to_row(note.end_time_ms, t_ms)
                for body_row in range(max(2, end_row), row):
                    if body_row < self.hit_line_row:
                        print(self.term.move(body_row, x) + self.cfg.visual.long_note_body_char)
    
    def _draw_hit_line(self):
        """Draw the hit line."""
        # Draw hit line across all lanes
        start_x = self.lane_x_positions[0]
        end_x = self.lane_x_positions[-1]
        
        for x in range(start_x, end_x + 1):
            print(self.term.move(self.hit_line_row, x) + self.cfg.visual.hit_line_char)
    
    def _draw_key_labels(self):
        """Draw key labels below the hit line."""
        if not self.keymap:
            return
        
        # Draw key labels below the hit line
        label_row = self.hit_line_row + 1
        
        for i, key in enumerate(self.keymap):
            if i < len(self.lane_x_positions):
                x = self.lane_x_positions[i]
                # Display key in uppercase and highlighted
                print(self.term.move(label_row, x) + self.term.bold + self.term.bright_blue + key.upper() + self.term.normal)
    
    def _draw_bottom_hud(self, state: ScoreState):
        """Draw bottom HUD."""
        hud_y = self.term.height - 1
        
        # Score
        score_text = f"Score: {state.score:,}"
        print(self.term.move(hud_y, 0) + score_text)
        
        # Combo
        combo_text = f"Combo: {state.combo}"
        combo_x = len(score_text) + 2
        print(self.term.move(hud_y, combo_x) + combo_text)
        
        # Accuracy
        accuracy = 0.0
        if state.judged_count > 0:
            accuracy = (state.weighted_sum / state.judged_count) * 100.0
        
        accuracy_text = f"Accuracy: {accuracy:.2f}%"
        accuracy_x = combo_x + len(combo_text) + 2
        print(self.term.move(hud_y, accuracy_x) + accuracy_text)
        
        # Health bar
        health_percent = (state.health / self.cfg.gameplay.max_health) * 100
        health_text = f"Health: {health_percent:.1f}%"
        health_x = self.term.width - len(health_text)
        print(self.term.move(hud_y, health_x) + health_text)
    
    def _get_visible_notes(self, t_ms: int) -> List[ManiaNote]:
        """Get notes that should be visible at current time."""
        visible = []
        preload_ms = self.cfg.gameplay.chart_preload_ms
        
        for note in self.beatmap.notes:
            # Check if note should be visible
            time_until_hit = note.start_time_ms - t_ms
            
            if -preload_ms <= time_until_hit <= self.cfg.gameplay.miss_window_ms:
                visible.append(note)
        
        return visible
    
    def _time_to_row(self, note_time_ms: int, current_time_ms: int) -> int:
        """
        Convert note time to screen row.
        
        Args:
            note_time_ms: Note time in milliseconds
            current_time_ms: Current time in milliseconds
            
        Returns:
            Screen row (0-based, top to bottom)
        """
        # Calculate time until hit
        time_until_hit = note_time_ms - current_time_ms
        
        # Convert to rows above hit line
        scroll_speed = self.cfg.gameplay.scroll_rows_per_second
        rows_above_hit = time_until_hit / 1000.0 * scroll_speed
        
        # Convert to screen row
        screen_row = int(round(self.hit_line_row - rows_above_hit))
        
        return screen_row
