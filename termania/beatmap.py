"""
Beatmap parsing for osu!mania .osu files
"""

from __future__ import annotations

import enum
import logging
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class TimingPoint(BaseModel):
    time_ms: int
    ms_per_beat: float
    meter: int
    volume: int
    uninherited: bool
    effects: int


class ManiaNoteType(enum.Enum):
    TAP = "TAP"
    HOLD = "HOLD"


class ManiaNote(BaseModel):
    start_time_ms: int
    end_time_ms: Optional[int] = None  # set for HOLD only
    column: int
    type: ManiaNoteType


class ManiaBeatmap(BaseModel):
    title: str
    artist: str
    version: str
    creator: str
    audio_path: Path
    audio_lead_in_ms: int = 0
    key_count: int
    timing_points: List[TimingPoint] = Field(default_factory=list)
    notes: List[ManiaNote] = Field(default_factory=list)
    total_length_ms: int = 0


def parse_osu(osu_path: Path) -> ManiaBeatmap:
    """
    Reads a .osu (mania) file; resolves audio path; returns ManiaBeatmap.
    Raises ValueError with explicit messages on errors.
    """
    if not osu_path.exists():
        raise FileNotFoundError(f"Beatmap file not found: {osu_path}")
    
    osu_dir = osu_path.parent
    
    with open(osu_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse sections
    sections = _parse_sections(content)
    
    # Extract metadata
    general = sections.get('General', {})
    metadata = sections.get('Metadata', {})
    difficulty = sections.get('Difficulty', {})
    
    # Validate mode
    mode = general.get('Mode', '0')
    if mode != '3':
        logging.warning(f"Beatmap Mode is not mania (3), got {mode}. Proceeding anyway.")
    
    # Get audio filename
    audio_filename = general.get('AudioFilename', '')
    if not audio_filename:
        raise ValueError("AudioFilename missing in [General] section")
    
    audio_path = osu_dir / audio_filename
    if not audio_path.exists():
        raise ValueError(
            f'Audio file not found: "{audio_path}". '
            f'Check [General].AudioFilename in the .osu and your beatmap folder.'
        )
    
    # Get key count from CircleSize
    circle_size_str = difficulty.get('CircleSize', '4')
    try:
        key_count = int(round(float(circle_size_str)))
    except ValueError:
        raise ValueError(f"Invalid CircleSize value: {circle_size_str}")
    
    if key_count < 1 or key_count > 9:
        raise ValueError(f"Invalid key count {key_count}. Must be between 1 and 9.")
    
    # Parse timing points
    timing_points_data = sections.get('TimingPoints', [])
    if isinstance(timing_points_data, list):
        timing_points = _parse_timing_points(timing_points_data)
    else:
        timing_points = []
    
    # Parse hit objects
    hit_objects = sections.get('HitObjects', [])
    if not hit_objects:
        raise ValueError("No HitObjects found in beatmap")
    
    notes = _parse_hit_objects(hit_objects, key_count)
    
    # Sort notes by start time
    notes.sort(key=lambda n: n.start_time_ms)
    
    # Calculate total length
    total_length_ms = 0
    if notes:
        last_end = max(
            note.end_time_ms or note.start_time_ms 
            for note in notes
        )
        total_length_ms = last_end + 2000  # 2 second buffer
    
    return ManiaBeatmap(
        title=metadata.get('Title', 'Unknown'),
        artist=metadata.get('Artist', 'Unknown'),
        version=metadata.get('Version', 'Unknown'),
        creator=metadata.get('Creator', 'Unknown'),
        audio_path=audio_path,
        audio_lead_in_ms=int(general.get('AudioLeadIn', '0')),
        key_count=key_count,
        timing_points=timing_points,
        notes=notes,
        total_length_ms=total_length_ms
    )


def _parse_sections(content: str) -> dict:
    """Parse .osu file into sections."""
    sections = {}
    current_section = None
    
    for line in content.split('\n'):
        line = line.strip()
        
        if line.startswith('[') and line.endswith(']'):
            # Start new section
            current_section = line[1:-1]
            if current_section in ['HitObjects', 'TimingPoints']:
                sections[current_section] = []
            else:
                sections[current_section] = {}
        elif line and current_section is not None:
            # For sections like HitObjects, TimingPoints, store as list
            if current_section in ['HitObjects', 'TimingPoints']:
                sections[current_section].append(line)
            elif ':' in line:
                # Parse key:value pairs for other sections
                key, value = line.split(':', 1)
                sections[current_section][key.strip()] = value.strip()
            else:
                sections[current_section][line] = True
    
    return sections


def _parse_timing_points(timing_lines: List[str]) -> List[TimingPoint]:
    """Parse timing points from raw lines."""
    timing_points = []
    
    for line in timing_lines:
        if not line.strip():
            continue
        
        parts = line.split(',')
        if len(parts) < 8:
            continue
        
        try:
            time_ms = int(float(parts[0]))
            ms_per_beat = float(parts[1])
            meter = int(parts[2])
            sample_set = int(parts[3])
            sample_index = int(parts[4])
            volume = int(parts[5])
            uninherited = int(parts[6]) == 1
            effects = int(parts[7])
            
            timing_points.append(TimingPoint(
                time_ms=time_ms,
                ms_per_beat=ms_per_beat,
                meter=meter,
                volume=volume,
                uninherited=uninherited,
                effects=effects
            ))
        except (ValueError, IndexError) as e:
            logging.warning(f"Failed to parse timing point: {line} - {e}")
            continue
    
    return timing_points


def _parse_hit_objects(hit_object_lines: List[str], key_count: int) -> List[ManiaNote]:
    """Parse hit objects into mania notes."""
    notes = []
    
    for line in hit_object_lines:
        if not line.strip():
            continue
        
        parts = line.split(',')
        if len(parts) < 5:
            continue
        
        try:
            x = int(float(parts[0]))
            y = int(float(parts[1]))
            time_ms = int(float(parts[2]))
            obj_type = int(parts[3])
            hit_sound = int(parts[4])
            
            # Calculate column
            column = min(key_count - 1, int(x * key_count / 512))
            
            # Check if it's a hold note
            is_hold = (obj_type & 128) == 128
            
            if is_hold:
                # Parse end time from extra data
                if len(parts) > 5:
                    extra_data = parts[5]
                    if ':' in extra_data:
                        end_time_str = extra_data.split(':')[0]
                        end_time_ms = int(float(end_time_str))
                    else:
                        end_time_ms = int(float(extra_data))
                else:
                    end_time_ms = time_ms + 1000  # Default 1 second hold
                
                notes.append(ManiaNote(
                    start_time_ms=time_ms,
                    end_time_ms=end_time_ms,
                    column=column,
                    type=ManiaNoteType.HOLD
                ))
            else:
                notes.append(ManiaNote(
                    start_time_ms=time_ms,
                    end_time_ms=None,
                    column=column,
                    type=ManiaNoteType.TAP
                ))
                
        except (ValueError, IndexError) as e:
            logging.warning(f"Failed to parse hit object: {line} - {e}")
            continue
    
    return notes
