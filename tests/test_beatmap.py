"""
Unit tests for beatmap parsing
"""

import pytest
from pathlib import Path
from termania.beatmap import parse_osu, ManiaNoteType


def test_parse_minimal_osu():
    """Test parsing a minimal .osu file."""
    # Create a temporary .osu file
    osu_content = """osu file format v14

[General]
AudioFilename: test.ogg
AudioLeadIn: 0
Mode: 3

[Metadata]
Title: Test Song
Artist: Test Artist
Version: 4K Easy
Creator: Test Creator

[Difficulty]
CircleSize: 4
OverallDifficulty: 8

[TimingPoints]
0,500,4,2,0,100,1,0

[HitObjects]
64,192,1000,1,0,0:0:0:0:           # column 0 tap at 1000ms
192,192,1200,1,0,0:0:0:0:          # column 1 tap
320,192,1400,1,0,0:0:0:0:          # column 2 tap
448,192,1600,128,0,2000:0:0:0:     # column 3 hold 1600->2000ms
"""
    
    # Write to temporary file
    test_dir = Path("test_temp")
    test_dir.mkdir(exist_ok=True)
    
    osu_path = test_dir / "test.osu"
    with open(osu_path, 'w') as f:
        f.write(osu_content)
    
    # Create dummy audio file
    audio_path = test_dir / "test.ogg"
    audio_path.touch()
    
    try:
        beatmap = parse_osu(osu_path)
        
        # Verify basic properties
        assert beatmap.title == "Test Song"
        assert beatmap.artist == "Test Artist"
        assert beatmap.version == "4K Easy"
        assert beatmap.creator == "Test Creator"
        assert beatmap.key_count == 4
        assert beatmap.audio_lead_in_ms == 0
        assert len(beatmap.timing_points) == 1
        assert len(beatmap.notes) == 4
        
        # Verify timing point
        tp = beatmap.timing_points[0]
        assert tp.time_ms == 0
        assert tp.ms_per_beat == 500.0
        assert tp.meter == 4
        assert tp.uninherited == True
        
        # Verify notes
        notes = beatmap.notes
        assert len(notes) == 4
        
        # First note (tap)
        assert notes[0].start_time_ms == 1000
        assert notes[0].end_time_ms is None
        assert notes[0].column == 0
        assert notes[0].type == ManiaNoteType.TAP
        
        # Second note (tap)
        assert notes[1].start_time_ms == 1200
        assert notes[1].column == 1
        assert notes[1].type == ManiaNoteType.TAP
        
        # Third note (tap)
        assert notes[2].start_time_ms == 1400
        assert notes[2].column == 2
        assert notes[2].type == ManiaNoteType.TAP
        
        # Fourth note (hold)
        assert notes[3].start_time_ms == 1600
        assert notes[3].end_time_ms == 2000
        assert notes[3].column == 3
        assert notes[3].type == ManiaNoteType.HOLD
        
        # Verify notes are sorted by start time
        for i in range(len(notes) - 1):
            assert notes[i].start_time_ms <= notes[i + 1].start_time_ms
        
    finally:
        # Cleanup
        osu_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)
        test_dir.rmdir()


def test_column_mapping():
    """Test column mapping for different x positions."""
    osu_content = """osu file format v14

[General]
AudioFilename: test.ogg
Mode: 3

[Metadata]
Title: Test
Artist: Test

[Difficulty]
CircleSize: 4

[TimingPoints]
0,500,4,2,0,100,1,0

[HitObjects]
0,192,1000,1,0,0:0:0:0:            # x=0 -> column 0
127,192,1100,1,0,0:0:0:0:          # x=127 -> column 0
128,192,1200,1,0,0:0:0:0:          # x=128 -> column 1
255,192,1300,1,0,0:0:0:0:          # x=255 -> column 1
256,192,1400,1,0,0:0:0:0:          # x=256 -> column 2
383,192,1500,1,0,0:0:0:0:          # x=383 -> column 2
384,192,1600,1,0,0:0:0:0:          # x=384 -> column 3
511,192,1700,1,0,0:0:0:0:          # x=511 -> column 3
"""
    
    test_dir = Path("test_temp")
    test_dir.mkdir(exist_ok=True)
    
    osu_path = test_dir / "test.osu"
    with open(osu_path, 'w') as f:
        f.write(osu_content)
    
    audio_path = test_dir / "test.ogg"
    audio_path.touch()
    
    try:
        beatmap = parse_osu(osu_path)
        
        # Verify column mapping
        expected_columns = [0, 0, 1, 1, 2, 2, 3, 3]
        for i, note in enumerate(beatmap.notes):
            assert note.column == expected_columns[i]
    
    finally:
        osu_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)
        test_dir.rmdir()


def test_missing_audio_file():
    """Test error handling for missing audio file."""
    osu_content = """osu file format v14

[General]
AudioFilename: missing.ogg
Mode: 3

[Metadata]
Title: Test
Artist: Test

[Difficulty]
CircleSize: 4

[TimingPoints]
0,500,4,2,0,100,1,0

[HitObjects]
64,192,1000,1,0,0:0:0:0:
"""
    
    test_dir = Path("test_temp")
    test_dir.mkdir(exist_ok=True)
    
    osu_path = test_dir / "test.osu"
    with open(osu_path, 'w') as f:
        f.write(osu_content)
    
    try:
        with pytest.raises(ValueError, match="Audio file not found"):
            parse_osu(osu_path)
    
    finally:
        osu_path.unlink(missing_ok=True)
        test_dir.rmdir()


def test_no_hit_objects():
    """Test error handling for empty hit objects."""
    osu_content = """osu file format v14

[General]
AudioFilename: test.ogg
Mode: 3

[Metadata]
Title: Test
Artist: Test

[Difficulty]
CircleSize: 4

[TimingPoints]
0,500,4,2,0,100,1,0

[HitObjects]
"""
    
    test_dir = Path("test_temp")
    test_dir.mkdir(exist_ok=True)
    
    osu_path = test_dir / "test.osu"
    with open(osu_path, 'w') as f:
        f.write(osu_content)
    
    audio_path = test_dir / "test.ogg"
    audio_path.touch()
    
    try:
        with pytest.raises(ValueError, match="No HitObjects found"):
            parse_osu(osu_path)
    
    finally:
        osu_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)
        test_dir.rmdir()
