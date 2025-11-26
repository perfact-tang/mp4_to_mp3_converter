"""
Main window for MP4 to MP3 Converter application.
"""

import os
from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QProgressBar, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QGroupBox, QSplitter, QFrame, QMenuBar, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QAction

from utils.logger import get_logger
from utils.file_manager import FileManager
from converter.conversion_manager import ConversionManager
from config.settings import Settings
from gui.settings_dialog import SettingsDialog
from gui.file_list_item import FileListItem
from exceptions import ConversionError, FFmpegNotFoundError


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.logger = get_logger()
        self.file_manager = FileManager()
        self.file_manager.set_logger(self.logger)
        self.conversion_manager = None
        self.conversion_thread = None
        
        self.setAcceptDrops(True)
        self.setup_ui()
        self.setup_menu()
        self.load_settings()
        
        # Setup conversion manager
        self.setup_conversion_manager()
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("MP4 to MP3 Converter")
        self.setMinimumSize(800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Drop area and controls
        left_panel = self.create_left_panel()
        
        # Right panel - File list
        right_panel = self.create_right_panel()
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("準備完了 - MP4ファイルをドラッグ＆ドロップしてください")
    
    def create_left_panel(self) -> QWidget:
        """Create the left control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Drop area
        drop_group = QGroupBox("ファイルをドロップ")
        drop_layout = QVBoxLayout(drop_group)
        
        self.drop_label = QLabel("📁\n\nMP4ファイルをここにドラッグ＆ドロップ")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #8E8E93;
                border-radius: 8px;
                padding: 40px;
                background-color: rgba(255, 255, 255, 0.5);
                color: #8E8E93;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #007AFF;
                background-color: rgba(0, 122, 255, 0.1);
            }
        """)
        
        drop_layout.addWidget(self.drop_label)
        
        # Add files button
        add_files_btn = QPushButton("📁 ファイルを追加")
        add_files_btn.clicked.connect(self.add_files)
        add_files_btn.setStyleSheet(self.get_button_style())
        drop_layout.addWidget(add_files_btn)
        
        layout.addWidget(drop_group)
        
        # Output directory
        output_group = QGroupBox("出力フォルダ")
        output_layout = QVBoxLayout(output_group)
        
        self.output_path_label = QLabel("未設定")
        self.output_path_label.setStyleSheet("color: #8E8E93; padding: 5px;")
        self.output_path_label.setWordWrap(True)
        
        select_output_btn = QPushButton("📁 出力フォルダを選択")
        select_output_btn.clicked.connect(self.select_output_directory)
        select_output_btn.setStyleSheet(self.get_button_style())
        
        output_layout.addWidget(self.output_path_label)
        output_layout.addWidget(select_output_btn)
        
        layout.addWidget(output_group)
        
        # Control buttons
        control_group = QGroupBox("変換")
        control_layout = QVBoxLayout(control_group)
        
        self.convert_btn = QPushButton("🔄 変換を開始")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setEnabled(False)
        self.convert_btn.setStyleSheet(self.get_primary_button_style())
        
        self.cancel_btn = QPushButton("⏹ キャンセル")
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet(self.get_button_style())
        
        control_layout.addWidget(self.convert_btn)
        control_layout.addWidget(self.cancel_btn)
        
        layout.addWidget(control_group)
        
        # Overall progress
        self.overall_progress = QProgressBar()
        self.overall_progress.setVisible(False)
        layout.addWidget(self.overall_progress)
        
        layout.addStretch()
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create the right file list panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E5E5EA;
                border-radius: 8px;
                background-color: white;
            }
            QListWidget::item {
                border-bottom: 1px solid #F2F2F7;
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #007AFF;
                color: white;
            }
        """)
        
        layout.addWidget(self.file_list)
        
        # File list controls
        controls_layout = QHBoxLayout()
        
        self.remove_selected_btn = QPushButton("🗑 選択削除")
        self.remove_selected_btn.clicked.connect(self.remove_selected_files)
        self.remove_selected_btn.setStyleSheet(self.get_button_style())
        
        self.clear_all_btn = QPushButton("🗑 すべてクリア")
        self.clear_all_btn.clicked.connect(self.clear_all_files)
        self.clear_all_btn.setStyleSheet(self.get_button_style())
        
        controls_layout.addWidget(self.remove_selected_btn)
        controls_layout.addWidget(self.clear_all_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        return panel
    
    def setup_menu(self):
        """Setup application menu."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("ファイル")
        
        add_files_action = QAction("ファイルを追加...", self)
        add_files_action.setShortcut("Ctrl+O")
        add_files_action.triggered.connect(self.add_files)
        file_menu.addAction(add_files_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("終了", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("編集")
        
        settings_action = QAction("設定...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("ヘルプ")
        
        about_action = QAction("このアプリについて", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_conversion_manager(self):
        """Setup the conversion manager and thread."""
        self.conversion_manager = ConversionManager(self.settings)
        self.conversion_manager.set_logger(self.logger)
        
        # Connect signals
        self.conversion_manager.conversion_started.connect(self.on_conversion_started)
        self.conversion_manager.conversion_progress.connect(self.on_conversion_progress)
        self.conversion_manager.conversion_completed.connect(self.on_conversion_completed)
        self.conversion_manager.conversion_error.connect(self.on_conversion_error)
        self.conversion_manager.all_conversions_completed.connect(self.on_all_conversions_completed)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events."""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                files.append(file_path)
        
        if files:
            self.add_files_to_list(files)
    
    def add_files(self):
        """Add files through file dialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "MP4ファイルを選択",
            "",
            "ビデオファイル (*.mp4 *.m4v *.mov *.avi *.mkv *.flv *.wmv)"
        )
        
        if files:
            self.add_files_to_list(files)
    
    def add_files_to_list(self, file_paths: List[str]):
        """Add files to the conversion list."""
        valid_files, invalid_files = self.file_manager.validate_input_files(file_paths)
        
        for file_path in valid_files:
            file_info = self.file_manager.get_file_info(file_path)
            item = FileListItem(file_info)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item.sizeHint())
            
            self.file_list.addItem(list_item)
            self.file_list.setItemWidget(list_item, item)
        
        if invalid_files:
            QMessageBox.warning(
                self,
                "無効なファイル",
                f"{len(invalid_files)}個のファイルは無効でした。\n"
                "MP4形式のファイルのみサポートしています。"
            )
        
        self.update_convert_button_state()
        self.status_bar.showMessage(f"{len(valid_files)}個のファイルを追加しました")
    
    def remove_selected_files(self):
        """Remove selected files from the list."""
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
        
        self.update_convert_button_state()
    
    def clear_all_files(self):
        """Clear all files from the list."""
        self.file_list.clear()
        self.update_convert_button_state()
    
    def select_output_directory(self):
        """Select output directory."""
        directory = self.file_manager.select_output_directory(self)
        if directory:
            self.settings.set('output_directory', directory)
            self.output_path_label.setText(directory)
            self.update_convert_button_state()
    
    def update_convert_button_state(self):
        """Update convert button enabled state."""
        has_files = self.file_list.count() > 0
        has_output = bool(self.settings.get('output_directory'))
        self.convert_btn.setEnabled(has_files and has_output)
    
    def start_conversion(self):
        """Start the conversion process."""
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "エラー", "変換するファイルがありません。")
            return
        
        if not self.settings.get('output_directory'):
            QMessageBox.warning(self, "エラー", "出力フォルダを選択してください。")
            return
        
        # Collect files to convert
        files_to_convert = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            widget = self.file_list.itemWidget(item)
            files_to_convert.append({
                'input_path': widget.file_info['path'],
                'output_name': widget.file_info['name']
            })

        # Start conversion
        self.conversion_manager.start_conversion(files_to_convert)
    
    def cancel_conversion(self):
        """Cancel the current conversion."""
        if self.conversion_manager:
            self.conversion_manager.cancel_conversion()
    
    def on_conversion_started(self, total_files: int):
        """Handle conversion started signal."""
        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.overall_progress.setVisible(True)
        self.overall_progress.setMaximum(total_files)
        self.overall_progress.setValue(0)
        self.status_bar.showMessage(f"変換中... 0/{total_files} ファイル完了")
    
    def on_conversion_progress(self, file_name: str, progress: int, current: int, total: int):
        """Handle conversion progress signal."""
        # Update individual file progress
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            widget = self.file_list.itemWidget(item)
            if widget.file_info['name'] == file_name:
                widget.update_progress(progress)
                break
        
        # Update overall progress
        self.overall_progress.setValue(current)
        self.status_bar.showMessage(f"変換中... {current}/{total} ファイル完了")
    
    def on_conversion_completed(self, file_name: str, success: bool, message: str):
        """Handle individual conversion completion."""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            widget = self.file_list.itemWidget(item)
            if widget.file_info['name'] == file_name:
                widget.set_conversion_status(success, message)
                break
    
    def on_conversion_error(self, error_message: str):
        """Handle conversion error."""
        QMessageBox.critical(self, "変換エラー", error_message)
    
    def on_all_conversions_completed(self, success_count: int, total_count: int):
        """Handle all conversions completion."""
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.overall_progress.setVisible(False)
        
        if success_count == total_count:
            self.status_bar.showMessage(f"完了: {success_count}/{total_count} ファイル変換成功")
            
            # Auto-open output folder if enabled
            if self.settings.get('auto_open_folder'):
                output_dir = self.settings.get('output_directory')
                self.file_manager.open_file_location(output_dir)
        else:
            self.status_bar.showMessage(f"完了: {success_count}/{total_count} ファイル変換成功")
            QMessageBox.warning(
                self,
                "変換完了",
                f"{success_count}/{total_count} ファイルが正常に変換されました。\n"
                f"{total_count - success_count} 個のファイルでエラーが発生しました。"
            )
    
    def show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self.settings, self)
        dialog.exec()
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "このアプリについて",
            "MP4 to MP3 Converter v1.0.0\n\n"
            "Mac向けのシンプルな動画音声抽出アプリケーションです。\n"
            "ドラッグ＆ドロップで簡単にMP4ファイルからMP3を作成できます。"
        )
    
    def load_settings(self):
        """Load application settings."""
        # Load output directory
        output_dir = self.settings.get_output_directory()
        self.output_path_label.setText(output_dir)
        
        # Load window geometry and state
        geometry = self.settings.get('window_geometry')
        if geometry:
            self.restoreGeometry(geometry)
        
        window_state = self.settings.get('window_state')
        if window_state:
            self.restoreState(window_state)
    
    def save_settings(self):
        """Save application settings."""
        self.settings.set('window_geometry', self.saveGeometry())
        self.settings.set('window_state', self.saveState())
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.save_settings()
        
        # Cancel any ongoing conversion
        if self.conversion_manager and self.conversion_manager.is_converting():
            reply = QMessageBox.question(
                self,
                "変換中",
                "変換が進行中です。終了しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.conversion_manager.cancel_conversion()
            else:
                event.ignore()
                return
        
        event.accept()
    
    def get_button_style(self) -> str:
        """Get standard button style."""
        return """
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #0056CC;
            }
            QPushButton:pressed {
                background-color: #004499;
            }
            QPushButton:disabled {
                background-color: #C7C7CC;
                color: #8E8E93;
            }
        """
    
    def get_primary_button_style(self) -> str:
        """Get primary button style."""
        return """
            QPushButton {
                background-color: #34C759;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #28A745;
            }
            QPushButton:pressed {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #C7C7CC;
                color: #8E8E93;
            }
        """
