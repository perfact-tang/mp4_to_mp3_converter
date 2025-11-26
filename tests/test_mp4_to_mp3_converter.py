"""
Test suite for MP4 to MP3 Converter application.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from exceptions import (
    ConversionError, FileValidationError, FFmpegNotFoundError, 
    DiskSpaceError, ConversionCancelledError
)
from utils.file_manager import FileManager
from utils.logger import setup_logger
from config.settings import Settings
from converter.ffmpeg_wrapper import FFmpegWrapper
from converter.conversion_manager import ConversionManager, ConversionWorker


class TestExceptions:
    """Test custom exception classes."""
    
    def test_conversion_error(self):
        """Test ConversionError exception."""
        error = ConversionError("Test error", "TEST_ERROR")
        assert str(error) == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.user_message == "変換中にエラーが発生しました"
    
    def test_file_validation_error(self):
        """Test FileValidationError exception."""
        error = FileValidationError("Invalid file", "/path/to/file.mp4")
        assert str(error) == "Invalid file"
        assert error.file_path == "/path/to/file.mp4"
        assert error.user_message == "MP4形式のファイルを選択してください"
    
    def test_ffmpeg_not_found_error(self):
        """Test FFmpegNotFoundError exception."""
        error = FFmpegNotFoundError("FFmpeg not found")
        assert str(error) == "FFmpeg not found"
        assert error.user_message == "FFmpegがインストールされていません"


class TestFileManager:
    """Test FileManager class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.file_manager = FileManager()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_supported_extensions(self):
        """Test validation of supported file extensions."""
        # Create test files
        test_files = [
            os.path.join(self.temp_dir, "test.mp4"),
            os.path.join(self.temp_dir, "test.m4v"),
            os.path.join(self.temp_dir, "test.mov"),
            os.path.join(self.temp_dir, "test.txt"),  # Unsupported
            os.path.join(self.temp_dir, "test.avi"),
        ]
        
        # Create actual files
        for file_path in test_files:
            Path(file_path).touch()
        
        valid_files, invalid_files = self.file_manager.validate_input_files(test_files)
        
        assert len(valid_files) == 4  # All except .txt
        assert len(invalid_files) == 1  # Only .txt
        assert os.path.join(self.temp_dir, "test.txt") in invalid_files
    
    def test_validate_nonexistent_file(self):
        """Test validation of non-existent file."""
        nonexistent_file = "/path/to/nonexistent.mp4"
        
        with pytest.raises(FileValidationError):
            self.file_manager._validate_single_file(nonexistent_file)
    
    def test_generate_output_filename(self):
        """Test output filename generation."""
        input_path = "/path/to/input.mp4"
        naming_pattern = "{original}_converted"
        suffix = "_audio"
        
        output_filename = self.file_manager.generate_output_filename(
            input_path, naming_pattern, suffix
        )
        
        assert output_filename == "input_converted.mp3"
    
    def test_get_file_info(self):
        """Test getting file information."""
        test_file = os.path.join(self.temp_dir, "test.mp4")
        with open(test_file, 'w') as f:
            f.write("test content" * 1000)  # Create file with content
        
        file_info = self.file_manager.get_file_info(test_file)
        
        assert file_info['name'] == "test.mp4"
        assert file_info['size_bytes'] > 0
        assert file_info['size_mb'] > 0
        assert file_info['extension'] == ".mp4"
        assert file_info['is_valid'] is True


class TestSettings:
    """Test Settings class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.settings = Settings()
    
    def test_default_settings(self):
        """Test that default settings are applied."""
        assert self.settings.get('audio_quality') == '192'
        assert self.settings.get('auto_open_folder') is True
        assert self.settings.get('max_concurrent_conversions') == 4
    
    def test_setting_and_getting_values(self):
        """Test setting and getting values."""
        self.settings.set('audio_quality', '320')
        assert self.settings.get('audio_quality') == '320'
        
        self.settings.set('auto_open_folder', False)
        assert self.settings.get('auto_open_folder') is False
    
    def test_audio_quality_options(self):
        """Test audio quality options."""
        options = self.settings.get_audio_quality_options()
        assert '128' in options
        assert '192' in options
        assert '320' in options
    
    def test_naming_pattern_options(self):
        """Test naming pattern options."""
        options = self.settings.get_naming_pattern_options()
        assert '{original}_converted' in options
        assert '{original}' in options


class TestFFmpegWrapper:
    """Test FFmpegWrapper class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.ffmpeg_wrapper = FFmpegWrapper()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('shutil.which')
    def test_find_ffmpeg_in_path(self, mock_which):
        """Test finding FFmpeg in system PATH."""
        mock_which.return_value = '/usr/local/bin/ffmpeg'
        
        wrapper = FFmpegWrapper()
        assert wrapper.ffmpeg_path == 'ffmpeg'  # Should use 'ffmpeg' from PATH
    
    @patch('shutil.which')
    @patch('pathlib.Path.exists')
    def test_find_ffmpeg_in_common_locations(self, mock_exists, mock_which):
        """Test finding FFmpeg in common locations."""
        mock_which.return_value = None  # Not in PATH
        mock_exists.return_value = True
        
        wrapper = FFmpegWrapper()
        # Should find FFmpeg in one of the common locations
        assert wrapper.ffmpeg_path in ['/usr/local/bin/ffmpeg', '/opt/homebrew/bin/ffmpeg']
    
    @patch('shutil.which')
    def test_ffmpeg_not_found(self, mock_which):
        """Test FFmpeg not found error."""
        mock_which.return_value = None
        
        with pytest.raises(FFmpegNotFoundError):
            FFmpegWrapper()
    
    def test_build_ffmpeg_command(self):
        """Test building FFmpeg command."""
        input_path = "/input/video.mp4"
        output_path = "/output/audio.mp3"
        options = {
            'bitrate': '192',
            'preserve_metadata': True,
            'volume_normalization': False,
        }
        
        cmd = self.ffmpeg_wrapper._build_ffmpeg_command(input_path, output_path, options)
        
        assert 'ffmpeg' in cmd[0]
        assert '-i' in cmd
        assert input_path in cmd
        assert '-acodec' in cmd
        assert 'libmp3lame' in cmd[cmd.index('-acodec') + 1]
        assert '-ab' in cmd
        assert '192k' in cmd[cmd.index('-ab') + 1]
        assert output_path in cmd


class TestConversionManager:
    """Test ConversionManager class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.settings = Mock()
        self.settings.get.side_effect = lambda key, default=None: {
            'audio_quality': '192',
            'max_concurrent_conversions': 4,
            'output_directory': '/tmp/output',
            'file_naming_pattern': '{original}_converted',
            'output_suffix': '_converted',
            'preserve_metadata': True,
            'volume_normalization': False,
            'delete_original': False,
        }.get(key, default)
        
        self.conversion_manager = ConversionManager(self.settings)
    
    def test_start_conversion_with_no_files(self):
        """Test starting conversion with no files."""
        self.conversion_manager.conversion_error.connect(
            lambda msg: setattr(self, 'error_message', msg)
        )
        
        self.conversion_manager.start_conversion([])
        
        assert hasattr(self, 'error_message')
        assert self.error_message == "変換するファイルがありません"
    
    def test_conversion_progress_tracking(self):
        """Test conversion progress tracking."""
        files = [
            {'input_path': '/input/file1.mp4', 'name': 'file1.mp4'},
            {'input_path': '/input/file2.mp4', 'name': 'file2.mp4'},
        ]
        
        progress_updates = []
        
        def track_progress(file_name, progress, current, total):
            progress_updates.append({
                'file_name': file_name,
                'progress': progress,
                'current': current,
                'total': total
            })
        
        self.conversion_manager.conversion_progress.connect(track_progress)
        
        # Mock the conversion to simulate progress
        with patch.object(self.conversion_manager, '_convert_single_file'):
            self.conversion_manager.start_conversion(files)
            
            # Simulate some progress
            self.conversion_manager._on_worker_progress('file1.mp4', 50)
            self.conversion_manager._on_worker_completed('file1.mp4', True, 'Success')
            self.conversion_manager._on_worker_progress('file2.mp4', 75)
            self.conversion_manager._on_worker_completed('file2.mp4', True, 'Success')
        
        assert len(progress_updates) > 0
        assert any(update['file_name'] == 'file1.mp4' for update in progress_updates)
    
    def test_cancel_conversion(self):
        """Test conversion cancellation."""
        files = [
            {'input_path': '/input/file1.mp4', 'name': 'file1.mp4'},
        ]
        
        self.conversion_manager.start_conversion(files)
        assert self.conversion_manager.converting is True
        
        self.conversion_manager.cancel_conversion()
        assert self.conversion_manager.cancelled is True
        assert self.conversion_manager.converting is False


class TestConversionWorker:
    """Test ConversionWorker class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.settings = Mock()
        self.settings.get.side_effect = lambda key, default=None: {
            'audio_quality': '192',
            'output_directory': '/tmp/output',
            'file_naming_pattern': '{original}_converted',
            'output_suffix': '_converted',
            'preserve_metadata': True,
            'volume_normalization': False,
            'delete_original': False,
        }.get(key, default)
        
        self.ffmpeg_wrapper = Mock()
        self.file_info = {
            'input_path': '/input/test.mp4',
            'name': 'test.mp4'
        }
        
        self.worker = ConversionWorker(self.file_info, self.settings, self.ffmpeg_wrapper)
    
    def test_worker_initialization(self):
        """Test worker initialization."""
        assert self.worker.file_info == self.file_info
        assert self.worker.settings == self.settings
        assert self.worker.ffmpeg_wrapper == self.ffmpeg_wrapper
        assert self.worker.cancelled is False
    
    def test_worker_cancellation(self):
        """Test worker cancellation."""
        self.worker.cancel()
        assert self.worker.cancelled is True
    
    @patch('converter.conversion_manager.FileManager')
    def test_worker_run_success(self, mock_file_manager_class):
        """Test successful worker execution."""
        # Mock FileManager
        mock_file_manager = Mock()
        mock_file_manager_class.return_value = mock_file_manager
        mock_file_manager.generate_output_filename.return_value = "test_converted.mp3"
        
        # Mock FFmpeg wrapper
        self.ffmpeg_wrapper.convert_mp4_to_mp3.return_value = True
        
        # Track signals
        progress_updates = []
        completion_results = []
        
        def track_progress(file_name, progress):
            progress_updates.append((file_name, progress))
        
        def track_completion(file_name, success, message):
            completion_results.append((file_name, success, message))
        
        self.worker.progress_updated.connect(track_progress)
        self.worker.conversion_completed.connect(track_completion)
        
        # Run worker
        self.worker.run()
        
        # Verify FFmpeg was called
        self.ffmpeg_wrapper.convert_mp4_to_mp3.assert_called_once()
        
        # Verify completion signal
        assert len(completion_results) == 1
        assert completion_results[0][1] is True  # success
        assert completion_results[0][2] == "変換完了"  # message


class TestIntegration:
    """Integration tests for the complete application."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.settings = Settings()
        self.file_manager = FileManager()
        self.logger = setup_logger("test")
        
        self.file_manager.set_logger(self.logger)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_end_to_end_conversion_workflow(self):
        """Test complete conversion workflow."""
        # Create a test MP4 file (empty file for testing)
        test_mp4 = os.path.join(self.temp_dir, "test_video.mp4")
        Path(test_mp4).touch()
        
        # Set up settings
        output_dir = os.path.join(self.temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        self.settings.set('output_directory', output_dir)
        self.settings.set('audio_quality', '192')
        
        # Validate file
        valid_files, invalid_files = self.file_manager.validate_input_files([test_mp4])
        assert len(valid_files) == 1
        assert len(invalid_files) == 0
        
        # Generate output filename
        naming_pattern = self.settings.get('file_naming_pattern')
        suffix = self.settings.get('output_suffix')
        output_filename = self.file_manager.generate_output_filename(
            test_mp4, naming_pattern, suffix
        )
        assert output_filename == "test_video_converted.mp3"
        
        # Check output path
        expected_output = os.path.join(output_dir, output_filename)
        assert expected_output.endswith(".mp3")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])