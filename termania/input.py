"""
Input handling using blessed for keyboard input
"""

from __future__ import annotations

import logging
import time
from typing import List, Tuple

from blessed import Terminal


class InputHandler:
    """Handles keyboard input using blessed terminal."""
    
    def __init__(self, term: Terminal, keymap: List[str]):
        """
        Initialize input handler.
        
        Args:
            term: Blessed terminal instance
            keymap: List of key labels for each lane (e.g., ['d', 'f', 'j', 'k'])
        """
        self.term = term
        self.keymap = keymap
        self.lane_count = len(keymap)
        
        # Track key states
        self._key_states = [False] * self.lane_count
        self._last_press_time = [0.0] * self.lane_count
        self._key_release_timeout_ms = 20  # Consider key released after 20ms of no input
        
        # Normalize keymap to lowercase
        self.keymap = [key.lower() for key in keymap]
        
        logging.info(f"Input handler initialized with {self.lane_count} lanes: {self.keymap}")
    
    def poll(self) -> List[Tuple[str, bool, int]]:
        """
        Non-blocking input polling.
        
        Returns:
            List of (key_label, is_press, t_ms) tuples.
            is_press=True on edge down, False on edge up.
        """
        events = []
        current_time_ms = int(time.perf_counter() * 1000)
        
        try:
            # Get key input with zero timeout (non-blocking)
            key = self.term.inkey(timeout=0)
            
            if key:
                # Normalize key name
                key_name = self._normalize_key(key)
                
                # Find which lane this key corresponds to
                lane = self._find_lane_for_key(key_name)
                
                if lane is not None:
                    # Check if this is a new press (key wasn't pressed before)
                    if not self._key_states[lane]:
                        # Key pressed
                        self._key_states[lane] = True
                        self._last_press_time[lane] = current_time_ms
                        events.append((key_name, True, current_time_ms))
                        logging.debug(f"Key pressed: {key_name} (lane {lane}) at {current_time_ms}ms")
                    else:
                        # Key was already pressed, update the press time
                        self._last_press_time[lane] = current_time_ms
        
        except Exception as e:
            logging.warning(f"Input polling error: {e}")
        
        return events
    
    def check_key_releases(self) -> List[Tuple[str, bool, int]]:
        """
        Check for key releases based on timeout.
        
        Returns:
            List of (key_label, is_press, t_ms) tuples for key releases.
        """
        events = []
        current_time_ms = int(time.perf_counter() * 1000)
        
        for lane in range(self.lane_count):
            if self._key_states[lane]:
                # Check if key has been held too long (consider it released)
                time_since_press = current_time_ms - self._last_press_time[lane]
                if time_since_press > self._key_release_timeout_ms:
                    # Key released
                    self._key_states[lane] = False
                    key_name = self.keymap[lane]
                    events.append((key_name, False, current_time_ms))
                    logging.debug(f"Key released (timeout): {key_name} (lane {lane}) at {current_time_ms}ms")
        
        return events
    
    def is_pressed(self, lane: int) -> bool:
        """
        Check if key for given lane is currently pressed.
        
        Args:
            lane: Lane index (0-based)
            
        Returns:
            True if key is pressed, False otherwise
        """
        if 0 <= lane < self.lane_count:
            return self._key_states[lane]
        return False
    
    def _normalize_key(self, key) -> str:
        """
        Normalize blessed key to our key format.
        
        Args:
            key: Blessed key object
            
        Returns:
            Normalized key string
        """
        # Handle special keys
        if key.name == 'KEY_SPACE':
            return 'space'
        
        # Get the character and normalize to lowercase
        char = str(key)
        if char:
            return char.lower()
        
        # Fallback to key name if available
        if hasattr(key, 'name') and key.name:
            return key.name.lower()
        
        return ''
    
    def _find_lane_for_key(self, key_name: str) -> int:
        """
        Find lane index for given key name.
        
        Args:
            key_name: Normalized key name
            
        Returns:
            Lane index or None if not found
        """
        try:
            return self.keymap.index(key_name)
        except ValueError:
            return None
