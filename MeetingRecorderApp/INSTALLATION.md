# 🎤 Meeting Recorder Mac App - Installation & Usage Guide

## ✅ **Build Complete!**

Your native macOS menu bar app is ready! Here's how to install and use it:

## 📦 **Installation**

### Option 1: Copy to Applications (Recommended)
```bash
cp -r MeetingRecorder.app /Applications/
```

### Option 2: Run from Current Directory
```bash
./MeetingRecorder.app/Contents/MacOS/MeetingRecorderApp
```

## 🚀 **First Launch**

1. **Double-click** `MeetingRecorder.app` or copy it to Applications
2. **Right-click** → **Open** to bypass Gatekeeper (first time only)
3. **Allow microphone access** when macOS prompts you
4. **Allow notifications** when prompted
5. **Look for the microphone icon** in your menu bar 🎤

## ⚙️ **Setup Your DietPi Server**

1. **Click** the microphone icon in your menu bar
2. **Select** "⚙️ Settings"
3. **Enter your DietPi server URL**: `http://192.168.31.58:9000`
4. **Click** "Test Connection" to verify it works
5. **Close** the settings window

## 🎯 **How to Use**

### Recording a Meeting
1. **Click** the microphone icon in your menu bar
2. **Select** "🔴 Start Recording" 
3. **Speak** - The icon will turn red while recording
4. **Click** "⏹️ Stop Recording" when done
5. **Wait** - Processing happens automatically on your DietPi server
6. **Get notified** when your summary is ready!

### Viewing Results
- **📋 Recent Summaries** - See all your meeting summaries
- **Download Transcripts** - Get full transcriptions as text files
- **Copy Summary** - Quick copy to clipboard

## 🌐 **Network Setup**

### Same Network (Home WiFi)
- ✅ **No setup needed** - Just use: `http://192.168.31.58:9000`

### Different Network (Office/Other WiFi)
- 🔧 **Set up port forwarding** on your home router (port 9000)
- 🔒 **Use VPN** to connect to your home network
- ☁️ **Use ngrok** or similar tunnel service

## 🔧 **Features**

### Menu Bar Controls
- 🔴 **Start Recording** - Begin audio capture
- ⏹️ **Stop Recording** - End recording and process
- 📋 **Recent Summaries** - View all summaries
- ⚙️ **Settings** - Configure server URL
- 🔄 **Check for Updates** - Auto-updater (future)
- ❌ **Quit** - Close the app

### Status Indicators
- 🎤 **Gray microphone** = Ready
- 🔴 **Red microphone** = Recording
- 📊 **Wave icon** = Processing

### Notifications
- 📢 **Summary Ready** - When transcription is complete
- 📥 **Transcript Downloaded** - When files are saved
- ❌ **Recording Failed** - If errors occur

## ⚡ **Performance**

- **High-quality audio**: 16kHz, 16-bit, Mono
- **Optimized for Whisper**: Best transcription quality
- **Fast processing**: Uses your DietPi server's whisper.cpp
- **Real-time progress**: WebSocket updates during processing

## 🛠️ **Troubleshooting**

### App Won't Start
1. **Check macOS version**: Requires macOS 13.0+ (Ventura)
2. **Right-click → Open** to bypass Gatekeeper
3. **Check Console.app** for error messages

### No Microphone Access
1. **System Settings** → **Privacy & Security** → **Microphone**
2. **Enable** "Meeting Recorder"
3. **Restart** the app

### Can't Connect to Server
1. **Check server URL** format: `http://IP:9000`
2. **Verify DietPi server** is running
3. **Test in browser**: Visit the URL directly
4. **Check network connectivity**

### No Recording Audio
1. **Check input device** in System Settings → Sound
2. **Test microphone** with other apps
3. **Check microphone levels** in Audio MIDI Setup

## 🔄 **Updates**

The app includes Sparkle framework for automatic updates:
- **Daily update checks** (when available)
- **Secure downloads** with cryptographic verification
- **User control** over when to install

## 🗂️ **Files & Locations**

- **App**: `/Applications/MeetingRecorder.app`
- **Settings**: Stored in macOS UserDefaults
- **Temp recordings**: Automatically cleaned up
- **Downloads**: Choose location when downloading transcripts

## 🎉 **You're Ready!**

Your Meeting Recorder Mac app is now installed and configured. 

**Next Steps:**
1. ✅ Record a test meeting
2. ✅ Verify the summary appears
3. ✅ Download a transcript
4. ✅ Set up remote access if needed

**Enjoy better meeting productivity!** 🎤✨

---

**Need Help?**
- Check the main [README.md](README.md) for detailed documentation
- Review DietPi server logs if processing fails
- Test the web interface at `http://192.168.31.58:9000` directly 