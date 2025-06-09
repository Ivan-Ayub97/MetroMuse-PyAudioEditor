from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect, Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QSlider,
    QProgressBar, QSplitter, QScrollArea, QToolBar, QAction, QMenu, QSystemTrayIcon,
    QMessageBox, QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem, QGroupBox,
    QGridLayout, QComboBox, QSpinBox, QCheckBox, QTabWidget, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem, QTextEdit
)
from PyQt5.QtGui import (
    QFont, QFontMetrics, QPixmap, QIcon, QColor, QPalette, QLinearGradient,
    QPainter, QBrush, QPen, QMovie, QFontDatabase
)
from error_handler import get_error_handler
import os
from pathlib import Path


class ModernUIManager(QObject):
    """
    Manages modern UI elements, themes, and user experience improvements
    """
    
    themeChanged = pyqtSignal(str)  # Theme name
    animationFinished = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.error_handler = get_error_handler()
        self.current_theme = "dark"
        self.animations = []
        self.ui_scale = 1.0
        
        # Load custom fonts
        self.load_custom_fonts()
        
        # Theme configurations
        self.themes = {
            "dark": self._get_dark_theme(),
            "light": self._get_light_theme(),
            "midnight": self._get_midnight_theme(),
            "ocean": self._get_ocean_theme()
        }
    
    def load_custom_fonts(self):
        """Load custom fonts for better typography"""
        try:
            # Load Inter font family for modern UI
            font_families = ["Segoe UI", "SF Pro Display", "Roboto", "Inter", "Arial"]
            self.primary_font = None
            
            for font_family in font_families:
                font = QFont(font_family)
                if QFontDatabase().hasFamily(font_family):
                    self.primary_font = font_family
                    break
            
            if not self.primary_font:
                self.primary_font = "Arial"  # Fallback
                
            self.error_handler.log_info(f"Using font family: {self.primary_font}")
            
        except Exception as e:
            self.error_handler.log_error(f"Error loading fonts: {str(e)}")
            self.primary_font = "Arial"
    
    def _get_dark_theme(self):
        """Enhanced dark theme configuration"""
        return {
            "name": "Dark",
            "colors": {
                "primary_bg": "#1e1e1e",
                "secondary_bg": "#2d2d2d",
                "tertiary_bg": "#3d3d3d",
                "accent": "#0078d4",
                "accent_hover": "#106ebe",
                "accent_pressed": "#005a9e",
                "text_primary": "#ffffff",
                "text_secondary": "#cccccc",
                "text_disabled": "#888888",
                "border": "#3d3d3d",
                "border_focus": "#0078d4",
                "success": "#00d862",
                "warning": "#ffb900",
                "error": "#e74856",
                "selection": "#0078d4",
                "hover": "#4d4d4d"
            },
            "fonts": {
                "primary": self.primary_font,
                "size_small": 9,
                "size_normal": 11,
                "size_large": 13,
                "size_title": 16,
                "size_header": 20
            },
            "borders": {
                "radius_small": 4,
                "radius_normal": 6,
                "radius_large": 8,
                "width_thin": 1,
                "width_normal": 2
            },
            "spacing": {
                "tiny": 4,
                "small": 8,
                "normal": 12,
                "large": 16,
                "xlarge": 24
            },
            "shadows": {
                "small": "rgba(0, 0, 0, 0.2)",
                "normal": "rgba(0, 0, 0, 0.3)",
                "large": "rgba(0, 0, 0, 0.4)"
            }
        }
    
    def _get_light_theme(self):
        """Modern light theme configuration"""
        return {
            "name": "Light",
            "colors": {
                "primary_bg": "#ffffff",
                "secondary_bg": "#f5f5f5",
                "tertiary_bg": "#e8e8e8",
                "accent": "#0078d4",
                "accent_hover": "#106ebe",
                "accent_pressed": "#005a9e",
                "text_primary": "#000000",
                "text_secondary": "#424242",
                "text_disabled": "#888888",
                "border": "#d0d0d0",
                "border_focus": "#0078d4",
                "success": "#00d862",
                "warning": "#ffb900",
                "error": "#e74856",
                "selection": "#0078d4",
                "hover": "#f0f0f0"
            },
            "fonts": {
                "primary": self.primary_font,
                "size_small": 9,
                "size_normal": 11,
                "size_large": 13,
                "size_title": 16,
                "size_header": 20
            },
            "borders": {
                "radius_small": 4,
                "radius_normal": 6,
                "radius_large": 8,
                "width_thin": 1,
                "width_normal": 2
            },
            "spacing": {
                "tiny": 4,
                "small": 8,
                "normal": 12,
                "large": 16,
                "xlarge": 24
            },
            "shadows": {
                "small": "rgba(0, 0, 0, 0.1)",
                "normal": "rgba(0, 0, 0, 0.15)",
                "large": "rgba(0, 0, 0, 0.2)"
            }
        }
    
    def _get_midnight_theme(self):
        """Ultra-dark midnight theme"""
        return {
            "name": "Midnight",
            "colors": {
                "primary_bg": "#0d1117",
                "secondary_bg": "#161b22",
                "tertiary_bg": "#21262d",
                "accent": "#58a6ff",
                "accent_hover": "#388bfd",
                "accent_pressed": "#1f6feb",
                "text_primary": "#f0f6fc",
                "text_secondary": "#7d8590",
                "text_disabled": "#484f58",
                "border": "#30363d",
                "border_focus": "#58a6ff",
                "success": "#3fb950",
                "warning": "#d29922",
                "error": "#f85149",
                "selection": "#58a6ff",
                "hover": "#262c36"
            },
            "fonts": {
                "primary": self.primary_font,
                "size_small": 9,
                "size_normal": 11,
                "size_large": 13,
                "size_title": 16,
                "size_header": 20
            },
            "borders": {
                "radius_small": 4,
                "radius_normal": 6,
                "radius_large": 8,
                "width_thin": 1,
                "width_normal": 2
            },
            "spacing": {
                "tiny": 4,
                "small": 8,
                "normal": 12,
                "large": 16,
                "xlarge": 24
            },
            "shadows": {
                "small": "rgba(0, 0, 0, 0.3)",
                "normal": "rgba(0, 0, 0, 0.4)",
                "large": "rgba(0, 0, 0, 0.5)"
            }
        }
    
    def _get_ocean_theme(self):
        """Ocean-inspired blue theme"""
        return {
            "name": "Ocean",
            "colors": {
                "primary_bg": "#0f1419",
                "secondary_bg": "#1a2332",
                "tertiary_bg": "#253340",
                "accent": "#39bae6",
                "accent_hover": "#59c7ea",
                "accent_pressed": "#2aa3d1",
                "text_primary": "#e6f1ff",
                "text_secondary": "#95a7c7",
                "text_disabled": "#5c7199",
                "border": "#34495e",
                "border_focus": "#39bae6",
                "success": "#2ecc71",
                "warning": "#f39c12",
                "error": "#e74c3c",
                "selection": "#39bae6",
                "hover": "#2c3e50"
            },
            "fonts": {
                "primary": self.primary_font,
                "size_small": 9,
                "size_normal": 11,
                "size_large": 13,
                "size_title": 16,
                "size_header": 20
            },
            "borders": {
                "radius_small": 4,
                "radius_normal": 6,
                "radius_large": 8,
                "width_thin": 1,
                "width_normal": 2
            },
            "spacing": {
                "tiny": 4,
                "small": 8,
                "normal": 12,
                "large": 16,
                "xlarge": 24
            },
            "shadows": {
                "small": "rgba(0, 0, 0, 0.2)",
                "normal": "rgba(0, 0, 0, 0.3)",
                "large": "rgba(0, 0, 0, 0.4)"
            }
        }
    
    def apply_theme(self, theme_name, widget):
        """Apply theme to a widget"""
        if theme_name not in self.themes:
            theme_name = "dark"
        
        theme = self.themes[theme_name]
        self.current_theme = theme_name
        
        # Generate comprehensive stylesheet
        stylesheet = self._generate_stylesheet(theme)
        widget.setStyleSheet(stylesheet)
        
        # Apply font
        font = QFont(theme["fonts"]["primary"], theme["fonts"]["size_normal"])
        widget.setFont(font)
        
        self.themeChanged.emit(theme_name)
        self.error_handler.log_info(f"Applied theme: {theme_name}")
    
    def _generate_stylesheet(self, theme):
        """Generate comprehensive QSS stylesheet from theme"""
        colors = theme["colors"]
        fonts = theme["fonts"]
        borders = theme["borders"]
        spacing = theme["spacing"]
        
        return f"""
        /* Global Styles */
        QWidget {{
            background-color: {colors['primary_bg']};
            color: {colors['text_primary']};
            font-family: '{fonts['primary']}';
            font-size: {fonts['size_normal']}px;
            selection-background-color: {colors['selection']};
        }}
        
        /* Main Window */
        QMainWindow {{
            background-color: {colors['primary_bg']};
            border: none;
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {colors['accent']};
            color: {colors['text_primary']};
            border: none;
            border-radius: {borders['radius_normal']}px;
            padding: {spacing['normal']}px {spacing['large']}px;
            font-weight: 600;
            min-height: 24px;
            min-width: 80px;
        }}
        
        QPushButton:hover {{
            background-color: {colors['accent_hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {colors['accent_pressed']};
        }}
        
        QPushButton:disabled {{
            background-color: {colors['tertiary_bg']};
            color: {colors['text_disabled']};
        }}
        
        QPushButton:checked {{
            background-color: {colors['accent_pressed']};
            border: 2px solid {colors['border_focus']};
        }}
        
        /* Tool Buttons */
        QToolButton {{
            background-color: {colors['secondary_bg']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: {borders['radius_normal']}px;
            padding: {spacing['small']}px;
            min-width: 48px;
            min-height: 48px;
            font-weight: 500;
        }}
        
        QToolButton:hover {{
            background-color: {colors['hover']};
            border-color: {colors['border_focus']};
        }}
        
        QToolButton:pressed {{
            background-color: {colors['accent']};
            color: {colors['text_primary']};
        }}
        
        QToolButton:checked {{
            background-color: {colors['accent']};
            color: {colors['text_primary']};
            border-color: {colors['border_focus']};
        }}
        
        /* Labels */
        QLabel {{
            color: {colors['text_primary']};
            background: transparent;
        }}
        
        QLabel[class="title"] {{
            font-size: {fonts['size_title']}px;
            font-weight: 700;
            color: {colors['accent']};
        }}
        
        QLabel[class="header"] {{
            font-size: {fonts['size_header']}px;
            font-weight: 600;
            color: {colors['text_primary']};
        }}
        
        QLabel[class="subtitle"] {{
            font-size: {fonts['size_large']}px;
            color: {colors['text_secondary']};
        }}
        
        /* Frames and Containers */
        QFrame {{
            background-color: {colors['secondary_bg']};
            border: 1px solid {colors['border']};
            border-radius: {borders['radius_normal']}px;
        }}
        
        QFrame[class="panel"] {{
            background-color: {colors['secondary_bg']};
            border: 1px solid {colors['border']};
            border-radius: {borders['radius_large']}px;
            padding: {spacing['normal']}px;
        }}
        
        QFrame[class="card"] {{
            background-color: {colors['secondary_bg']};
            border: 1px solid {colors['border']};
            border-radius: {borders['radius_large']}px;
            padding: {spacing['large']}px;
        }}
        
        /* Group Boxes */
        QGroupBox {{
            font-weight: 600;
            border: 2px solid {colors['border']};
            border-radius: {borders['radius_large']}px;
            margin-top: {spacing['normal']}px;
            padding-top: {spacing['large']}px;
            background-color: {colors['secondary_bg']};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: {spacing['normal']}px;
            padding: 0 {spacing['small']}px;
            color: {colors['accent']};
            font-weight: 600;
            background-color: {colors['secondary_bg']};
        }}
        
        /* Sliders */
        QSlider::groove:horizontal {{
            border: 1px solid {colors['border']};
            height: 8px;
            background: {colors['tertiary_bg']};
            border-radius: 4px;
        }}
        
        QSlider::handle:horizontal {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                stop:0 {colors['accent']}, stop:1 {colors['accent_hover']});
            border: 1px solid {colors['border_focus']};
            width: 20px;
            height: 20px;
            margin: -6px 0;
            border-radius: 10px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                stop:0 {colors['accent_hover']}, stop:1 {colors['accent']});
        }}
        
        QSlider::sub-page:horizontal {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                stop:0 {colors['accent']}, stop:1 {colors['accent_hover']});
            border-radius: 4px;
        }}
        
        /* Progress Bars */
        QProgressBar {{
            border: 2px solid {colors['border']};
            border-radius: {borders['radius_normal']}px;
            text-align: center;
            background-color: {colors['tertiary_bg']};
            color: {colors['text_primary']};
            font-weight: 600;
        }}
        
        QProgressBar::chunk {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                stop:0 {colors['accent']}, stop:1 {colors['accent_hover']});
            border-radius: {borders['radius_small']}px;
        }}
        
        /* Text Inputs */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors['primary_bg']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border']};
            border-radius: {borders['radius_normal']}px;
            padding: {spacing['small']}px;
            font-size: {fonts['size_normal']}px;
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {colors['border_focus']};
        }}
        
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
            background-color: {colors['tertiary_bg']};
            color: {colors['text_disabled']};
        }}
        
        /* Lists and Trees */
        QListWidget, QTreeWidget {{
            background-color: {colors['primary_bg']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: {borders['radius_normal']}px;
            alternate-background-color: {colors['secondary_bg']};
            outline: none;
        }}
        
        QListWidget::item, QTreeWidget::item {{
            padding: {spacing['small']}px;
            border-radius: {borders['radius_small']}px;
            margin: 1px;
        }}
        
        QListWidget::item:selected, QTreeWidget::item:selected {{
            background-color: {colors['selection']};
            color: {colors['text_primary']};
        }}
        
        QListWidget::item:hover, QTreeWidget::item:hover {{
            background-color: {colors['hover']};
        }}
        
        /* Tabs */
        QTabWidget::pane {{
            border: 1px solid {colors['border']};
            border-radius: {borders['radius_large']}px;
            background-color: {colors['secondary_bg']};
            top: -1px;
        }}
        
        QTabBar::tab {{
            background-color: {colors['tertiary_bg']};
            color: {colors['text_secondary']};
            padding: {spacing['normal']}px {spacing['large']}px;
            margin-right: 2px;
            border-top-left-radius: {borders['radius_normal']}px;
            border-top-right-radius: {borders['radius_normal']}px;
            min-width: 100px;
            font-weight: 500;
        }}
        
        QTabBar::tab:selected {{
            background-color: {colors['secondary_bg']};
            color: {colors['text_primary']};
            border-bottom: 3px solid {colors['accent']};
            font-weight: 600;
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: {colors['hover']};
            color: {colors['text_primary']};
        }}
        
        /* Checkboxes */
        QCheckBox {{
            color: {colors['text_primary']};
            spacing: {spacing['small']}px;
            font-weight: 500;
        }}
        
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: {borders['radius_small']}px;
            border: 2px solid {colors['border']};
            background-color: {colors['primary_bg']};
        }}
        
        QCheckBox::indicator:hover {{
            border-color: {colors['border_focus']};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {colors['accent']};
            border-color: {colors['accent']};
        }}
        
        /* Combo Boxes */
        QComboBox {{
            background-color: {colors['secondary_bg']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: {borders['radius_normal']}px;
            padding: {spacing['small']}px {spacing['normal']}px;
            min-width: 100px;
        }}
        
        QComboBox:hover {{
            border-color: {colors['border_focus']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {colors['secondary_bg']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: {borders['radius_normal']}px;
            selection-background-color: {colors['selection']};
        }}
        
        /* Scroll Bars */
        QScrollBar {{
            background-color: {colors['secondary_bg']};
            width: 16px;
            height: 16px;
            border-radius: 8px;
        }}
        
        QScrollBar::handle {{
            background-color: {colors['tertiary_bg']};
            border-radius: 6px;
            min-height: 30px;
            min-width: 30px;
        }}
        
        QScrollBar::handle:hover {{
            background-color: {colors['hover']};
        }}
        
        QScrollBar::add-line, QScrollBar::sub-line {{
            height: 0px;
            width: 0px;
        }}
        
        QScrollBar::add-page, QScrollBar::sub-page {{
            background: none;
        }}
        
        /* Menu Bar */
        QMenuBar {{
            background-color: {colors['primary_bg']};
            color: {colors['text_primary']};
            border-bottom: 1px solid {colors['border']};
            padding: {spacing['small']}px;
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: {spacing['small']}px {spacing['normal']}px;
            border-radius: {borders['radius_small']}px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {colors['hover']};
        }}
        
        /* Menus */
        QMenu {{
            background-color: {colors['secondary_bg']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: {borders['radius_normal']}px;
            padding: {spacing['small']}px;
        }}
        
        QMenu::item {{
            padding: {spacing['small']}px {spacing['large']}px;
            border-radius: {borders['radius_small']}px;
        }}
        
        QMenu::item:selected {{
            background-color: {colors['selection']};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {colors['border']};
            margin: {spacing['small']}px;
        }}
        
        /* Status Bar */
        QStatusBar {{
            background-color: {colors['primary_bg']};
            color: {colors['text_primary']};
            border-top: 1px solid {colors['border']};
            padding: {spacing['small']}px;
        }}
        
        /* Tool Tips */
        QToolTip {{
            background-color: {colors['secondary_bg']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_focus']};
            border-radius: {borders['radius_normal']}px;
            padding: {spacing['small']}px;
            font-size: {fonts['size_small']}px;
        }}
        
        /* Splitters */
        QSplitter::handle {{
            background-color: {colors['border']};
        }}
        
        QSplitter::handle:hover {{
            background-color: {colors['accent']};
        }}
        """
    
    def create_modern_button(self, text, icon=None, button_type="primary", size="normal"):
        """Create a modern styled button"""
        button = QPushButton(text)
        
        if icon:
            button.setIcon(icon)
            button.setIconSize(self._get_icon_size(size))
        
        # Set object name for specific styling
        button.setObjectName(f"button_{button_type}_{size}")
        
        # Apply size-specific properties
        if size == "small":
            button.setMinimumSize(60, 28)
        elif size == "large":
            button.setMinimumSize(120, 48)
        else:  # normal
            button.setMinimumSize(80, 36)
        
        return button
    
    def create_modern_card(self, title=None, content_widget=None):
        """Create a modern card container"""
        card = QFrame()
        card.setObjectName("card")
        
        layout = QVBoxLayout(card)
        
        if title:
            title_label = QLabel(title)
            title_label.setObjectName("title")
            layout.addWidget(title_label)
        
        if content_widget:
            layout.addWidget(content_widget)
        
        return card
    
    def create_modern_panel(self, title=None):
        """Create a modern panel container"""
        panel = QFrame()
        panel.setObjectName("panel")
        
        layout = QVBoxLayout(panel)
        
        if title:
            title_label = QLabel(title)
            title_label.setObjectName("subtitle")
            layout.addWidget(title_label)
        
        return panel, layout
    
    def add_drop_shadow(self, widget, blur_radius=15, offset=(0, 2)):
        """Add drop shadow effect to widget"""
        try:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(blur_radius)
            shadow.setOffset(offset[0], offset[1])
            shadow.setColor(QColor(0, 0, 0, 50))
            widget.setGraphicsEffect(shadow)
        except Exception as e:
            self.error_handler.log_error(f"Error adding shadow: {str(e)}")
    
    def animate_widget(self, widget, property_name, start_value, end_value, duration=300):
        """Animate widget property"""
        try:
            animation = QPropertyAnimation(widget, property_name.encode())
            animation.setDuration(duration)
            animation.setStartValue(start_value)
            animation.setEndValue(end_value)
            animation.setEasingCurve(QEasingCurve.OutCubic)
            
            # Clean up animation when finished
            animation.finished.connect(lambda: self.animations.remove(animation))
            animation.finished.connect(self.animationFinished.emit)
            
            self.animations.append(animation)
            animation.start()
            
            return animation
            
        except Exception as e:
            self.error_handler.log_error(f"Error creating animation: {str(e)}")
            return None
    
    def fade_in_widget(self, widget, duration=300):
        """Fade in widget with animation"""
        widget.setWindowOpacity(0)
        widget.show()
        return self.animate_widget(widget, "windowOpacity", 0.0, 1.0, duration)
    
    def fade_out_widget(self, widget, duration=300):
        """Fade out widget with animation"""
        animation = self.animate_widget(widget, "windowOpacity", 1.0, 0.0, duration)
        if animation:
            animation.finished.connect(widget.hide)
        return animation
    
    def slide_widget(self, widget, direction="down", duration=300):
        """Slide widget in from direction"""
        geometry = widget.geometry()
        
        if direction == "down":
            start_pos = QRect(geometry.x(), geometry.y() - geometry.height(), 
                            geometry.width(), geometry.height())
        elif direction == "up":
            start_pos = QRect(geometry.x(), geometry.y() + geometry.height(), 
                            geometry.width(), geometry.height())
        elif direction == "left":
            start_pos = QRect(geometry.x() + geometry.width(), geometry.y(), 
                            geometry.width(), geometry.height())
        else:  # right
            start_pos = QRect(geometry.x() - geometry.width(), geometry.y(), 
                            geometry.width(), geometry.height())
        
        widget.setGeometry(start_pos)
        widget.show()
        
        return self.animate_widget(widget, "geometry", start_pos, geometry, duration)
    
    def _get_icon_size(self, size):
        """Get icon size based on button size"""
        sizes = {
            "small": (16, 16),
            "normal": (20, 20),
            "large": (24, 24)
        }
        return sizes.get(size, (20, 20))
    
    def set_ui_scale(self, scale_factor):
        """Set UI scale factor for high DPI displays"""
        self.ui_scale = scale_factor
        # Update theme font sizes
        for theme in self.themes.values():
            fonts = theme["fonts"]
            fonts["size_small"] = int(9 * scale_factor)
            fonts["size_normal"] = int(11 * scale_factor)
            fonts["size_large"] = int(13 * scale_factor)
            fonts["size_title"] = int(16 * scale_factor)
            fonts["size_header"] = int(20 * scale_factor)
    
    def get_current_theme(self):
        """Get current theme configuration"""
        return self.themes.get(self.current_theme, self.themes["dark"])
    
    def get_available_themes(self):
        """Get list of available theme names"""
        return list(self.themes.keys())


# Global UI manager instance
_ui_manager = None

def get_ui_manager():
    """Get the global UI manager instance"""
    global _ui_manager
    if _ui_manager is None:
        _ui_manager = ModernUIManager()
    return _ui_manager

