"""
Conversion manager for handling batch MP4 to MP3 conversions.
"""

import os
import time
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer

from converter.ffmpeg_wrapper import FFmpegWrapper
from utils.file_manager import FileManager
from exceptions import ConversionError, ConversionCancelledError


class ConversionWorker(QThread):
    """Worker thread for individual file conversion."""
    
    progress_updated = pyqtSignal(str, int)  # file_name, progress
    conversion_completed = pyqtSignal(str, bool, str)  # file_name, success, message
    
    def __init__(self, file_info: Dict[str, Any], settings: Any, ffmpeg_wrapper: FFmpegWrapper):
        super().__init__()
        self.file_info = file_info
        self.settings = settings
        self.ffmpeg_wrapper = ffmpeg_wrapper
        self.cancelled = False
    
    def run(self):
        """Run the conversion."""
        try:
            if self.cancelled:
                return
            
            input_path = self.file_info['input_path']
            output_name = self.file_info['output_name']
            
            # Generate output filename
            naming_pattern = self.settings.get('file_naming_pattern')
            suffix = self.settings.get('output_suffix', '_converted')
            
            file_manager = FileManager()
            output_filename = file_manager.generate_output_filename(
                input_path, naming_pattern, suffix
            )
            
            output_path = os.path.join(
                self.settings.get_output_directory(),
                output_filename
            )
            
            # Prepare conversion options
            options = {
                'bitrate': self.settings.get('audio_quality', '192'),
                'preserve_metadata': self.settings.get('preserve_metadata', True),
                'volume_normalization': self.settings.get('volume_normalization', False),
                'fade_in': self.settings.get('fade_in', 0),
                'fade_out': self.settings.get('fade_out', 0),
            }
            
            # Progress callback
            def progress_callback(progress: int):
                if self.cancelled:
                    return False
                self.progress_updated.emit(output_name, progress)
                return True
            
            # Perform conversion
            success = self.ffmpeg_wrapper.convert_mp4_to_mp3(
                input_path, output_path, options, progress_callback
            )
            
            if self.cancelled:
                message = "キャンセルされました"
                success = False
            elif success:
                message = "変換完了"
                
                # Delete original file if enabled
                if self.settings.get('delete_original', False):
                    try:
                        os.remove(input_path)
                    except OSError:
                        pass  # Ignore deletion errors
            else:
                message = "変換失敗"
            
            self.conversion_completed.emit(output_name, success, message)
            
        except ConversionCancelledError:
            file_name = self.file_info.get('name', 'Unknown File')
            self.conversion_completed.emit(file_name, False, "キャンセルされました")
        except Exception as e:
            file_name = self.file_info.get('name', 'Unknown File')
            self.conversion_completed.emit(file_name, False, str(e))
    
    def cancel(self):
        """Cancel the conversion."""
        self.cancelled = True


class ConversionManager(QObject):
    """Manages batch conversion of MP4 files to MP3."""
    
    conversion_started = pyqtSignal(int)  # total_files
    conversion_progress = pyqtSignal(str, int, int, int)  # file_name, progress, current, total
    conversion_completed = pyqtSignal(str, bool, str)  # file_name, success, message
    all_conversions_completed = pyqtSignal(int, int)  # success_count, total_count
    conversion_error = pyqtSignal(str)  # error_message
    
    def __init__(self, settings: Any):
        super().__init__()
        self.settings = settings
        self.ffmpeg_wrapper = FFmpegWrapper()
        self.file_manager = FileManager()
        
        self.converting = False
        self.cancelled = False
        self.workers = []
        self.completed_count = 0
        self.success_count = 0
        self.total_files = 0
        
        self.logger = None
    
    def set_logger(self, logger):
        """Set logger instance."""
        self.logger = logger
        self.ffmpeg_wrapper.set_logger(logger)
        self.file_manager.set_logger(logger)
    
    def start_conversion(self, files_to_convert: List[Dict[str, Any]]):
        """
        Start batch conversion of files.
        
        Args:
            files_to_convert (List[Dict[str, Any]]): List of files to convert
        """
        if self.converting:
            return
        
        if not files_to_convert:
            self.conversion_error.emit("変換するファイルがありません")
            return
        
        self.converting = True
        self.cancelled = False
        self.workers = []
        self.completed_count = 0
        self.success_count = 0
        self.total_files = len(files_to_convert)
        
        self.conversion_started.emit(self.total_files)
        
        if self.logger:
            self.logger.info(f"Starting conversion of {self.total_files} files")
        
        # Start conversion with limited concurrency
        max_concurrent = self.settings.get('max_concurrent_conversions', 4)
        self._process_files(files_to_convert, max_concurrent)
    
    def _process_files(self, files_to_convert: List[Dict[str, Any]], max_concurrent: int):
        """Process files with limited concurrency."""
        import queue
        import threading
        
        file_queue = queue.Queue()
        for file_info in files_to_convert:
            file_queue.put(file_info)
        
        def worker_thread():
            while not file_queue.empty() and not self.cancelled:
                try:
                    file_info = file_queue.get_nowait()
                    self._convert_single_file(file_info)
                    file_queue.task_done()
                except queue.Empty:
                    break
        
        # Start worker threads
        threads = []
        for _ in range(min(max_concurrent, len(files_to_convert))):
            thread = threading.Thread(target=worker_thread)
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check if all conversions are complete
        self._check_all_conversions_complete()
    
    def _convert_single_file(self, file_info: Dict[str, Any]):
        """Convert a single file."""
        if self.cancelled:
            return
        
        try:
            # Create worker thread for this file
            worker = ConversionWorker(file_info, self.settings, self.ffmpeg_wrapper)
            
            # Connect signals
            worker.progress_updated.connect(self._on_worker_progress)
            worker.conversion_completed.connect(self._on_worker_completed)
            
            self.workers.append(worker)
            
            # Run conversion (blocking in this thread)
            worker.run()
            
        except Exception as e:
            if self.logger:
                file_name = file_info.get('name', 'Unknown File')
                self.logger.error(f"Error converting file {file_name}: {e}")
            file_name = file_info.get('name', 'Unknown File')
            self.conversion_error.emit(f"ファイル変換エラー: {file_name}")
    
    def _on_worker_progress(self, file_name: str, progress: int):
        """Handle worker progress update."""
        self.conversion_progress.emit(file_name, progress, self.completed_count, self.total_files)
    
    def _on_worker_completed(self, file_name: str, success: bool, message: str):
        """Handle worker completion."""
        self.completed_count += 1
        if success:
            self.success_count += 1
        
        self.conversion_completed.emit(file_name, success, message)
        
        # Check if all conversions are complete
        self._check_all_conversions_complete()
    
    def _check_all_conversions_complete(self):
        """Check if all conversions are complete."""
        if self.completed_count >= self.total_files:
            self.converting = False
            self.all_conversions_completed.emit(self.success_count, self.total_files)
            
            if self.logger:
                self.logger.info(
                    f"Conversion batch completed: {self.success_count}/{self.total_files} successful"
                )
    
    def cancel_conversion(self):
        """Cancel the current conversion process."""
        if not self.converting:
            return
        
        self.cancelled = True
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        if self.logger:
            self.logger.info("Conversion cancelled by user")
        
        self.converting = False
    
    def is_converting(self) -> bool:
        """Check if conversion is in progress."""
        return self.converting
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current conversion progress."""
        return {
            'converting': self.converting,
            'completed': self.completed_count,
            'total': self.total_files,
            'success_count': self.success_count,
            'progress_percentage': (self.completed_count / self.total_files * 100) if self.total_files > 0 else 0
        }
