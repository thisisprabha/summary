#!/bin/bash

echo "🎤 Meeting Recorder & Summarizer Startup Script"
echo "================================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
echo "📥 Installing/updating dependencies..."
pip install -r requirements.txt

# Check dependencies
echo "🔍 Checking system dependencies..."

# Check ffmpeg
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg is installed"
else
    echo "❌ FFmpeg not found. Please install it:"
    echo "   macOS: brew install ffmpeg"
    echo "   Ubuntu: sudo apt install ffmpeg"
    exit 1
fi

# Check whisper.cpp
if [ -f "./whisper.cpp/build/bin/whisper-cli" ]; then
    echo "✅ Whisper.cpp is available"
else
    echo "⚠️  Whisper.cpp not found. The app will show an error when processing audio."
    echo "   To set up whisper.cpp, see setup_guide.md"
fi

# Check model
if [ -f "./whisper.cpp/models/for-tests-ggml-base.bin" ]; then
    echo "✅ Whisper model is available"
else
    echo "⚠️  Whisper model not found. The app will show an error when processing audio."
    echo "   To download the model, see setup_guide.md"
fi

# Create necessary directories
mkdir -p Uploads static

echo ""
echo "🚀 Starting the application..."
echo "   Access it at: http://localhost:9000"
echo "   Press Ctrl+C to stop"
echo ""

# Start the application
python app.py 