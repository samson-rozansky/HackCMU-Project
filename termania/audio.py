"""
Audio subsystem using pygame.mixer for music playback
"""

from __future__ import annotations

import logging
from pathlib import Path

import pygame


class AudioPlayer:
    """Audio player using pygame.mixer for music playback."""
    
    def __init__(self, music_path: Path, master_volume: float, music_volume: float):
        """
        Initialize audio player.
        
        Args:
            music_path: Path to audio file (.ogg, .mp3, .wav)
            master_volume: Master volume (0.0 to 1.0)
            music_volume: Music volume (0.0 to 1.0)
        """
        self.music_path = music_path
        self.master_volume = master_volume
        self.music_volume = music_volume
        self._initialized = False
        
        # Initialize pygame mixer
        self._init_pygame()
    
    def _init_pygame(self):
        """Initialize pygame mixer with optimal settings."""
        try:
            # Pre-initialize mixer with good defaults
            pygame.mixer.pre_init(
                frequency=44100,
                size=-16,  # 16-bit signed
                channels=2,  # stereo
                buffer=1024
            )
            pygame.init()
            self._initialized = True
            logging.info("Pygame mixer initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize pygame mixer: {e}")
            raise RuntimeError(f"Audio initialization failed: {e}")
    
    def load_music(self):
        """Load the music file."""
        if not self._initialized:
            raise RuntimeError("Audio not initialized")
        
        if not self.music_path.exists():
            raise FileNotFoundError(f"Audio file not found: {self.music_path}")
        
        try:
            pygame.mixer.music.load(str(self.music_path))
            self.set_volume(self.music_volume)
            logging.info(f"Loaded audio: {self.music_path}")
        except Exception as e:
            logging.error(f"Failed to load audio file {self.music_path}: {e}")
            raise RuntimeError(f"Failed to load audio: {e}")
    
    def start(self):
        """Start music playback."""
        if not self._initialized:
            raise RuntimeError("Audio not initialized")
        
        try:
            pygame.mixer.music.play(loops=0, start=0.0)
            logging.info("Music playback started")
        except Exception as e:
            logging.error(f"Failed to start music: {e}")
            raise RuntimeError(f"Failed to start music: {e}")
    
    def stop(self):
        """Stop music playback."""
        if self._initialized:
            try:
                pygame.mixer.music.stop()
                logging.info("Music playback stopped")
            except Exception as e:
                logging.warning(f"Error stopping music: {e}")
    
    def set_volume(self, volume: float):
        """
        Set music volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        if not self._initialized:
            return
        
        # Clamp volume
        volume = max(0.0, min(1.0, volume))
        
        # Apply master volume
        final_volume = volume * self.master_volume
        
        try:
            pygame.mixer.music.set_volume(final_volume)
            logging.debug(f"Set music volume to {final_volume:.2f}")
        except Exception as e:
            logging.warning(f"Failed to set volume: {e}")
    
    def is_playing(self) -> bool:
        """Check if music is currently playing."""
        if not self._initialized:
            return False
        
        try:
            return pygame.mixer.music.get_busy()
        except Exception:
            return False
    
    def cleanup(self):
        """Clean up audio resources."""
        self.stop()
        if self._initialized:
            try:
                pygame.mixer.quit()
                self._initialized = False
                logging.info("Audio cleanup completed")
            except Exception as e:
                logging.warning(f"Error during audio cleanup: {e}")
