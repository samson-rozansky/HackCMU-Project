"""
Unit tests for scoring engine
"""

import pytest
from termania.scoring import ScoringEngine, ScoreState
from termania.beatmap import ManiaBeatmap, ManiaNote, ManiaNoteType
from termania.config import GameplayConfig


def test_judgment_windows():
    """Test judgment window selection."""
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
    
    cfg = GameplayConfig()
    engine = ScoringEngine(beatmap, cfg)
    
    # Test judgment selection
    test_cases = [
        (5, "MARV"),    # Within MARV window
        (20, "PERF"),    # Within PERF window
        (50, "GREAT"),   # Within GREAT window
        (80, "GOOD"),    # Within GOOD window
        (120, "OK"),     # Within OK window
        (180, "MISS"),   # Within MISS window
        (250, "MISS"),   # Beyond MISS window
    ]
    
    for dt_ms, expected_judgment in test_cases:
        actual_judgment = engine._get_judgment(dt_ms)
        assert actual_judgment == expected_judgment, f"Failed for dt={dt_ms}ms"


def test_combo_break():
    """Test combo breaking on MISS."""
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
    
    cfg = GameplayConfig()
    engine = ScoringEngine(beatmap, cfg)
    
    # Build up combo
    engine._apply_judgment("GREAT", 0, 0, 1000, False)
    engine._apply_judgment("PERF", 1, 1, 1100, False)
    engine._apply_judgment("MARV", 2, 2, 1200, False)
    
    assert engine.state.combo == 3
    
    # MISS should break combo
    engine._apply_judgment("MISS", 3, 3, 1300, False)
    assert engine.state.combo == 0
    
    # Combo should start over
    engine._apply_judgment("GOOD", 0, 4, 1400, False)
    assert engine.state.combo == 1


def test_health_changes():
    """Test health changes on different judgments."""
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
    
    cfg = GameplayConfig()
    engine = ScoringEngine(beatmap, cfg)
    
    initial_health = engine.state.health
    
    # Test health gains
    engine._apply_judgment("MARV", 0, 0, 1000, False)
    expected_health = min(cfg.max_health, initial_health + cfg.health_gain["MARV"])
    assert engine.state.health == expected_health
    
    engine._apply_judgment("PERF", 1, 1, 1100, False)
    expected_health = min(cfg.max_health, initial_health + cfg.health_gain["MARV"] + cfg.health_gain["PERF"])
    assert engine.state.health == expected_health
    
    # Test health loss
    engine._apply_judgment("MISS", 2, 2, 1200, False)
    expected_health = max(0.0, expected_health + cfg.health_gain["MISS"])
    assert engine.state.health == expected_health
    
    # Health should not go below 0
    engine.state.health = 1.0
    engine._apply_judgment("MISS", 3, 3, 1300, False)
    assert engine.state.health == 0.0


def test_hold_note_judgments():
    """Test hold note head and tail judgments."""
    # Create beatmap with hold note
    hold_note = ManiaNote(
        start_time_ms=1000,
        end_time_ms=2000,
        column=0,
        type=ManiaNoteType.HOLD
    )
    
    beatmap = ManiaBeatmap(
        title="Test",
        artist="Test",
        version="Test",
        creator="Test",
        audio_path="test.ogg",
        key_count=4,
        notes=[hold_note],
        total_length_ms=10000
    )
    
    cfg = GameplayConfig()
    engine = ScoringEngine(beatmap, cfg)
    
    # Press key for hold note head
    engine.on_key_press(0, 1000)
    
    # Should have judged the head
    assert len(engine.state.judgments) == 1
    assert engine.state.judgments[0].is_tail == False
    assert engine.state.judgments[0].type in ["MARV", "PERF", "GREAT", "GOOD", "OK"]
    
    # Release key for hold note tail
    engine.on_key_release(0, 2000)
    
    # Should have judged the tail
    assert len(engine.state.judgments) == 2
    assert engine.state.judgments[1].is_tail == True
    assert engine.state.judgments[1].type in ["MARV", "PERF", "GREAT", "GOOD", "OK"]


def test_grade_calculation():
    """Test grade calculation based on accuracy."""
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
    
    cfg = GameplayConfig()
    engine = ScoringEngine(beatmap, cfg)
    
    # Test different accuracy levels
    test_cases = [
        (99.0, "S"),
        (96.0, "A"),
        (92.0, "B"),
        (85.0, "C"),
        (75.0, "D"),
    ]
    
    for accuracy, expected_grade in test_cases:
        grade = engine._calculate_grade(accuracy)
        assert grade == expected_grade, f"Failed for accuracy={accuracy}%"
