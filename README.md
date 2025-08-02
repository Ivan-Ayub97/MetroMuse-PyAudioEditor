# ![MetroMuse](Banner.png)

<div align="center">
 
# **MetroMuse – PyAudioEditor**

### Version 0.12.0 — *INCOMPLETE BETA*

> ⚠️ **Disclaimer:** *MetroMuse is currently in beta. Some features may be incomplete, unstable, or under development.*

---

## 🎵 What is MetroMuse?

**MetroMuse** is a **modern, cross-platform audio editor** featuring:

* Multitrack capabilities
* Enhanced waveform visualization
* An intuitive, sleek interface built for creators

---

## ✨ Features Overview

### 🎚️ Multitrack Support

* Solo, mute, and volume per track
* Color coding & track naming
* Synchronized playback
* **NEW:** Asynchronous audio loading
* **NEW:** Optimized waveform rendering

### 📊 Waveform Visualization

* Zoomable, interactive display
* Adaptive time grids & real-time amplitude
* **NEW:** Automatic downsampling
* **NEW:** Performance-based detail levels

### ✂️ Editing Tools

* Cut, copy, paste with precision
* Non-destructive edits & track-specific editing
* **NEW:** Enhanced keyboard shortcuts
* **NEW:** Improved error recovery

### 💾 Project System

* **NEW:** `.mmp` project save/load
* **NEW:** Recent projects manager
* **NEW:** Auto-save & change tracking
* **NEW:** Project templates/presets

### 🔧 Performance Monitoring

* **NEW:** Real-time CPU/RAM usage
* **NEW:** Quality/Performance modes
* **NEW:** System optimization engine

### 🛡️ Error Handling

* **NEW:** Detailed logging system
* **NEW:** User-friendly error dialogs
* **NEW:** Auto recovery & warning prompts

### 🎛️ Audio Effects

* Volume, fade in/out, preview in real-time
* Per-track effect control

### ▶️ Playback

* Scrubbing & synced playback
* **NEW:** Optimized multitrack engine

### 🎨 UI/UX

* Dark theme, high-contrast icons (48×48 px)
* **NEW:** Context-aware window title
* **NEW:** Streamlined shortcuts

### 💾 File Formats

* Supports WAV, MP3, AAC, FLAC
* Drag-and-drop audio + metadata support
* **NEW:** Better format handling

### ⚙️ Technical Highlights

* Sample-accurate editing
* Real-time waveform rendering
* **NEW:** Memory-efficient processing
* **NEW:** Background tasking
* **NEW:** Smart resource management

---

## 🛠️ Development Status (v0.12.0)

| Component           | Status        | Notes                                   |
| ------------------- | ------------- | --------------------------------------- |
| Waveform Display    | 🟢 Enhanced   | Scrubbing, markers, optimized rendering |
| Multitrack System   | 🟢 Enhanced   | Full controls, async loading            |
| Editing Tools       | 🟢 Enhanced   | Undo/redo, improved interaction         |
| Project Management  | 🟢 New        | `.mmp` format, autosave, templates      |
| Error Handling      | 🟢 New        | Logging, dialogs, recovery              |
| Performance Monitor | 🟢 New        | Realtime CPU/memory usage               |
| Exporting           | 🟡 Functional | Supports WAV, MP3, AAC, FLAC            |
| Playback            | 🟡 Enhanced   | Real-time, multitrack improvements      |
| UI/UX               | 🟢 Enhanced   | Shortcuts, responsiveness, polish       |

---

## 📸 Interface Preview

### 🔹 New Icon

![Icon](src/icon.ico)

### 🔹 General UI

![General UI](Captures/General_UI.png)

### 🔹 Effects Options

![Effects Options](Captures/Effects_Options.png)

### 🔹 Quick Effects Menu

![Quick Effects](Captures/Quick_Effects.png)

### 🔹 Audio Effects Studio

![Audio Effects](Captures/Audio_Effects.png)
![Audio Effects 2](Captures/Audio_Effects2.png)
![Audio Effects 3](Captures/Audio_Effects3.png)

### 🔹 File & Edit Menus

![File Options](Captures/File_Options.png)
![Edit Options](Captures/Edit_Options.png)

### 🔹 View Menu

![View Options](Captures/View_Options.png)
![View Options 2](Captures/View_Options2.png.png)
![View Options 3](Captures/View_Options3.png.png)

### 🔹 Shortcuts & About

![Shortcuts](Captures/Shortcuts_UI.png)
![About](Captures/About_UI.png)

---

## 📦 Dependencies

### Core Libraries

* `PyQt5` (>=5.15.0)
* `numpy` (>=1.21.0)
* `matplotlib` (>=3.5.0)
* `pydub` (>=0.25.0)
* `librosa` (>=0.9.0)
* `sounddevice` (>=0.4.0)
* `scipy` (>=1.7.0)

### Optional Enhancements

* `psutil` (>=5.8.0) — system monitoring
* `PyQt5-stubs` — for development with type hinting

### External Tools

* **ffmpeg** — for MP3, AAC, FLAC support

  * Windows: binaries included in `resources/`
  * Linux/macOS: install via package manager or [ffmpeg.org](https://ffmpeg.org)

---

## 🚀 Installation

1. **Clone the repository:**

```bash
git clone https://github.com/Ivan-Ayub97/MetroMuse-AudioEditor.git
cd MetroMuse
```

2. **Install required Python packages:**

```bash
pip install -r requirements.txt
```

3. **Install ffmpeg (Windows):**

```bash
winget install ffmpeg
```

Then, copy `ffmpeg.exe`, `ffprobe.exe`, and `ffplay.exe` into the `resources/` folder.

---

## 🎮 Usage

### Launch the App

```bash
python src/metro_muse.py
```

### 🗂️ Project Shortcuts

| Action       | Shortcut     |
| ------------ | ------------ |
| New Project  | Ctrl+N       |
| Open Project | Ctrl+Shift+O |
| Save Project | Ctrl+S       |
| Save As      | Ctrl+Shift+S |

### 🎧 Audio Tasks

| Action       | Shortcut / Action                       |
| ------------ | --------------------------------------- |
| Import Audio | Ctrl+O / Drag-and-drop / "Import Audio" |
| Export Audio | Ctrl+E                                  |
| Add Track    | "+ Add Track"                           |
| Delete Track | Click "✕" in header                     |

### ⏯ Playback Controls

| Action       | Shortcut              |
| ------------ | --------------------- |
| Play/Pause   | Spacebar              |
| Stop         | Esc                   |
| Rewind       | Home                  |
| Fast Forward | End                   |
| Scrub        | Click + Drag Waveform |

### ✂️ Edit Commands

| Action | Shortcut |
| ------ | -------- |
| Cut    | Ctrl+X   |
| Copy   | Ctrl+C   |
| Paste  | Ctrl+V   |
| Undo   | Ctrl+Z   |
| Redo   | Ctrl+Y   |

### 🧭 Navigation

| Action    | Shortcut            |
| --------- | ------------------- |
| Zoom In   | Ctrl++ / Wheel Up   |
| Zoom Out  | Ctrl+- / Wheel Down |
| Pan Left  | ← Arrow             |
| Pan Right | → Arrow             |

---

## 🔥 Recent Enhancements (v0.12.0)

* ✅ `.mmp` project format with full save/load
* ✅ Auto-save with tracking
* ✅ Detailed error logging
* ✅ Real-time performance monitor
* ✅ Async audio file handling
* ✅ Memory-optimized waveform renderer
* ✅ Shortcut improvements

---

## 🚧 Upcoming Features

* Spectrum analyzer
* VST plugin support
* Track automation
* MIDI input
* Recording interface
* Effect chain manager
* Export profiles/settings
* In-app guides/tutorials
* Full theme customization

---

## ⚠️ Known Issues

* Exporting fails if `ffmpeg` isn’t properly set up
* Echo/reverb effect modules still in progress
* No VST support yet
* Performance dips with large files (>500MB)
* Preview lag possible on low-spec hardware

---

## 💻 System Requirements

* **Python**: 3.7+
* **FFmpeg**: Installed or placed in `resources/`
* See [Dependencies](#-dependencies) section above

---

## 🗂️ Project Structure

</div>

```
MetroMuse/
├── Captures/                      # Screenshots of the interface
│   └── ...                       
│
├── src/                           # Main source code
│   ├── metro_muse.py             # Main entry point
│   ├── audio_effects.py          # Audio processing effects
│   ├── error_handler.py          # Error handling utilities
│   ├── performance_monitor.py    # Performance tracking
│   ├── project_manager.py        # Project loading/saving logic
│   ├── track_manager.py          # Handles audio tracks
│   ├── track_renderer.py         # Track visualization or rendering
│   ├── ui_manager.py             # GUI management
│   ├── styles.qss                # Qt Style Sheet
│   ├── icon.png                  # App icon (PNG)
│   └── icon.ico                  # App icon (ICO)
│
├── resources/                    # Bundled third-party binaries
│   ├── ffmpeg.exe
│   ├── ffplay.exe
│   └── ffprobe.exe
│
├── requirements.txt              # Python dependencies
├── README.md                     # Project overview
├── CHANGELOG.md                  # Version history
├── LICENSE                       # License information
├── CODE_OF_CONDUCT.md           # Contributor behavior guidelines
├── CONTRIBUTING.md              # Guidelines for contributing
└── SECURITY.md                  # Security policies and contact

```
<div align="center">
---

## 🤝 Contributions

We welcome your help to improve MetroMuse!

1. Fork the repo
2. Create a new branch for your feature or fix
3. Submit a **pull request** with a clear description

💬 Bug reports, ideas, or questions?
📧 Contact: [negroayub97@gmail.com](mailto:negroayub97@gmail.com)

---

## 👤 Author

**Iván Eduardo Chavez Ayub**
🔗 [GitHub](https://github.com/Ivan-Ayub97)
📧 [negroayub97@gmail.com](mailto:negroayub97@gmail.com)
🛠️ Python, PyQt5, pydub, librosa

---

## 🌟 Why MetroMuse?

Because sometimes you just need a **simple, powerful editor that works**.
**MetroMuse** is built with **focus, clarity, and creativity in mind** — open-source, evolving, and creator-driven.
</div>
