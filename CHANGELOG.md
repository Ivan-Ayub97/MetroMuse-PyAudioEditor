# Changelog

All notable changes to this project will be documented in this file.

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
