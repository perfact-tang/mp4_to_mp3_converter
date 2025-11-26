"""
File list item widget for displaying file information and conversion progress.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon


class FileListItem(QWidget):
    """Custom widget for displaying file information in the list."""
    
    remove_requested = pyqtSignal(str)
    
    def __init__(self, file_info: dict):
        super().__init__()
        self.file_info = file_info
        self.file_info['path'] = file_info.get('path', '')
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # File icon
        icon_label = QLabel("🎬")
        icon_label.setStyleSheet("font-size: 24px;")
        layout.addWidget(icon_label)
        
        # File info
        info_layout = QVBoxLayout()
        
        # File name
        name_label = QLabel(self.file_info['name'])
        name_label.setStyleSheet("font-weight: 500; font-size: 14px;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        # File size and status
        size_label = QLabel(f"サイズ: {self.file_info['size_mb']:.1f} MB")
        size_label.setStyleSheet("color: #8E8E93; font-size: 12px;")
        info_layout.addWidget(size_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #E5E5EA;
                border-radius: 4px;
                background-color: #F2F2F7;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #007AFF;
                border-radius: 4px;
            }
        """)
        info_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("待機中")
        self.status_label.setStyleSheet("color: #8E8E93; font-size: 12px;")
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout, 1)
        
        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #FF3B30;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FFE5E5;
            }
        """)
        remove_btn.clicked.connect(self.request_removal)
        layout.addWidget(remove_btn)
        
        self.setStyleSheet("""
            FileListItem {
                background-color: white;
                border-radius: 6px;
                margin: 2px;
            }
            FileListItem:hover {
                background-color: #F2F2F7;
            }
        """)
    
    def update_progress(self, progress: int):
        """Update conversion progress."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(progress)
        
        if progress < 100:
            self.status_label.setText(f"変換中... {progress}%")
            self.status_label.setStyleSheet("color: #007AFF; font-size: 12px;")
        else:
            self.status_label.setText("完了")
            self.status_label.setStyleSheet("color: #34C759; font-size: 12px;")
    
    def set_conversion_status(self, success: bool, message: str = ""):
        """Set conversion status."""
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_label.setText("✅ 成功")
            self.status_label.setStyleSheet("color: #34C759; font-size: 12px;")
        else:
            self.status_label.setText(f"❌ 失敗: {message}")
            self.status_label.setStyleSheet("color: #FF3B30; font-size: 12px;")
    
    def request_removal(self):
        """Request removal of this item."""
        self.remove_requested.emit(self.file_info['path'])
    
    def get_file_path(self) -> str:
        """Get the file path."""
        return self.file_info['path']