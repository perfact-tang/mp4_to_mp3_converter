"""
FFmpeg wrapper for MP4 to MP3 conversion.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from exceptions import ConversionError, FFmpegNotFoundError, DiskSpaceError


class FFmpegWrapper:
    """Wrapper for FFmpeg command-line operations."""
    
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.logger = None
    
    def set_logger(self, logger):
        """Set logger instance."""
        self.logger = logger
    
    def _find_ffmpeg(self) -> str:
        """
        Find FFmpeg binary in system PATH or bundled location.
        
        Returns:
            str: Path to FFmpeg binary
            
        Raises:
            FFmpegNotFoundError: If FFmpeg is not found
        """
        # Check common locations
        possible_paths = [
            'ffmpeg',  # System PATH
            '/usr/local/bin/ffmpeg',  # Homebrew on macOS
            '/opt/homebrew/bin/ffmpeg',  # Homebrew on Apple Silicon
            './ffmpeg',  # Bundled with app
            '../ffmpeg',  # Relative to app
        ]
        
        for path in possible_paths:
            if shutil.which(path):
                return path
        
        # Check if FFmpeg exists but not in PATH
        for path in possible_paths[1:]:  # Skip 'ffmpeg' as it's already checked
            if Path(path).exists() and os.access(path, os.X_OK):
                return path
        
        raise FFmpegNotFoundError(
            "FFmpegが見つかりません。FFmpegをインストールしてください。"
        )
    
    def get_ffmpeg_version(self) -> str:
        """
        Get FFmpeg version information.
        
        Returns:
            str: FFmpeg version string
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Extract version from first line
                first_line = result.stdout.split('\n')[0]
                return first_line.strip()
            else:
                return "Unknown"
                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return "Unknown"
    
    def convert_mp4_to_mp3(self, input_path: str, output_path: str, 
                          options: Dict[str, Any] = None,
                          progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """
        Convert MP4 file to MP3 format.
        
        Args:
            input_path (str): Input MP4 file path
            output_path (str): Output MP3 file path
            options (Dict[str, Any]): Conversion options
            progress_callback (Optional[Callable]): Progress callback function
            
        Returns:
            bool: Success status
            
        Raises:
            ConversionError: If conversion fails
            DiskSpaceError: If insufficient disk space
        """
        if options is None:
            options = {}
        
        # Validate input path
        if not input_path or input_path.strip() == '':
            raise ConversionError("入力ファイルパスが空です")
        
        # Validate input file
        if not Path(input_path).exists():
            raise ConversionError(f"入力ファイルが見つかりません: {input_path}")
        
        # Check disk space (estimate 10% of video size for audio)
        input_size = Path(input_path).stat().st_size
        estimated_output_size = int(input_size * 0.1)  # Rough estimate
        
        output_dir = Path(output_path).parent
        self._check_disk_space(str(output_dir), estimated_output_size)
        
        # Build FFmpeg command
        cmd = self._build_ffmpeg_command(input_path, output_path, options)
        
        if self.logger:
            self.logger.info(f"Starting conversion: {input_path} -> {output_path}")
            self.logger.debug(f"FFmpeg command: {' '.join(cmd)}")
        
        try:
            # Run FFmpeg with progress monitoring
            success = self._run_ffmpeg_with_progress(cmd, progress_callback)
            
            if success:
                if self.logger:
                    self.logger.info(f"Conversion completed successfully: {output_path}")
                return True
            else:
                raise ConversionError("FFmpeg conversion failed")
                
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg error: {e.stderr if e.stderr else 'Unknown error'}"
            if self.logger:
                self.logger.error(error_msg)
            raise ConversionError(error_msg)
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Conversion error: {e}")
            raise ConversionError(f"変換エラー: {str(e)}")
    
    def _build_ffmpeg_command(self, input_path: str, output_path: str, 
                              options: Dict[str, Any]) -> list:
        """
        Build FFmpeg command with specified options.
        
        Args:
            input_path (str): Input file path
            output_path (str): Output file path
            options (Dict[str, Any]): Conversion options
            
        Returns:
            list: FFmpeg command arguments
        """
        cmd = [self.ffmpeg_path, '-i', input_path]
        
        # Audio codec
        cmd.extend(['-acodec', 'libmp3lame'])
        
        # Audio bitrate
        bitrate = options.get('bitrate', '192')
        cmd.extend(['-ab', f'{bitrate}k'])
        
        # Audio channels (default to stereo)
        channels = options.get('channels', 2)
        cmd.extend(['-ac', str(channels)])
        
        # Sample rate
        sample_rate = options.get('sample_rate', '44100')
        cmd.extend(['-ar', sample_rate])
        
        # Metadata options
        if options.get('preserve_metadata', True):
            cmd.extend(['-map_metadata', '0'])
        
        # Volume normalization
        if options.get('volume_normalization', False):
            cmd.extend(['-af', 'loudnorm'])
        
        # Fade in/out
        fade_in = options.get('fade_in', 0)
        fade_out = options.get('fade_out', 0)
        if fade_in > 0 or fade_out > 0:
            fade_filters = []
            if fade_in > 0:
                fade_filters.append(f"afade=t=in:st=0:d={fade_in}")
            if fade_out > 0:
                # Get video duration first (simplified approach)
                duration = self._get_video_duration(input_path)
                if duration and duration > fade_out:
                    fade_filters.append(f"afade=t=out:st={duration-fade_out}:d={fade_out}")
            
            if fade_filters:
                cmd.extend(['-af', ','.join(fade_filters)])
        
        # Overwrite output file
        cmd.append('-y')
        
        # Output file
        cmd.append(output_path)
        
        return cmd
    
    def _get_video_duration(self, input_path: str) -> Optional[float]:
        """
        Get video duration using ffprobe.
        
        Args:
            input_path (str): Input file path
            
        Returns:
            Optional[float]: Duration in seconds or None
        """
        try:
            # Try to find ffprobe
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg', 'ffprobe')
            if not shutil.which(ffprobe_path):
                return None
            
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return float(result.stdout.strip())
            
        except (ValueError, subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
        
        return None
    
    def _run_ffmpeg_with_progress(self, cmd: list, 
                                  progress_callback: Optional[Callable[[int], None]]) -> bool:
        """
        Run FFmpeg command with progress monitoring.
        
        Args:
            cmd (list): FFmpeg command
            progress_callback (Optional[Callable]): Progress callback
            
        Returns:
            bool: Success status
        """
        try:
            # Start FFmpeg process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor progress (simplified approach)
            # FFmpeg doesn't provide easy progress parsing, so we use time-based estimation
            if progress_callback:
                # Simulate progress updates
                import time
                for progress in range(0, 101, 5):
                    progress_callback(progress)
                    time.sleep(0.1)  # Simulate conversion time
            
            # Wait for process to complete
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                if progress_callback:
                    progress_callback(100)
                return True
            else:
                if self.logger:
                    self.logger.error(f"FFmpeg error: {stderr}")
                return False
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error running FFmpeg: {e}")
            return False
    
    def _check_disk_space(self, directory: str, required_bytes: int) -> None:
        """
        Check if there's enough disk space.
        
        Args:
            directory (str): Directory to check
            required_bytes (int): Required space in bytes
            
        Raises:
            DiskSpaceError: If insufficient space
        """
        try:
            stat = os.statvfs(directory)
            available_bytes = stat.f_frsize * stat.f_bavail
            
            if available_bytes < required_bytes:
                raise DiskSpaceError(
                    f"Insufficient disk space in {directory}",
                    required_space=required_bytes,
                    available_space=available_bytes
                )
                
        except OSError:
            # If we can't check disk space, continue anyway
            pass
    
    def validate_ffmpeg(self) -> bool:
        """
        Validate that FFmpeg is working correctly.
        
        Returns:
            bool: Validation status
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            return result.returncode == 0
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False
    
    def get_supported_formats(self) -> Dict[str, str]:
        """
        Get supported audio formats.
        
        Returns:
            Dict[str, str]: Format name -> description
        """
        return {
            'mp3': 'MP3 - MPEG Audio Layer III',
            'aac': 'AAC - Advanced Audio Coding',
            'wav': 'WAV - Waveform Audio File Format',
            'flac': 'FLAC - Free Lossless Audio Codec',
            'ogg': 'OGG - Ogg Vorbis',
            'm4a': 'M4A - MPEG-4 Audio'
        }
