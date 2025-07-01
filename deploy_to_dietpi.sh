#!/bin/bash

# Enhanced DietPi Deployment Script with OpenAI Integration & Audio Optimization
# Deploy Meeting Recorder with hybrid OpenAI/Local processing

set -e

echo "🚀 Deploying Hybrid Meeting Recorder to DietPi..."

# Configuration
DIETPI_IP="192.168.31.58"
DIETPI_USER="dietpi"
LOCAL_PROJECT_DIR="."
REMOTE_PROJECT_DIR="/home/dietpi/meeting-recorder"

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set. Add it to your environment or the script will use local processing only."
    echo "   To set it: export OPENAI_API_KEY='your-key-here'"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "📁 Copying files to DietPi..."
# Copy application files
scp app.py requirements.txt "${DIETPI_USER}@${DIETPI_IP}:${REMOTE_PROJECT_DIR}/"
scp -r static/ "${DIETPI_USER}@${DIETPI_IP}:${REMOTE_PROJECT_DIR}/"

echo "🔧 Installing audio optimization dependencies on DietPi..."
ssh "${DIETPI_USER}@${DIETPI_IP}" << 'EOF'
cd /home/dietpi/meeting-recorder

# Update system
sudo apt update

# Install additional system dependencies for audio processing
sudo apt install -y libsndfile1 libsndfile1-dev portaudio19-dev

# Activate virtual environment and install Python dependencies
source venv/bin/activate

# Install audio optimization libraries
pip install pydub>=0.25.1
pip install librosa>=0.10.1  
pip install soundfile>=0.12.1
pip install webrtcvad>=2.0.10

# Verify installation
echo "📋 Checking audio optimization capabilities..."
python3 -c "
try:
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
    import librosa
    import soundfile as sf
    import webrtcvad
    print('✅ All audio optimization libraries installed successfully!')
    print('   - pydub: Audio manipulation')
    print('   - librosa: Audio analysis')  
    print('   - soundfile: Audio I/O')
    print('   - webrtcvad: Voice Activity Detection')
except ImportError as e:
    print(f'❌ Missing library: {e}')
"

echo "🔑 Setting OpenAI API key (if provided)..."
if [ ! -z "$OPENAI_API_KEY" ]; then
    echo "export OPENAI_API_KEY='$OPENAI_API_KEY'" >> ~/.bashrc
    export OPENAI_API_KEY='$OPENAI_API_KEY'
    echo "✅ OpenAI API key configured for hybrid processing"
else
    echo "⚠️  No OpenAI API key - using local processing only"
fi

# Check application status
echo "🔍 Checking application capabilities..."
cd /home/dietpi/meeting-recorder
source venv/bin/activate

python3 -c "
import os
print('🎯 Hybrid Meeting Recorder Status:')
print(f'   OpenAI API: {'✅ Available' if os.getenv('OPENAI_API_KEY') else '❌ Not configured'}')
print(f'   Local Whisper: {'✅ Available' if os.path.exists('./whisper.cpp/build/bin/whisper-cli') else '❌ Missing'}')
print(f'   Base Model: {'✅ Available' if os.path.exists('./whisper.cpp/models/ggml-base.bin') else '❌ Missing'}')
print(f'   Tiny Model: {'✅ Available' if os.path.exists('./whisper.cpp/models/ggml-tiny.bin') else '❌ Missing'}')
print(f'   VAD Model: {'✅ Available' if os.path.exists('./whisper.cpp/models/ggml-silero-v5.1.2.bin') else '❌ Missing'}')

try:
    from pydub import AudioSegment
    print('   Audio Optimization: ✅ Available')
except:
    print('   Audio Optimization: ❌ Missing')
"

# Restart the service
echo "🔄 Restarting Meeting Recorder service..."
sudo systemctl restart meeting-recorder
sudo systemctl status meeting-recorder --no-pager -l

EOF

echo ""
echo "🎉 Deployment Complete!"
echo ""
echo "🌐 Access your Hybrid Meeting Recorder at: http://${DIETPI_IP}:9000"
echo ""
echo "💡 Features Available:"
echo "   🎯 Smart Auto Selection: Chooses best method based on duration"
echo "   🚀 OpenAI Fast: Ultra-fast, perfect Tamil accuracy (small cost)"
echo "   🆓 Local Free: No cost, slower processing"
echo "   🔧 Audio Optimization: Silence removal, mono conversion, compression"
echo "   💰 Cost Tracking: Monitor OpenAI API usage"
echo ""
echo "📊 Check status: http://${DIETPI_IP}:9000/health"
echo "💰 Check costs: http://${DIETPI_IP}:9000/cost-tracker" 