# Changelog

All notable changes to this project will be documented in this file.

## [0.12.0] - 2025-06-09

### Added

- Full project save/load support with `.mmp` format
- Recent project manager
- Auto-save with modification tracking
- Project templates and presets
- Real-time performance monitor (CPU & RAM)
- Quality vs. performance modes
- System recommendations based on performance
- Detailed error logging and automatic recovery
- User-friendly error dialogs
- Asynchronous audio loading
- Automatic downsampling for waveform rendering
- Performance-based waveform detail levels
- Background resource management
- Improved keyboard shortcuts and shortcut system

### Changed

- Optimized multitrack mixing engine for playback
- Memory-efficient and optimized waveform rendering
- Editing system with better error recovery
- Polished UI with project-aware window title
- Improved file format handling and metadata display

### Fixed

- Better performance with large audio files
- Improved stability in real-time effect preview
- Fixes in editing and playback control synchronization
- Reduced memory usage during intensive tasks
- Better handling of ffmpeg-related errors

## [0.10.0] - 2025-04-28

### Added

- Multitrack support with synchronized playback and per-track controls (solo, mute, volume)
- Enhanced waveform display with adaptive time grid and scrubbing
- Real-time amplitude visualization
- Non-destructive editing (cut/copy/paste/trim per track)
- Undo/redo stack with snapshot-based restore
- Modern dark theme user interface with accessible large buttons
- Drag and drop audio file import
- Collapsible track headers and track color customization
- Effects: Gain adjustment, fade-in, fade-out with instant preview
- Export to WAV, FLAC, MP3, and AAC formats
- Recent files management in sidebar
- Efficient playback mixing with sounddevice
- Keyboard shortcuts for common editing and navigation operations

### Changed

- Redesigned interface (QSS flat design, large controls, SVG icon support)
- Improved error handling for missing dependencies and file IO
- File browser sidebar and menu bar enhancements for track management

### Fixed

- Playback synchronization for multitrack
- Selection synchronization and highlighting bugs
- Audio format compatibility issues

## [0.9.0] - 2025-04-22

### Added

- Initial release with basic waveform display
- Loading and playing single track audio files
- Basic editing: cut/copy/paste/trim
- Basic playback and export
