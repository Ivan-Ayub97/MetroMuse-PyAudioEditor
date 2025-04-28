import os
import uuid
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import sounddevice as sd
from scipy import signal
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSlider, QToolButton, 
    QVBoxLayout, QWidget, QLineEdit, QColorDialog, QScrollArea,
    QSizePolicy, QPushButton, QMenu
)

# Import the existing WaveformCanvas class
from track_renderer import EnhancedWaveformCanvas
from pydub import AudioSegment

# Constants for UI
DARK_BG = '#232629'
DARK_FG = '#eef1f4'
ACCENT_COLOR = '#47cbff'
TRACK_COLORS = [
    '#47cbff',  # Sky blue
    '#ff6b6b',  # Coral red
    '#5ad95a',  # Green
    '#ffc14d',  # Orange
    '#af8cff',  # Purple
    '#ff9cee',  # Pink
    '#4deeea',  # Cyan
    '#ffec59',  # Yellow
    '#ffa64d',  # Amber
    '#9cff9c',  # Light green
]


class AudioTrack(QObject):
    """
    Represents a single audio track with its own waveform, controls, and audio data.
    """
    # Signals for track events
    nameChanged = pyqtSignal(str)
    colorChanged = pyqtSignal(QColor)
    muteChanged = pyqtSignal(bool)
    soloChanged = pyqtSignal(bool)
    volumeChanged = pyqtSignal(float)
    trackDeleted = pyqtSignal(object)  # Emits self reference
    
    def __init__(self, parent=None, track_id=None, name="New Track", color=None):
        super().__init__(parent)
        self.track_id = track_id or str(uuid.uuid4())
        self._name = name
        self._color = QColor(color or TRACK_COLORS[0])
        self._muted = False
        self._soloed = False
        self._volume = 1.0  # 0.0 to 1.0
        
        # Audio data
        self.samples = None
        self.sr = None
        self.audio_segment = None
        self.filepath = None
        
        # UI components
        self.waveform_canvas = None
        self.track_widget = None
        self.header_widget = None
        
        # Initialize UI components
        self._init_ui_components()
    
    def _init_ui_components(self):
        """Initialize the track's UI components including waveform and header"""
        # Create waveform canvas
        # Create waveform canvas
        self.waveform_canvas = EnhancedWaveformCanvas()
        self.waveform_canvas.setMinimumHeight(120)
        
        # Create header widget with controls
        self.header_widget = self._create_header_widget()
        
        # Create main track widget (container for header and waveform)
        self.track_widget = QWidget()
        layout = QVBoxLayout(self.track_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header_widget)
        layout.addWidget(self.waveform_canvas)
        
        # Style the track widget
        self.track_widget.setStyleSheet(f"""
            QWidget {{ background-color: {DARK_BG}; }}
            QLabel {{ color: {DARK_FG}; }}
        """)
    
    def _create_header_widget(self):
        """Create the track header with name, color, mute, solo, and volume controls"""
        header = QFrame()
        header.setFrameShape(QFrame.StyledPanel)
        header.setMaximumHeight(48)
        header.setMinimumHeight(48)
        header.setStyleSheet(f"""
            QFrame {{ 
                background-color: #21242b; 
                border: 1px solid #31343a; 
                border-radius: 6px;
                margin: 2px;
            }}
            QToolButton {{
                background-color: #2a2e36;
                color: {DARK_FG};
                border: none;
                border-radius: 4px;
                padding: 4px;
                min-width: 48px;
                min-height: 48px;
            }}
            QToolButton:hover {{
                background-color: #383c45;
            }}
            QToolButton:checked {{
                background-color: {self._color.name()};
                color: #000000;
            }}
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        
        # Color selector button
        self.color_btn = QToolButton()
        self.color_btn.setFixedSize(32, 32)
        self.color_btn.setStyleSheet(f"background-color: {self._color.name()}; border-radius: 16px;")
        self.color_btn.setToolTip("Change track color")
        self.color_btn.clicked.connect(self._show_color_dialog)
        
        # Track name edit
        self.name_edit = QLineEdit(self._name)
        self.name_edit.setStyleSheet(f"color: {DARK_FG}; background-color: #2a2e36; border: 1px solid #373a42; border-radius: 4px; padding: 4px;")
        self.name_edit.editingFinished.connect(self._update_name)
        self.name_edit.setMinimumWidth(150)
        
        # Mute button
        self.mute_btn = QToolButton()
        self.mute_btn.setText("M")
        self.mute_btn.setCheckable(True)
        self.mute_btn.setToolTip("Mute track")
        self.mute_btn.clicked.connect(self._toggle_mute)
        
        # Solo button
        self.solo_btn = QToolButton()
        self.solo_btn.setText("S")
        self.solo_btn.setCheckable(True)
        self.solo_btn.setToolTip("Solo track")
        self.solo_btn.clicked.connect(self._toggle_solo)
        
        # Volume slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self._volume * 100))
        self.volume_slider.setToolTip("Adjust track volume")
        self.volume_slider.valueChanged.connect(self._update_volume)
        
        # Delete track button
        self.delete_btn = QToolButton()
        self.delete_btn.setText("✕")
        self.delete_btn.setToolTip("Delete track")
        self.delete_btn.clicked.connect(self._delete_track)
        
        # Add widgets to layout
        layout.addWidget(self.color_btn)
        layout.addWidget(self.name_edit, 1)
        layout.addWidget(self.mute_btn)
        layout.addWidget(self.solo_btn)
        layout.addWidget(self.volume_slider, 2)
        layout.addWidget(self.delete_btn)
        
        return header
    
    def set_audio_data(self, samples, sr, audio_segment=None, filepath=None):
        """Set the audio data for this track and update the waveform display"""
        self.samples = samples
        self.sr = sr
        self.audio_segment = audio_segment
        self.filepath = filepath
        
        if self.waveform_canvas and samples is not None and sr is not None:
            self.waveform_canvas.plot_waveform(samples, sr)
            self._update_header_info()
    
    def _update_header_info(self):
        """Update header with audio information"""
        if hasattr(self, 'filepath') and self.filepath and self.name_edit:
            if self._name == "New Track":  # Only auto-update if using default name
                basename = os.path.basename(self.filepath)
                self.name_edit.setText(basename)
                self._name = basename
                self.nameChanged.emit(self._name)
    
    # Properties and event handlers
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value):
        if value != self._name:
            self._name = value
            if hasattr(self, 'name_edit') and self.name_edit:
                self.name_edit.setText(value)
            self.nameChanged.emit(value)
    
    def _update_name(self):
        new_name = self.name_edit.text()
        if new_name != self._name:
            self._name = new_name
            self.nameChanged.emit(new_name)
    
    @property
    def color(self):
        return self._color
    
    @color.setter
    def color(self, value):
        if isinstance(value, str):
            value = QColor(value)
        
        if value != self._color:
            self._color = value
            if hasattr(self, 'color_btn') and self.color_btn:
                self.color_btn.setStyleSheet(f"background-color: {value.name()}; border-radius: 16px;")
            
            # Update mute/solo button colors
            if hasattr(self, 'mute_btn') and self.mute_btn:
                self.mute_btn.setStyleSheet(f"QToolButton:checked {{ background-color: {value.name()}; }}")
            if hasattr(self, 'solo_btn') and self.solo_btn:
                self.solo_btn.setStyleSheet(f"QToolButton:checked {{ background-color: {value.name()}; }}")
                
            self.colorChanged.emit(value)
    
    def _show_color_dialog(self):
        color = QColorDialog.getColor(self._color, None, "Select Track Color")
        if color.isValid():
            self.color = color
    
    @property
    def muted(self):
        return self._muted
    
    @muted.setter
    def muted(self, value):
        if value != self._muted:
            self._muted = value
            if hasattr(self, 'mute_btn') and self.mute_btn:
                self.mute_btn.setChecked(value)
            self.muteChanged.emit(value)
    
    def _toggle_mute(self):
        self.muted = self.mute_btn.isChecked()
    
    @property
    def soloed(self):
        return self._soloed
    
    @soloed.setter
    def soloed(self, value):
        if value != self._soloed:
            self._soloed = value
            if hasattr(self, 'solo_btn') and self.solo_btn:
                self.solo_btn.setChecked(value)
            self.soloChanged.emit(value)
    
    def _toggle_solo(self):
        self.soloed = self.solo_btn.isChecked()
    
    @property
    def volume(self):
        return self._volume
    
    @volume.setter
    def volume(self, value):
        # Ensure volume is between 0 and 1
        value = max(0.0, min(1.0, value))
        if value != self._volume:
            self._volume = value
            if hasattr(self, 'volume_slider') and self.volume_slider:
                self.volume_slider.setValue(int(value * 100))
            self.volumeChanged.emit(value)
    
    def _update_volume(self):
        self.volume = self.volume_slider.value() / 100.0
    
    def _delete_track(self):
        """Handle track deletion request"""
        self.trackDeleted.emit(self)
    
    def is_playable(self):
        """Check if this track has playable audio data"""
        return (self.samples is not None and self.sr is not None) or self.audio_segment is not None
    
    def get_mixed_samples(self, start_time=0, duration=None):
        """
        Get audio samples for playback, applying volume and mute settings.
        Returns None if track is muted or has no audio data.
        """
        if self.muted or not self.is_playable():
            return None, None
        
        if self.audio_segment is not None:
            # Convert start_time from seconds to milliseconds
            start_ms = int(start_time * 1000)
            if duration is not None:
                duration_ms = int(duration * 1000)
                segment = self.audio_segment[start_ms:start_ms + duration_ms]
            else:
                segment = self.audio_segment[start_ms:]
            
            # Apply volume
            if self._volume != 1.0:
                gain_db = 20 * np.log10(self._volume) if self._volume > 0 else -96.0
                segment = segment.apply_gain(gain_db)
            
            # Convert to numpy array for mixing
            samples = np.array(segment.get_array_of_samples()).astype(np.float32)
            if segment.channels > 1:
                samples = samples.reshape((-1, segment.channels)).T
            else:
                samples = samples[None, :]
            samples = samples / (2 ** (8 * segment.sample_width - 1))
            
            return samples, segment.frame_rate
        
        elif self.samples is not None and self.sr is not None:
            # Convert start_time to sample index
            start_idx = int(start_time * self.sr)
            if duration is not None:
                end_idx = min(start_idx + int(duration * self.sr), self.samples.shape[-1])
            else:
                end_idx = self.samples.shape[-1]
            
            # Extract the samples and apply volume
            if self.samples.ndim > 1:
                samples = self.samples[:, start_idx:end_idx].copy()
            else:
                samples = self.samples[start_idx:end_idx].copy()
            
            samples = samples * self._volume
            return samples, self.sr
        
        return None, None
    
    def get_selection(self):
        """Get the current selection range from the waveform canvas"""
        if self.waveform_canvas and self.waveform_canvas.selection:
            return self.waveform_canvas.selection
        return None
    
    def set_selection(self, start, end):
        """Set selection range on waveform canvas"""
        if self.waveform_canvas:
            self.waveform_canvas.set_selection(start, end)


class MultiTrackContainer(QWidget):
    """
    Container widget that manages multiple audio tracks and provides global playback controls.
    Synchronizes all track timelines and handles mixed playback.
    """
    # Signals for multitrack events
    playbackStarted = pyqtSignal()
    playbackPaused = pyqtSignal()
    playbackStopped = pyqtSignal()
    playbackPositionChanged = pyqtSignal(float)  # Current position in seconds
    trackAdded = pyqtSignal(object)  # AudioTrack reference
    trackRemoved = pyqtSignal(object)  # AudioTrack reference
    selectionChanged = pyqtSignal(float, float)  # start, end in seconds
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracks = []  # List of AudioTrack objects
        self.track_widgets = []  # List of track UI containers
        
        # Playback state
        self.is_playing = False
        self.is_paused = False
        self.playback_position = 0.0  # in seconds
        self.playback_stream = None
        self.playback_thread = None
        self.global_volume = 1.0
        
        # Timeline and selection
        self.time_ruler = None
        self.playhead = None
        self.global_selection = None  # (start, end) in seconds or None
        
        # Initialize UI
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the multitrack container UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Time ruler (shows seconds, minutes markers)
        self.time_ruler = self._create_time_ruler()
        main_layout.addWidget(self.time_ruler)
        
        # Tracks scroll area
        self.tracks_scroll = QScrollArea()
        self.tracks_scroll.setWidgetResizable(True)
        self.tracks_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.tracks_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tracks_scroll.setStyleSheet(f"""
            QScrollArea {{ background: {DARK_BG}; border: none; }}
            QScrollBar {{ background: #21242b; width: 16px; height: 16px; }}
            QScrollBar::handle {{ background: #3a3f4b; border-radius: 5px; }}
            QScrollBar::handle:hover {{ background: #474d5d; }}
        """)
        
        # Container for all tracks
        self.tracks_container = QWidget()
        self.tracks_layout = QVBoxLayout(self.tracks_container)
        self.tracks_layout.setContentsMargins(0, 0, 0, 0)
        self.tracks_layout.setSpacing(4)
        self.tracks_layout.addStretch(1)  # Push tracks to top
        
        self.tracks_scroll.setWidget(self.tracks_container)
        main_layout.addWidget(self.tracks_scroll, 1)  # Tracks get all available space
        
        # Track controls (add track button, etc.)
        self.controls_widget = self._create_track_controls()
        main_layout.addWidget(self.controls_widget)
        
        # Playback controls
        self.playback_widget = self._create_playback_controls()
        main_layout.addWidget(self.playback_widget)
    
    def _create_time_ruler(self):
        """Create a time ruler widget that shows time markers"""
        ruler = QFrame()
        ruler.setMinimumHeight(30)
        ruler.setMaximumHeight(30)
        ruler.setFrameShape(QFrame.StyledPanel)
        ruler.setStyleSheet(f"""
            QFrame {{ 
                background-color: #1a1d23; 
                border-bottom: 1px solid #31343a; 
            }}
        """)
        
        # The actual time markers will be drawn using paintEvent when implemented
        # For now, we'll use a placeholder
        layout = QHBoxLayout(ruler)
        layout.setContentsMargins(8, 2, 8, 2)
        label = QLabel("Timeline - 00:00:00")
        label.setStyleSheet(f"color: {DARK_FG}; font-family: monospace;")
        layout.addWidget(label)
        
        return ruler
    
    def _create_track_controls(self):
        """Create controls for track management (add track, etc.)"""
        controls = QFrame()
        controls.setMaximumHeight(48)
        controls.setFrameShape(QFrame.StyledPanel)
        controls.setStyleSheet(f"""
            QFrame {{ 
                background-color: #1e2128; 
                border-top: 1px solid #31343a; 
            }}
            QPushButton {{ 
                background-color: #2a2e36;
                color: {DARK_FG};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-height: 36px;
            }}
            QPushButton:hover {{ 
                background-color: #383c45;
            }}
        """)
        
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Add Track button
        self.add_track_btn = QPushButton("+ Add Track")
        self.add_track_btn.setToolTip("Add a new empty track")
        self.add_track_btn.clicked.connect(self.add_empty_track)
        
        # Import Audio button
        self.import_audio_btn = QPushButton("Import Audio")
        self.import_audio_btn.setToolTip("Import audio to a new track")
        self.import_audio_btn.clicked.connect(self.import_audio_file)
        
        layout.addWidget(self.add_track_btn)
        layout.addWidget(self.import_audio_btn)
        layout.addStretch(1)
        
        return controls
    
    def _create_playback_controls(self):
        """Create transport controls for playback"""
        controls = QFrame()
        controls.setMaximumHeight(60)
        controls.setFrameShape(QFrame.StyledPanel)
        controls.setStyleSheet(f"""
            QFrame {{ 
                background-color: #21242b; 
                border-top: 1px solid #31343a; 
            }}
            QToolButton {{ 
                background-color: #2a2e36;
                color: {DARK_FG};
                border: none;
                border-radius: 6px;
                padding: 8px;
                min-width: 48px;
                min-height: 48px;
            }}
            QToolButton:hover {{ 
                background-color: #383c45;
            }}
            QToolButton:checked {{ 
                background-color: {ACCENT_COLOR};
                color: #000000;
            }}
        """)
        
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)
        
        # Create playback control buttons
        self.rewind_btn = QToolButton()
        self.rewind_btn.setText("⏪")
        self.rewind_btn.setToolTip("Rewind (Home)")
        self.rewind_btn.clicked.connect(self.rewind)
        
        self.play_btn = QToolButton()
        self.play_btn.setText("▶")
        self.play_btn.setToolTip("Play (Space)")
        self.play_btn.clicked.connect(self.play)
        
        self.pause_btn = QToolButton()
        self.pause_btn.setText("⏸")
        self.pause_btn.setToolTip("Pause (Space)")
        self.pause_btn.clicked.connect(self.pause)
        
        self.stop_btn = QToolButton()
        self.stop_btn.setText("⏹")
        self.stop_btn.setToolTip("Stop (Esc)")
        self.stop_btn.clicked.connect(self.stop)
        
        # Current time display
        self.time_display = QLabel("00:00.000")
        self.time_display.setStyleSheet(f"""
            color: {DARK_FG}; 
            font-family: monospace; 
            font-size: 16px; 
            background-color: #1a1d23; 
            padding: 4px 8px; 
            border-radius: 4px;
        """)
        
        # Add widgets to layout
        layout.addWidget(self.rewind_btn)
        layout.addWidget(self.play_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.time_display, 1)
        
        return controls
    
    # Track management methods
    def add_empty_track(self):
        """Add a new empty track to the container"""
        # Create a new track with a color from the TRACK_COLORS list
        track_color = TRACK_COLORS[len(self.tracks) % len(TRACK_COLORS)]
        track = AudioTrack(self, name=f"Track {len(self.tracks) + 1}", color=track_color)
        return self._add_track(track)
    
    def _add_track(self, track):
        """Internal method to add a track to the container"""
        # Connect track signals
        track.trackDeleted.connect(self.remove_track)
        
        # Add track to list and UI
        self.tracks.append(track)
        
        # Add track widget to the layout (before the stretch)
        self.tracks_layout.insertWidget(self.tracks_layout.count() - 1, track.track_widget)
        self.track_widgets.append(track.track_widget)
        
        # Emit signal
        self.trackAdded.emit(track)
        return track
    
    def remove_track(self, track):
        """Remove a track from the container"""
        if track in self.tracks:
            # Remove track widget from layout
            if track.track_widget in self.track_widgets:
                self.tracks_layout.removeWidget(track.track_widget)
                self.track_widgets.remove(track.track_widget)
                track.track_widget.deleteLater()
            
            # Remove track from list
            self.tracks.remove(track)
            
            # Emit signal
            self.trackRemoved.emit(track)
            
            # Clean up track resources
            track.deleteLater()
    
    def clear_tracks(self):
        """Remove all tracks"""
        # Make a copy of the list to avoid modification during iteration
        tracks_copy = self.tracks.copy()
        for track in tracks_copy:
            self.remove_track(track)
    
    def get_track_by_id(self, track_id):
        """Get a track by its ID"""
        for track in self.tracks:
            if track.track_id == track_id:
                return track
        return None
    
    def import_audio_file(self):
        """Open a file dialog to import audio file to a new track"""
        from PyQt5.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Audio File", "",
            "Audio Files (*.wav *.flac *.mp3 *.aac);;All Files (*)"
        )
        if filepath:
            self.load_audio_to_new_track(filepath)
    
    def load_audio_to_new_track(self, filepath):
        """Load an audio file into a new track"""
        try:
            # Create a new track with the file basename as the track name
            basename = os.path.basename(filepath)
            track_color = TRACK_COLORS[len(self.tracks) % len(TRACK_COLORS)]
            track = AudioTrack(self, name=basename, color=track_color)
            
            # Try to load the audio file
            self._load_audio_file(track, filepath)
            
            # Add track to container
            self._add_track(track)
            return track
            
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Import Error", f"Could not import audio file:\n{str(e)}")
            return None
    
    def _load_audio_file(self, track, filepath):
        """Load an audio file into a track using the appropriate loader"""
        ext = os.path.splitext(filepath)[1][1:].lower()
        
        # Try pydub first for supported formats
        if ext in ['mp3', 'flac', 'wav', 'aac']:
            try:
                if ext == 'aac':
                    audio = AudioSegment.from_file(filepath, 'aac')
                else:
                    audio = AudioSegment.from_file(filepath)
                    
                # Convert to numpy array
                samples = np.array(audio.get_array_of_samples()).astype(np.float32)
                if audio.channels > 1:
                    samples = samples.reshape((-1, audio.channels)).T
                samples = samples / (2 ** (8 * audio.sample_width - 1))
                
                # Set track data
                track.set_audio_data(samples, audio.frame_rate, audio, filepath)
                return
                
            except Exception as e:
                raise RuntimeError(f"Failed to decode {ext.upper()} audio file; ensure ffmpeg is present.\nError: {str(e)}")
                
        # Fallback to librosa for other formats
        import librosa
        samples, sr = librosa.load(filepath, sr=None, mono=False)
        if samples.ndim == 1:
            samples = np.expand_dims(samples, axis=0)
            
        # Set track data
        track.set_audio_data(samples, sr, None, filepath)
        
    # --- Playback Methods ---
    def play(self, start_position=None):
        """Start playback from the given position or current position"""
        if not self.tracks:
            return
            
        if start_position is not None:
            self.playback_position = start_position
        
        self.is_playing = True
        self.is_paused = False
        self._start_playback()
        self.playbackStarted.emit()
        
    def pause(self):
        """Pause playback"""
        self.is_playing = False
        self.is_paused = True
        self._stop_playback()
        self.playbackPaused.emit()
        
    def stop(self):
        """Stop playback and reset position"""
        self.is_playing = False
        self.is_paused = False
        self._stop_playback()
        self.playback_position = 0.0
        self.playbackStopped.emit()
        
    def rewind(self):
        """Rewind to beginning"""
        was_playing = self.is_playing
        self.stop()
        if was_playing:
            self.play(start_position=0.0)
            
    def _start_playback(self):
        """Start audio playback using sounddevice"""
        self._stop_playback()  # Stop any existing playback
        
        # Start a new thread for playback to avoid UI blocking
        self.playback_thread = threading.Thread(target=self._playback_thread_func, daemon=True)
        self.playback_thread.start()
        
    def _stop_playback(self):
        """Stop current audio playback"""
        if self.playback_stream is not None:
            try:
                self.playback_stream.stop()
                self.playback_stream.close()
            except Exception:
                pass
            self.playback_stream = None
        
    def _playback_thread_func(self):
        """Thread function for audio playback"""
        if not self.tracks:
            return
            
        try:
            # Get information about tracks to play
            active_tracks = [t for t in self.tracks if not t.muted and t.is_playable()]
            if not active_tracks:
                return
                
            # Find if any track is soloed
            has_solo = any(t.soloed for t in active_tracks)
            if has_solo:
                active_tracks = [t for t in active_tracks if t.soloed]
            
            # Determine sample rate to use (use highest among tracks)
            sr = max(t.sr for t in active_tracks if t.sr is not None)
            
            # Setup sounddevice callback for streaming audio
            def audio_callback(outdata, frames, time, status):
                if not self.is_playing:
                    # Fill with zeros and stop stream
                    outdata.fill(0)
                    self.playback_stream.stop()
                    return
                    
                # Calculate what portion of each track to play
                duration = frames / sr
                
                # Mix all active tracks
                mixed_samples = np.zeros((2, frames))  # Stereo output
                
                for track in active_tracks:
                    track_samples, track_sr = track.get_mixed_samples(
                        start_time=self.playback_position,
                        duration=duration
                    )
                    
                    if track_samples is not None:
                        # Resample if needed
                        if track_sr != sr:
                            # Simple resampling - for proper implementation use a resampling library
                            ratio = sr / track_sr
                            new_len = int(track_samples.shape[1] * ratio)
                            from scipy import signal
                            track_samples = signal.resample(track_samples, new_len, axis=1)
                            
                        # Ensure correct length
                        if track_samples.shape[1] < frames:
                            # Pad with zeros
                            pad_width = frames - track_samples.shape[1]
                            track_samples = np.pad(track_samples, ((0, 0), (0, pad_width)))
                        elif track_samples.shape[1] > frames:
                            # Trim excess
                            track_samples = track_samples[:, :frames]
                            
                        # Mix into output with track volume
                        channels = track_samples.shape[0]
                        if channels == 1:
                            # Mono to stereo
                            mixed_samples[0] += track_samples[0]
                            mixed_samples[1] += track_samples[0]
                        else:
                            # Use first two channels (or duplicate if only one)
                            mixed_samples[0] += track_samples[0]
                            mixed_samples[1] += track_samples[min(1, channels-1)]
                
                # Apply global volume
                mixed_samples *= self.global_volume
                
                # Prevent clipping
                if np.max(np.abs(mixed_samples)) > 1.0:
                    mixed_samples /= np.max(np.abs(mixed_samples))
                
                # Update output buffer (convert to float32 non-interleaved format)
                outdata[:] = mixed_samples.T.astype(np.float32)
                
                # Update playback position and emit signal
                self.playback_position += duration
                self.playbackPositionChanged.emit(self.playback_position)
                
                # Update playhead in each track
                for track in self.tracks:
                    if track.waveform_canvas:
                        track.waveform_canvas.update_playhead(self.playback_position)
            
            # Start the sounddevice stream
            self.playback_stream = sd.OutputStream(
                samplerate=sr,
                channels=2,
                callback=audio_callback,
                blocksize=1024,
                dtype='float32'
            )
            
            self.playback_stream.start()
            
        except Exception as e:
            print(f"Playback error: {e}")
            self.is_playing = False
            self.playbackStopped.emit()
            
    def set_global_selection(self, start, end):
        """Set global selection across all tracks"""
        self.global_selection = (start, end)
        
        # Apply to all tracks
        for track in self.tracks:
            if track.waveform_canvas:
                track.waveform_canvas.set_selection(start, end)
                
        # Emit signal
        self.selectionChanged.emit(start, end)
        
    def get_max_duration(self):
        """Get the maximum duration across all tracks"""
        if not self.tracks:
            return 0.0
            
        return max(
            (t.waveform_canvas.max_time if t.waveform_canvas else 0.0)
            for t in self.tracks
        )
