# Meeting Recorder - OpenAI Powered Setup

## ✅ WORKING & TESTED

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```
**Note**: Uses compatible versions (OpenAI 1.3.0 + httpx 0.24.1) to avoid initialization errors.

### 2. Set OpenAI API Key
Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_openai_api_key_here
```

Get your API key from: https://platform.openai.com/api-keys

### 3. Run the Application
```bash
python app.py
```

Visit: http://localhost:9000

### 4. Test Health
```bash
curl http://localhost:9000/health
```
Should return: `{"openai_configured":true,"service":"OpenAI Whisper + GPT","status":"healthy"}`

## How It Works

1. **Upload Audio** → Choose any audio file (MP3, WAV, M4A, OGG, FLAC)
2. **Get Transcription** → OpenAI Whisper API processes the audio
3. **Download Transcription** → Save the text file
4. **Generate MOM Summary** → OpenAI GPT creates Minutes of Meeting format with:
   - Key Discussion Points
   - Important Updates  
   - Action Items/Next Steps
   - Participants & Roles

## Cost Estimate
- **Transcription**: ~$0.006 per minute of audio
- **Summary**: ~$0.002 per summary (GPT-3.5-turbo)

## Features Removed
- All offline processing (whisper.cpp, local models)
- Real-time recording 
- Complex configuration options
- Database storage (files saved in Uploads/ folder)

## Clean & Simple
- Static HTML frontend
- Minimal Flask backend
- OpenAI API only
- Two-step process: Transcription → Summary

## Ready for DietPi
- Minimal dependencies (5 packages only)
- No complex local processing
- Lightweight and fast
- Easy deployment 