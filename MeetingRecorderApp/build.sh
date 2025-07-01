#!/bin/bash

# Meeting Recorder App Build Script
# This script builds the Swift menu bar app for macOS

set -e

echo "🍎 Building Meeting Recorder Mac App..."

# Clean previous builds
rm -rf .build/release
rm -rf MeetingRecorder.app

# Build the Swift package with the required flag
echo "📦 Building Swift package..."
swift build -c release -Xswiftc -parse-as-library

# Create app bundle structure
echo "📁 Creating app bundle..."
mkdir -p MeetingRecorder.app/Contents/MacOS
mkdir -p MeetingRecorder.app/Contents/Resources

# Copy executable
cp .build/release/MeetingRecorderApp MeetingRecorder.app/Contents/MacOS/

# Create Info.plist for the app bundle
cat > MeetingRecorder.app/Contents/Info.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>MeetingRecorderApp</string>
    <key>CFBundleIdentifier</key>
    <string>com.yourcompany.meetingrecorder</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Meeting Recorder</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Meeting Recorder needs microphone access to record audio for transcription and summarization.</string>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
        <key>NSExceptionDomains</key>
        <dict>
            <key>192.168.31.58</key>
            <dict>
                <key>NSExceptionAllowsInsecureHTTPLoads</key>
                <true/>
                <key>NSExceptionMinimumTLSVersion</key>
                <string>TLSv1.0</string>
            </dict>
        </dict>
    </dict>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2024 Your Company. All rights reserved.</string>
</dict>
</plist>
EOF

# Create app icon (you'll need to add this)
# cp app-icon.icns MeetingRecorder.app/Contents/Resources/

# Make executable
chmod +x MeetingRecorder.app/Contents/MacOS/MeetingRecorderApp

# Sign the app (optional, for distribution)
if [ "$1" = "sign" ]; then
    echo "✍️ Signing app..."
    codesign --force --deep --sign "Developer ID Application: Your Name" MeetingRecorder.app
fi

echo "✅ Build complete! App created at MeetingRecorder.app"
echo ""
echo "To install:"
echo "1. Copy MeetingRecorder.app to /Applications/"
echo "2. Right-click and select 'Open' to bypass Gatekeeper"
echo "3. Allow microphone access when prompted"
echo "4. The app will appear in your menu bar as a microphone icon"
echo ""
echo "To run from command line:"
echo "./MeetingRecorder.app/Contents/MacOS/MeetingRecorderApp"
echo ""
echo "To test:"
echo "1. Click the microphone icon in your menu bar"
echo "2. Go to Settings and configure your DietPi server URL"
echo "3. Test the connection"
echo "4. Start recording!" 