# 🎙️ Meeting Recorder - Tamil/English Transcription

> **Dual API system: OpenAI Whisper + DeepSeek/OpenAI Summarization for maximum cost efficiency**

## ✨ Features

- 🌍 **Direct English Transcription** - Speak Tamil, get accurate English transcripts
- 🧹 **Post-processing Cleanup** - Removes artifacts, repetitions, and trailing dots
- 📝 **Dual API Support** - OpenAI for transcription, DeepSeek/OpenAI for summaries
- 💰 **Cost Optimization** - DeepSeek is 90-95% cheaper than OpenAI for summaries
- 🔄 **API Switching** - Switch between providers dynamically
- 💻 **Web App** - Upload audio files via browser
- 🍎 **Mac App** - Menu bar recording with manual summary generation
- 📥 **Download History** - Access all transcriptions and summaries
- 🎯 **Real-time Processing** - Fast transcription with OpenAI Whisper

---

## 💰 **Cost Comparison: Your $2 Budget**

| Provider | Input Cost | Output Cost | Summaries per $2 | Savings |
|----------|------------|-------------|------------------|---------|
| **DeepSeek** | $0.14/1M tokens | $0.28/1M tokens | **~3,600** | **95% cheaper** |
| OpenAI GPT-3.5 | $0.50/1M tokens | $1.50/1M tokens | ~1,300 | Baseline |
| OpenAI GPT-4o | $2.50/1M tokens | $10.00/1M tokens | ~200 | Most expensive |

**🎉 DeepSeek gives you 18x more summaries for the same budget!**

---

## 🚀 Quick Start

### Prerequisites

```bash
# Check Python version (3.8+ required)
python --version

# Check if git is installed
git --version
```

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd Summary

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. **DUAL API SETUP** (New!)

```bash
# Run the interactive setup script
python setup_dual_api.py

# Or manually configure your .env file:
# OPENAI_API_KEY=sk-proj-your-openai-key-here
# DEEPSEEK_API_KEY=sk-your-deepseek-key-here  
# API_PROVIDER=auto
```

**What each option means:**
- `auto` - Uses DeepSeek if available (cheapest), falls back to OpenAI
- `deepseek` - Forces DeepSeek for summaries (maximum savings)
- `openai` - Forces OpenAI for summaries (more expensive but familiar)

### 3. Start the Server

```bash
# Start the dual API server
python app.py
```

**Expected Output:**
```
🎙️ Meeting Recorder - DUAL API SYSTEM
📝 Features: Audio Upload → OpenAI Whisper → DeepSeek/OpenAI Summary
🤖 API Status:
   - OpenAI: ✅ Configured
   - DeepSeek: ✅ Configured
   - Active Provider: deepseek
💰 COST SAVINGS: Using DeepSeek for summaries (90-95% cheaper than OpenAI)
📊 Budget Estimate: $2 = ~3,600 summaries with DeepSeek vs ~200 with OpenAI
🌐 Server starting at: http://localhost:9000
```

---

## 🔄 **API Provider Switching**

### Switch via API (Recommended)

```bash
# Switch to DeepSeek (cheapest)
curl -X POST -H "Content-Type: application/json" \
     -d '{"provider":"deepseek"}' \
     http://localhost:9000/api/switch-provider

# Switch to OpenAI
curl -X POST -H "Content-Type: application/json" \
     -d '{"provider":"openai"}' \
     http://localhost:9000/api/switch-provider

# Use auto-selection (recommended)
curl -X POST -H "Content-Type: application/json" \
     -d '{"provider":"auto"}' \
     http://localhost:9000/api/switch-provider
```

### Switch via Environment Variable

```bash
# Set provider for current session
export API_PROVIDER=deepseek
python app.py

# Or update .env file
echo "API_PROVIDER=deepseek" >> .env
```

---

## ✅ Health Check Commands

### Verify Server Status

```bash
# Check if server is running with dual API info
curl -s http://localhost:9000/health | python -m json.tool
```

**Expected Response:**
```json
{
    "status": "healthy",
    "openai_configured": true,
    "deepseek_configured": true,
    "active_provider": "deepseek",
    "service": "Dual API Meeting Recorder - OpenAI Whisper + OpenAI/DeepSeek Summarization",
    "total_transcriptions": 46,
    "features": [
        "dual_api_support",
        "openai_whisper_transcription", 
        "deepseek_openai_summarization",
        "cost_optimization",
        "api_switching"
    ],
    "cost_savings": {
        "deepseek_vs_openai": "90-95% cheaper for summarization",
        "recommendation": "Use DeepSeek for summaries to maximize your $2 budget"
    }
}
```

### Test API Connections

```bash
# Test both API connections
python setup_dual_api.py test

# Expected output:
# 🧪 Testing API Connections...
# ✅ OpenAI connection successful
# ✅ DeepSeek connection successful
```

### Check Database

```bash
# Verify database includes API provider tracking
sqlite3 transcriptions.db "SELECT id, filename, api_provider, summary_provider, created_at FROM transcriptions ORDER BY created_at DESC LIMIT 5;"
```

---

## 🖥️ Usage Guide

### Web App

1. **Open Browser**: Navigate to `http://localhost:9000`
2. **Upload Audio**: Choose your audio file (supports .m4a, .wav, .mp3)
3. **Get Transcription**: Automatic transcription with OpenAI Whisper
4. **Generate Summary**: 
   - Uses DeepSeek by default (if configured) - **18x cheaper!**
   - Falls back to OpenAI if DeepSeek unavailable
5. **Download**: Access transcription and summary files with provider info

### Mac App

1. **Install**: 
   ```bash
cd MeetingRecorderApp
./build.sh
   cp -R release/MeetingRecorder.app /Applications/
   ```

2. **Launch**:
   ```bash
   open /Applications/MeetingRecorder.app
   ```

3. **Use**: Look for 🎤 icon in menu bar → Start Recording → Stop Recording → View History

---

## 🔧 Troubleshooting

### API Configuration Issues

```bash
# Check which APIs are configured
python setup_dual_api.py test

# Reconfigure APIs
python setup_dual_api.py

# Check current provider
curl -s http://localhost:9000/health | grep active_provider
```

### Cost Optimization

```bash
# Force DeepSeek for maximum savings
export API_PROVIDER=deepseek
python app.py

# Check summary provider in history
curl -s http://localhost:9000/history | grep summary_provider
```

### Server Won't Start

```bash
# Check if port 9000 is in use
lsof -ti:9000

# Kill existing processes
pkill -f "python.*app.py"
lsof -ti:9000 | xargs kill -9

# Restart server
python app.py
```

### OpenAI API Issues

```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     -H "Content-Type: application/json" \
     https://api.openai.com/v1/models | head -20
```

### DeepSeek API Issues

```bash
# Verify DeepSeek API key
echo $DEEPSEEK_API_KEY

# Test DeepSeek API
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
     -H "Content-Type: application/json" \
     https://api.deepseek.com/v1/models | head -20
```

---

## 🎯 Quick Reference

```bash
# Essential commands
python setup_dual_api.py                        # Configure dual APIs
python app.py                                    # Start server
curl -s http://localhost:9000/health            # Check health + API status
pkill -f "python.*app.py"                      # Stop server

# API switching
curl -X POST -H "Content-Type: application/json" -d '{"provider":"deepseek"}' http://localhost:9000/api/switch-provider
curl -X POST -H "Content-Type: application/json" -d '{"provider":"openai"}' http://localhost:9000/api/switch-provider

# Database with provider tracking
sqlite3 transcriptions.db "SELECT COUNT(*) FROM transcriptions WHERE summary_provider='deepseek';"

# Cost monitoring
sqlite3 transcriptions.db "SELECT summary_provider, COUNT(*) as count FROM transcriptions WHERE summary IS NOT NULL GROUP BY summary_provider;"
```

---

## 💡 **Pro Tips for Maximizing Your $2 Budget**

1. **Use DeepSeek for summaries**: Set `API_PROVIDER=auto` or `deepseek`
2. **Monitor usage**: Check `/history` endpoint to see which provider was used
3. **Batch processing**: Upload multiple audio files and summarize them all with DeepSeek
4. **Test both providers**: Compare quality and pick your preference

**🎉 With DeepSeek, your $2 budget will last months instead of days, giving you 18x more meeting summaries!**

---

**🚀 You're all set! Your Meeting Recorder now supports both APIs with massive cost savings through DeepSeek integration.** 