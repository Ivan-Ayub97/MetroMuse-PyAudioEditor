import time
import psutil
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from error_handler import get_error_handler

@dataclass
class PerformanceMetrics:
    """Data class to store performance metrics"""
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    audio_buffer_size: int = 1024
    audio_latency_ms: float = 0.0
    active_tracks: int = 0
    is_playing: bool = False
    waveform_render_time_ms: float = 0.0
    
class PerformanceMonitor(QObject):
    """
    Monitors system performance and provides optimization recommendations
    for MetroMuse audio editing operations.
    """
    
    # Signals
    metricsUpdated = pyqtSignal(object)  # PerformanceMetrics object
    warningIssued = pyqtSignal(str, str)  # Warning type, warning message
    recommendationIssued = pyqtSignal(str, str)  # Recommendation type, recommendation message
    
    def __init__(self, parent=None, update_interval_ms=1000):
        super().__init__(parent)
        self.error_handler = get_error_handler()
        self.update_interval = update_interval_ms
        self.monitoring_enabled = False
        
        # Performance history (keep last 60 measurements)
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history_size = 60
        
        # Thresholds for warnings
        self.cpu_warning_threshold = 80.0  # %
        self.memory_warning_threshold = 85.0  # %
        self.memory_critical_threshold = 95.0  # %
        
        # Optimization settings
        self.optimization_callbacks: Dict[str, Callable] = {}
        
        # Timer for periodic monitoring
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._collect_metrics)
        
        # Performance optimization flags
        self.performance_mode = "balanced"  # "performance", "balanced", "quality"
        
    def start_monitoring(self):
        """Start performance monitoring"""
        if not self.monitoring_enabled:
            self.monitoring_enabled = True
            self.monitor_timer.start(self.update_interval)
            self.error_handler.log_info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        if self.monitoring_enabled:
            self.monitoring_enabled = False
            self.monitor_timer.stop()
            self.error_handler.log_info("Performance monitoring stopped")
    
    def _collect_metrics(self):
        """Collect current performance metrics"""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            
            # Create metrics object
            metrics = PerformanceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024)
            )
            
            # Add to history
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history.pop(0)
            
            # Check for warnings
            self._check_performance_warnings(metrics)
            
            # Emit updated metrics
            self.metricsUpdated.emit(metrics)
            
        except Exception as e:
            self.error_handler.log_error(f"Error collecting performance metrics: {str(e)}")
    
    def _check_performance_warnings(self, metrics: PerformanceMetrics):
        """Check metrics for performance issues and emit warnings"""
        # CPU warnings
        if metrics.cpu_percent > self.cpu_warning_threshold:
            if metrics.cpu_percent > 95:
                self.warningIssued.emit(
                    "Critical CPU Usage",
                    f"CPU usage is at {metrics.cpu_percent:.1f}%. Consider reducing audio quality or track count."
                )
                self._recommend_cpu_optimization()
            else:
                self.warningIssued.emit(
                    "High CPU Usage", 
                    f"CPU usage is high ({metrics.cpu_percent:.1f}%). Performance may be affected."
                )
        
        # Memory warnings
        if metrics.memory_percent > self.memory_critical_threshold:
            self.warningIssued.emit(
                "Critical Memory Usage",
                f"Memory usage is at {metrics.memory_percent:.1f}%. Application may become unstable."
            )
            self._recommend_memory_optimization()
        elif metrics.memory_percent > self.memory_warning_threshold:
            self.warningIssued.emit(
                "High Memory Usage",
                f"Memory usage is high ({metrics.memory_percent:.1f}%). Consider closing other applications."
            )
    
    def _recommend_cpu_optimization(self):
        """Provide CPU optimization recommendations"""
        recommendations = [
            "Consider switching to Performance Mode for reduced CPU usage",
            "Reduce the number of active audio tracks",
            "Lower audio quality settings if possible",
            "Close other applications to free up CPU resources"
        ]
        
        for rec in recommendations:
            self.recommendationIssued.emit("CPU Optimization", rec)
    
    def _recommend_memory_optimization(self):
        """Provide memory optimization recommendations"""
        recommendations = [
            "Close unused tracks to free memory",
            "Work with shorter audio files when possible",
            "Restart the application to clear memory leaks",
            "Close other applications to free up system memory"
        ]
        
        for rec in recommendations:
            self.recommendationIssued.emit("Memory Optimization", rec)
    
    def set_performance_mode(self, mode: str):
        """
        Set performance mode: 'performance', 'balanced', or 'quality'
        
        Args:
            mode: The performance mode to set
        """
        if mode not in ["performance", "balanced", "quality"]:
            raise ValueError("Mode must be 'performance', 'balanced', or 'quality'")
        
        self.performance_mode = mode
        self.error_handler.log_info(f"Performance mode set to: {mode}")
        
        # Apply mode-specific optimizations
        if mode == "performance":
            self._apply_performance_optimizations()
        elif mode == "balanced":
            self._apply_balanced_optimizations()
        elif mode == "quality":
            self._apply_quality_optimizations()
    
    def _apply_performance_optimizations(self):
        """Apply optimizations for maximum performance"""
        optimizations = {
            "waveform_detail_level": "low",
            "audio_buffer_size": 2048,
            "real_time_effects": False,
            "waveform_antialiasing": False,
            "background_processing": True
        }
        
        for key, value in optimizations.items():
            if key in self.optimization_callbacks:
                self.optimization_callbacks[key](value)
    
    def _apply_balanced_optimizations(self):
        """Apply balanced optimizations"""
        optimizations = {
            "waveform_detail_level": "medium",
            "audio_buffer_size": 1024,
            "real_time_effects": True,
            "waveform_antialiasing": True,
            "background_processing": True
        }
        
        for key, value in optimizations.items():
            if key in self.optimization_callbacks:
                self.optimization_callbacks[key](value)
    
    def _apply_quality_optimizations(self):
        """Apply optimizations for maximum quality"""
        optimizations = {
            "waveform_detail_level": "high",
            "audio_buffer_size": 512,
            "real_time_effects": True,
            "waveform_antialiasing": True,
            "background_processing": False
        }
        
        for key, value in optimizations.items():
            if key in self.optimization_callbacks:
                self.optimization_callbacks[key](value)
    
    def register_optimization_callback(self, setting_name: str, callback: Callable):
        """
        Register a callback function for performance optimizations
        
        Args:
            setting_name: Name of the setting to optimize
            callback: Function to call when optimization is applied
        """
        self.optimization_callbacks[setting_name] = callback
    
    def get_average_metrics(self, duration_seconds: int = 30) -> Optional[PerformanceMetrics]:
        """
        Get average performance metrics over the specified duration
        
        Args:
            duration_seconds: Duration to calculate average over
            
        Returns:
            Average metrics or None if insufficient data
        """
        if not self.metrics_history:
            return None
        
        # Filter metrics within the specified duration
        current_time = time.time()
        cutoff_time = current_time - duration_seconds
        
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return None
        
        # Calculate averages
        avg_metrics = PerformanceMetrics(
            timestamp=current_time,
            cpu_percent=sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
            memory_percent=sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
            memory_used_mb=sum(m.memory_used_mb for m in recent_metrics) / len(recent_metrics),
            memory_available_mb=sum(m.memory_available_mb for m in recent_metrics) / len(recent_metrics),
            audio_buffer_size=recent_metrics[-1].audio_buffer_size,  # Use latest
            audio_latency_ms=sum(m.audio_latency_ms for m in recent_metrics) / len(recent_metrics),
            active_tracks=recent_metrics[-1].active_tracks,  # Use latest
            is_playing=recent_metrics[-1].is_playing,  # Use latest
            waveform_render_time_ms=sum(m.waveform_render_time_ms for m in recent_metrics) / len(recent_metrics)
        )
        
        return avg_metrics
    
    def update_audio_metrics(self, buffer_size: int, latency_ms: float, active_tracks: int, is_playing: bool):
        """
        Update audio-specific performance metrics
        
        Args:
            buffer_size: Current audio buffer size
            latency_ms: Current audio latency in milliseconds
            active_tracks: Number of active audio tracks
            is_playing: Whether audio is currently playing
        """
        if self.metrics_history:
            latest = self.metrics_history[-1]
            latest.audio_buffer_size = buffer_size
            latest.audio_latency_ms = latency_ms
            latest.active_tracks = active_tracks
            latest.is_playing = is_playing
    
    def update_waveform_render_time(self, render_time_ms: float):
        """
        Update waveform rendering performance metrics
        
        Args:
            render_time_ms: Time taken to render waveform in milliseconds
        """
        if self.metrics_history:
            latest = self.metrics_history[-1]
            latest.waveform_render_time_ms = render_time_ms
    
    def get_performance_report(self) -> Dict[str, any]:
        """
        Generate a comprehensive performance report
        
        Returns:
            Dictionary containing performance analysis
        """
        if not self.metrics_history:
            return {"status": "No data available"}
        
        latest = self.metrics_history[-1]
        avg_30s = self.get_average_metrics(30)
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "performance_mode": self.performance_mode,
            "current_metrics": {
                "cpu_percent": latest.cpu_percent,
                "memory_percent": latest.memory_percent,
                "memory_used_mb": latest.memory_used_mb,
                "active_tracks": latest.active_tracks,
                "is_playing": latest.is_playing
            },
            "average_30s": {
                "cpu_percent": avg_30s.cpu_percent if avg_30s else 0,
                "memory_percent": avg_30s.memory_percent if avg_30s else 0,
                "waveform_render_time_ms": avg_30s.waveform_render_time_ms if avg_30s else 0
            } if avg_30s else None,
            "recommendations": self._generate_recommendations(latest, avg_30s)
        }
        
        return report
    
    def _generate_recommendations(self, current: PerformanceMetrics, average: Optional[PerformanceMetrics]) -> List[str]:
        """
        Generate performance recommendations based on current metrics
        
        Args:
            current: Current performance metrics
            average: Average performance metrics
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # CPU recommendations
        if current.cpu_percent > 80:
            recommendations.append("Consider reducing CPU usage by switching to Performance Mode")
            if current.active_tracks > 5:
                recommendations.append("Consider reducing the number of active tracks")
        
        # Memory recommendations
        if current.memory_percent > 80:
            recommendations.append("Memory usage is high - consider closing other applications")
            recommendations.append("Work with shorter audio files to reduce memory usage")
        
        # Audio performance recommendations
        if current.is_playing and current.audio_latency_ms > 50:
            recommendations.append("Audio latency is high - consider increasing buffer size")
        
        # Waveform rendering recommendations
        if average and average.waveform_render_time_ms > 100:
            recommendations.append("Waveform rendering is slow - consider reducing detail level")
        
        if not recommendations:
            recommendations.append("Performance is optimal - no recommendations at this time")
        
        return recommendations


class AudioBufferOptimizer:
    """
    Utility class for optimizing audio buffer sizes based on system performance
    """
    
    @staticmethod
    def calculate_optimal_buffer_size(sample_rate: int, target_latency_ms: float = 20.0) -> int:
        """
        Calculate optimal buffer size for given sample rate and target latency
        
        Args:
            sample_rate: Audio sample rate in Hz
            target_latency_ms: Target latency in milliseconds
            
        Returns:
            Optimal buffer size in samples
        """
        # Convert target latency to samples
        target_samples = int((target_latency_ms / 1000.0) * sample_rate)
        
        # Round to nearest power of 2 for optimal performance
        power_of_2 = 1
        while power_of_2 < target_samples:
            power_of_2 *= 2
        
        # Ensure minimum buffer size for stability
        min_buffer = 256
        max_buffer = 4096
        
        return max(min_buffer, min(max_buffer, power_of_2))
    
    @staticmethod
    def adapt_buffer_size_for_performance(current_buffer: int, cpu_percent: float, memory_percent: float) -> int:
        """
        Adapt buffer size based on current system performance
        
        Args:
            current_buffer: Current buffer size
            cpu_percent: Current CPU usage percentage
            memory_percent: Current memory usage percentage
            
        Returns:
            Recommended buffer size
        """
        # Increase buffer size if system is under stress
        if cpu_percent > 80 or memory_percent > 85:
            return min(4096, current_buffer * 2)
        
        # Decrease buffer size if system has plenty of resources
        elif cpu_percent < 50 and memory_percent < 70:
            return max(256, current_buffer // 2)
        
        # Keep current buffer size
        return current_buffer


# Global performance monitor instance
_performance_monitor = None

def get_performance_monitor():
    """Get the global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

