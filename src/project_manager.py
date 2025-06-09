import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QFileDialog


class ProjectManager(QObject):
    """
    Manages project save/load operations for MetroMuse.
    Handles serialization of tracks, settings, and project state.
    """
    
    projectSaved = pyqtSignal(str)  # Emits project file path
    projectLoaded = pyqtSignal(str)  # Emits project file path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project_path = None
        self.project_modified = False
        
    def create_new_project(self):
        """Create a new empty project"""
        self.current_project_path = None
        self.project_modified = False
        return {
            "version": "1.0",
            "name": "Untitled Project",
            "tracks": [],
            "settings": {
                "sample_rate": 44100,
                "bit_depth": 16,
                "global_volume": 1.0,
                "playback_position": 0.0
            },
            "metadata": {
                "created_date": None,
                "last_modified": None,
                "total_duration": 0.0
            }
        }
    
    def serialize_track(self, track) -> Dict[str, Any]:
        """Serialize a track object to a dictionary"""
        track_data = {
            "track_id": track.track_id,
            "name": track.name,
            "color": track.color.name() if track.color else None,
            "muted": track.muted,
            "soloed": track.soloed,
            "volume": track.volume,
            "filepath": track.filepath,
            "position": {
                "x": 0,  # Track position in timeline
                "y": 0   # Track vertical position
            },
            "effects": [],  # Placeholder for future effects
            "automation": {}  # Placeholder for automation data
        }
        
        # Only store file path, not actual audio data (for file size efficiency)
        # Audio data will be reloaded from file path when project is opened
        
        return track_data
    
    def save_project(self, tracks, settings=None, filepath=None):
        """Save current project to file"""
        try:
            # If no filepath provided, show save dialog
            if filepath is None:
                filepath, _ = QFileDialog.getSaveFileName(
                    None,
                    "Save Project",
                    "",
                    "MetroMuse Project Files (*.mmp);;All Files (*)"
                )
                if not filepath:
                    return False
            
            # Ensure .mmp extension
            if not filepath.endswith('.mmp'):
                filepath += '.mmp'
            
            # Create project data structure
            project_data = {
                "version": "1.0",
                "name": os.path.splitext(os.path.basename(filepath))[0],
                "tracks": [self.serialize_track(track) for track in tracks],
                "settings": settings or {
                    "sample_rate": 44100,
                    "bit_depth": 16,
                    "global_volume": 1.0,
                    "playback_position": 0.0
                },
                "metadata": {
                    "created_date": None,  # Will be set on first save
                    "last_modified": None,  # Will be updated on each save
                    "total_duration": max([t.waveform_canvas.max_time for t in tracks if t.waveform_canvas]) if tracks else 0.0
                }
            }
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            
            self.current_project_path = filepath
            self.project_modified = False
            self.projectSaved.emit(filepath)
            
            return True
            
        except Exception as e:
            QMessageBox.critical(None, "Save Error", f"Could not save project:\n{str(e)}")
            return False
    
    def load_project(self, filepath=None):
        """Load project from file"""
        try:
            # If no filepath provided, show open dialog
            if filepath is None:
                filepath, _ = QFileDialog.getOpenFileName(
                    None,
                    "Open Project",
                    "",
                    "MetroMuse Project Files (*.mmp);;All Files (*)"
                )
                if not filepath:
                    return None
            
            # Check if file exists
            if not os.path.exists(filepath):
                QMessageBox.warning(None, "File Not Found", f"Project file not found: {filepath}")
                return None
            
            # Load project data
            with open(filepath, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # Validate project data
            if not self._validate_project_data(project_data):
                QMessageBox.warning(None, "Invalid Project", "The project file appears to be corrupted or invalid.")
                return None
            
            self.current_project_path = filepath
            self.project_modified = False
            self.projectLoaded.emit(filepath)
            
            return project_data
            
        except json.JSONDecodeError:
            QMessageBox.critical(None, "Load Error", "The project file is corrupted or not a valid MetroMuse project.")
            return None
        except Exception as e:
            QMessageBox.critical(None, "Load Error", f"Could not load project:\n{str(e)}")
            return None
    
    def _validate_project_data(self, data):
        """Validate project data structure"""
        required_keys = ['version', 'tracks', 'settings']
        return all(key in data for key in required_keys)
    
    def save_project_as(self, tracks, settings=None):
        """Save project with new filename"""
        return self.save_project(tracks, settings, filepath=None)
    
    def is_project_modified(self):
        """Check if project has unsaved changes"""
        return self.project_modified
    
    def mark_project_modified(self):
        """Mark project as modified"""
        self.project_modified = True
    
    def get_current_project_name(self):
        """Get current project name"""
        if self.current_project_path:
            return os.path.splitext(os.path.basename(self.current_project_path))[0]
        return "Untitled Project"
    
    def get_recent_projects(self, max_count=10):
        """Get list of recent project files"""
        recent_projects_file = Path(__file__).resolve().parent / "recent_projects.json"
        try:
            if recent_projects_file.exists():
                with open(recent_projects_file, 'r') as f:
                    recent = json.load(f)
                    # Filter out non-existent files
                    return [p for p in recent if os.path.exists(p)][:max_count]
        except Exception:
            pass
        return []
    
    def add_to_recent_projects(self, filepath):
        """Add project to recent projects list"""
        recent_projects_file = Path(__file__).resolve().parent / "recent_projects.json"
        try:
            recent = self.get_recent_projects()
            if filepath in recent:
                recent.remove(filepath)
            recent.insert(0, filepath)
            recent = recent[:10]  # Keep only 10 most recent
            
            with open(recent_projects_file, 'w') as f:
                json.dump(recent, f)
        except Exception:
            pass

