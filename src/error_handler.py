import logging
import sys
import traceback
from pathlib import Path
from typing import Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout


class ErrorHandler(QObject):
    """
    Centralized error handling and logging system for MetroMuse.
    Provides user-friendly error messages and detailed logging.
    """
    
    errorOccurred = pyqtSignal(str, str)  # Error type, error message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_logging()
        self.error_callback = None
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path(__file__).resolve().parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / "metromuse.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('MetroMuse')
        
    def set_error_callback(self, callback: Callable):
        """Set a callback function to be called when errors occur"""
        self.error_callback = callback
        
    def handle_exception(self, exc_type, exc_value, exc_traceback, user_message=None):
        """
        Handle exceptions with logging and user notification.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
            user_message: Optional user-friendly message
        """
        # Log the full exception
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self.logger.error(f"Unhandled exception: {error_msg}")
        
        # Create user-friendly message
        if user_message is None:
            user_message = self._create_user_friendly_message(exc_type, exc_value)
        
        # Show error dialog
        self.show_error_dialog("Application Error", user_message, error_msg)
        
        # Emit signal
        self.errorOccurred.emit(exc_type.__name__, str(exc_value))
        
        # Call error callback if set
        if self.error_callback:
            self.error_callback(exc_type, exc_value, exc_traceback)
    
    def _create_user_friendly_message(self, exc_type, exc_value):
        """Create user-friendly error messages based on exception type"""
        error_messages = {
            FileNotFoundError: "A required file could not be found. Please check that all audio files and resources are in the correct location.",
            PermissionError: "Permission denied. Please check that you have the necessary permissions to access the file or folder.",
            MemoryError: "The system is running low on memory. Try closing other applications or working with smaller audio files.",
            ImportError: "A required component could not be loaded. Please check that all dependencies are properly installed.",
            ValueError: "Invalid data encountered. Please check your input and try again.",
            RuntimeError: "A runtime error occurred. This may be due to audio processing or system resource issues."
        }
        
        for exc_class, message in error_messages.items():
            if isinstance(exc_value, exc_class):
                return f"{message}\n\nTechnical details: {str(exc_value)}"
        
        return f"An unexpected error occurred: {str(exc_value)}"
    
    def show_error_dialog(self, title, message, details=None):
        """Show error dialog with optional details"""
        dialog = ErrorDialog(title, message, details)
        dialog.exec_()
    
    def log_info(self, message):
        """Log informational message"""
        self.logger.info(message)
    
    def log_warning(self, message):
        """Log warning message"""
        self.logger.warning(message)
    
    def log_error(self, message):
        """Log error message"""
        self.logger.error(message)
    
    def handle_audio_error(self, operation, error):
        """Handle audio-specific errors"""
        error_msg = f"Audio {operation} failed: {str(error)}"
        self.log_error(error_msg)
        
        user_messages = {
            "load": "Failed to load audio file. Please check that the file is a valid audio format and not corrupted.",
            "save": "Failed to save audio file. Please check disk space and file permissions.",
            "play": "Failed to play audio. Please check your audio device settings.",
            "record": "Failed to record audio. Please check your microphone settings.",
            "process": "Failed to process audio. The operation may be too complex for the current system resources."
        }
        
        user_msg = user_messages.get(operation, f"Audio {operation} failed.")
        user_msg += f"\n\nError details: {str(error)}"
        
        QMessageBox.critical(None, f"Audio {operation.title()} Error", user_msg)
        self.errorOccurred.emit("AudioError", error_msg)
    
    def handle_file_error(self, operation, filepath, error):
        """Handle file operation errors"""
        error_msg = f"File {operation} failed for '{filepath}': {str(error)}"
        self.log_error(error_msg)
        
        user_messages = {
            "open": f"Could not open file '{filepath}'. Please check that the file exists and you have permission to access it.",
            "save": f"Could not save file '{filepath}'. Please check disk space and write permissions.",
            "delete": f"Could not delete file '{filepath}'. Please check file permissions.",
            "move": f"Could not move file '{filepath}'. Please check source and destination permissions."
        }
        
        user_msg = user_messages.get(operation, f"File {operation} failed for '{filepath}'.")
        user_msg += f"\n\nError details: {str(error)}"
        
        QMessageBox.critical(None, f"File {operation.title()} Error", user_msg)
        self.errorOccurred.emit("FileError", error_msg)


class ErrorDialog(QDialog):
    """Custom error dialog with expandable details"""
    
    def __init__(self, title, message, details=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Main message
        from PyQt5.QtWidgets import QLabel
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Details section (initially hidden)
        if details:
            self.details_widget = QTextEdit()
            self.details_widget.setPlainText(details)
            self.details_widget.setReadOnly(True)
            self.details_widget.setMaximumHeight(200)
            self.details_widget.hide()
            layout.addWidget(self.details_widget)
            
            # Show/Hide details button
            self.details_button = QPushButton("Show Details")
            self.details_button.clicked.connect(self.toggle_details)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        if details:
            button_layout.addWidget(self.details_button)
        
        button_layout.addStretch()
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
    
    def toggle_details(self):
        """Toggle visibility of error details"""
        if self.details_widget.isVisible():
            self.details_widget.hide()
            self.details_button.setText("Show Details")
            self.resize(self.width(), self.minimumHeight())
        else:
            self.details_widget.show()
            self.details_button.setText("Hide Details")
            self.resize(self.width(), self.height() + 200)


# Global error handler instance
_error_handler = None

def get_error_handler():
    """Get the global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler

def setup_exception_handler():
    """Setup global exception handler"""
    error_handler = get_error_handler()
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        error_handler.handle_exception(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = handle_exception

