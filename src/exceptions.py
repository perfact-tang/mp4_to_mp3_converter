"""
Custom exceptions for MP4 to MP3 Converter application.
"""


class ConversionError(Exception):
    """Base exception for conversion-related errors."""
    def __init__(self, message, error_code=None):
        super().__init__(message)
        self.error_code = error_code
        self.user_message = "変換中にエラーが発生しました"


class FileValidationError(ConversionError):
    """Exception raised when input file validation fails."""
    def __init__(self, message, file_path=None):
        super().__init__(message, "FILE_VALIDATION_ERROR")
        self.file_path = file_path
        self.user_message = "MP4形式のファイルを選択してください"


class FFmpegNotFoundError(ConversionError):
    """Exception raised when FFmpeg binary is not found."""
    def __init__(self, message):
        super().__init__(message, "FFMPEG_NOT_FOUND")
        self.user_message = "FFmpegがインストールされていません"


class DiskSpaceError(ConversionError):
    """Exception raised when there's insufficient disk space."""
    def __init__(self, message, required_space=None, available_space=None):
        super().__init__(message, "DISK_SPACE_ERROR")
        self.required_space = required_space
        self.available_space = available_space
        self.user_message = "保存先に十分な空き容量がありません"


class ConversionCancelledError(ConversionError):
    """Exception raised when conversion is cancelled by user."""
    def __init__(self, message):
        super().__init__(message, "CONVERSION_CANCELLED")
        self.user_message = "変換がキャンセルされました"


class OutputDirectoryError(ConversionError):
    """Exception raised when output directory is invalid or inaccessible."""
    def __init__(self, message, directory_path=None):
        super().__init__(message, "OUTPUT_DIRECTORY_ERROR")
        self.directory_path = directory_path
        self.user_message = "出力ディレクトリにアクセスできません"


class SettingsError(ConversionError):
    """Exception raised when settings are invalid or corrupted."""
    def __init__(self, message, setting_key=None):
        super().__init__(message, "SETTINGS_ERROR")
        self.setting_key = setting_key
        self.user_message = "設定の読み込みに失敗しました"