#!/bin/bash

# Meeting Recorder Mac App Builder
# Updated for simplified message format and enhanced Tamil/English support

set -e

echo "🎤 Building Meeting Recorder Mac App v2.0 - Enhanced"
echo "✨ Features: Message format, Tamil/English optimization, Auto-cleanup"
echo ""

# Configuration
APP_NAME="MeetingRecorder"
BUILD_DIR=".build"
RELEASE_DIR="release"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf "$BUILD_DIR"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# Build the app
echo "🔨 Building Swift package..."
swift build -c release --arch arm64 --arch x86_64 -Xswiftc -parse-as-library

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
else
    echo "❌ Build failed!"
    exit 1
fi

# Create app bundle
echo "📦 Creating app bundle..."
APP_BUNDLE="$RELEASE_DIR/$APP_NAME.app"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# Copy executable
cp ".build/apple/Products/Release/MeetingRecorderApp" "$APP_BUNDLE/Contents/MacOS/"

# Create Info.plist
cat > "$APP_BUNDLE/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>MeetingRecorderApp</string>
    <key>CFBundleIdentifier</key>
    <string>com.meetingrecorder.app</string>
    <key>CFBundleName</key>
    <string>Meeting Recorder</string>
    <key>CFBundleDisplayName</key>
    <string>Meeting Recorder Enhanced</string>
    <key>CFBundleVersion</key>
    <string>2.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Meeting Recorder needs microphone access to record audio for transcription with Tamil/English support.</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>Meeting Recorder needs to control other apps to provide enhanced recording features.</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.productivity</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
</dict>
</plist>
EOF

# Make executable
chmod +x "$APP_BUNDLE/Contents/MacOS/MeetingRecorderApp"

echo "✅ App bundle created successfully!"
echo ""
echo "📱 Meeting Recorder Enhanced v2.0 Features:"
echo "   • 💬 Clean message format (no more Person1/Person2)"
echo "   • 🌐 Enhanced Tamil/English mixed language support"
echo "   • 🗃️ Auto-cleanup and persistent storage"
echo "   • 📥 Download transcriptions and summaries"
echo "   • 🔄 Real-time language analysis"
echo ""
echo "📁 App location: $APP_BUNDLE"
echo "🚀 Ready to use! Drag to Applications folder."

# Optional: Create a DMG
if command -v create-dmg >/dev/null 2>&1; then
    echo "📀 Creating DMG..."
    create-dmg \
        --volname "Meeting Recorder Enhanced" \
        --volicon "$APP_BUNDLE/Contents/Resources/AppIcon.icns" \
        --window-pos 200 120 \
        --window-size 600 300 \
        --icon-size 100 \
        --icon "$APP_NAME.app" 175 120 \
        --hide-extension "$APP_NAME.app" \
        --app-drop-link 425 120 \
        "$RELEASE_DIR/MeetingRecorder-Enhanced-v2.0.dmg" \
        "$RELEASE_DIR/"
    
    echo "✅ DMG created: $RELEASE_DIR/MeetingRecorder-Enhanced-v2.0.dmg"
else
    echo "ℹ️  Install create-dmg for DMG creation: brew install create-dmg"
fi

echo ""
echo "🎉 Build complete! Launch the app to start using enhanced meeting recording." 