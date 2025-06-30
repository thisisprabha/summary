# 🎤 Meeting Recorder & Summarizer

A web-based application that records audio, transcribes it using Whisper.cpp, and generates AI-powered summaries using OpenAI's GPT-4o-mini.

![Meeting Recorder Interface](https://img.shields.io/badge/Status-Working-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-2.3.3-blue)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-green)

## ✨ Features

- 🎙️ **Browser-based Recording**: Direct microphone recording with real-time feedback
- 📁 **File Upload**: Support for multiple audio formats (WAV, MP3, M4A, OGG, WebM)
- 🤖 **Offline Transcription**: Using Whisper.cpp for privacy-focused transcription
- 📝 **AI Summarization**: Intelligent summaries using OpenAI GPT-4o-mini
- 📱 **Mobile Responsive**: Works seamlessly on phones and tablets
- 🗂️ **History Management**: View and manage all previous summaries
- 🔒 **Privacy Focused**: Audio processing happens locally with Whisper.cpp

## 🚀 Quick Start

### Method 1: Automated Setup (Recommended)
```bash
git clone https://github.com/thisisprabha/summary.git
cd summary
./start.sh
```

### Method 2: Manual Setup
```bash
git clone https://github.com/thisisprabha/summary.git
cd summary
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:9000` in your browser.

## 📋 Prerequisites

- **Python 3.8+**
- **FFmpeg** (for audio conversion)
- **OpenAI API Key** (for summarization)
- **Modern Web Browser** (Chrome, Firefox, Safari, Edge)

## 🔧 Installation

### 1. System Dependencies

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg build-essential
```

**DietPi/Raspberry Pi:**
```bash
sudo apt update
sudo apt install ffmpeg build-essential git cmake
```

### 2. Whisper.cpp Setup (Required for Transcription)

```bash
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
make
bash ./models/download-ggml-model.sh base
ln -sf models/ggml-base.bin models/for-tests-ggml-base.bin
cd ..
```

### 3. OpenAI API Key

Set your OpenAI API key as an environment variable:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or edit the key directly in `app.py` (line 18).

## 🎯 Usage

1. **Start the Application**
   ```bash
   ./start.sh
   ```

2. **Open Web Interface**
   - Go to `http://localhost:9000`
   - Allow microphone permissions when prompted

3. **Record or Upload Audio**
   - **Record**: Click "🔴 Start Recording" → speak → "⏹️ Stop Recording"
   - **Upload**: Click "📁 Upload Audio File" and select any audio file

4. **Get AI Summary**
   - The app automatically transcribes and summarizes your audio
   - View all summaries in the history section

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │  Flask Server   │    │   Whisper.cpp   │
│                 │───▶│                 │───▶│                 │
│ - Microphone    │    │ - Audio Upload  │    │ - Transcription │
│ - File Upload   │    │ - FFmpeg Conv.  │    │ - Local Process │
│ - UI/UX         │    │ - API Routes    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   OpenAI API    │
                       │                 │
                       │ - GPT-4o-mini   │
                       │ - Summarization │
                       │                 │
                       └─────────────────┘
```

## 📁 Project Structure

```
summary/
├── app.py                 # Main Flask application
├── static/
│   └── index.html        # Web interface
├── requirements.txt      # Python dependencies
├── start.sh             # Automated startup script
├── setup_guide.md       # Detailed setup instructions
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## 🔧 Configuration

### Port Configuration
The app runs on port 9000 by default. To change:
```python
# In app.py, line 231
app.run(host='0.0.0.0', port=YOUR_PORT, debug=True)
```

### Language Settings
Change transcription language in `app.py`, line 98:
```python
"-l", "auto",  # Change to "en" for English, "ta" for Tamil, etc.
```

## 🐛 Troubleshooting

### Common Issues

1. **Port Already in Use**
   - The app will show which port is in use
   - Kill existing processes or change the port

2. **Microphone Not Working**
   - Check browser permissions
   - Try HTTPS in production
   - Use file upload as alternative

3. **Whisper Not Found**
   - Run the Whisper.cpp setup commands
   - Check if the executable exists: `./whisper.cpp/build/bin/whisper-cli`

4. **Model Not Found**
   - Download the model: `bash ./whisper.cpp/models/download-ggml-model.sh base`

### Health Check
Visit `http://localhost:9000/health` to check system status.

## 🚀 Deployment

### For Local Use
The app is ready to run locally with the setup above.

### For DietPi/Raspberry Pi
1. Copy the project to your device
2. Follow the same setup steps
3. Access via `http://[device-ip]:9000`

### Production Considerations
- Use environment variables for API keys
- Set up HTTPS for microphone access
- Configure proper logging
- Consider using a production WSGI server

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source. Feel free to use, modify, and distribute.

## 🙏 Acknowledgments

- **OpenAI** for GPT-4o-mini API
- **Whisper.cpp** for efficient local transcription
- **Flask** for the web framework
- **FFmpeg** for audio processing

## 📞 Support

For issues and questions:
1. Check the [setup_guide.md](setup_guide.md) for detailed instructions
2. Review the troubleshooting section above
3. Check server logs in `app.log`
4. Open an issue on GitHub

---

**Made with ❤️ for better meeting productivity** 