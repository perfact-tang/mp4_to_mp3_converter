"""
Settings dialog for MP4 to MP3 Converter application.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QCheckBox, QSpinBox, QPushButton, QLineEdit,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from config.settings import Settings


class SettingsDialog(QDialog):
    """Settings configuration dialog."""
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("設定")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Audio Quality
        quality_group = QGroupBox("音質設定")
        quality_layout = QVBoxLayout(quality_group)
        
        quality_label = QLabel("出力音質:")
        self.quality_combo = QComboBox()
        
        quality_options = self.settings.get_audio_quality_options()
        for value, description in quality_options.items():
            self.quality_combo.addItem(description, value)
        
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_combo)
        
        layout.addWidget(quality_group)
        
        # File Naming
        naming_group = QGroupBox("ファイル命名")
        naming_layout = QVBoxLayout(naming_group)
        
        naming_label = QLabel("命名パターン:")
        self.naming_combo = QComboBox()
        
        naming_options = self.settings.get_naming_pattern_options()
        for pattern, description in naming_options.items():
            self.naming_combo.addItem(description, pattern)
        
        naming_layout.addWidget(naming_label)
        naming_layout.addWidget(self.naming_combo)
        
        layout.addWidget(naming_group)
        
        # Output Settings
        output_group = QGroupBox("出力設定")
        output_layout = QVBoxLayout(output_group)
        
        # Output directory
        output_dir_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        output_dir_btn = QPushButton("選択...")
        output_dir_btn.clicked.connect(self.select_output_directory)
        
        output_dir_layout.addWidget(QLabel("出力フォルダ:"))
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(output_dir_btn)
        
        output_layout.addLayout(output_dir_layout)
        
        # Auto-open folder
        self.auto_open_checkbox = QCheckBox("変換完了後に出力フォルダを開く")
        output_layout.addWidget(self.auto_open_checkbox)
        
        # Delete original files
        self.delete_original_checkbox = QCheckBox("変換後に元ファイルを削除")
        output_layout.addWidget(self.delete_original_checkbox)
        
        layout.addWidget(output_group)
        
        # Conversion Settings
        conversion_group = QGroupBox("変換設定")
        conversion_layout = QVBoxLayout(conversion_group)
        
        # Concurrent conversions
        concurrent_layout = QHBoxLayout()
        concurrent_label = QLabel("同時変換数:")
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 8)
        self.concurrent_spin.setSuffix(" 個")
        
        concurrent_layout.addWidget(concurrent_label)
        concurrent_layout.addWidget(self.concurrent_spin)
        concurrent_layout.addStretch()
        
        conversion_layout.addLayout(concurrent_layout)
        
        # Preserve metadata
        self.preserve_metadata_checkbox = QCheckBox("メタデータを保持")
        conversion_layout.addWidget(self.preserve_metadata_checkbox)
        
        # Volume normalization
        self.volume_normalization_checkbox = QCheckBox("音量を正規化")
        conversion_layout.addWidget(self.volume_normalization_checkbox)
        
        layout.addWidget(conversion_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("初期値に戻す")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        self.reset_btn.setStyleSheet(self.get_secondary_button_style())
        
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet(self.get_button_style())
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.save_settings)
        self.ok_btn.setStyleSheet(self.get_primary_button_style())
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
    
    def load_settings(self):
        """Load current settings into the UI."""
        # Audio quality
        current_quality = self.settings.get('audio_quality')
        index = self.quality_combo.findData(current_quality)
        if index >= 0:
            self.quality_combo.setCurrentIndex(index)
        
        # File naming
        current_pattern = self.settings.get('file_naming_pattern')
        index = self.naming_combo.findData(current_pattern)
        if index >= 0:
            self.naming_combo.setCurrentIndex(index)
        
        # Output directory
        output_dir = self.settings.get('output_directory')
        self.output_dir_edit.setText(output_dir)
        
        # Checkboxes
        self.auto_open_checkbox.setChecked(self.settings.get('auto_open_folder'))
        self.delete_original_checkbox.setChecked(self.settings.get('delete_original'))
        self.preserve_metadata_checkbox.setChecked(self.settings.get('preserve_metadata'))
        self.volume_normalization_checkbox.setChecked(self.settings.get('volume_normalization'))
        
        # Concurrent conversions
        self.concurrent_spin.setValue(self.settings.get('max_concurrent_conversions'))
    
    def save_settings(self):
        """Save settings from the UI."""
        # Audio quality
        quality_index = self.quality_combo.currentIndex()
        quality_value = self.quality_combo.itemData(quality_index)
        self.settings.set('audio_quality', quality_value)
        
        # File naming
        naming_index = self.naming_combo.currentIndex()
        naming_value = self.naming_combo.itemData(naming_index)
        self.settings.set('file_naming_pattern', naming_value)
        
        # Output directory
        output_dir = self.output_dir_edit.text()
        if output_dir:
            self.settings.set('output_directory', output_dir)
        
        # Checkboxes
        self.settings.set('auto_open_folder', self.auto_open_checkbox.isChecked())
        self.settings.set('delete_original', self.delete_original_checkbox.isChecked())
        self.settings.set('preserve_metadata', self.preserve_metadata_checkbox.isChecked())
        self.settings.set('volume_normalization', self.volume_normalization_checkbox.isChecked())
        
        # Concurrent conversions
        self.settings.set('max_concurrent_conversions', self.concurrent_spin.value())
        
        self.accept()
    
    def select_output_directory(self):
        """Select output directory."""
        from PyQt6.QtWidgets import QFileDialog
        
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setWindowTitle("出力フォルダを選択")
        
        if dialog.exec():
            selected_dirs = dialog.selectedFiles()
            if selected_dirs:
                self.output_dir_edit.setText(selected_dirs[0])
    
    def reset_to_defaults(self):
        """Reset all settings to default values."""
        reply = QMessageBox.question(
            self,
            "設定を初期化",
            "すべての設定を初期値に戻しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.reset_to_defaults()
            self.load_settings()
    
    def get_button_style(self) -> str:
        """Get standard button style."""
        return """
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0056CC;
            }
            QPushButton:pressed {
                background-color: #004499;
            }
        """
    
    def get_primary_button_style(self) -> str:
        """Get primary button style."""
        return """
            QPushButton {
                background-color: #34C759;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #28A745;
            }
            QPushButton:pressed {
                background-color: #218838;
            }
        """
    
    def get_secondary_button_style(self) -> str:
        """Get secondary button style."""
        return """
            QPushButton {
                background-color: #8E8E93;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #636366;
            }
            QPushButton:pressed {
                background-color: #48484A;
            }
        """