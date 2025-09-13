"""
Configuration models and loading system for Termania
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError


class AudioConfig(BaseModel):
    master_volume: float = Field(ge=0, le=1, default=0.8)
    music_volume: float = Field(ge=0, le=1, default=1.0)
    offset_ms: int = Field(default=0)


class GameplayConfig(BaseModel):
    scroll_rows_per_second: float = Field(gt=0, default=24)
    chart_preload_ms: int = Field(ge=0, default=2000)
    lead_in_ms: int = Field(ge=0, default=1500)
    hit_line_row_from_bottom: int = Field(ge=1, default=2)
    miss_window_ms: int = Field(gt=0, default=200)
    windows_ms: Dict[str, int] = Field(default={
        "MARV": 16,
        "PERF": 34,
        "GREAT": 67,
        "GOOD": 100,
        "OK": 150,
        "MISS": 200
    })
    long_note_release_tolerance_ms: int = Field(gt=0, default=80)
    fail_enabled: bool = Field(default=True)
    health_drain_per_second_idle: float = Field(default=0.0)
    health_gain: Dict[str, float] = Field(default={
        "MARV": 0.5,
        "PERF": 0.4,
        "GREAT": 0.2,
        "GOOD": 0.0,
        "OK": -0.2,
        "MISS": -2.0
    })
    score_values: Dict[str, int] = Field(default={
        "MARV": 320,
        "PERF": 300,
        "GREAT": 200,
        "GOOD": 100,
        "OK": 50,
        "MISS": 0
    })
    max_health: int = Field(gt=0, default=100)
    fail_threshold: int = Field(ge=0, default=0)


class VisualConfig(BaseModel):
    lanes_char_vertical: str = Field(default="│")
    hit_line_char: str = Field(default="═")
    note_char: str = Field(default="█")
    long_note_body_char: str = Field(default="▓")
    long_note_head_char: str = Field(default="█")
    lane_spacing: int = Field(ge=0, default=2)
    fps_target: int = Field(ge=1, le=120, default=60)


class InputConfig(BaseModel):
    keybinds_file: str = Field(default="examples/keybinds.yaml")


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO")


class AppConfig(BaseModel):
    version: int = Field(default=1)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    gameplay: GameplayConfig = Field(default_factory=GameplayConfig)
    visual: VisualConfig = Field(default_factory=VisualConfig)
    input: InputConfig = Field(default_factory=InputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(path: Optional[str], overrides: Optional[argparse.Namespace] = None) -> AppConfig:
    """
    Load configuration from YAML file with optional overrides from CLI args.
    
    Args:
        path: Path to config YAML file. If None, uses default config.
        overrides: CLI argument namespace to override config values.
        
    Returns:
        AppConfig instance with loaded and validated configuration.
    """
    config_data = {}
    
    if path:
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    
    # Apply CLI overrides
    if overrides:
        if hasattr(overrides, 'rate') and overrides.rate != 1.0:
            raise ValueError("Rate modification not supported in v1. Must be 1.0")
        
        # Map CLI args to config structure
        if hasattr(overrides, 'lead_in') and overrides.lead_in is not None:
            config_data.setdefault('gameplay', {})['lead_in_ms'] = overrides.lead_in
        
        if hasattr(overrides, 'offset') and overrides.offset is not None:
            config_data.setdefault('audio', {})['offset_ms'] = overrides.offset
        
        if hasattr(overrides, 'scroll') and overrides.scroll is not None:
            config_data.setdefault('gameplay', {})['scroll_rows_per_second'] = overrides.scroll
        
        if hasattr(overrides, 'fps') and overrides.fps is not None:
            config_data.setdefault('visual', {})['fps_target'] = overrides.fps
    
    try:
        return AppConfig(**config_data)
    except ValidationError as e:
        raise ValueError(f"Invalid configuration: {e}")


def load_keybinds(path: Path) -> Dict[int, List[str]]:
    """
    Load keybind mappings from YAML file.
    
    Args:
        path: Path to keybinds YAML file.
        
    Returns:
        Dictionary mapping keycount to list of key labels.
        
    Raises:
        FileNotFoundError: If keybinds file doesn't exist.
        ValueError: If keybinds file is invalid or missing required keycount.
    """
    if not path.exists():
        raise FileNotFoundError(f"Keybinds file not found: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        keybinds_data = yaml.safe_load(f)
    
    if not isinstance(keybinds_data, dict):
        raise ValueError("Keybinds file must contain a dictionary")
    
    # Convert string keys to integers and validate
    result = {}
    for key_str, keys in keybinds_data.items():
        try:
            keycount = int(key_str)
            if not isinstance(keys, list) or not all(isinstance(k, str) for k in keys):
                raise ValueError(f"Keybinds for {keycount}K must be a list of strings")
            if len(keys) != keycount:
                raise ValueError(f"Keybinds for {keycount}K must have exactly {keycount} keys")
            result[keycount] = keys
        except ValueError as e:
            raise ValueError(f"Invalid keybinds entry '{key_str}': {e}")
    
    return result


def get_keybinds_for_keycount(keybinds: Dict[int, List[str]], keycount: int) -> List[str]:
    """
    Get keybinds for a specific keycount, raising clear error if not found.
    
    Args:
        keybinds: Loaded keybinds dictionary.
        keycount: Number of keys needed.
        
    Returns:
        List of key labels for the keycount.
        
    Raises:
        ValueError: If keycount not configured.
    """
    if keycount not in keybinds:
        available = ", ".join(f"{k}K" for k in sorted(keybinds.keys()))
        raise ValueError(
            f"No keybinds configured for keycount={keycount}. "
            f"Available keycounts: {available}. "
            f"Add a \"{keycount}\" entry in keybinds.yaml."
        )
    
    return keybinds[keycount]
