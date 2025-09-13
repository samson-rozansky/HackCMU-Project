"""
Scoring engine for judgment, scoring, and health management
"""

from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .beatmap import ManiaBeatmap, ManiaNote, ManiaNoteType
from .config import GameplayConfig


@dataclass
class Judgement:
    time_ms: int
    column: int
    note_index: int
    type: str  # 'MARV'|'PERF'|'GREAT'|'GOOD'|'OK'|'MISS'
    is_tail: bool = False


@dataclass
class ScoreState:
    score: int = 0
    combo: int = 0
    max_combo: int = 0
    health: float = 50.0
    judgments: List[Judgement] = field(default_factory=list)
    judged_count: int = 0
    weighted_sum: float = 0.0  # for accuracy


class ScoringEngine:
    """Handles scoring, judgment, and health management."""
    
    def __init__(self, beatmap: ManiaBeatmap, gameplay_cfg: GameplayConfig):
        """
        Initialize scoring engine.
        
        Args:
            beatmap: Parsed beatmap data
            gameplay_cfg: Gameplay configuration
        """
        self.beatmap = beatmap
        self.cfg = gameplay_cfg
        self.state = ScoreState()
        
        # Initialize health to max
        self.state.health = self.cfg.max_health
        
        # Per-column note queues (pending notes)
        self._note_queues = [[] for _ in range(beatmap.key_count)]
        self._active_holds = [None] * beatmap.key_count  # note_index or None
        
        # Populate note queues
        self._populate_note_queues()
        
        # Judgment weights for accuracy calculation
        self._judgment_weights = {
            'MARV': 1.0,
            'PERF': 0.99,
            'GREAT': 0.88,
            'GOOD': 0.77,
            'OK': 0.5,
            'MISS': 0.0
        }
        
        logging.info(f"Scoring engine initialized for {beatmap.key_count}K with {len(beatmap.notes)} notes")
    
    def on_key_press(self, column: int, t_ms: int) -> None:
        """
        Handle key press event.
        
        Args:
            column: Column index (0-based)
            t_ms: Current time in milliseconds
        """
        if column < 0 or column >= self.beatmap.key_count:
            return
        
        # Check if there's a pending note in this column
        if self._note_queues[column]:
            note_idx = self._note_queues[column][0]
            note = self.beatmap.notes[note_idx]
            
            # Calculate timing difference
            dt_ms = abs(t_ms - note.start_time_ms)
            
            # Determine judgment
            judgment = self._get_judgment(dt_ms)
            
            # Apply judgment
            self._apply_judgment(judgment, column, note_idx, t_ms, is_tail=False)
            
            # Remove note from queue
            self._note_queues[column].pop(0)
            
            # If it's a hold note, mark it as active
            if note.type == ManiaNoteType.HOLD:
                self._active_holds[column] = note_idx
                logging.debug(f"Started hold note {note_idx} in column {column}")
    
    def on_key_release(self, column: int, t_ms: int) -> None:
        """
        Handle key release event.
        
        Args:
            column: Column index (0-based)
            t_ms: Current time in milliseconds
        """
        if column < 0 or column >= self.beatmap.key_count:
            return
        
        # Check if there's an active hold in this column
        if self._active_holds[column] is not None:
            note_idx = self._active_holds[column]
            note = self.beatmap.notes[note_idx]
            
            # Calculate timing difference for tail
            dt_ms = abs(t_ms - note.end_time_ms)
            
            # Check if release is within tolerance
            if dt_ms <= self.cfg.long_note_release_tolerance_ms:
                judgment = self._get_judgment(dt_ms)
                self._apply_judgment(judgment, column, note_idx, t_ms, is_tail=True)
            else:
                # Release too early or too late
                self._apply_judgment('MISS', column, note_idx, t_ms, is_tail=True)
            
            # Clear active hold
            self._active_holds[column] = None
            logging.debug(f"Released hold note {note_idx} in column {column}")
    
    def update_for_time(self, t_ms: int) -> None:
        """
        Update scoring state for current time (auto-miss overdue notes).
        
        Args:
            t_ms: Current time in milliseconds
        """
        # Check for overdue notes in each column
        for column in range(self.beatmap.key_count):
            # Check pending notes
            while self._note_queues[column]:
                note_idx = self._note_queues[column][0]
                note = self.beatmap.notes[note_idx]
                
                # Check if note is overdue
                if t_ms - note.start_time_ms > self.cfg.miss_window_ms:
                    self._apply_judgment('MISS', column, note_idx, t_ms, is_tail=False)
                    self._note_queues[column].pop(0)
                    
                    # If it was a hold note, also miss the tail
                    if note.type == ManiaNoteType.HOLD:
                        self._apply_judgment('MISS', column, note_idx, t_ms, is_tail=True)
                        self._active_holds[column] = None
                else:
                    break
            
            # Check active holds for overdue tails
            if self._active_holds[column] is not None:
                note_idx = self._active_holds[column]
                note = self.beatmap.notes[note_idx]
                
                if t_ms - note.end_time_ms > self.cfg.long_note_release_tolerance_ms:
                    self._apply_judgment('MISS', column, note_idx, t_ms, is_tail=True)
                    self._active_holds[column] = None
        
        # Apply health drain
        if self.cfg.health_drain_per_second_idle > 0:
            # This would need to be called with proper timing, but for now we'll skip
            # the idle drain implementation as it requires frame timing
            pass
    
    def results(self) -> Dict[str, float | int | str]:
        """
        Get final results.
        
        Returns:
            Dictionary with accuracy, grade, max combo, score, and judgment counts
        """
        # Calculate accuracy
        accuracy = 0.0
        if self.state.judged_count > 0:
            accuracy = (self.state.weighted_sum / self.state.judged_count) * 100.0
        
        # Determine grade
        grade = self._calculate_grade(accuracy)
        
        # Count judgments
        judgment_counts = {}
        for judgment_type in ['MARV', 'PERF', 'GREAT', 'GOOD', 'OK', 'MISS']:
            judgment_counts[judgment_type] = sum(
                1 for j in self.state.judgments 
                if j.type == judgment_type
            )
        
        return {
            'accuracy': accuracy,
            'grade': grade,
            'max_combo': self.state.max_combo,
            'score': self.state.score,
            'judgment_counts': judgment_counts,
            'total_notes': self.state.judged_count
        }
    
    def _populate_note_queues(self):
        """Populate per-column note queues."""
        for i, note in enumerate(self.beatmap.notes):
            self._note_queues[note.column].append(i)
    
    def _get_judgment(self, dt_ms: int) -> str:
        """
        Get judgment type based on timing difference.
        
        Args:
            dt_ms: Absolute timing difference in milliseconds
            
        Returns:
            Judgment type string
        """
        if dt_ms <= self.cfg.windows_ms['MARV']:
            return 'MARV'
        elif dt_ms <= self.cfg.windows_ms['PERF']:
            return 'PERF'
        elif dt_ms <= self.cfg.windows_ms['GREAT']:
            return 'GREAT'
        elif dt_ms <= self.cfg.windows_ms['GOOD']:
            return 'GOOD'
        elif dt_ms <= self.cfg.windows_ms['OK']:
            return 'OK'
        else:
            return 'MISS'
    
    def _apply_judgment(self, judgment: str, column: int, note_idx: int, t_ms: int, is_tail: bool):
        """
        Apply a judgment and update scoring state.
        
        Args:
            judgment: Judgment type
            column: Column index
            note_idx: Note index in beatmap
            t_ms: Time of judgment
            is_tail: Whether this is a hold note tail judgment
        """
        # Create judgment record
        judgment_record = Judgement(
            time_ms=t_ms,
            column=column,
            note_index=note_idx,
            type=judgment,
            is_tail=is_tail
        )
        
        self.state.judgments.append(judgment_record)
        self.state.judged_count += 1
        
        # Update combo
        if judgment == 'MISS':
            self.state.combo = 0
        else:
            self.state.combo += 1
            self.state.max_combo = max(self.state.max_combo, self.state.combo)
        
        # Update score
        base_score = self.cfg.score_values.get(judgment, 0)
        combo_bonus = 1 + (self.state.combo / 100)
        self.state.score += int(base_score * combo_bonus)
        
        # Update accuracy
        weight = self._judgment_weights.get(judgment, 0.0)
        self.state.weighted_sum += weight
        
        # Update health
        health_change = self.cfg.health_gain.get(judgment, 0.0)
        self.state.health = max(0.0, min(self.cfg.max_health, self.state.health + health_change))
        
        logging.debug(f"Judgment: {judgment} (tail={is_tail}) - Combo: {self.state.combo}, Health: {self.state.health:.1f}")
    
    def _calculate_grade(self, accuracy: float) -> str:
        """
        Calculate grade based on accuracy.
        
        Args:
            accuracy: Accuracy percentage
            
        Returns:
            Grade string (S, A, B, C, D)
        """
        if accuracy >= 98.00:
            return 'S'
        elif accuracy >= 95.00:
            return 'A'
        elif accuracy >= 90.00:
            return 'B'
        elif accuracy >= 80.00:
            return 'C'
        else:
            return 'D'
