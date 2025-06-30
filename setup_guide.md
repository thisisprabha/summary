# 🎤 Meeting Recorder & Summarizer Setup Guide

This guide will help you set up the meeting recorder with microphone recording and audio upload functionality.

## Prerequisites

Before starting, ensure you have:
- Python 3.8+ installed
- Git installed
- A modern web browser (Chrome, Firefox, Safari, Edge)
- OpenAI API key

## Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Install System Dependencies

### On macOS:
```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install ffmpeg
brew install ffmpeg
```

### On Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ffmpeg build-essential
```

### On DietPi (Raspberry Pi):
```bash
sudo apt update
sudo apt install ffmpeg build-essential git cmake
```

## Step 3: Set Up Whisper.cpp

```bash
# Clone whisper.cpp repository
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# Build the project
make

# Download the base model (required)
bash ./models/download-ggml-model.sh base

# Create symbolic link for easier access (optional)
ln -sf models/ggml-base.bin models/for-tests-ggml-base.bin

cd ..
```

## Step 4: Set Up OpenAI API Key

### Option 1: Environment Variable (Recommended)
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### Option 2: Edit app.py
If you prefer, you can keep the API key in the code (already set in app.py)

## Step 5: Run the Application

```bash
python app.py
```

The server will start and display:
```
🎤 Meeting Recorder & Summarizer Server Starting...
📁 Make sure you have:
   - whisper.cpp built at ./whisper.cpp/build/bin/whisper-cli
   - Model file at ./whisper.cpp/models/for-tests-ggml-base.bin
   - ffmpeg installed and accessible
   - OpenAI API key set (either in environment or in code)
🌐 Server will be available at: http://localhost:9000
```

## Step 6: Access the Application

1. Open your web browser
2. Go to `http://localhost:9000`
3. Allow microphone permissions when prompted

## Troubleshooting

### Microphone Not Working

1. **Check Browser Permissions**: Ensure your browser has microphone access
2. **Try HTTPS**: Some browsers require HTTPS for microphone access
3. **Check Console**: Open browser developer tools (F12) and check for errors
4. **Use Upload Instead**: If microphone doesn't work, use the file upload feature

### Common Error Messages

- **"Whisper executable not found"**: Run `make` in the whisper.cpp directory
- **"Model not found"**: Download the model with the script in Step 3
- **"FFmpeg not found"**: Install ffmpeg using the commands in Step 2
- **"OpenAI API error"**: Check your API key and billing status

### For DietPi Deployment

1. Copy the entire project to your DietPi device
2. Follow the same setup steps
3. Make sure to change the Flask host to `0.0.0.0` (already configured)
4. Access via `http://[dietpi-ip]:9000` from other devices

### Audio Format Support

The system supports:
- **Recording**: WebM, MP4 (browser dependent)
- **Upload**: WAV, MP3, M4A, OGG, WebM
- **Processing**: All formats converted to WAV for Whisper

### Performance Tips

- Use shorter audio files (under 10 minutes) for faster processing
- Ensure good audio quality for better transcription
- The base model works well for English and many other languages

## Features

✅ **Microphone Recording**: Direct browser recording with real-time feedback
✅ **File Upload**: Support for multiple audio formats
✅ **Automatic Transcription**: Using Whisper.cpp for offline processing
✅ **AI Summarization**: OpenAI GPT-4o-mini for intelligent summaries
✅ **History**: View all previous summaries
✅ **Error Handling**: Comprehensive error messages and troubleshooting
✅ **Mobile Responsive**: Works on phones and tablets

## Security Notes

- Keep your OpenAI API key secure
- The application runs on all interfaces (0.0.0.0) for DietPi deployment
- Consider using environment variables for sensitive data
- Audio files are automatically cleaned up after processing

## Support

If you encounter issues:
1. Check the server logs in `app.log`
2. Check browser console for JavaScript errors
3. Verify all dependencies are installed correctly
4. Test the health endpoint: `http://localhost:9000/health`

### Port Issues

If you see "AirTunes" errors or port conflicts:
- The app now uses port 9000 (to avoid conflicts)
- Access via `http://localhost:9000`
- For DietPi: `http://[dietpi-ip]:9000` 