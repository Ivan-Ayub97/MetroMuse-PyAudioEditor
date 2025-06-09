import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtCore import Qt, pyqtSignal, QObject, QEvent
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QSizePolicy

# Constants for visualization
DARK_BG = '#232629'
DARK_FG = '#eef1f4'
ACCENT_COLOR = '#47cbff'
PLAYHEAD_COLOR = '#ff9cee'
GRID_COLOR = '#31343a'
SELECTION_COLOR = '#ffc14d'


class EnhancedWaveformCanvas(FigureCanvas):
    """
    Enhanced waveform display with scrubbing support, time grid, and advanced visualization.
    Extends the original WaveformCanvas with more interactive features.
    """
    # Signals for interaction
    positionClicked = pyqtSignal(float)  # Time position clicked in seconds
    positionDragged = pyqtSignal(float)  # Time position dragged to in seconds
    selectionChanged = pyqtSignal(float, float)  # Selection changed (start, end) in seconds
    zoomChanged = pyqtSignal(float, float)  # Visible range changed (start, end) in seconds
    
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots(facecolor=DARK_BG)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Configure the plot style
        self._style_axes()
        
        # Zoom & view state
        self._xmin = 0  # View start time (seconds)
        self._xmax = 1  # View end time (seconds)
        self.max_time = 1  # Total audio duration (seconds)
        
        # Selection state
        self.selection = None  # (start_time, end_time) in seconds or None
        self._is_selecting = False
        self._select_start = None
        
        # Playhead state
        self.playhead_position = 0  # Current playback position in seconds
        self.playhead_line = None  # The line object representing the playhead
        
        # Scrubbing state
        self._is_scrubbing = False
        self._last_scrub_pos = None
        
        # Grid and time markers
        self.grid_lines = []
        self.time_markers = []
        self.grid_visible = True
        
        # Live cursor and info display
        self.live_cursor_line = None
        self.live_cursor_text = None
        self.amplitude_label = None
        self.samples = None  # Cached audio data
        self.sr = None  # Sample rate
        
        # Connect mouse and key events
        self.mpl_connect("button_press_event", self.on_mouse_press)
        self.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.mpl_connect("button_release_event", self.on_mouse_release)
        self.mpl_connect("scroll_event", self.on_scroll)
        self.mpl_connect("key_press_event", self.on_key_press)
        
        # Store color theme
        self.waveform_color = ACCENT_COLOR
        self.playhead_color = PLAYHEAD_COLOR
        self.grid_color = GRID_COLOR
        self.selection_color = SELECTION_COLOR
        
        # Set size policy for better layout behavior
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(120)
        
    def _style_axes(self):
        """Apply visual styling to the axes for a modern dark theme"""
        self.ax.set_facecolor(DARK_BG)
        self.ax.tick_params(colors=DARK_FG, labelsize=9)
        
        # Style the spines (borders)
        for spine in self.ax.spines.values():
            spine.set_color(DARK_FG)
            spine.set_linewidth(0.5)
        
        # Set the figure background
        self.fig.patch.set_facecolor(DARK_BG)
        
        # Configure padding and layout
        self.fig.tight_layout(pad=0.5)
        
    def plot_waveform(self, samples, sr, color=None):
        """
        Plot audio waveform with enhanced visualization.
        Includes grid lines and keeps the current selection if any.
        
        Args:
            samples: Audio samples (numpy array)
            sr: Sample rate (Hz)
            color: Optional custom color for this waveform
        """
        self.samples = samples
        self.sr = sr
        
        # Store waveform color if provided
        if color:
            self.waveform_color = color
        
        # Clear the plot but keep axis settings
        self.ax.clear()
        self._style_axes()
        
        # Calculate time array and max time
        if samples.ndim > 1:
            samples_mono = samples.mean(axis=0)
        else:
            samples_mono = samples
            
        t = np.linspace(0, len(samples_mono) / sr, num=len(samples_mono))
        self.max_time = t[-1] if len(t) > 0 else 1
        
        # Set reasonable default view if current view is invalid
        if self._xmax <= self._xmin or self._xmax > self.max_time:
            self._xmin, self._xmax = 0, min(30, self.max_time)  # Show first 30 seconds by default
        
        # Plot the waveform with the specified color
        self.ax.plot(t, samples_mono, color=self.waveform_color, linewidth=0.8)
        
        # Set axis limits and labels
        self.ax.set_xlim([self._xmin, self._xmax])
        self.ax.set_ylim([-1.05, 1.05])
        self.ax.set_xlabel('Time (s)', color=DARK_FG, fontsize=9)
        self.ax.set_ylabel('Amplitude', color=DARK_FG, fontsize=9)
        
        # Draw time grid
        self._draw_time_grid()
        
        # Draw selection if present
        self._draw_selection()
        
        # Draw playhead
        self._draw_playhead()
        
        # Remove any existing cursor displays
        if self.live_cursor_line is not None:
            self.live_cursor_line.remove()
            self.live_cursor_line = None
        if self.live_cursor_text is not None:
            self.live_cursor_text.remove()
            self.live_cursor_text = None
            
        self.draw()
        
    def _draw_time_grid(self):
        """Draw adaptive time grid with time markers based on zoom level"""
        # Clear existing grid lines and markers
        for line in self.grid_lines:
            try:
                line.remove()
            except (ValueError, AttributeError):
                # Line might already be removed or not in the axes
                pass
        self.grid_lines = []
        
        for text in self.time_markers:
            try:
                text.remove()
            except (ValueError, AttributeError):
                # Text might already be removed or not in the axes
                pass
        self.time_markers = []
        
        if not self.grid_visible:
            return
            
        # Determine appropriate grid spacing based on zoom level
        view_span = self._xmax - self._xmin
        
        if view_span <= 5:  # <= 5 seconds visible: show 0.5 second grid
            grid_step = 0.5
            major_step = 1.0
        elif view_span <= 20:  # <= 20 seconds visible: show 1 second grid
            grid_step = 1.0
            major_step = 5.0
        elif view_span <= 60:  # <= 1 minute visible: show 5 second grid
            grid_step = 5.0
            major_step = 15.0
        elif view_span <= 300:  # <= 5 minutes visible: show 15 second grid
            grid_step = 15.0
            major_step = 60.0
        else:  # > 5 minutes: show 1 minute grid
            grid_step = 60.0
            major_step = 300.0
            
        # Get rounded start and end times for grid
        start_time = int(self._xmin / grid_step) * grid_step
        end_time = int(self._xmax / grid_step + 1) * grid_step
        
        # Draw vertical grid lines
        current_time = start_time
        while current_time <= end_time:
            # Skip if outside view
            if current_time < 0:
                current_time += grid_step
                continue
                
            # Determine if this is a major grid line
            is_major = (current_time % major_step) < 0.001 or abs(current_time % major_step - major_step) < 0.001
            
            # Draw the grid line with appropriate style
            line = self.ax.axvline(
                current_time, 
                color=self.grid_color,
                linestyle='-' if is_major else ':',
                linewidth=0.8 if is_major else 0.5,
                alpha=0.6 if is_major else 0.3,
                zorder=-1
            )
            self.grid_lines.append(line)
            
            # Add time marker text (only for major grid lines)
            if is_major and current_time >= 0:
                # Format time based on value
                if current_time >= 3600:  # >= 1 hour
                    time_str = f"{int(current_time/3600):02d}:{int((current_time%3600)/60):02d}:{int(current_time%60):02d}"
                elif current_time >= 60:  # >= 1 minute
                    time_str = f"{int(current_time/60):d}:{int(current_time%60):02d}"
                else:  # < 1 minute
                    time_str = f"{current_time:.1f}s" if grid_step < 1 else f"{int(current_time):d}s"
                    
                text = self.ax.text(
                    current_time, 
                    0.98,  # Position at top of y-axis
                    time_str,
                    fontsize=8,
                    color=DARK_FG,
                    alpha=0.8,
                    va='top',
                    ha='center',
                    bbox=dict(
                        boxstyle="round,pad=0.2",
                        facecolor=DARK_BG,
                        alpha=0.7,
                        edgecolor=self.grid_color,
                        linewidth=0.5
                    )
                )
                self.time_markers.append(text)
                
            current_time += grid_step
    
    def _draw_selection(self):
        """Draw the audio selection region"""
        # Remove previous selection patch if it exists
        if hasattr(self, "_sel_patch") and self._sel_patch:
            for patch in self._sel_patch:
                try:
                    patch.remove()
                except (ValueError, AttributeError):
                    # Patch might already be removed or not in the axes
                    pass
        self._sel_patch = []
        
        # Draw new selection if present
        if self.selection:
            from matplotlib.patches import Rectangle
            start, end = self.selection
            
            # Create the selection rectangle
            rect = Rectangle(
                (start, -1.05),
                end - start, 
                2.1,  # Full height of plot
                facecolor=self.selection_color,
                alpha=0.2,
                zorder=-1
            )
            self.ax.add_patch(rect)
            self._sel_patch.append(rect)
            
            # Add start and end markers
            for x in [start, end]:
                line = self.ax.axvline(
                    x,
                    color=self.selection_color,
                    linestyle='-',
                    linewidth=1.5,
                    alpha=0.8,
                    zorder=0
                )
                self._sel_patch.append(line)
                
            # Add selection time info at top
            duration = end - start
            if duration > 0:
                # Format selection time based on duration
                if duration >= 60:
                    time_str = f"{int(duration/60):d}m {int(duration%60):02d}s"
                else:
                    time_str = f"{duration:.2f}s"
                    
                text = self.ax.text(
                    (start + end) / 2,  # Center of selection
                    1.0,  # Top of plot
                    f"Selection: {time_str}",
                    fontsize=9,
                    color=DARK_FG,
                    weight='bold',
                    va='top',
                    ha='center',
                    bbox=dict(
                        boxstyle="round,pad=0.3",
                        facecolor=self.selection_color,
                        alpha=0.4,
                        edgecolor=None
                    )
                )
                self._sel_patch.append(text)
    
    def _draw_playhead(self):
        """Draw the playhead indicator line"""
        # Remove previous playhead
        if self.playhead_line is not None:
            try:
                self.playhead_line.remove()
            except (ValueError, AttributeError):
                # Playhead line might already be removed or not in the axes
                pass
            
        # Draw new playhead
        self.playhead_line = self.ax.axvline(
            self.playhead_position,
            color=self.playhead_color,
            linestyle='-',
            linewidth=2,
            alpha=0.9,
            zorder=10
        )
    
    def update_playhead(self, position):
        """Update the playhead position and redraw"""
        # Store new position
        self.playhead_position = position
        
        # Check if we need to scroll the view to follow the playhead
        view_width = self._xmax - self._xmin
        needs_scroll = (position < self._xmin or position > self._xmax)
        
        # Auto-scroll if playhead moves outside visible area
        if needs_scroll:
            # Center the view on the playhead
            half_width = view_width / 2
            self._xmin = max(0, position - half_width)
            self._xmax = min(self.max_time, position + half_width)
            self.ax.set_xlim([self._xmin, self._xmax])
            
            # Emit signal that view changed
            self.zoomChanged.emit(self._xmin, self._xmax)
        
        # Redraw the playhead
        self._draw_playhead()
        self.draw()
    
    def set_selection(self, start, end):
        """Set selection region in seconds"""
        if start > end:
            start, end = end, start
            
        # Bound selection to valid range
        start = max(0, min(start, self.max_time))
        end = max(0, min(end, self.max_time))
        
        self.selection = (start, end)
        self._draw_selection()
        self.draw()
        
        # Emit selection changed signal
        self.selectionChanged.emit(start, end)
    
    def clear_selection(self):
        """Clear the selection"""
        self.selection = None
        self._draw_selection()
        self.draw()
        
    def zoom(self, factor=0.5, center=None):
        """
        Zoom in/out centered on a specific point or the current view center.
        
        Args:
            factor: Zoom factor (0.5 = zoom in to half the width, 2.0 = zoom out to twice the width)
            center: Time point to center on (in seconds), or None to use current view center
        """
        # Get current view
        view_width = self._xmax - self._xmin
        
        # Determine center point for zoom
        if center is None:
            center = (self._xmin + self._xmax) / 2
        
        # Calculate new view width
        new_width = view_width * factor
        
        # Prevent zooming in too far (minimum 0.1 seconds) or out too far (maximum = track length)
        new_width = max(0.1, min(new_width, self.max_time))
        
        # Calculate new view bounds centered on the specified position
        half_width = new_width / 2
        new_xmin = max(0, center - half_width)
        new_xmax = min(self.max_time, center + half_width)
        
        # Adjust if we hit the boundaries
        if new_xmin <= 0:
            new_xmax = min(self.max_time, new_width)
        if new_xmax >= self.max_time:
            new_xmin = max(0, self.max_time - new_width)
        
        # Update the view
        self._xmin, self._xmax = new_xmin, new_xmax
        self.ax.set_xlim([self._xmin, self._xmax])
        
        # Update grid based on new zoom level
        self._draw_time_grid()
        self._draw_selection()
        self._draw_playhead()
        self.draw()
        
        # Emit signal that view changed
        self.zoomChanged.emit(self._xmin, self._xmax)
    
    def pan(self, offset):
        """
        Pan view by offset seconds.
        
        Args:
            offset: Pan amount in seconds (positive = right, negative = left)
        """
        # Get current view width
        view_width = self._xmax - self._xmin
        
        # Calculate new bounds
        new_xmin = max(0, self._xmin + offset)
        new_xmax = min(self.max_time, self._xmax + offset)
        
        # Adjust if we hit boundaries, maintaining view width
        if new_xmin <= 0:
            new_xmin = 0
            new_xmax = min(self.max_time, view_width)
        elif new_xmax >= self.max_time:
            new_xmax = self.max_time
            new_xmin = max(0, self.max_time - view_width)
        
        # Update the view
        self._xmin, self._xmax = new_xmin, new_xmax
        self.ax.set_xlim([self._xmin, self._xmax])
        
        # Update grid and redraw
        self._draw_time_grid()
        self.draw()
        
        # Emit signal that view changed
        self.zoomChanged.emit(self._xmin, self._xmax)
    
    # Event handlers
    def on_mouse_press(self, event):
        """Handle mouse press events for selection and scrubbing"""
        if event.inaxes != self.ax:
            return
            
        # Get time position from x-coordinate
        time_pos = event.xdata
        
        # Determine action based on mouse button
        if event.button == 1:  # Left button
            if event.key == 'shift':
                # Shift+Click: Position playhead
                self.playhead_position = time_pos
                self._draw_playhead()
                self.draw()
                self.positionClicked.emit(time_pos)
                return
                
            # Start selection
            self._is_selecting = True
            self._select_start = time_pos
            self.set_selection(time_pos, time_pos)  # Start with empty selection
            
        elif event.button == 2:  # Middle button
            # Start scrubbing
            self._is_scrubbing = True
            self._last_scrub_pos = time_pos
            self.playhead_position = time_pos
            self._draw_playhead()
            self.draw()
            self.positionClicked.emit(time_pos)
    
    def on_mouse_move(self, event):
        """Handle mouse move events for selection, scrubbing, and cursor tracking"""
        # Handle selection dragging
        if self._is_selecting and event.inaxes == self.ax and self._select_start is not None:
            if event.xdata is not None:
                self.set_selection(self._select_start, event.xdata)
        
        # Handle scrubbing
        elif self._is_scrubbing and event.inaxes == self.ax:
            if event.xdata is not None:
                self.playhead_position = max(0, min(event.xdata, self.max_time))
                self._draw_playhead()
                self.draw()
                self.positionDragged.emit(self.playhead_position)
                self._last_scrub_pos = event.xdata
        
        # Update cursor info display
        else:
            self._update_cursor_info(event)
    
    def on_mouse_release(self, event):
        """Handle mouse release events for selection and scrubbing"""
        # Handle selection completion
        if self._is_selecting and event.inaxes == self.ax and self._select_start is not None:
            if event.xdata is not None:
                self.set_selection(self._select_start, event.xdata)
            self._is_selecting = False
            
        # Handle scrubbing end
        elif self._is_scrubbing:
            if event.xdata is not None and event.inaxes == self.ax:
                self.playhead_position = max(0, min(event.xdata, self.max_time))
                self._draw_playhead()
                self.draw()
                self.positionDragged.emit(self.playhead_position)
            self._is_scrubbing = False
            self._last_scrub_pos = None
    
    def on_scroll(self, event):
        """Handle mouse scroll events for zooming"""
        # Only handle scroll in the plot area
        if event.inaxes != self.ax:
            return
            
        # Determine zoom direction and factor
        if event.button == 'up':  # Scroll up = zoom in
            factor = 0.5
        else:  # Scroll down = zoom out
            factor = 2.0
            
        # Zoom centered on the scroll position
        self.zoom(factor, center=event.xdata)
    
    def on_key_press(self, event):
        """Handle keyboard events for navigation and selection"""
        if event.key == 'left':  # Left arrow = pan left
            shift_pressed = event.key.startswith('shift')
            self.pan(-5.0 if shift_pressed else -1.0)
            
        elif event.key == 'right':  # Right arrow = pan right
            shift_pressed = event.key.startswith('shift')
            self.pan(5.0 if shift_pressed else 1.0)
            
        elif event.key == 'up':  # Up arrow = zoom in
            self.zoom(0.5)
            
        elif event.key == 'down':  # Down arrow = zoom out
            self.zoom(2.0)
            
        elif event.key == 'home':  # Home = go to start
            self.pan(-self.max_time)  # Pan all the way left
            
        elif event.key == 'end':  # End = go to end
            self.pan(self.max_time)  # Pan all the way right
            
        elif event.key == 'escape':  # Escape = clear selection
            self.clear_selection()
    
    def _update_cursor_info(self, event):
        """Update cursor information display with time and amplitude"""
        # Remove previous cursor markers
        if self.live_cursor_line is not None:
            try:
                self.live_cursor_line.remove()
            except (ValueError, AttributeError):
                pass
            self.live_cursor_line = None
            
        if self.live_cursor_text is not None:
            try:
                self.live_cursor_text.remove()
            except (ValueError, AttributeError):
                pass
            self.live_cursor_text = None
        
        # Only proceed if cursor is in the plot area
        if event.inaxes != self.ax or event.xdata is None:
            self.draw()
            return
            
        # Get time position
        t_cursor = event.xdata
        
        # Create vertical cursor line
        self.live_cursor_line = self.ax.axvline(
            t_cursor,
            color="#ffe658",
            alpha=0.45,
            linewidth=1.2,
            zorder=5
        )
        
        # Display time and amplitude if we have audio data
        if self.samples is not None and self.sr is not None and 0 <= t_cursor < self.max_time:
            # Find the sample closest to cursor position
            sample_idx = int(t_cursor * self.sr)
            if sample_idx < len(self.samples[0] if self.samples.ndim > 1 else self.samples):
                # Extract amplitude value
                if self.samples.ndim > 1:
                    val = self.samples[0, sample_idx]
                else:
                    val = self.samples[sample_idx]
                    
                # Format time and amplitude text
                if t_cursor >= 60:
                    time_str = f"{int(t_cursor/60):d}:{int(t_cursor%60):02d}.{int((t_cursor*1000)%1000):03d}"
                else:
                    time_str = f"{t_cursor:.3f}s"
                    
                txt = f"{time_str}, amp {val:+.3f}"
            else:
                txt = f"{t_cursor:.3f}s"
        else:
            txt = f"{t_cursor:.3f}s"
            
        # Create text label with time/amplitude info
        self.live_cursor_text = self.ax.text(
            t_cursor,
            1,  # Top of y-axis
            txt,
            va="bottom",
            ha="left",
            fontsize=9,
            color="#ffee88",
            bbox=dict(
                facecolor="#292a24",
                edgecolor="none",
                alpha=0.8,
                pad=1
            )
        )
        
        # Redraw to show the cursor info
        self.draw()
        
    def toggle_grid(self):
        """Toggle grid visibility"""
        self.grid_visible = not self.grid_visible
        if self.grid_visible:
            self._draw_time_grid()
        else:
            # Clear existing grid lines and markers
            for line in self.grid_lines:
                try:
                    line.remove()
                except (ValueError, AttributeError):
                    pass
            self.grid_lines = []
            
            for text in self.time_markers:
                try:
                    text.remove()
                except (ValueError, AttributeError):
                    pass
            self.time_markers = []
        
        self.draw()

    def set_color_theme(self, waveform_color=None, playhead_color=None, grid_color=None, selection_color=None):
        """Update the color theme for the waveform display"""
        if waveform_color:
            self.waveform_color = waveform_color
        if playhead_color:
            self.playhead_color = playhead_color
        if grid_color:
            self.grid_color = grid_color
        if selection_color:
            self.selection_color = selection_color
            
        # Redraw with new colors (if we have data)
        if self.samples is not None and self.sr is not None:
            self.plot_waveform(self.samples, self.sr)
