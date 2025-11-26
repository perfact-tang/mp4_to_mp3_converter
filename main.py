#!/usr/bin/env python3
"""
MP4 to MP3 Converter - Main Application Entry Point

A macOS GUI application for converting MP4 video files to MP3 audio format.
Features drag-and-drop functionality, batch conversion, and progress tracking.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from gui.main_window import MainWindow
    from utils.logger import setup_logger
    from config.settings import Settings
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please install required dependencies: pip install -r requirements.txt")
    sys.exit(1)


def main():
    """Main application entry point."""
    # Enable high DPI scaling for macOS
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("MP4 to MP3 Converter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("MP4toMP3Converter")
    
    # Set application icon (if available)
    icon_path = Path(__file__).parent / "icons" / "app.icns"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # Setup logging
    logger = setup_logger()
    logger.info("MP4 to MP3 Converter started")
    
    # Load settings
    settings = Settings()
    
    try:
        # Create and show main window
        main_window = MainWindow(settings)
        main_window.show()
        
        # Run application
        return app.exec()
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Application error: {e}")
        return 1
    finally:
        logger.info("MP4 to MP3 Converter stopped")


if __name__ == "__main__":
    sys.exit(main())