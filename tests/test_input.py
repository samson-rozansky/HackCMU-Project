"""
Unit tests for input handling
"""

import pytest
from termania.input import InputHandler
from blessed import Terminal


def test_key_normalization():
    """Test key normalization."""
    term = Terminal()
    keymap = ["d", "f", "j", "k"]
    handler = InputHandler(term, keymap)
    
    # Test key normalization
    test_cases = [
        ("KEY_SPACE", "space"),
        ("D", "d"),
        ("f", "f"),
        ("J", "j"),
        ("k", "k"),
    ]
    
    for input_key, expected_normalized in test_cases:
        # Mock the key object
        class MockKey:
            def __init__(self, name_or_char):
                if name_or_char.startswith("KEY_"):
                    self.name = name_or_char
                    self.char = ""
                else:
                    self.name = None
                    self.char = name_or_char
            
            def __str__(self):
                return self.char
        
        mock_key = MockKey(input_key)
        normalized = handler._normalize_key(mock_key)
        assert normalized == expected_normalized, f"Failed for input '{input_key}'"


def test_lane_finding():
    """Test finding lane for key."""
    term = Terminal()
    keymap = ["d", "f", "j", "k"]
    handler = InputHandler(term, keymap)
    
    # Test lane finding
    test_cases = [
        ("d", 0),
        ("f", 1),
        ("j", 2),
        ("k", 3),
        ("x", None),  # Invalid key
        ("space", None),  # Not in keymap
    ]
    
    for key_name, expected_lane in test_cases:
        actual_lane = handler._find_lane_for_key(key_name)
        assert actual_lane == expected_lane, f"Failed for key '{key_name}'"


def test_key_state_tracking():
    """Test key state tracking."""
    term = Terminal()
    keymap = ["d", "f", "j", "k"]
    handler = InputHandler(term, keymap)
    
    # Initially no keys should be pressed
    for i in range(len(keymap)):
        assert not handler.is_pressed(i)
    
    # Simulate key press (this would normally come from poll())
    handler._key_states[0] = True
    assert handler.is_pressed(0)
    assert not handler.is_pressed(1)
    
    # Simulate key release
    handler._key_states[0] = False
    assert not handler.is_pressed(0)
