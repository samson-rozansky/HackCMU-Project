"""
Unit tests for renderer
"""

import pytest
from termania.render import Renderer
from termania.beatmap import ManiaBeatmap
from termania.config import AppConfig
from blessed import Terminal


def test_lane_position_calculation():
    """Test lane position calculations."""
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
    
    cfg = AppConfig()
    cfg.visual.lane_spacing = 2
    
    # Mock terminal with specific width
    class MockTerminal:
        def __init__(self, width, height):
            self.width = width
            self.height = height
    
    term = MockTerminal(100, 30)
    
    # Create renderer
    renderer = Renderer(term, beatmap, cfg)
    
    # With 4 lanes and spacing of 2, total width needed = 4 + 2*3 = 10
    # Centered in width 100: x0 = (100 - 10) // 2 = 45
    expected_positions = [45, 48, 51, 54]  # 45, 45+3, 45+6, 45+9
    
    assert renderer.lane_x_positions == expected_positions


def test_hit_line_calculation():
    """Test hit line row calculation."""
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
    
    cfg = AppConfig()
    cfg.gameplay.hit_line_row_from_bottom = 2
    
    # Mock terminal
    class MockTerminal:
        def __init__(self, width, height):
            self.width = width
            self.height = height
    
    term = MockTerminal(100, 30)
    
    # Create renderer
    renderer = Renderer(term, beatmap, cfg)
    
    # Hit line should be at height - hit_line_row_from_bottom
    expected_hit_line = 30 - 2  # 28
    assert renderer.hit_line_row == expected_hit_line


def test_note_rendering_bounds():
    """Test that notes are only rendered within bounds."""
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
    
    cfg = AppConfig()
    cfg.gameplay.scroll_rows_per_second = 24.0
    cfg.gameplay.hit_line_row_from_bottom = 2
    
    # Mock terminal
    class MockTerminal:
        def __init__(self, width, height):
            self.width = width
            self.height = height
    
    term = MockTerminal(100, 30)
    
    # Create renderer
    renderer = Renderer(term, beatmap, cfg)
    
    # Test notes at different positions
    test_cases = [
        (1000, 1000, True),   # Note at hit line - should render
        (2000, 1000, True),   # Note 1 second ahead - should render
        (500, 1000, False),   # Note 0.5 seconds past - should not render (below hit line)
        (0, 1000, False),     # Note 1 second past - should not render (below hit line)
        (3000, 1000, False), # Note 2 seconds ahead - should not render (above screen)
    ]
    
    for note_time_ms, current_time_ms, should_render in test_cases:
        row = renderer._time_to_row(note_time_ms, current_time_ms)
        
        if should_render:
            assert 2 <= row <= renderer.hit_line_row, f"Note at {note_time_ms} should be visible"
        else:
            assert row < 2 or row > renderer.hit_line_row, f"Note at {note_time_ms} should not be visible"
