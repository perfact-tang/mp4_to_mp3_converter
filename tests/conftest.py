"""
Test configuration and fixtures for MP4 to MP3 Converter tests.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    # Cleanup
    import shutil
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_settings():
    """Create mock settings object."""
    settings = Mock()
    settings.get.side_effect = lambda key, default=None: {
        'audio_quality': '192',
        'output_directory': '/tmp/output',
        'file_naming_pattern': '{original}_converted',
        'output_suffix': '_converted',
        'auto_open_folder': True,
        'delete_original': False,
        'max_concurrent_conversions': 4,
        'preserve_metadata': True,
        'volume_normalization': False,
        'fade_in': 0,
        'fade_out': 0,
    }.get(key, default)
    return settings


@pytest.fixture
def sample_mp4_file(temp_dir):
    """Create a sample MP4 file for testing."""
    mp4_path = os.path.join(temp_dir, "sample_video.mp4")
    # Create a small dummy file (not a real MP4, but sufficient for file operations)
    with open(mp4_path, 'wb') as f:
        f.write(b'dummy mp4 content' * 1000)  # ~17KB file
    return mp4_path


@pytest.fixture
def unsupported_file(temp_dir):
    """Create an unsupported file for testing."""
    txt_path = os.path.join(temp_dir, "document.txt")
    with open(txt_path, 'w') as f:
        f.write("This is a text file, not a video file.")
    return txt_path


@pytest.fixture
def mock_ffmpeg_wrapper():
    """Create a mock FFmpegWrapper."""
    from converter.ffmpeg_wrapper import FFmpegWrapper
    
    wrapper = Mock(spec=FFmpegWrapper)
    wrapper.convert_mp4_to_mp3.return_value = True
    wrapper.get_ffmpeg_version.return_value = "ffmpeg version 5.1.0"
    return wrapper


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = Mock()
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    return logger