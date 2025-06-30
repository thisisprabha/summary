# 🥧 DietPi Setup Guide for Meeting Recorder

This guide will help you deploy the Meeting Recorder & Summarizer on your DietPi device with local whisper.cpp transcription.

## 🚀 Quick Setup on DietPi

### Step 1: Connect to Your DietPi
```bash
ssh dietpi@[your-dietpi-ip]
# Default password: dietpi
```

### Step 2: Update System and Install Dependencies
```bash
# Update the system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git ffmpeg build-essential cmake

# Install additional build tools for whisper.cpp
sudo apt install -y pkg-config libopenblas-dev
```

### Step 3: Clone the Project
```bash
cd /home/dietpi
git clone https://github.com/thisisprabha/summary.git
cd summary
```

### Step 4: Set Up Python Environment
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 5: Build Whisper.cpp (The Key Component!)
```bash
# Clone whisper.cpp
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# Build whisper.cpp (this may take 10-15 minutes on Pi)
make

# Download the base model (about 150MB)
bash ./models/download-ggml-model.sh base

# Create the expected model path
ln -sf models/ggml-base.bin models/for-tests-ggml-base.bin

# Go back to project directory
cd ..
```

### Step 6: Configure for DietPi
```bash
# Set your OpenAI API key (optional, for summarization)
export OPENAI_API_KEY="your-api-key-here"

# Or edit the key directly in app.py
nano app.py
# Edit line 18 to add your API key
```

### Step 7: Test the Setup
```bash
# Run the health check
source venv/bin/activate
python -c "
import subprocess
import os
print('FFmpeg:', 'OK' if subprocess.run(['which', 'ffmpeg'], capture_output=True).returncode == 0 else 'MISSING')
print('Whisper.cpp:', 'OK' if os.path.exists('./whisper.cpp/build/bin/whisper-cli') else 'MISSING')
print('Model:', 'OK' if os.path.exists('./whisper.cpp/models/for-tests-ggml-base.bin') else 'MISSING')
"
```

### Step 8: Start the Application
```bash
# Use the automated start script
./start.sh

# Or manually:
# source venv/bin/activate
# python app.py
```

### Step 9: Access from Other Devices
The app will be available at:
- **From DietPi**: `http://localhost:9000`
- **From other devices**: `http://[dietpi-ip]:9000`

To find your DietPi IP:
```bash
hostname -I
```

## 🔧 DietPi-Specific Optimizations

### Performance Tuning for Raspberry Pi

#### 1. GPU Memory Split (for better performance)
```bash
sudo dietpi-config
# Navigate to: Advanced Options > Memory Split
# Set GPU memory to 128MB or higher
```

#### 2. Enable Hardware-Specific Optimizations
```bash
# For Raspberry Pi, enable hardware acceleration
cd whisper.cpp
make clean
make UNAME_M=armv7l  # For Pi 3/4
# or
make UNAME_M=aarch64  # For Pi 4 64-bit
```

#### 3. Optimize for Low Memory Usage
Edit `app.py` to use smaller model if needed:
```bash
nano app.py
# On line 87, change model path to use 'tiny' or 'small' model for faster processing:
# bash ./models/download-ggml-model.sh tiny
```

### Auto-Start on Boot (Optional)

#### Create systemd service:
```bash
sudo nano /etc/systemd/system/meeting-recorder.service
```

Add this content:
```ini
[Unit]
Description=Meeting Recorder & Summarizer
After=network.target

[Service]
Type=simple
User=dietpi
WorkingDirectory=/home/dietpi/summary
Environment=PATH=/home/dietpi/summary/venv/bin
ExecStart=/home/dietpi/summary/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable meeting-recorder.service
sudo systemctl start meeting-recorder.service
```

## 📱 Usage on DietPi

### From a Computer/Phone Browser:
1. Open `http://[dietpi-ip]:9000`
2. Allow microphone permissions
3. Record or upload audio files
4. Get transcription and AI summaries

### Performance Expectations:
- **Raspberry Pi 4**: 1-2 minutes for 1 minute of audio
- **Raspberry Pi 3**: 3-5 minutes for 1 minute of audio
- **Other DietPi devices**: Varies by CPU power

## 🛠️ Troubleshooting on DietPi

### Common Issues:

#### 1. Whisper.cpp Build Fails
```bash
# Install missing dependencies
sudo apt install -y gcc g++ make cmake

# Clear and rebuild
cd whisper.cpp
make clean
make
```

#### 2. Out of Memory During Build
```bash
# Increase swap space
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

#### 3. Model Download Fails
```bash
# Manual download
cd whisper.cpp/models
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin
ln -sf ggml-base.bin for-tests-ggml-base.bin
```

#### 4. Permission Issues
```bash
# Fix permissions
sudo chown -R dietpi:dietpi /home/dietpi/summary
chmod +x start.sh
```

### Performance Optimization:

#### Use Smaller Models for Faster Processing:
```bash
cd whisper.cpp/models
# Download tiny model (39MB, fastest)
bash download-ggml-model.sh tiny
ln -sf ggml-tiny.bin for-tests-ggml-base.bin

# Or small model (244MB, good balance)
bash download-ggml-model.sh small
ln -sf ggml-small.bin for-tests-ggml-base.bin
```

#### Monitor System Resources:
```bash
# Check CPU and memory usage
htop

# Check disk space
df -h

# Monitor logs
tail -f app.log
```

## 🌐 Network Configuration

### Port Forwarding (Optional):
If you want to access from outside your network:
1. Forward port 9000 on your router to your DietPi IP
2. Access via `http://[your-public-ip]:9000`

### HTTPS Setup (Recommended for external access):
```bash
# Install nginx and certbot
sudo apt install nginx certbot python3-certbot-nginx

# Configure nginx proxy (create /etc/nginx/sites-available/meeting-recorder)
# Get SSL certificate with certbot
```

## 📊 DietPi vs Local Performance

| Feature | DietPi (Pi 4) | Local Computer |
|---------|---------------|----------------|
| Recording | Same | Same |
| Upload | Same | Same |
| Transcription | 2-5x slower | Baseline |
| Summarization | Same (API) | Same (API) |
| Power Usage | ~5W | ~100-300W |
| Always On | ✅ Perfect | ❌ Impractical |

## 🎯 Perfect Use Cases for DietPi:

1. **Always-On Meeting Recorder**: Leave it running 24/7
2. **Family Voice Memos**: Accessible from any device at home
3. **Interview Transcription**: Portable, low-power solution
4. **Learning Tool**: Practice with speech-to-text locally
5. **Privacy-Focused**: All transcription happens locally

Your DietPi setup will be perfect for local transcription with whisper.cpp! 🚀 