"""
File manager utility for MP4 to MP3 Converter application.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
from exceptions import FileValidationError, OutputDirectoryError, DiskSpaceError


class FileManager:
    """Manages file operations for the converter application."""
    
    # Supported video file extensions
    SUPPORTED_EXTENSIONS = {'.mp4', '.m4v', '.mov', '.avi', '.mkv', '.flv', '.wmv'}
    
    def __init__(self):
        self.logger = None  # Will be set by the application
    
    def set_logger(self, logger):
        """Set logger instance."""
        self.logger = logger
    
    def validate_input_files(self, file_paths: List[str]) -> Tuple[List[str], List[str]]:
        """
        Validate input files and return valid and invalid file lists.
        
        Args:
            file_paths (List[str]): List of file paths to validate
            
        Returns:
            Tuple[List[str], List[str]]: (valid_files, invalid_files)
        """
        valid_files = []
        invalid_files = []
        
        for file_path in file_paths:
            try:
                self._validate_single_file(file_path)
                valid_files.append(file_path)
            except FileValidationError as e:
                invalid_files.append(file_path)
                if self.logger:
                    self.logger.warning(f"Invalid file: {file_path} - {e}")
        
        return valid_files, invalid_files
    
    def _validate_single_file(self, file_path: str) -> None:
        """
        Validate a single input file.
        
        Args:
            file_path (str): File path to validate
            
        Raises:
            FileValidationError: If file is invalid
        """
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            raise FileValidationError(f"ファイルが存在しません: {file_path}", file_path)
        
        # Check if it's a file (not directory)
        if not path.is_file():
            raise FileValidationError(f"ファイルではありません: {file_path}", file_path)
        
        # Check file extension
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise FileValidationError(
                f"サポートされていないファイル形式です: {path.suffix}", 
                file_path
            )
        
        # Check file size (minimum 1KB, maximum 10GB)
        file_size = path.stat().st_size
        if file_size < 1024:  # Less than 1KB
            raise FileValidationError(f"ファイルが小さすぎます: {file_path}", file_path)
        if file_size > 10 * 1024 * 1024 * 1024:  # More than 10GB
            raise FileValidationError(f"ファイルが大きすぎます: {file_path}", file_path)
    
    def select_output_directory(self, parent=None) -> Optional[str]:
        """
        Show directory selection dialog.
        
        Args:
            parent: Parent widget for the dialog
            
        Returns:
            Optional[str]: Selected directory path or None
        """
        from PyQt6.QtWidgets import QFileDialog
        
        dialog = QFileDialog(parent)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setWindowTitle("出力フォルダを選択")
        
        if dialog.exec():
            selected_dirs = dialog.selectedFiles()
            if selected_dirs:
                return selected_dirs[0]
        
        return None
    
    def generate_output_filename(self, input_path: str, naming_pattern: str, 
                               suffix: str = "_converted") -> str:
        """
        Generate output filename based on input file and naming pattern.
        
        Args:
            input_path (str): Input file path
            naming_pattern (str): Naming pattern
            suffix (str): File suffix
            
        Returns:
            str: Generated output filename
        """
        input_path_obj = Path(input_path)
        original_name = input_path_obj.stem
        
        # Replace placeholders in pattern
        output_name = naming_pattern.replace('{original}', original_name)
        output_name = output_name.replace('{suffix}', suffix)
        
        # Ensure we have a valid filename
        if not output_name or output_name == original_name:
            output_name = f"{original_name}{suffix}"
        
        # Add .mp3 extension
        return f"{output_name}.mp3"
    
    def check_disk_space(self, directory: str, required_bytes: int) -> bool:
        """
        Check if there's enough disk space in the specified directory.
        
        Args:
            directory (str): Directory to check
            required_bytes (int): Required space in bytes
            
        Returns:
            bool: True if enough space available
            
        Raises:
            DiskSpaceError: If insufficient space
        """
        try:
            stat = shutil.disk_usage(directory)
            available_bytes = stat.free
            
            if available_bytes < required_bytes:
                raise DiskSpaceError(
                    f"Insufficient disk space in {directory}",
                    required_space=required_bytes,
                    available_space=available_bytes
                )
            
            return True
            
        except OSError as e:
            raise OutputDirectoryError(f"Cannot access directory: {directory}")
    
    def get_file_size_mb(self, file_path: str) -> float:
        """
        Get file size in megabytes.
        
        Args:
            file_path (str): File path
            
        Returns:
            float: File size in MB
        """
        try:
            return os.path.getsize(file_path) / (1024 * 1024)
        except OSError:
            return 0.0
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Get comprehensive file information.
        
        Args:
            file_path (str): File path
            
        Returns:
            dict: File information
        """
        try:
            path = Path(file_path)
            stat = path.stat()
            
            return {
                'name': path.name,
                'path': str(path.absolute()),
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified_time': stat.st_mtime,
                'extension': path.suffix.lower(),
                'is_valid': path.suffix.lower() in self.SUPPORTED_EXTENSIONS
            }
        except OSError:
            return {
                'name': Path(file_path).name,
                'path': str(Path(file_path).absolute()),
                'size_bytes': 0,
                'size_mb': 0.0,
                'modified_time': 0,
                'extension': '',
                'is_valid': False
            }
    
    def create_output_directory(self, directory: str) -> None:
        """
        Create output directory if it doesn't exist.
        
        Args:
            directory (str): Directory path
            
        Raises:
            OutputDirectoryError: If directory cannot be created
        """
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OutputDirectoryError(f"Cannot create directory: {directory}")
    
    def delete_file_safely(self, file_path: str) -> bool:
        """
        Safely delete a file.
        
        Args:
            file_path (str): File path to delete
            
        Returns:
            bool: Success status
        """
        try:
            Path(file_path).unlink()
            if self.logger:
                self.logger.info(f"Deleted file: {file_path}")
            return True
        except OSError as e:
            if self.logger:
                self.logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    def open_file_location(self, file_path: str) -> bool:
        """
        Open file location in Finder.
        
        Args:
            file_path (str): File path
            
        Returns:
            bool: Success status
        """
        try:
            import subprocess
            path = Path(file_path)
            if path.exists():
                subprocess.run(['open', '-R', str(path)], check=True)
                return True
            return False
        except (OSError, subprocess.CalledProcessError):
            return False
