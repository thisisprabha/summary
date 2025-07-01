# 🎤 Meeting Recorder - Native macOS App

A native macOS menu bar application for recording, transcribing, and summarizing meetings using your DietPi server with whisper.cpp.

## ✨ Features

- 🎤 **High-quality audio recording** (16kHz, 16-bit, Mono - optimized for Whisper)
- 📱 **Menu bar integration** - Always accessible from the status bar
- 🔴 **Visual recording indicators** - Know when you're recording
- 📊 **Real-time progress** - See transcription progress live
- 🔔 **Native notifications** - Summary ready notifications
- 📝 **Download transcripts** - Save full transcriptions locally
- ⚙️ **Settings panel** - Configure server URL and preferences
- 🔄 **Auto-updater** - Automatic app updates via Sparkle
- 🌐 **Cross-network support** - Works from office to access home server

## 🚀 Quick Start

### 1. Build the App

```bash
cd MeetingRecorderApp
./build.sh
```

### 2. Install

```bash
# Copy to Applications folder
cp -r MeetingRecorder.app /Applications/

# Or double-click MeetingRecorder.app to install
```

### 3. First Launch

1. **Launch the app** - It will appear in your menu bar as a microphone icon
2. **Allow microphone access** when prompted
3. **Configure server** - Click the microphone icon → Settings
4. **Set your DietPi server URL** (e.g., `http://192.168.31.58:9000`)
5. **Test connection** to verify everything works

## 🎯 How to Use

### Recording a Meeting

1. **Click** the microphone icon in your menu bar
2. **Select** "🔴 Start Recording"
3. **Speak** - The icon will turn red while recording
4. **Click** "⏹️ Stop Recording" when done
5. **Wait** - Processing happens automatically
6. **Get notified** when your summary is ready!

### Viewing Results

- **Recent Summaries** - Click "📋 Recent Summaries" in the menu
- **Download Transcripts** - Full transcriptions available for download
- **Copy Summary** - Quick copy to clipboard

## ⚙️ Configuration

### Server Settings
- **Server URL**: Your DietPi server address
- **Auto-process**: Automatic upload and processing
- **Notifications**: Summary ready alerts

### Audio Quality
- **Sample Rate**: 16kHz (optimal for Whisper)
- **Channels**: Mono (faster processing)
- **Format**: WAV PCM (best quality)

## 🔧 Technical Details

### System Requirements
- **macOS 13.0+** (Ventura or later)
- **Microphone access** permission
- **Network access** to your DietPi server

### Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Mac Menu Bar  │───▶│  DietPi Server   │───▶│  OpenAI/Local   │
│   Recording App │    │  (whisper.cpp)   │    │  Summarization  │
│                 │◀───│  Flask + Socket  │◀───│                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Dependencies
- **SwiftUI** - Modern Mac app UI
- **AVFoundation** - High-quality audio recording
- **Starscream** - WebSocket communication
- **Sparkle** - Automatic updates

## 🌐 Network Setup

### For Home Network Only
- No setup needed - just use local IP: `192.168.31.58:9000`

### For Remote Access (Office/Other WiFi)

#### Option 1: Port Forwarding
1. Login to your home router
2. Forward port `9000` to `192.168.31.58:9000`
3. Use your public IP in the app settings

#### Option 2: VPN (Recommended)
```bash
# On your DietPi server
dietpi-software install 172  # WireGuard VPN
# Follow setup instructions
```

#### Option 3: Cloud Tunnel
```bash
# On your DietPi server
ngrok http 9000
# Use the provided public URL
```

## 🔄 Auto-Updates

The app includes Sparkle framework for automatic updates:

1. **Automatic checks** - Daily update checks
2. **Secure updates** - Cryptographically signed
3. **Background downloads** - Non-intrusive
4. **User control** - Choose when to install

### Setting Up Update Server (Optional)
1. Create an appcast XML file
2. Host on your server
3. Update `SUFeedURL` in Info.plist
4. Generate signing keys for security

## 🛠️ Development

### Building from Source

```bash
# Clone the repository
git clone <your-repo>
cd MeetingRecorderApp

# Install dependencies (automatic with Swift Package Manager)
swift package resolve

# Build for development
swift build

# Build for release
swift build -c release

# Create app bundle
./build.sh

# Sign for distribution (optional)
./build.sh sign
```

### Project Structure
```
MeetingRecorderApp/
├── Package.swift           # Swift Package Manager config
├── Sources/
│   └── MeetingRecorderApp/
│       ├── main.swift      # App entry point
│       ├── AppDelegate.swift     # macOS app lifecycle
│       ├── MenuBarManager.swift  # Menu bar UI
│       ├── AudioManager.swift    # Recording logic
│       ├── NetworkManager.swift  # Server communication
│       ├── SettingsView.swift    # Settings UI
│       └── SummariesWindow.swift # Summaries UI
├── build.sh                # Build script
└── README.md              # This file
```

## 🐛 Troubleshooting

### Microphone Not Working
1. Check **System Settings → Privacy & Security → Microphone**
2. Ensure **Meeting Recorder** is enabled
3. Restart the app after granting permission

### Can't Connect to Server
1. **Test connection** in Settings
2. Check **server URL** format: `http://IP:9000`
3. Verify **DietPi server** is running
4. Check **network connectivity**

### No Audio Recorded
1. Select correct **input device** in System Settings
2. Check **microphone levels** in Audio MIDI Setup
3. Test with **other apps** to verify microphone works

### Processing Fails
1. Check **DietPi server logs**
2. Verify **whisper.cpp** is working
3. Test **manual upload** via web interface

## 📝 Changelog

### Version 1.0.0
- ✅ Initial release
- ✅ Menu bar recording
- ✅ Real-time progress
- ✅ WebSocket integration
- ✅ Settings panel
- ✅ Auto-updater support
- ✅ Download transcripts

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - feel free to use and modify!

## 🔗 Related Projects

- **[Meeting Recorder Server](../README.md)** - The DietPi Flask backend
- **[Whisper.cpp](https://github.com/ggerganov/whisper.cpp)** - Local transcription
- **[Sparkle Framework](https://sparkle-project.org/)** - Auto-updater

---

**Happy Recording!** 🎤✨ 