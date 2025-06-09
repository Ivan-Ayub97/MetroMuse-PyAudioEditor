import numpy as np
import scipy.signal as signal
from scipy.interpolate import interp1d
from typing import Tuple, Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton,
    QGroupBox, QGridLayout, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QProgressBar, QTabWidget, QWidget, QFrame, QDialogButtonBox
)
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import Qt
from error_handler import get_error_handler


class AudioEffectProcessor:
    """
    Advanced audio effects processor with modern algorithms
    """
    
    @staticmethod
    def apply_reverb(samples: np.ndarray, sr: int, room_size: float = 0.5, 
                    damping: float = 0.5, wet_level: float = 0.3) -> np.ndarray:
        """
        Apply reverb effect using Schroeder reverb algorithm
        
        Args:
            samples: Audio samples
            sr: Sample rate
            room_size: Room size (0.0 - 1.0)
            damping: High frequency damping (0.0 - 1.0)
            wet_level: Wet/dry mix (0.0 - 1.0)
        """
        try:
            # Ensure samples are 2D
            if samples.ndim == 1:
                samples = samples[np.newaxis, :]
            
            channels, length = samples.shape
            output = np.zeros_like(samples)
            
            # Comb filter delays (in samples)
            comb_delays = [int(sr * delay) for delay in [0.0297, 0.0371, 0.0411, 0.0437]]
            comb_gains = [0.742, 0.733, 0.715, 0.697]
            
            # Allpass filter delays
            allpass_delays = [int(sr * delay) for delay in [0.005, 0.0168, 0.0298]]
            allpass_gains = [0.7, 0.7, 0.7]
            
            # Scale delays by room size
            comb_delays = [int(delay * (0.5 + room_size * 0.5)) for delay in comb_delays]
            allpass_delays = [int(delay * (0.5 + room_size * 0.5)) for delay in allpass_delays]
            
            for ch in range(channels):
                # Initialize delay lines
                comb_buffers = [np.zeros(delay) for delay in comb_delays]
                allpass_buffers = [np.zeros(delay) for delay in allpass_delays]
                comb_indices = [0] * len(comb_delays)
                allpass_indices = [0] * len(allpass_delays)
                
                reverb_signal = np.zeros(length)
                
                for i in range(length):
                    # Sum comb filter outputs
                    comb_sum = 0
                    for j, (buffer, delay, gain) in enumerate(zip(comb_buffers, comb_delays, comb_gains)):
                        if delay > 0:
                            delayed_sample = buffer[comb_indices[j]]
                            feedback = delayed_sample * gain * (1 - damping)
                            buffer[comb_indices[j]] = samples[ch, i] + feedback
                            comb_sum += delayed_sample
                            comb_indices[j] = (comb_indices[j] + 1) % delay
                    
                    # Apply allpass filters
                    allpass_out = comb_sum
                    for j, (buffer, delay, gain) in enumerate(zip(allpass_buffers, allpass_delays, allpass_gains)):
                        if delay > 0:
                            delayed_sample = buffer[allpass_indices[j]]
                            buffer[allpass_indices[j]] = allpass_out + delayed_sample * gain
                            allpass_out = delayed_sample - allpass_out * gain
                            allpass_indices[j] = (allpass_indices[j] + 1) % delay
                    
                    reverb_signal[i] = allpass_out
                
                # Mix wet and dry signals
                output[ch] = samples[ch] * (1 - wet_level) + reverb_signal * wet_level
            
            return output if samples.ndim > 1 else output[0]
            
        except Exception as e:
            get_error_handler().log_error(f"Error applying reverb: {str(e)}")
            return samples
    
    @staticmethod
    def apply_echo(samples: np.ndarray, sr: int, delay_ms: float = 300, 
                  feedback: float = 0.3, wet_level: float = 0.5) -> np.ndarray:
        """
        Apply echo effect
        
        Args:
            samples: Audio samples
            sr: Sample rate
            delay_ms: Echo delay in milliseconds
            feedback: Feedback amount (0.0 - 0.9)
            wet_level: Wet/dry mix (0.0 - 1.0)
        """
        try:
            if samples.ndim == 1:
                samples = samples[np.newaxis, :]
            
            channels, length = samples.shape
            delay_samples = int(sr * delay_ms / 1000)
            
            if delay_samples <= 0 or delay_samples >= length:
                return samples if samples.ndim > 1 else samples[0]
            
            output = np.zeros_like(samples)
            
            for ch in range(channels):
                delay_buffer = np.zeros(delay_samples)
                delay_index = 0
                
                for i in range(length):
                    # Get delayed sample
                    delayed_sample = delay_buffer[delay_index]
                    
                    # Calculate output with feedback
                    echo_sample = samples[ch, i] + delayed_sample * feedback
                    
                    # Update delay buffer
                    delay_buffer[delay_index] = echo_sample
                    delay_index = (delay_index + 1) % delay_samples
                    
                    # Mix wet and dry
                    output[ch, i] = samples[ch, i] * (1 - wet_level) + echo_sample * wet_level
            
            return output if samples.ndim > 1 else output[0]
            
        except Exception as e:
            get_error_handler().log_error(f"Error applying echo: {str(e)}")
            return samples
    
    @staticmethod
    def apply_chorus(samples: np.ndarray, sr: int, rate: float = 1.5, 
                    depth: float = 0.02, voices: int = 3) -> np.ndarray:
        """
        Apply chorus effect
        
        Args:
            samples: Audio samples
            sr: Sample rate
            rate: LFO rate in Hz
            depth: Modulation depth in seconds
            voices: Number of chorus voices
        """
        try:
            if samples.ndim == 1:
                samples = samples[np.newaxis, :]
            
            channels, length = samples.shape
            output = np.copy(samples)
            
            max_delay = int(sr * depth * 2)
            
            for ch in range(channels):
                for voice in range(voices):
                    # Phase offset for each voice
                    phase_offset = (2 * np.pi * voice) / voices
                    
                    # Create delay line
                    delay_buffer = np.zeros(max_delay)
                    
                    for i in range(length):
                        # Calculate LFO value
                        lfo_phase = 2 * np.pi * rate * i / sr + phase_offset
                        lfo_value = np.sin(lfo_phase)
                        
                        # Calculate delay in samples
                        delay_time = depth * sr * (1 + lfo_value) / 2
                        delay_samples = int(delay_time)
                        
                        if delay_samples < max_delay and i >= delay_samples:
                            # Linear interpolation for fractional delay
                            frac = delay_time - delay_samples
                            delayed_sample = (delay_buffer[delay_samples] * (1 - frac) + 
                                            delay_buffer[min(delay_samples + 1, max_delay - 1)] * frac)
                            
                            output[ch, i] += delayed_sample * 0.3 / voices
                        
                        # Update delay buffer
                        if i < length - max_delay:
                            delay_buffer[i % max_delay] = samples[ch, i]
            
            return output if samples.ndim > 1 else output[0]
            
        except Exception as e:
            get_error_handler().log_error(f"Error applying chorus: {str(e)}")
            return samples
    
    @staticmethod
    def apply_parametric_eq(samples: np.ndarray, sr: int, 
                           low_gain: float = 0, mid_gain: float = 0, high_gain: float = 0,
                           low_freq: float = 200, mid_freq: float = 1000, high_freq: float = 5000,
                           q_factor: float = 1.0) -> np.ndarray:
        """
        Apply 3-band parametric equalizer
        
        Args:
            samples: Audio samples
            sr: Sample rate
            low_gain, mid_gain, high_gain: Gain in dB for each band
            low_freq, mid_freq, high_freq: Center frequencies for each band
            q_factor: Q factor for mid band
        """
        try:
            if samples.ndim == 1:
                samples = samples[np.newaxis, :]
            
            channels, length = samples.shape
            output = np.copy(samples)
            
            # Design filters for each band
            nyquist = sr / 2
            
            for ch in range(channels):
                signal_data = samples[ch]
                
                # Low shelf filter
                if abs(low_gain) > 0.1:
                    low_sos = signal.iirfilter(2, low_freq/nyquist, btype='lowpass', 
                                             ftype='butter', output='sos')
                    low_filtered = signal.sosfilt(low_sos, signal_data)
                    gain_linear = 10 ** (low_gain / 20)
                    signal_data = signal_data + (low_filtered - signal_data) * (gain_linear - 1)
                
                # Mid peaking filter
                if abs(mid_gain) > 0.1:
                    # Create peaking filter
                    w0 = 2 * np.pi * mid_freq / sr
                    alpha = np.sin(w0) / (2 * q_factor)
                    A = 10 ** (mid_gain / 40)
                    
                    # Peaking EQ coefficients
                    b0 = 1 + alpha * A
                    b1 = -2 * np.cos(w0)
                    b2 = 1 - alpha * A
                    a0 = 1 + alpha / A
                    a1 = -2 * np.cos(w0)
                    a2 = 1 - alpha / A
                    
                    # Normalize
                    b = [b0/a0, b1/a0, b2/a0]
                    a = [1, a1/a0, a2/a0]
                    
                    signal_data = signal.lfilter(b, a, signal_data)
                
                # High shelf filter
                if abs(high_gain) > 0.1:
                    high_sos = signal.iirfilter(2, high_freq/nyquist, btype='highpass', 
                                              ftype='butter', output='sos')
                    high_filtered = signal.sosfilt(high_sos, signal_data)
                    gain_linear = 10 ** (high_gain / 20)
                    signal_data = signal_data + (high_filtered - signal_data) * (gain_linear - 1)
                
                output[ch] = signal_data
            
            return output if samples.ndim > 1 else output[0]
            
        except Exception as e:
            get_error_handler().log_error(f"Error applying EQ: {str(e)}")
            return samples
    
    @staticmethod
    def apply_compressor(samples: np.ndarray, sr: int, threshold: float = -12, 
                        ratio: float = 4, attack_ms: float = 5, release_ms: float = 50) -> np.ndarray:
        """
        Apply dynamic range compressor
        
        Args:
            samples: Audio samples
            sr: Sample rate
            threshold: Threshold in dB
            ratio: Compression ratio
            attack_ms: Attack time in milliseconds
            release_ms: Release time in milliseconds
        """
        try:
            if samples.ndim == 1:
                samples = samples[np.newaxis, :]
            
            channels, length = samples.shape
            output = np.zeros_like(samples)
            
            # Convert times to coefficients
            attack_coef = np.exp(-1 / (sr * attack_ms / 1000))
            release_coef = np.exp(-1 / (sr * release_ms / 1000))
            threshold_linear = 10 ** (threshold / 20)
            
            for ch in range(channels):
                envelope = 0
                
                for i in range(length):
                    # Calculate envelope
                    input_level = abs(samples[ch, i])
                    if input_level > envelope:
                        envelope = input_level + (envelope - input_level) * attack_coef
                    else:
                        envelope = input_level + (envelope - input_level) * release_coef
                    
                    # Calculate gain reduction
                    if envelope > threshold_linear:
                        gain_reduction = threshold_linear + (envelope - threshold_linear) / ratio
                        gain_reduction = gain_reduction / envelope if envelope > 0 else 1
                    else:
                        gain_reduction = 1
                    
                    # Apply compression
                    output[ch, i] = samples[ch, i] * gain_reduction
            
            return output if samples.ndim > 1 else output[0]
            
        except Exception as e:
            get_error_handler().log_error(f"Error applying compressor: {str(e)}")
            return samples


class ModernEffectsDialog(QDialog):
    """
    Modern, user-friendly effects dialog with real-time preview
    """
    
    def __init__(self, parent=None, samples=None, sr=None):
        super().__init__(parent)
        self.samples = samples
        self.sr = sr
        self.preview_samples = None
        self.processor = AudioEffectProcessor()
        
        self.setWindowTitle("Audio Effects - MetroMuse")
        self.setModal(True)
        self.resize(600, 500)
        
        # Apply modern dark theme
        self.setStyleSheet(self._get_modern_stylesheet())
        
        self.setup_ui()
        self.connect_signals()
    
    def _get_modern_stylesheet(self):
        return """
        QDialog {
            background-color: #1e1e1e;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        
        QTabWidget::pane {
            border: 1px solid #3d3d3d;
            border-radius: 8px;
            background-color: #2d2d2d;
        }
        
        QTabBar::tab {
            background-color: #3d3d3d;
            color: #ffffff;
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            min-width: 100px;
        }
        
        QTabBar::tab:selected {
            background-color: #0078d4;
            color: #ffffff;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #4d4d4d;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #3d3d3d;
            border-radius: 8px;
            margin-top: 1ex;
            padding-top: 15px;
            background-color: #2d2d2d;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 10px 0 10px;
            color: #0078d4;
        }
        
        QSlider::groove:horizontal {
            border: 1px solid #3d3d3d;
            height: 8px;
            background: #1e1e1e;
            border-radius: 4px;
        }
        
        QSlider::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0078d4, stop:1 #106ebe);
            border: 1px solid #0078d4;
            width: 18px;
            height: 18px;
            margin: -5px 0;
            border-radius: 9px;
        }
        
        QSlider::handle:horizontal:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1084d8, stop:1 #1378c8);
        }
        
        QSlider::sub-page:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0078d4, stop:1 #106ebe);
            border-radius: 4px;
        }
        
        QPushButton {
            background-color: #0078d4;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-weight: bold;
            min-width: 100px;
        }
        
        QPushButton:hover {
            background-color: #106ebe;
        }
        
        QPushButton:pressed {
            background-color: #005a9e;
        }
        
        QPushButton:disabled {
            background-color: #3d3d3d;
            color: #8d8d8d;
        }
        
        QLabel {
            color: #ffffff;
            font-size: 11px;
        }
        
        QCheckBox {
            color: #ffffff;
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 3px;
            border: 2px solid #3d3d3d;
            background-color: #1e1e1e;
        }
        
        QCheckBox::indicator:checked {
            background-color: #0078d4;
            border-color: #0078d4;
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMCAxMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEuNSA1TDQgNy41TDguNSAyLjUiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
        }
        
        QProgressBar {
            border: 2px solid #3d3d3d;
            border-radius: 5px;
            text-align: center;
            background-color: #1e1e1e;
        }
        
        QProgressBar::chunk {
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0078d4, stop:1 #106ebe);
            border-radius: 3px;
        }
        """
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Audio Effects Studio")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #0078d4; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Tab widget for different effect categories
        self.tab_widget = QTabWidget()
        
        # Time-based effects tab
        time_tab = self.create_time_effects_tab()
        self.tab_widget.addTab(time_tab, "🎵 Time Effects")
        
        # Frequency-based effects tab
        freq_tab = self.create_frequency_effects_tab()
        self.tab_widget.addTab(freq_tab, "🎛️ EQ & Filters")
        
        # Dynamics effects tab
        dynamics_tab = self.create_dynamics_effects_tab()
        self.tab_widget.addTab(dynamics_tab, "📊 Dynamics")
        
        layout.addWidget(self.tab_widget)
        
        # Preview section
        preview_group = QGroupBox("Real-time Preview")
        preview_layout = QHBoxLayout(preview_group)
        
        self.preview_button = QPushButton("🎧 Preview")
        self.preview_button.setEnabled(self.samples is not None)
        
        self.stop_preview_button = QPushButton("⏹ Stop")
        self.stop_preview_button.setEnabled(False)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        preview_layout.addWidget(self.preview_button)
        preview_layout.addWidget(self.stop_preview_button)
        preview_layout.addWidget(self.progress_bar)
        preview_layout.addStretch()
        
        layout.addWidget(preview_group)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Reset)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Reset).clicked.connect(self.reset_all)
        
        layout.addWidget(button_box)
    
    def create_time_effects_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Reverb section
        reverb_group = QGroupBox("🏛️ Reverb")
        reverb_layout = QGridLayout(reverb_group)
        
        self.reverb_enabled = QCheckBox("Enable Reverb")
        reverb_layout.addWidget(self.reverb_enabled, 0, 0, 1, 2)
        
        # Room size
        reverb_layout.addWidget(QLabel("Room Size:"), 1, 0)
        self.room_size_slider = QSlider(Qt.Horizontal)
        self.room_size_slider.setRange(0, 100)
        self.room_size_slider.setValue(50)
        self.room_size_label = QLabel("50%")
        reverb_layout.addWidget(self.room_size_slider, 1, 1)
        reverb_layout.addWidget(self.room_size_label, 1, 2)
        
        # Damping
        reverb_layout.addWidget(QLabel("Damping:"), 2, 0)
        self.damping_slider = QSlider(Qt.Horizontal)
        self.damping_slider.setRange(0, 100)
        self.damping_slider.setValue(50)
        self.damping_label = QLabel("50%")
        reverb_layout.addWidget(self.damping_slider, 2, 1)
        reverb_layout.addWidget(self.damping_label, 2, 2)
        
        # Wet level
        reverb_layout.addWidget(QLabel("Wet Level:"), 3, 0)
        self.reverb_wet_slider = QSlider(Qt.Horizontal)
        self.reverb_wet_slider.setRange(0, 100)
        self.reverb_wet_slider.setValue(30)
        self.reverb_wet_label = QLabel("30%")
        reverb_layout.addWidget(self.reverb_wet_slider, 3, 1)
        reverb_layout.addWidget(self.reverb_wet_label, 3, 2)
        
        layout.addWidget(reverb_group)
        
        # Echo section
        echo_group = QGroupBox("🔊 Echo")
        echo_layout = QGridLayout(echo_group)
        
        self.echo_enabled = QCheckBox("Enable Echo")
        echo_layout.addWidget(self.echo_enabled, 0, 0, 1, 2)
        
        # Delay time
        echo_layout.addWidget(QLabel("Delay (ms):"), 1, 0)
        self.echo_delay_slider = QSlider(Qt.Horizontal)
        self.echo_delay_slider.setRange(50, 1000)
        self.echo_delay_slider.setValue(300)
        self.echo_delay_label = QLabel("300ms")
        echo_layout.addWidget(self.echo_delay_slider, 1, 1)
        echo_layout.addWidget(self.echo_delay_label, 1, 2)
        
        # Feedback
        echo_layout.addWidget(QLabel("Feedback:"), 2, 0)
        self.echo_feedback_slider = QSlider(Qt.Horizontal)
        self.echo_feedback_slider.setRange(0, 90)
        self.echo_feedback_slider.setValue(30)
        self.echo_feedback_label = QLabel("30%")
        echo_layout.addWidget(self.echo_feedback_slider, 2, 1)
        echo_layout.addWidget(self.echo_feedback_label, 2, 2)
        
        # Wet level
        echo_layout.addWidget(QLabel("Wet Level:"), 3, 0)
        self.echo_wet_slider = QSlider(Qt.Horizontal)
        self.echo_wet_slider.setRange(0, 100)
        self.echo_wet_slider.setValue(50)
        self.echo_wet_label = QLabel("50%")
        echo_layout.addWidget(self.echo_wet_slider, 3, 1)
        echo_layout.addWidget(self.echo_wet_label, 3, 2)
        
        layout.addWidget(echo_group)
        
        # Chorus section
        chorus_group = QGroupBox("🌊 Chorus")
        chorus_layout = QGridLayout(chorus_group)
        
        self.chorus_enabled = QCheckBox("Enable Chorus")
        chorus_layout.addWidget(self.chorus_enabled, 0, 0, 1, 2)
        
        # Rate
        chorus_layout.addWidget(QLabel("Rate (Hz):"), 1, 0)
        self.chorus_rate_slider = QSlider(Qt.Horizontal)
        self.chorus_rate_slider.setRange(1, 50)
        self.chorus_rate_slider.setValue(15)
        self.chorus_rate_label = QLabel("1.5Hz")
        chorus_layout.addWidget(self.chorus_rate_slider, 1, 1)
        chorus_layout.addWidget(self.chorus_rate_label, 1, 2)
        
        # Depth
        chorus_layout.addWidget(QLabel("Depth:"), 2, 0)
        self.chorus_depth_slider = QSlider(Qt.Horizontal)
        self.chorus_depth_slider.setRange(1, 50)
        self.chorus_depth_slider.setValue(20)
        self.chorus_depth_label = QLabel("0.020s")
        chorus_layout.addWidget(self.chorus_depth_slider, 2, 1)
        chorus_layout.addWidget(self.chorus_depth_label, 2, 2)
        
        # Voices
        chorus_layout.addWidget(QLabel("Voices:"), 3, 0)
        self.chorus_voices_slider = QSlider(Qt.Horizontal)
        self.chorus_voices_slider.setRange(2, 8)
        self.chorus_voices_slider.setValue(3)
        self.chorus_voices_label = QLabel("3")
        chorus_layout.addWidget(self.chorus_voices_slider, 3, 1)
        chorus_layout.addWidget(self.chorus_voices_label, 3, 2)
        
        layout.addWidget(chorus_group)
        layout.addStretch()
        
        return widget
    
    def create_frequency_effects_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Parametric EQ section
        eq_group = QGroupBox("🎛️ 3-Band Parametric EQ")
        eq_layout = QGridLayout(eq_group)
        
        self.eq_enabled = QCheckBox("Enable EQ")
        eq_layout.addWidget(self.eq_enabled, 0, 0, 1, 4)
        
        # Low band
        eq_layout.addWidget(QLabel("Low Band:"), 1, 0)
        eq_layout.addWidget(QLabel("Freq (Hz):"), 2, 0)
        self.low_freq_slider = QSlider(Qt.Horizontal)
        self.low_freq_slider.setRange(20, 500)
        self.low_freq_slider.setValue(200)
        self.low_freq_label = QLabel("200Hz")
        eq_layout.addWidget(self.low_freq_slider, 2, 1)
        eq_layout.addWidget(self.low_freq_label, 2, 2)
        
        eq_layout.addWidget(QLabel("Gain (dB):"), 3, 0)
        self.low_gain_slider = QSlider(Qt.Horizontal)
        self.low_gain_slider.setRange(-200, 200)
        self.low_gain_slider.setValue(0)
        self.low_gain_label = QLabel("0dB")
        eq_layout.addWidget(self.low_gain_slider, 3, 1)
        eq_layout.addWidget(self.low_gain_label, 3, 2)
        
        # Mid band
        eq_layout.addWidget(QLabel("Mid Band:"), 4, 0)
        eq_layout.addWidget(QLabel("Freq (Hz):"), 5, 0)
        self.mid_freq_slider = QSlider(Qt.Horizontal)
        self.mid_freq_slider.setRange(200, 5000)
        self.mid_freq_slider.setValue(1000)
        self.mid_freq_label = QLabel("1000Hz")
        eq_layout.addWidget(self.mid_freq_slider, 5, 1)
        eq_layout.addWidget(self.mid_freq_label, 5, 2)
        
        eq_layout.addWidget(QLabel("Gain (dB):"), 6, 0)
        self.mid_gain_slider = QSlider(Qt.Horizontal)
        self.mid_gain_slider.setRange(-200, 200)
        self.mid_gain_slider.setValue(0)
        self.mid_gain_label = QLabel("0dB")
        eq_layout.addWidget(self.mid_gain_slider, 6, 1)
        eq_layout.addWidget(self.mid_gain_label, 6, 2)
        
        # High band
        eq_layout.addWidget(QLabel("High Band:"), 7, 0)
        eq_layout.addWidget(QLabel("Freq (Hz):"), 8, 0)
        self.high_freq_slider = QSlider(Qt.Horizontal)
        self.high_freq_slider.setRange(1000, 20000)
        self.high_freq_slider.setValue(5000)
        self.high_freq_label = QLabel("5000Hz")
        eq_layout.addWidget(self.high_freq_slider, 8, 1)
        eq_layout.addWidget(self.high_freq_label, 8, 2)
        
        eq_layout.addWidget(QLabel("Gain (dB):"), 9, 0)
        self.high_gain_slider = QSlider(Qt.Horizontal)
        self.high_gain_slider.setRange(-200, 200)
        self.high_gain_slider.setValue(0)
        self.high_gain_label = QLabel("0dB")
        eq_layout.addWidget(self.high_gain_slider, 9, 1)
        eq_layout.addWidget(self.high_gain_label, 9, 2)
        
        layout.addWidget(eq_group)
        layout.addStretch()
        
        return widget
    
    def create_dynamics_effects_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Compressor section
        comp_group = QGroupBox("📊 Compressor")
        comp_layout = QGridLayout(comp_group)
        
        self.comp_enabled = QCheckBox("Enable Compressor")
        comp_layout.addWidget(self.comp_enabled, 0, 0, 1, 2)
        
        # Threshold
        comp_layout.addWidget(QLabel("Threshold (dB):"), 1, 0)
        self.comp_threshold_slider = QSlider(Qt.Horizontal)
        self.comp_threshold_slider.setRange(-400, 0)
        self.comp_threshold_slider.setValue(-120)
        self.comp_threshold_label = QLabel("-12dB")
        comp_layout.addWidget(self.comp_threshold_slider, 1, 1)
        comp_layout.addWidget(self.comp_threshold_label, 1, 2)
        
        # Ratio
        comp_layout.addWidget(QLabel("Ratio:"), 2, 0)
        self.comp_ratio_slider = QSlider(Qt.Horizontal)
        self.comp_ratio_slider.setRange(10, 200)
        self.comp_ratio_slider.setValue(40)
        self.comp_ratio_label = QLabel("4:1")
        comp_layout.addWidget(self.comp_ratio_slider, 2, 1)
        comp_layout.addWidget(self.comp_ratio_label, 2, 2)
        
        # Attack
        comp_layout.addWidget(QLabel("Attack (ms):"), 3, 0)
        self.comp_attack_slider = QSlider(Qt.Horizontal)
        self.comp_attack_slider.setRange(1, 100)
        self.comp_attack_slider.setValue(5)
        self.comp_attack_label = QLabel("5ms")
        comp_layout.addWidget(self.comp_attack_slider, 3, 1)
        comp_layout.addWidget(self.comp_attack_label, 3, 2)
        
        # Release
        comp_layout.addWidget(QLabel("Release (ms):"), 4, 0)
        self.comp_release_slider = QSlider(Qt.Horizontal)
        self.comp_release_slider.setRange(10, 500)
        self.comp_release_slider.setValue(50)
        self.comp_release_label = QLabel("50ms")
        comp_layout.addWidget(self.comp_release_slider, 4, 1)
        comp_layout.addWidget(self.comp_release_label, 4, 2)
        
        layout.addWidget(comp_group)
        layout.addStretch()
        
        return widget
    
    def connect_signals(self):
        """Connect all slider signals to update labels"""
        # Time effects
        self.room_size_slider.valueChanged.connect(
            lambda v: self.room_size_label.setText(f"{v}%"))
        self.damping_slider.valueChanged.connect(
            lambda v: self.damping_label.setText(f"{v}%"))
        self.reverb_wet_slider.valueChanged.connect(
            lambda v: self.reverb_wet_label.setText(f"{v}%"))
        
        self.echo_delay_slider.valueChanged.connect(
            lambda v: self.echo_delay_label.setText(f"{v}ms"))
        self.echo_feedback_slider.valueChanged.connect(
            lambda v: self.echo_feedback_label.setText(f"{v}%"))
        self.echo_wet_slider.valueChanged.connect(
            lambda v: self.echo_wet_label.setText(f"{v}%"))
        
        self.chorus_rate_slider.valueChanged.connect(
            lambda v: self.chorus_rate_label.setText(f"{v/10:.1f}Hz"))
        self.chorus_depth_slider.valueChanged.connect(
            lambda v: self.chorus_depth_label.setText(f"{v/1000:.3f}s"))
        self.chorus_voices_slider.valueChanged.connect(
            lambda v: self.chorus_voices_label.setText(str(v)))
        
        # EQ
        self.low_freq_slider.valueChanged.connect(
            lambda v: self.low_freq_label.setText(f"{v}Hz"))
        self.low_gain_slider.valueChanged.connect(
            lambda v: self.low_gain_label.setText(f"{v/10:.1f}dB"))
        self.mid_freq_slider.valueChanged.connect(
            lambda v: self.mid_freq_label.setText(f"{v}Hz"))
        self.mid_gain_slider.valueChanged.connect(
            lambda v: self.mid_gain_label.setText(f"{v/10:.1f}dB"))
        self.high_freq_slider.valueChanged.connect(
            lambda v: self.high_freq_label.setText(f"{v}Hz"))
        self.high_gain_slider.valueChanged.connect(
            lambda v: self.high_gain_label.setText(f"{v/10:.1f}dB"))
        
        # Compressor
        self.comp_threshold_slider.valueChanged.connect(
            lambda v: self.comp_threshold_label.setText(f"{v/10:.1f}dB"))
        self.comp_ratio_slider.valueChanged.connect(
            lambda v: self.comp_ratio_label.setText(f"{v/10:.1f}:1"))
        self.comp_attack_slider.valueChanged.connect(
            lambda v: self.comp_attack_label.setText(f"{v}ms"))
        self.comp_release_slider.valueChanged.connect(
            lambda v: self.comp_release_label.setText(f"{v}ms"))
    
    def get_effect_parameters(self):
        """Get all effect parameters as a dictionary"""
        return {
            'reverb': {
                'enabled': self.reverb_enabled.isChecked(),
                'room_size': self.room_size_slider.value() / 100.0,
                'damping': self.damping_slider.value() / 100.0,
                'wet_level': self.reverb_wet_slider.value() / 100.0
            },
            'echo': {
                'enabled': self.echo_enabled.isChecked(),
                'delay_ms': self.echo_delay_slider.value(),
                'feedback': self.echo_feedback_slider.value() / 100.0,
                'wet_level': self.echo_wet_slider.value() / 100.0
            },
            'chorus': {
                'enabled': self.chorus_enabled.isChecked(),
                'rate': self.chorus_rate_slider.value() / 10.0,
                'depth': self.chorus_depth_slider.value() / 1000.0,
                'voices': self.chorus_voices_slider.value()
            },
            'eq': {
                'enabled': self.eq_enabled.isChecked(),
                'low_freq': self.low_freq_slider.value(),
                'low_gain': self.low_gain_slider.value() / 10.0,
                'mid_freq': self.mid_freq_slider.value(),
                'mid_gain': self.mid_gain_slider.value() / 10.0,
                'high_freq': self.high_freq_slider.value(),
                'high_gain': self.high_gain_slider.value() / 10.0
            },
            'compressor': {
                'enabled': self.comp_enabled.isChecked(),
                'threshold': self.comp_threshold_slider.value() / 10.0,
                'ratio': self.comp_ratio_slider.value() / 10.0,
                'attack_ms': self.comp_attack_slider.value(),
                'release_ms': self.comp_release_slider.value()
            }
        }
    
    def reset_all(self):
        """Reset all parameters to default values"""
        # Reset all checkboxes
        for checkbox in [self.reverb_enabled, self.echo_enabled, self.chorus_enabled, 
                        self.eq_enabled, self.comp_enabled]:
            checkbox.setChecked(False)
        
        # Reset all sliders to default values
        defaults = {
            self.room_size_slider: 50,
            self.damping_slider: 50,
            self.reverb_wet_slider: 30,
            self.echo_delay_slider: 300,
            self.echo_feedback_slider: 30,
            self.echo_wet_slider: 50,
            self.chorus_rate_slider: 15,
            self.chorus_depth_slider: 20,
            self.chorus_voices_slider: 3,
            self.low_freq_slider: 200,
            self.low_gain_slider: 0,
            self.mid_freq_slider: 1000,
            self.mid_gain_slider: 0,
            self.high_freq_slider: 5000,
            self.high_gain_slider: 0,
            self.comp_threshold_slider: -120,
            self.comp_ratio_slider: 40,
            self.comp_attack_slider: 5,
            self.comp_release_slider: 50
        }
        
        for slider, value in defaults.items():
            slider.setValue(value)

