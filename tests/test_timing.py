"""
Unit tests for timing calculations
"""

import pytest
from termania.render import Renderer
from termania.beatmap import ManiaBeatmap, ManiaNote, ManiaNoteType
from termania.config import AppConfig
from blessed import Terminal


def test_time_to_row_mapping():
    """Test time to row mapping calculations."""
    # Create mock beatmap
    beatmap = ManiaBeatmap(
        title="Test",
        artist="Test",
        version="Test",
        creator="Test",
        audio_path="test.ogg",
        key_count=4,
        notes=[],
        total_length_ms=10000
    )
    
    # Create mock config
    cfg = AppConfig()
    cfg.gameplay.scroll_rows_per_second = 24.0
    cfg.gameplay.hit_line_row_from_bottom = 2
    
    # Create mock terminal
    term = Terminal()
    
    # Create renderer
    renderer = Renderer(term, beatmap, cfg)
    
    # Test cases: (note_time_ms, current_time_ms, expected_row)
    test_cases = [
        (1000, 1000, renderer.hit_line_row),  # Note at hit line
        (2000, 1000, renderer.hit_line_row - 24),  # Note 1 second ahead
        (500, 1000, renderer.hit_line_row + 12),  # Note 0.5 seconds past
        (0, 1000, renderer.hit_line_row + 24),  # Note 1 second past
    ]
    
    for note_time_ms, current_time_ms, expected_row in test_cases:
        actual_row = renderer._time_to_row(note_time_ms, current_time_ms)
        assert actual_row == expected_row, f"Failed for note_time={note_time_ms}, current_time={current_time_ms}"


def test_visible_notes():
    """Test visible notes calculation."""
    # Create mock beatmap with notes
    notes = [
        ManiaNote(start_time_ms=1000, column=0, type=ManiaNoteType.TAP),
        ManiaNote(start_time_ms=2000, column=1, type=ManiaNoteType.TAP),
        ManiaNote(start_time_ms=3000, column=2, type=ManiaNoteType.TAP),
    ]
    
    beatmap = ManiaBeatmap(
        title="Test",
        artist="Test",
        version="Test",
        creator="Test",
        audio_path="test.ogg",
        key_count=4,
        notes=notes,
        total_length_ms=10000
    )
    
    # Create mock config
    cfg = AppConfig()
    cfg.gameplay.chart_preload_ms = 2000
    cfg.gameplay.miss_window_ms = 200
    
    # Create mock terminal
    term = Terminal()
    
    # Create renderer
    renderer = Renderer(term, beatmap, cfg)
    
    # Test at different times
    visible_at_500 = renderer._get_visible_notes(500)  # Before any notes
    assert len(visible_at_500) == 0  # No notes should be visible yet (preload is 2000ms)
    
    visible_at_1500 = renderer._get_visible_notes(1500)  # Middle of notes
    assert len(visible_at_1500) == 1  # First note should be visible
    
    visible_at_2500 = renderer._get_visible_notes(2500)  # After some notes
    assert len(visible_at_2500) == 2  # Second and third notes should be visible
    
    visible_at_3500 = renderer._get_visible_notes(3500)  # After all notes
    assert len(visible_at_3500) == 2  # Second and third notes should be visible
