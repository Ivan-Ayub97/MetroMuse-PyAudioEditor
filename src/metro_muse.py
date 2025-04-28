import json
import os
import platform
import sys
import threading
from pathlib import Path

import matplotlib
import numpy as np

# Required before other matplotlib imports
matplotlib.use('Qt5Agg')

import librosa
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigureCanvas
from pydub import AudioSegment
from PyQt5.QtCore import QSize, Qt, pyqtSlot
from PyQt5.QtGui import QColor, QIcon, QPixmap
from PyQt5.QtWidgets import (QAction, QApplication,  # Added QListWidget
                             QDialog, QFileDialog, QFrame, QHBoxLayout,
                             QInputDialog, QLabel, QListWidget,
                             QListWidgetItem, QMainWindow, QMenuBar,
                             QMessageBox, QPushButton, QScrollArea,
                             QSizePolicy, QSlider, QSplitter, QToolButton,
                             QVBoxLayout, QWidget)

from track_manager import AudioTrack, MultiTrackContainer
# Import our custom modules
from track_renderer import EnhancedWaveformCanvas

# Import QtSvg for SVG icon support if available
try:
    from PyQt5 import QtSvg
    HAS_SVG_SUPPORT = True
except ImportError:
    HAS_SVG_SUPPORT = False


# Detect and configure local ffmpeg/ffplay/ffprobe and resource assets
def get_resources_ffmpeg_paths():
    """
    Return dict of ffmpeg, ffprobe, ffplay paths if found in resources/.
    Searches for binaries with the appropriate extension for the platform.
    """
    base_dir = Path(__file__).resolve().parent.parent
    resources_dir = base_dir / "resources"
    platform_system = platform.system()
    exts = ['']  # default: no extension (mac or linux)
    if platform_system == "Windows":
        exts = ['.exe']
    # macOS/Linux: make sure the files have exec permissions (os.access)
    def find_exe(name):
        for ext in exts:
            candidate = resources_dir / f"{name}{ext}"
            if candidate.is_file():
                if platform_system == "Windows" or os.access(str(candidate), os.X_OK):
                    return str(candidate.resolve())
        return None
    return {
        'ffmpeg': find_exe('ffmpeg'),
        'ffprobe': find_exe('ffprobe'),
        'ffplay': find_exe('ffplay'),
    }

def get_resource_icon_path(name: str) -> str:
    """Return absolute path to icons in src/ regardless of cwd."""
    base_dir = Path(__file__).resolve().parent
    icon_path = base_dir / name
    if not icon_path.exists():
        return str(icon_path.resolve())
    return str(icon_path.resolve())

ffmpeg_bins = get_resources_ffmpeg_paths()
FFMPEG_ERR_MSG = None
ffmpeg_err_details = []
if not all(ffmpeg_bins.values()):
    for k, v in ffmpeg_bins.items():
        if not v:
            ffmpeg_err_details.append(f"Missing: {k} in resources/")
    FFMPEG_ERR_MSG = (
        "Required audio engine components not found.\n"
        "Make sure ffmpeg, ffplay, and ffprobe executables are present in the resources/ folder.\n" +
        "\n".join(ffmpeg_err_details)
    )
else:
    AudioSegment.converter = ffmpeg_bins['ffmpeg']
    AudioSegment.ffprobe = ffmpeg_bins['ffprobe']
    AudioSegment.ffplay = ffmpeg_bins['ffplay']


# For playback (pydub + simpleaudio backend)
try:
    from pydub.playback import _play_with_simpleaudio as play_with_audio
except ImportError:
    play_with_audio = None  # Will show error dialog if unavailable

# Add sounddevice for better multitrack audio handling if available
try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

SUPPORTED_FORMATS = ['wav', 'flac', 'mp3', 'aac']

# UI Color constants - now from styles.qss
DARK_BG = '#232629'
DARK_FG = '#eef1f4'
ACCENT_COLOR = '#47cbff'
# WaveformCanvas is now imported from track_renderer.py as EnhancedWaveformCanvas
class MetroMuse(QMainWindow):
    """Main application window for MetroMuse.
    Now supports multitrack editing, enhanced waveform scrubbing, and modern UI.
    """
    recent_files_path = str(Path(__file__).resolve().parent / "recent_files.json")

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MetroMuse")
        self.setWindowIcon(QIcon(get_resource_icon_path("icon.ico")))
        self.resize(1100, 700)

        # Load and apply stylesheet
        self.load_stylesheet()

        # Playback and editing state
        self.active_track = None
        self.play_thread = None
        self.is_playing = False
        self.is_paused = False
        self.playback_pos_sec = 0.0  # Seconds from start (updated on pause/stop)

        # Editing/undo state
        self.edit_clipboard = None
        self._edit_stack = []   # For undo
        self._redo_stack = []   # For redo

        # Check FFMPEG availability and show error if missing
        if FFMPEG_ERR_MSG is not None:
            QMessageBox.critical(self, "Missing Audio Engine", FFMPEG_ERR_MSG)
            self.audio_enabled = False
        else:
            self.audio_enabled = True

        self.setAcceptDrops(True)  # Enable drag-and-drop
        self._load_recent_files()

        # Initialize UI
        self.init_menu()
        self.init_ui()

    def load_stylesheet(self):
        """Load and apply the application stylesheet"""
        stylesheet_path = Path(__file__).resolve().parent / "styles.qss"

        if stylesheet_path.exists():
            try:
                with open(stylesheet_path, "r") as f:
                    self.setStyleSheet(f.read())
            except Exception as e:
                print(f"Error loading stylesheet: {e}")
                # Fallback to basic styling
                self.setStyleSheet(f"background-color: {DARK_BG}; color: {DARK_FG};")
        else:
            print(f"Stylesheet not found at: {stylesheet_path}")
            # Fallback to basic styling
            self.setStyleSheet(f"background-color: {DARK_BG}; color: {DARK_FG};")

    def init_ui(self):
        """Initialize the application UI with multitrack support"""
        # Master layout: horizontal (sidebar | main)
        master_layout = QHBoxLayout()
        self.central_widget = QWidget()
        self.central_widget.setObjectName("MainWidget")
        self.setCentralWidget(self.central_widget)
        self.central_widget.setLayout(master_layout)

        # Create splitter for flexible layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        ## ----- Left Sidebar: File/Project Browser -----
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setObjectName("ProjectBrowser")
        self.sidebar_widget.setMinimumWidth(200)
        self.sidebar_widget.setMaximumWidth(300)

        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(8, 8, 8, 8)
        sidebar_layout.setSpacing(10)

        # Sidebar header
        sidebar_header = QFrame()
        sidebar_header.setObjectName("SidebarHeader")
        sidebar_header_layout = QHBoxLayout(sidebar_header)
        sidebar_header_layout.setContentsMargins(4, 4, 4, 4)

        sidebar_label = QLabel("Project Browser")
        sidebar_label.setObjectName("SidebarTitle")
        sidebar_header_layout.addWidget(sidebar_label)

        # Add new project button
        new_project_btn = QPushButton("+")
        new_project_btn.setToolTip("New Project")
        new_project_btn.setFixedSize(QSize(32, 32))
        new_project_btn.clicked.connect(self.new_project)
        sidebar_header_layout.addWidget(new_project_btn)

        sidebar_layout.addWidget(sidebar_header)

        # Sidebar file list
        self.file_list_widget = QListWidget()
        self.file_list_widget.setObjectName("FileList")
        sidebar_layout.addWidget(self.file_list_widget, 1)

        # Initialize file list
        self.refresh_file_list()
        self.file_list_widget.itemClicked.connect(self.browse_file_clicked)

        # Add sidebar to splitter
        splitter.addWidget(self.sidebar_widget)

        ## ----- Main editor area with multitrack support -----
        main_area = QWidget()
        main_area.setObjectName("EditorArea")
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Info Bar above tracks ---
        self.info_bar = QFrame()
        self.info_bar.setObjectName("InfoBar")
        info_bar_layout = QHBoxLayout(self.info_bar)
        self.file_info_label = QLabel("No file loaded")
        info_bar_layout.addWidget(self.file_info_label)

        # Add zoom controls to info bar
        zoom_widget = QWidget()
        zoom_layout = QHBoxLayout(zoom_widget)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(8)

        # Get path to icons
        srcdir = str(Path(__file__).resolve().parent)

        self.zoom_in_btn = self._create_tool_button(
            icon=os.path.join(srcdir, 'zoom_in.png'),
            text="+",
            tooltip="Zoom In (Mouse Wheel Up)",
            slot=self.zoom_in
        )

        self.zoom_out_btn = self._create_tool_button(
            icon=os.path.join(srcdir, 'zoom_out.png'),
            text="-",
            tooltip="Zoom Out (Mouse Wheel Down)",
            slot=self.zoom_out
        )

        self.pan_left_btn = self._create_tool_button(
            icon=os.path.join(srcdir, 'pan_left.png'),
            text="◀",
            tooltip="Pan Left (Left Arrow)",
            slot=self.pan_left
        )

        self.pan_right_btn = self._create_tool_button(
            icon=os.path.join(srcdir, 'pan_right.png'),
            text="▶",
            tooltip="Pan Right (Right Arrow)",
            slot=self.pan_right
        )

        for btn in [self.zoom_in_btn, self.zoom_out_btn, self.pan_left_btn, self.pan_right_btn]:
            zoom_layout.addWidget(btn)

        info_bar_layout.addWidget(zoom_widget)
        main_layout.addWidget(self.info_bar)

        # --- MultiTrack Container for all tracks ---
        self.track_container = MultiTrackContainer()
        self.track_container.setObjectName("MultiTrackContainer")

        # Connect track container signals
        self.track_container.playbackStarted.connect(self.on_playback_started)
        self.track_container.playbackPaused.connect(self.on_playback_paused)
        self.track_container.playbackStopped.connect(self.on_playback_stopped)
        self.track_container.playbackPositionChanged.connect(self.on_playback_position_changed)
        self.track_container.trackAdded.connect(self.on_track_added)
        self.track_container.trackRemoved.connect(self.on_track_removed)
        self.track_container.selectionChanged.connect(self.on_selection_changed)

        main_layout.addWidget(self.track_container, 1)  # Give tracks most of the space

        # --- Status Bar ---
        self.status = QLabel("Ready")
        self.status.setObjectName("StatusLabel")
        self.statusBar().addWidget(self.status, 1)
        self.statusBar().setObjectName("StatusBar")

        # Add main area to splitter
        splitter.addWidget(main_area)

        # Add splitter to master layout
        master_layout.addWidget(splitter)

    def _create_tool_button(self, icon=None, text=None, tooltip=None, slot=None, checkable=False):
        """Create a styled tool button with icon or text"""
        btn = QToolButton()

        if icon and os.path.exists(icon):
            # Use SVG if available and supported
            if HAS_SVG_SUPPORT and icon.lower().endswith('.svg'):
                btn.setIcon(QIcon(icon))
            else:
                btn.setIcon(QIcon(icon))
        elif text:
            btn.setText(text)

        if tooltip:
            btn.setToolTip(tooltip)

        if slot:
            btn.clicked.connect(slot)

        btn.setCheckable(checkable)
        btn.setMinimumSize(48, 48)
        btn.setIconSize(QSize(32, 32))

        return btn
    # --- Navigation and zoom methods ---
    def zoom_in(self):
        """Zoom in on the active track"""
        if hasattr(self, 'track_container') and self.track_container and self.track_container.tracks:
            # Apply zoom to all tracks for consistency
            for track in self.track_container.tracks:
                if track.waveform_canvas and hasattr(track.waveform_canvas, 'zoom'):
                    track.waveform_canvas.zoom(0.5)  # 0.5 means zoom in (half width)
            self.status.setText("Zoomed in")

    def zoom_out(self):
        """Zoom out on the active track"""
        if hasattr(self, 'track_container') and self.track_container and self.track_container.tracks:
            # Apply zoom to all tracks for consistency
            for track in self.track_container.tracks:
                if track.waveform_canvas and hasattr(track.waveform_canvas, 'zoom'):
                    track.waveform_canvas.zoom(2.0)  # 2.0 means zoom out (double width)
            self.status.setText("Zoomed out")

    def pan_left(self):
        """Pan view left on all tracks"""
        if hasattr(self, 'track_container') and self.track_container and self.track_container.tracks:
            # Apply pan to all tracks for consistency
            for track in self.track_container.tracks:
                if track.waveform_canvas and hasattr(track.waveform_canvas, 'pan'):
                    track.waveform_canvas.pan(-1.0)  # Pan left by 1 second
            self.status.setText("Panned left")

    def pan_right(self):
        """Pan view right on all tracks"""
        if hasattr(self, 'track_container') and self.track_container and self.track_container.tracks:
            # Apply pan to all tracks for consistency
            for track in self.track_container.tracks:
                if track.waveform_canvas and hasattr(track.waveform_canvas, 'pan'):
                    track.waveform_canvas.pan(1.0)  # Pan right by 1 second
            self.status.setText("Panned right")
    def _load_recent_files(self):
        """Load recent files list from disk (JSON), or empty if unavailable."""
        try:
            with open(self.recent_files_path, "r", encoding="utf-8") as f:
                self._recent_files = [p for p in json.load(f) if os.path.exists(p)]
        except Exception:
            self._recent_files = []

    def _save_recent_files(self):
        """Save recent files list to disk."""
        try:
            with open(self.recent_files_path, "w", encoding="utf-8") as f:
                # Only store files that still exist
                valid = [p for p in self._recent_files if os.path.exists(p)]
                json.dump(valid, f, indent=2)
        except Exception:
            pass

    def dragEnterEvent(self, event):
        """Accept drag enter of supported audio file."""
        if event.mimeData().hasUrls():
            # Only accept if at least one URL is a supported file
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                ext = os.path.splitext(path)[1][1:].lower()
                if ext in SUPPORTED_FORMATS:
                    event.accept()
                    return
        event.ignore()

    def dropEvent(self, event):
        """Handle dropped file(s): open first supported audio file."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                ext = os.path.splitext(path)[1][1:].lower()
                if ext in SUPPORTED_FORMATS and os.path.isfile(path):
                    self.open_audio_from_path(path)
                    break

    def init_menu(self):
        menubar = self.menuBar()
        menubar.setStyleSheet(
            f"QMenuBar {{ background: {DARK_BG}; color: {DARK_FG}; }} "
            f"QMenuBar::item:selected {{ background: #383c45; }}"
        )

        # File menu
        fileMenu = menubar.addMenu("File")
        openAct = QAction("Open...", self)
        openAct.setShortcut("Ctrl+O")
        openAct.triggered.connect(self.open_file)

        saveAsAct = QAction("Save As...", self)
        saveAsAct.setShortcut("Ctrl+S")
        saveAsAct.triggered.connect(self.save_as_file)

        exitAct = QAction("Exit", self)
        exitAct.triggered.connect(self.close)

        fileMenu.addAction(openAct)
        fileMenu.addAction(saveAsAct)
        fileMenu.addSeparator()
        fileMenu.addAction(exitAct)

        # Edit menu
        editMenu = menubar.addMenu("Edit")
        for name, shortcut in [
            ('Cut', 'Ctrl+X'), ('Copy', 'Ctrl+C'), ('Paste', 'Ctrl+V'),
            ('Trim', ''), ('Undo', 'Ctrl+Z'), ('Redo', 'Ctrl+Y')
        ]:
            act = QAction(name, self)
            if shortcut:
                act.setShortcut(shortcut)
            # Connect real edit handlers
            if name == 'Cut':
                act.setToolTip("Remove and copy selection")
                act.triggered.connect(self.edit_cut)
            elif name == 'Copy':
                act.setToolTip("Copy selection")
                act.triggered.connect(self.edit_copy)
            elif name == 'Paste':
                act.setToolTip("Paste at cursor/selection")
                act.triggered.connect(self.edit_paste)
            elif name == 'Trim':
                act.setToolTip("Keep only selection")
                act.triggered.connect(self.edit_trim)
            elif name == 'Undo':
                act.setToolTip("Undo last edit")
                act.triggered.connect(self.edit_undo)
            elif name == 'Redo':
                act.setToolTip("Redo last undo")
                act.triggered.connect(self.edit_redo)
            else:
                act.triggered.connect(self.edit_stub)
            editMenu.addAction(act)
        # Effects menu
        effectsMenu = menubar.addMenu("Effects")
        gainAct = QAction("Adjust Gain...", self)
        gainAct.setToolTip("Change the volume (gain) of selected audio region")
        gainAct.triggered.connect(self.apply_gain_dialog)
        fadeInAct = QAction("Fade In...", self)
        fadeInAct.setToolTip("Apply fade-in effect to selection")
        fadeInAct.triggered.connect(self.apply_fade_in)
        fadeOutAct = QAction("Fade Out...", self)
        fadeOutAct.setToolTip("Apply fade-out effect to selection")
        fadeOutAct.triggered.connect(self.apply_fade_out)
        effectsMenu.addAction(gainAct)
        effectsMenu.addAction(fadeInAct)
        effectsMenu.addAction(fadeOutAct)

        # Help menu
        helpMenu = menubar.addMenu("Help")
        aboutAct = QAction("About", self)
        aboutAct.triggered.connect(self.show_about)
        helpMenu.addAction(aboutAct)
    def _button_style(self):
        return (
            "QPushButton { background: #232e39; color: #eef1f4; border-radius:5px; padding:6px 18px; }"
            "QPushButton::hover { background: #313e50; }"
        )

    def open_file(self, filepath=None):
        """Open an audio file. If filepath is None, show a file dialog."""
        if not getattr(self, "audio_enabled", True):
            QMessageBox.critical(self, "Cannot Load Audio", FFMPEG_ERR_MSG or "Audio I/O unavailable")
            self.status.setText("Audio engine unavailable.")
            return False

        # Show file dialog if no filepath provided
        if filepath is None:
            filepath, _ = QFileDialog.getOpenFileName(
                self, "Open Audio File", "",
                "Audio Files (*.wav *.flac *.mp3 *.aac);;All Files (*)"
            )
            if not filepath:
                self.status.setText("Load cancelled.")
                return False

        # Check filepath is a valid path type
        if not isinstance(filepath, (str, bytes, os.PathLike)):
            self.status.setText("Invalid file path.")
            return False

        # Check file exists
        if not os.path.isfile(filepath):
            self.status.setText(f"File does not exist: {filepath}")
            return False

        ext = os.path.splitext(filepath)[1][1:].lower()
        if ext not in SUPPORTED_FORMATS:
            QMessageBox.warning(self, "Unsupported Format", f"{ext.upper()} not supported. Supported: {', '.join(SUPPORTED_FORMATS).upper()}")
            self.status.setText("Unsupported format.")
            return False
        try:
            # Robust import using pydub and fallback to librosa
            if ext in ['mp3', 'flac', 'wav', 'aac']:
                try:
                    if ext == 'aac':
                        audio = AudioSegment.from_file(filepath, 'aac')
                    else:
                        audio = AudioSegment.from_file(filepath)
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to decode {ext.upper()} audio file; ensure ffmpeg is present.\nError: {str(e)}"
                    )
                self.audio_segment = audio
                samples = np.array(audio.get_array_of_samples()).astype(np.float32)
                if audio.channels > 1:
                    samples = samples[None, :]  # Make 2D array with shape (1, N)
                samples = samples / (2 ** (8 * audio.sample_width - 1))
                sr = audio.frame_rate
                self.samples = samples
                self.sr = sr
            else:
                # Fallback to librosa
                import librosa
                samples, sr = librosa.load(filepath, sr=None, mono=False)
                if samples.ndim == 1:
                    samples = np.expand_dims(samples, axis=0)
                self.samples = samples
                self.sr = sr
            self.filepath = filepath

            # Create a new track with the loaded audio
            self.load_audio_to_track(samples, sr, self.audio_segment, filepath)

            self.status.setText(f"Loaded: {os.path.basename(self.filepath)}")
            self.update_file_info_bar()

            # Add to recent files
            if filepath not in self._recent_files:
                self._recent_files.insert(0, filepath)
                if len(self._recent_files) > 10:  # Limit to 10 recent files
                    self._recent_files = self._recent_files[:10]
                self._save_recent_files()
                self._save_recent_files()

            return True
        except Exception as e:
            QMessageBox.critical(self, "Error Loading File", str(e))
            self.status.setText("Error loading file.")
            return False
    def open_audio_from_path(self, filepath):
        """Open audio file from path (used by drag-and-drop and recent files)"""
        if filepath and os.path.exists(filepath):
            try:
                return self.open_file(filepath)
            except Exception as e:
                QMessageBox.critical(self, "Error Opening File", str(e))
                self.status.setText("Error loading file.")
                return False
        else:
            self.status.setText(f"Error: File not found: {filepath}")
            return False

    def load_audio_to_track(self, samples, sr, audio_segment=None, filepath=None):
        """Load audio data into a new track in the multitrack container"""
        # Create a new track if the container exists
        if hasattr(self, 'track_container') and self.track_container:
            if filepath:
                track = self.track_container.load_audio_to_new_track(filepath)
            else:
                # Create a track from raw samples
                track = self.track_container.add_empty_track()
                track.set_audio_data(samples, sr, audio_segment, filepath)

            # Set as active track
            self.active_track = track
            return track
        else:
            self.status.setText("Error: MultiTrack container not initialized")
            return None

    def new_project(self):
        """Create a new empty project"""
        # Clear any existing tracks
        if hasattr(self, 'track_container') and self.track_container:
            self.track_container.clear_tracks()

        # Reset state
        self.samples = None
        self.sr = None
        self.audio_segment = None
        self.filepath = None
        self.active_track = None
        self._edit_stack = []
        self._redo_stack = []

        # Update UI
        self.update_file_info_bar()
        self.status.setText("New project created")

    def browse_file_clicked(self, item):
        """Handle click on file in browser sidebar"""
        if not item:
            return

        path = item.data(Qt.UserRole)
        if path and os.path.exists(path):
            self.open_audio_from_path(path)
        else:
            # Remove invalid item
            self.file_list_widget.takeItem(self.file_list_widget.row(item))
            self._recent_files = [p for p in self._recent_files if p != path]
            self._save_recent_files()
            QMessageBox.warning(self, "File Not Found", f"The file {path} no longer exists.")

    def refresh_file_list(self):
        """Update the file list in the sidebar"""
        self.file_list_widget.clear()

        for path in self._recent_files:
            if os.path.exists(path):
                basename = os.path.basename(path)
                item = QListWidgetItem(basename)
                item.setData(Qt.UserRole, path)
                item.setToolTip(path)
                self.file_list_widget.addItem(item)

        if not self._recent_files:
            item = QListWidgetItem("No recent files")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.file_list_widget.addItem(item)

    def update_file_info_bar(self):
        """Update the file info bar with information about the current file"""
        if hasattr(self, 'file_info_label'):
            if hasattr(self, 'active_track') and self.active_track and self.active_track.filepath:
                filepath = self.active_track.filepath
                fname = os.path.basename(filepath)
                sr = self.active_track.sr

                if self.active_track.samples is not None:
                    samples = self.active_track.samples
                    if hasattr(samples, 'shape'):
                        dur_sec = samples.shape[-1] / sr
                        channels = samples.shape[0] if samples.ndim > 1 else 1
                        fmt = os.path.splitext(fname)[1][1:].upper()
                        info = f"File: {fname}  |  {int(dur_sec)//60}:{int(dur_sec)%60:02d}  |  {fmt}, {sr} Hz, {channels} ch."
                        self.file_info_label.setText(info)
                        return

            # Default if no track or no audio
            self.file_info_label.setText("No file loaded")

    def save_as_file(self):
        """Export current audio to file in supported formats."""
        if not getattr(self, "audio_enabled", True):
            QMessageBox.critical(self, "Cannot Export Audio", FFMPEG_ERR_MSG or "Audio I/O unavailable")
            self.status.setText("Audio engine unavailable.")
            return
        if self.samples is None and self.audio_segment is None:
            QMessageBox.warning(self, "No Audio", "No audio loaded to export.")
            self.status.setText("No audio loaded.")
            return
        if self.samples is None or self.sr is None:
            QMessageBox.warning(self, "No Audio", "No audio data loaded.")
            self.status.setText("No audio data.")
            return

        formats_str = "Audio Files (*.wav *.flac *.mp3 *.aac);;All Files (*)"
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self, "Save Audio File As", "",
            formats_str
        )
        if not filepath:
            self.status.setText("Save cancelled.")
            return

        ext = os.path.splitext(filepath)[1][1:].lower()
        if not ext:  # Add extension if missing
            for fmt in ['wav', 'flac', 'mp3', 'aac']:
                if fmt in selected_filter:
                    ext = fmt
                    filepath += f".{fmt}"
                    break
            if not ext:
                ext = 'wav'
                filepath += ".wav"
        else:
            ext = ext.lstrip('.')
        if ext not in SUPPORTED_FORMATS:
            QMessageBox.warning(
                self, "Unsupported format",
                f"Export only supported as: {', '.join(SUPPORTED_FORMATS).upper()}"
            )
            self.status.setText("Export error: unsupported format")
            return
        try:
            if self.audio_segment is not None:
                params = {} if ext != 'mp3' else {"bitrate": "192k"}
                self.audio_segment.export(filepath, format=ext, **params)
                QMessageBox.information(
                    self, "Export Success", f"Exported as {filepath}"
                )
                self.status.setText(f"Exported: {os.path.basename(filepath)}")
            else:
                if self.samples is None or self.sr is None:
                    raise RuntimeError("No audio data found to export.")
                samples = self.samples
                channels = samples.shape[0] if samples.ndim > 1 else 1
                samples = (samples * (2 ** 15 - 1)).astype(np.int16)
                if channels == 1:
                    array = samples.T
                else:
                    array = samples.T.flatten()
                exported = AudioSegment(
                    array.tobytes(),
                    frame_rate=int(self.sr),
                    sample_width=2,  # int16
                    channels=channels
                )
                params = {} if ext != 'mp3' else {"bitrate": "192k"}
                exported.export(filepath, format=ext, **params)
                QMessageBox.information(
                    self, "Export Success", f"Exported as {filepath}"
                )
                self.status.setText(f"Exported: {os.path.basename(filepath)}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Could not save:\n{str(e)}")
            self.status.setText("Export Error")


    # --- Track Event Handlers ---
    def on_track_added(self, track):
        """Handle track added event"""
        # Update UI for the new track
        self.active_track = track
        self.status.setText(f"Added track: {track.name}")

    def on_track_removed(self, track):
        """Handle track removed event"""
        if self.active_track == track:
            self.active_track = None
            if self.track_container.tracks:
                self.active_track = self.track_container.tracks[0]

        self.status.setText(f"Removed track: {track.name}")

    def on_selection_changed(self, start, end):
        """Handle selection changed event"""
        self.status.setText(f"Selection: {start:.2f}s to {end:.2f}s")

    # --- Playback Control Methods ---
    def on_playback_started(self):
        """Handle playback started event"""
        self.is_playing = True
        self.is_paused = False
        self.status.setText("Playing...")

    def on_playback_paused(self):
        """Handle playback paused event"""
        self.is_playing = False
        self.is_paused = True
        self.status.setText("Paused")

    def on_playback_stopped(self):
        """Handle playback stopped event"""
        self.is_playing = False
        self.is_paused = False
        self.playback_pos_sec = 0.0
        self.status.setText("Stopped")

    def on_playback_position_changed(self, position_sec):
        """Handle playback position changed event"""
        self.playback_pos_sec = position_sec

        # Format time string for display
        minutes = int(position_sec) // 60
        seconds = int(position_sec) % 60
        milliseconds = int((position_sec - int(position_sec)) * 1000)
        time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

        # Update status bar with current position
        self.status.setText(f"Position: {time_str}")

    # --- Undo/Redo state utilities for multitrack ---
    def _make_state_snapshot(self):
        """Create a snapshot of the current project state for undo/redo"""
        tracks_data = []

        if hasattr(self, 'track_container') and self.track_container:
            for track in self.track_container.tracks:
                track_snapshot = {
                    "track_id": track.track_id,
                    "name": track.name,
                    "color": track.color.name() if track.color else None,
                    "muted": track.muted,
                    "soloed": track.soloed,
                    "volume": track.volume,
                    "audio_segment": track.audio_segment[:] if track.audio_segment is not None else None,
                    "samples": np.copy(track.samples) if track.samples is not None else None,
                    "sr": track.sr,
                    "selection": track.get_selection()
                }
                tracks_data.append(track_snapshot)

        # For backward compatibility with single-track code
        active_track_snapshot = {
            "audio_segment": self.audio_segment[:] if hasattr(self, 'audio_segment') and self.audio_segment is not None else None,
            "samples": np.copy(self.samples) if hasattr(self, 'samples') and self.samples is not None else None,
            "sr": self.sr if hasattr(self, 'sr') else None,
            "selection": None
        }

        if hasattr(self, 'active_track') and self.active_track:
            active_track_snapshot["selection"] = self.active_track.get_selection()

        return {
            "tracks": tracks_data,
            "active_track": active_track_snapshot
        }
    def _push_undo(self):
        """Save current state to undo stack"""
        self._edit_stack.append(self._make_state_snapshot())
        # New edit clears redo stack
        self._redo_stack.clear()
    def rewind_audio(self):
        """Rewind to beginning"""
        was_playing = self.is_playing

        # Stop any playing audio
        if was_playing:
            self.stop_audio()

        # Set position to beginning
        self.playback_pos_sec = 0.0

        # Update all track playheads
        if hasattr(self, 'track_container') and self.track_container and self.track_container.tracks:
            for track in self.track_container.tracks:
                if track.waveform_canvas:
                    track.waveform_canvas.update_playhead(0.0)

        self.status.setText("Rewound to beginning")

        # Resume if was playing
        if was_playing and hasattr(self, 'track_container') and self.track_container:
            self.track_container.play(start_position=0.0)

    def fast_forward_audio(self):
        """Fast forward by 5 seconds"""
        was_playing = self.is_playing

        # Stop any playing audio
        if was_playing:
            self.stop_audio()

        # Calculate new position (5 seconds forward)
        max_time = 0
        if hasattr(self, 'track_container') and self.track_container and self.track_container.tracks:
            for track in self.track_container.tracks:
                if track.waveform_canvas and track.waveform_canvas.max_time > max_time:
                    max_time = track.waveform_canvas.max_time

        new_pos = min(self.playback_pos_sec + 5.0, max_time)
        self.playback_pos_sec = new_pos

        # Update all track playheads
        if hasattr(self, 'track_container') and self.track_container and self.track_container.tracks:
            for track in self.track_container.tracks:
                if track.waveform_canvas:
                    track.waveform_canvas.update_playhead(new_pos)

        # Resume playback if was playing
        if was_playing and hasattr(self, 'track_container') and self.track_container:
            self.track_container.play(start_position=new_pos)

        self.status.setText(f"Fast-forwarded to {new_pos:.2f}s")
    def play_audio(self):
        """Play audio using the multitrack container"""
        if not hasattr(self, 'track_container') or not self.track_container:
            self.status.setText("No tracks available.")
            return

        if not self.track_container.tracks:
            self.status.setText("No tracks to play.")
            return

        # Let the track container handle playback
        if self.is_paused:
            # Resume from current position
            self.track_container.play(start_position=self.playback_pos_sec)
            self.status.setText(f"Resumed from {self.playback_pos_sec:.2f}s")
        else:
            # Start from beginning or selection start
            start_position = 0.0
            if hasattr(self, 'active_track') and self.active_track:
                selection = self.active_track.get_selection()
                if selection:
                    start_position = selection[0]  # Start from selection beginning

            self.track_container.play(start_position=start_position)
            self.status.setText("Playing...")

    def pause_audio(self):
        """Pause audio playback"""
        if hasattr(self, 'track_container') and self.track_container:
            self.track_container.pause()
            self.status.setText("Paused")

    def stop_audio(self):
        """Stop audio playback"""
        if hasattr(self, 'track_container') and self.track_container:
            self.track_container.stop()
            self.playback_pos_sec = 0.0
            self.status.setText("Stopped")

    def _restore_state(self, state):
        """Restore application state from a snapshot"""
        if "tracks" in state:
            # Multitrack state
            if hasattr(self, 'track_container') and self.track_container:
                # Clear current tracks
                self.track_container.clear_tracks()

                # Restore tracks from snapshot
                for track_data in state["tracks"]:
                    # Create a new track
                    new_track = self.track_container.add_empty_track()

                    # Restore track properties
                    new_track.name = track_data["name"]
                    new_track.color = QColor(track_data["color"]) if track_data["color"] else None
                    new_track.muted = track_data["muted"]
                    new_track.soloed = track_data["soloed"]
                    new_track.volume = track_data["volume"]

                    # Restore audio data
                    new_track.set_audio_data(
                        track_data["samples"],
                        track_data["sr"],
                        track_data["audio_segment"]
                    )

                    # Restore selection
                    # Restore selection
                    try:
                        if track_data["selection"]:
                            new_track.set_selection(track_data["selection"][0], track_data["selection"][1])
                    except Exception as e:
                        print(f"Error restoring selection: {e}")
        active_track_snapshot = state.get("active_track", None)
        if active_track_snapshot:
            self.audio_segment = active_track_snapshot["audio_segment"]
            self.samples = active_track_snapshot["samples"]
            self.sr = active_track_snapshot["sr"]

            # Update UI
            self.update_file_info_bar()
            self.status.setText("State restored.")


    def edit_undo(self):
        """Undo the last edit action"""
        if not self._edit_stack:
            self.status.setText("Nothing to undo.")
            return

        now = self._make_state_snapshot()
        last = self._edit_stack.pop()
        self._redo_stack.append(now)
        self._restore_state(last)
        self.status.setText("Undo completed.")

    def edit_redo(self):
        """Redo the last undone edit action"""
        if not self._redo_stack:
            self.status.setText("Nothing to redo.")
            return

        now = self._make_state_snapshot()
        next_state = self._redo_stack.pop()
        self._edit_stack.append(now)
        self._restore_state(next_state)
        self.status.setText("Redo completed.")

    # --- Edit operations ---
    def _selection_indices(self):
        """Get selection bounds in samples (start_idx, end_idx), or None if no/invalid selection."""
        if not hasattr(self, 'active_track') or not self.active_track:
            return None

        # Get selection from active track
        selection = self.active_track.get_selection()
        if not selection or self.active_track.samples is None or self.active_track.sr is None:
            return None

        start_t, end_t = selection
        if start_t == end_t:
            return None

        start_idx = int(self.active_track.sr * min(start_t, end_t))
        end_idx = int(self.active_track.sr * max(start_t, end_t))
        end_idx = min(end_idx, self.active_track.samples.shape[-1])
        return start_idx, end_idx

    def edit_cut(self):
        """Cut selected audio to clipboard, remove from buffer, update waveform and undo."""
        if not hasattr(self, 'active_track') or not self.active_track:
            QMessageBox.information(self, "Cut", "No active track.")
            self.status.setText("Cut failed: No active track.")
            return

        idx = self._selection_indices()
        if idx is None:
            QMessageBox.information(self, "Cut", "No valid selection to cut.")
            self.status.setText("Cut failed: No valid selection.")
            return

        # Save state for undo
        self._push_undo()

        start, end = idx
        track = self.active_track

        if start == end or end > track.samples.shape[-1]:
            QMessageBox.information(self, "Cut", "Invalid cut region.")
            self.status.setText("Cut failed: Empty or out-of-bounds region.")
            return

        try:
            # Copy to clipboard
            self.edit_clipboard = {
                "samples": np.copy(track.samples[:, start:end] if track.samples.ndim > 1 else track.samples[start:end]),
                "segment": track.audio_segment[start * 1000 // track.sr : end * 1000 // track.sr] if track.audio_segment else None,
                "sr": track.sr,
            }

            # Remove region from samples and AudioSegment
            if track.samples.ndim == 1:
                track.samples = np.concatenate([track.samples[:start], track.samples[end:]])
            else:
                track.samples = np.concatenate([track.samples[:, :start], track.samples[:, end:]], axis=1)

            if track.audio_segment:
                before = track.audio_segment[: start * 1000 // track.sr]
                after = track.audio_segment[end * 1000 // track.sr :]
                track.audio_segment = before + after

            # Update waveform
            track.waveform_canvas.clear_selection()
            track.set_audio_data(track.samples, track.sr, track.audio_segment, track.filepath)

            self.status.setText("Cut selection.")
        except Exception as e:
            QMessageBox.critical(self, "Cut Failed", f"Could not cut selection:\n{str(e)}")
            self.status.setText("Error: Cut failed.")

    def edit_copy(self):
        """Copy selection to clipboard buffer, with error checks."""
        if not hasattr(self, 'active_track') or not self.active_track:
            QMessageBox.information(self, "Copy", "No active track.")
            self.status.setText("Copy failed: No active track.")
            return

        idx = self._selection_indices()
        if idx is None:
            QMessageBox.information(self, "Copy", "No valid selection to copy.")
            self.status.setText("Copy failed: No valid selection.")
            return

        start, end = idx
        track = self.active_track

        if start == end or end > track.samples.shape[-1]:
            QMessageBox.information(self, "Copy", "Invalid copy region.")
            self.status.setText("Copy failed: Invalid region.")
            return

        try:
            self.edit_clipboard = {
                "samples": np.copy(track.samples[:, start:end] if track.samples.ndim > 1 else track.samples[start:end]),
                "segment": track.audio_segment[start * 1000 // track.sr : end * 1000 // track.sr] if track.audio_segment else None,
                "sr": track.sr,
            }
            self.status.setText("Copied selection.")
        except Exception as e:
            QMessageBox.critical(self, "Copy Failed", f"Could not copy selection:\n{str(e)}")
            self.status.setText("Error: Copy failed.")

    def edit_paste(self):
        """Paste clipboard buffer at selection/cursor position."""
        if not hasattr(self, 'active_track') or not self.active_track:
            QMessageBox.information(self, "Paste", "No active track.")
            self.status.setText("Paste failed: No active track.")
            return

        track = self.active_track

        if not self.edit_clipboard or self.edit_clipboard.get('sr') != track.sr:
            QMessageBox.information(self, "Paste", "Clipboard empty or sample rates do not match.")
            self.status.setText("Paste failed: Clipboard invalid or rates differ.")
            return

        if track.samples is None:
            QMessageBox.information(self, "Paste", "No audio to paste into.")
            self.status.setText("Paste failed: No audio loaded.")
            return

        self._push_undo()

        idx = self._selection_indices()
        if idx is None:
            idx = (0, 0)  # Paste at start

        insert_at = min(max(idx[0], 0), track.samples.shape[-1])
        clip_samples = self.edit_clipboard['samples']

        try:
            # Insert into samples
            if track.samples.ndim == 1:
                track.samples = np.concatenate([track.samples[:insert_at], clip_samples, track.samples[insert_at:]])
            else:
                track.samples = np.concatenate([track.samples[:, :insert_at], clip_samples, track.samples[:, insert_at:]], axis=1)

            # Insert into AudioSegment
            if track.audio_segment and self.edit_clipboard['segment']:
                before = track.audio_segment[: insert_at * 1000 // track.sr]
                after = track.audio_segment[insert_at * 1000 // track.sr :]
                track.audio_segment = before + self.edit_clipboard['segment'] + after

            # Update waveform
            track.set_audio_data(track.samples, track.sr, track.audio_segment, track.filepath)
            self.status.setText("Pasted buffer.")
        except Exception as e:
            QMessageBox.critical(self, "Paste Failed", f"Could not paste clipboard:\n{str(e)}")
            self.status.setText("Error: Paste failed.")
    def edit_trim(self):
        """Keep only selected audio. Adds edge and error checks."""
        if not hasattr(self, 'active_track') or not self.active_track:
            QMessageBox.information(self, "Trim", "No active track.")
            self.status.setText("Trim failed: No active track.")
            return

        idx = self._selection_indices()
        if idx is None:
            QMessageBox.information(self, "Trim", "No valid selection to trim.")
            self.status.setText("Trim failed: No valid selection.")
            return

        track = self.active_track
        start, end = idx

        if start == end or end > track.samples.shape[-1]:
            QMessageBox.information(self, "Trim", "Invalid trim region.")
            self.status.setText("Trim failed: Empty or out-of-bounds region.")
            return

        self._push_undo()

        try:
            # Trim samples to selection
            if track.samples.ndim == 1:
                track.samples = track.samples[start:end]
            else:
                track.samples = track.samples[:, start:end]

            # Trim audio segment
            if track.audio_segment:
                track.audio_segment = track.audio_segment[start * 1000 // track.sr : end * 1000 // track.sr]

            # Update waveform
            track.waveform_canvas.clear_selection()
            track.set_audio_data(track.samples, track.sr, track.audio_segment, track.filepath)

            self.status.setText("Trimmed to selection.")
        except Exception as e:
            QMessageBox.critical(self, "Trim Failed", f"Could not trim:\n{str(e)}")
            self.status.setText("Error: Trim failed.")

    # --- Gain/fade processing ---
    def apply_gain_dialog(self):
        """Ask user for desired gain in dB, then apply to selection."""
        if not hasattr(self, 'active_track') or not self.active_track:
            QMessageBox.information(self, "Gain", "No active track.")
            self.status.setText("Gain failed: No active track.")
            return

        idx = self._selection_indices()
        if idx is None:
            QMessageBox.information(self, "Gain", "No region selected for gain adjustment.")
            return

        track = self.active_track

        import PyQt5.QtWidgets
        value, ok = PyQt5.QtWidgets.QInputDialog.getDouble(
            self, "Adjust Gain",
            "Gain (dB, range -20..+20):",
            value=0.0, min=-20.0, max=20.0, decimals=2
        )
        if not ok:
            return

        self._push_undo()

        start, end = idx
        # Apply gain to samples
        factor = 10.0 ** (value / 20.0)

        if track.samples.ndim == 1:
            track.samples[start:end] *= factor
        else:
            track.samples[:, start:end] *= factor

        # Apply gain to AudioSegment (ms indices)
        if track.audio_segment:
            seg = track.audio_segment[start * 1000 // track.sr : end * 1000 // track.sr].apply_gain(value)
            before = track.audio_segment[: start * 1000 // track.sr]
            after = track.audio_segment[end * 1000 // track.sr :]
            track.audio_segment = before + seg + after

        # Update waveform
        track.set_audio_data(track.samples, track.sr, track.audio_segment, track.filepath)
        self.status.setText(f"Applied gain {value:+.2f} dB to selection.")

    def _fade_duration_dialog(self, default_ms):
        import PyQt5.QtWidgets
        value, ok = PyQt5.QtWidgets.QInputDialog.getInt(
            self, "Fade Duration",
            "Fade duration (ms):", value=default_ms, min=1, max=int(default_ms*2)
        )
        return value if ok else None

    def apply_fade_in(self):
        """Apply fade-in effect to selection."""
        if not hasattr(self, 'active_track') or not self.active_track:
            QMessageBox.information(self, "Fade In", "No active track.")
            self.status.setText("Fade In failed: No active track.")
            return

        idx = self._selection_indices()
        if idx is None:
            QMessageBox.information(self, "Fade In", "No region selected for fade-in.")
            return

        track = self.active_track
        start, end = idx
        length_ms = (end - start) * 1000 // track.sr
        fade_ms = self._fade_duration_dialog(length_ms)

        if fade_ms is None:
            return

        self._push_undo()

        # Apply fade to samples (linear fade-in)
        dur_samp = end - start
        # Numpy: linear ramp from 0 to 1
        fade_curve = np.linspace(0.0, 1.0, dur_samp)

        if track.samples.ndim == 1:
            track.samples[start:end] *= fade_curve
        else:
            track.samples[:, start:end] = (track.samples[:, start:end].T * fade_curve).T

        # PyDub: fade in
        if track.audio_segment:
            faded = track.audio_segment[start * 1000 // track.sr : end * 1000 // track.sr].fade_in(fade_ms)
            before = track.audio_segment[: start * 1000 // track.sr]
            after = track.audio_segment[end * 1000 // track.sr :]
            track.audio_segment = before + faded + after

        # Update waveform
        track.set_audio_data(track.samples, track.sr, track.audio_segment, track.filepath)
        self.status.setText("Applied fade-in to selection.")

    def apply_fade_out(self):
        """Apply fade-out effect to selection."""
        if not hasattr(self, 'active_track') or not self.active_track:
            QMessageBox.information(self, "Fade Out", "No active track.")
            self.status.setText("Fade Out failed: No active track.")
            return

        idx = self._selection_indices()
        if idx is None:
            QMessageBox.information(self, "Fade Out", "No region selected for fade-out.")
            return

        track = self.active_track
        start, end = idx
        length_ms = (end - start) * 1000 // track.sr
        fade_ms = self._fade_duration_dialog(length_ms)

        if fade_ms is None:
            return

        self._push_undo()

        # Numpy fade-out: linear ramp down
        dur_samp = end - start
        fade_curve = np.linspace(1.0, 0.0, dur_samp)

        if track.samples.ndim == 1:
            track.samples[start:end] *= fade_curve
        else:
            track.samples[:, start:end] = (track.samples[:, start:end].T * fade_curve).T

        # PyDub: fade out
        if track.audio_segment:
            faded = track.audio_segment[start * 1000 // track.sr : end * 1000 // track.sr].fade_out(fade_ms)
            before = track.audio_segment[: start * 1000 // track.sr]
            after = track.audio_segment[end * 1000 // track.sr :]
            track.audio_segment = before + faded + after

        # Update waveform
        track.set_audio_data(track.samples, track.sr, track.audio_segment, track.filepath)
        self.status.setText("Applied fade-out to selection.")

    def edit_stub(self):
        """Show stub dialog for edit menu actions."""
        action = self.sender()
        feat = action.text()
        QMessageBox.information(self, "Not Yet Implemented",
                f"{feat} feature is in development.")
    def show_about(self):
        QMessageBox.about(
            self, "About MetroMuse",
            "MetroMuse Audio Editor\n\n"
    "A simple, cross-platform, dark-themed audio editor inspired by Audacity.\n\n"
    "Supports opening and viewing the waveform of WAV, FLAC, MP3, and AAC files.\n"
    "Features multitrack support, enhanced waveform scrubbing, and modern UI.\n"
    "Editing, advanced playback, project browser, and more!\n"
    "Developed with Python, PyQt5, matplotlib, numpy, and pydub."
)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Enable Fusion style for better cross-platform dark interface
    app.setStyle("Fusion")
    window = MetroMuse()
    window.show()
    sys.exit(app.exec_())

# TODO:
# - Add spectrum analysis view
# - Implement more audio effects (echo, reverb, eq)
# - Add support for VST plugins
# - Implement project saving/loading
# - Add track automation
# - Enhanced error handling and user-guide dialogs
