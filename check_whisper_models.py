#!/usr/bin/env python3
"""
Check Whisper Models and Download VAD for Speed Boost
This script checks for available whisper models and downloads the VAD model
which provides 40-60% speed improvement by skipping silent parts.
"""

import os
import subprocess
import urllib.request
import sys

def check_model_exists(path, name):
    """Check if a model exists and print its size"""
    if os.path.exists(path):
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"✅ {name}: {path} ({size_mb:.1f} MB)")
        return True
    else:
        print(f"❌ {name}: {path} (not found)")
        return False

def download_vad_model():
    """Download VAD model for major speed improvement"""
    vad_path = "./whisper.cpp/models/ggml-silero-v5.1.2.bin"
    
    if os.path.exists(vad_path):
        print("✅ VAD model already exists!")
        return True
    
    print("📥 Downloading VAD model for 40-60% speed boost...")
    
    # Create models directory if it doesn't exist
    os.makedirs("./whisper.cpp/models/", exist_ok=True)
    
    # Use whisper.cpp VAD download script if available
    if os.path.exists("./whisper.cpp/models/download-vad-model.sh"):
        try:
            print("Using whisper.cpp VAD download script...")
            result = subprocess.run([
                "bash", "./whisper.cpp/models/download-vad-model.sh", "silero-v5.1.2"
            ], cwd="./whisper.cpp", capture_output=True, text=True, check=True)
            
            if os.path.exists(vad_path):
                size_mb = os.path.getsize(vad_path) / (1024 * 1024)
                print(f"✅ VAD model downloaded successfully! ({size_mb:.1f} MB)")
                print("🚀 This will provide 40-60% speed improvement by skipping silence!")
                return True
            else:
                print("❌ Download script completed but file not found")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Download script failed: {e}")
        except Exception as e:
            print(f"❌ Error running download script: {e}")
    
    # Try multiple VAD model sources as fallback
    vad_urls = [
        "https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v5.1.2.bin",
        "https://github.com/ggerganov/whisper.cpp/raw/master/models/ggml-silero-v5.1.2.bin",
    ]
    
    for vad_url in vad_urls:
        try:
            print(f"Trying: {vad_url}")
            urllib.request.urlretrieve(vad_url, vad_path)
            
            if os.path.exists(vad_path) and os.path.getsize(vad_path) > 1000:  # At least 1KB
                size_mb = os.path.getsize(vad_path) / (1024 * 1024)
                print(f"✅ VAD model downloaded successfully! ({size_mb:.1f} MB)")
                print("🚀 This will provide 40-60% speed improvement by skipping silence!")
                return True
            else:
                if os.path.exists(vad_path):
                    os.remove(vad_path)
                
        except Exception as e:
            print(f"❌ Failed to download from {vad_url}: {e}")
            continue
    
    print("❌ All VAD model downloads failed")
    print("💡 You can manually download it or try downloading from whisper.cpp:")
    print("   cd whisper.cpp && bash ./models/download-vad-model.sh silero-v5.1.2")
    return False

def download_tiny_model():
    """Download tiny model for 3x faster English processing"""
    tiny_path = "./whisper.cpp/models/ggml-tiny.bin"
    
    if os.path.exists(tiny_path):
        print("✅ Tiny model already exists!")
        return True
    
    print("📥 Downloading tiny model for 3x faster English processing...")
    
    # Create models directory if it doesn't exist
    os.makedirs("./whisper.cpp/models/", exist_ok=True)
    
    # Use whisper.cpp download script if available
    if os.path.exists("./whisper.cpp/models/download-ggml-model.sh"):
        try:
            print("Using whisper.cpp download script...")
            result = subprocess.run([
                "bash", "./whisper.cpp/models/download-ggml-model.sh", "tiny"
            ], cwd="./whisper.cpp", capture_output=True, text=True, check=True)
            
            if os.path.exists(tiny_path):
                size_mb = os.path.getsize(tiny_path) / (1024 * 1024)
                print(f"✅ Tiny model downloaded successfully! ({size_mb:.1f} MB)")
                print("⚡ This provides 3x faster English processing!")
                return True
            else:
                print("❌ Download script completed but file not found")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Download script failed: {e}")
        except Exception as e:
            print(f"❌ Error running download script: {e}")
    
    # Try direct download as fallback
    tiny_urls = [
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin"
    ]
    
    for tiny_url in tiny_urls:
        try:
            print(f"Trying direct download: {tiny_url}")
            urllib.request.urlretrieve(tiny_url, tiny_path)
            
            if os.path.exists(tiny_path) and os.path.getsize(tiny_path) > 10000000:  # At least 10MB
                size_mb = os.path.getsize(tiny_path) / (1024 * 1024)
                print(f"✅ Tiny model downloaded successfully! ({size_mb:.1f} MB)")
                print("⚡ This provides 3x faster English processing!")
                return True
            else:
                if os.path.exists(tiny_path):
                    os.remove(tiny_path)
                    
        except Exception as e:
            print(f"❌ Failed to download from {tiny_url}: {e}")
            continue
    
    print("❌ Tiny model download failed")
    print("💡 Try manually: cd whisper.cpp && bash ./models/download-ggml-model.sh tiny")
    return False

def check_whisper_executable():
    """Check if whisper executable exists"""
    whisper_exe = "./whisper.cpp/build/bin/whisper-cli"
    if os.path.exists(whisper_exe):
        print(f"✅ Whisper executable: {whisper_exe}")
        return True
    else:
        print(f"❌ Whisper executable: {whisper_exe} (not found)")
        print("💡 Build whisper.cpp first:")
        print("   cd whisper.cpp && make")
        return False

def check_ffmpeg():
    """Check if ffmpeg is available"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ FFmpeg: Available")
            return True
        else:
            print("❌ FFmpeg: Not working properly")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg: Not found")
        print("💡 Install ffmpeg:")
        print("   macOS: brew install ffmpeg")
        print("   Ubuntu: sudo apt install ffmpeg")
        return False

def main():
    print("🎤 Meeting Recorder - Whisper Model Check")
    print("=" * 50)
    
    # Check whisper executable
    whisper_ok = check_whisper_executable()
    
    # Check models
    print("\n📁 Checking Models:")
    base_ok = check_model_exists("./whisper.cpp/models/ggml-base.bin", "Base Model (Tamil+English)")
    tiny_ok = check_model_exists("./whisper.cpp/models/ggml-tiny.bin", "Tiny Model (English, 3x faster)")
    vad_ok = check_model_exists("./whisper.cpp/models/ggml-silero-v5.1.2.bin", "VAD Model (40-60% speed boost)")
    
    # Check ffmpeg
    print("\n🛠️  Checking Dependencies:")
    ffmpeg_ok = check_ffmpeg()
    
    # Summary and recommendations
    print("\n📊 Summary:")
    print(f"   Whisper Executable: {'✅' if whisper_ok else '❌'}")
    print(f"   Base Model (Required): {'✅' if base_ok else '❌'}")
    print(f"   Tiny Model (Speed): {'✅' if tiny_ok else '❌'}")
    print(f"   VAD Model (Major Speed Boost): {'✅' if vad_ok else '❌'}")
    print(f"   FFmpeg: {'✅' if ffmpeg_ok else '❌'}")
    
    # Speed recommendations
    print("\n⚡ Speed Optimization Status:")
    if tiny_ok and vad_ok:
        print("🚀 EXCELLENT: Both tiny model and VAD available - maximum speed!")
    elif vad_ok:
        print("🔥 GOOD: VAD model available - 40-60% speed boost!")
    elif tiny_ok:
        print("⚡ FAIR: Tiny model available - 3x faster for English")
    else:
        print("🐌 SLOW: No speed optimizations available")
    
    # Offer to download VAD model
    if not vad_ok:
        print("\n💡 Recommendation: Download VAD model for major speed improvement!")
        response = input("Download VAD model now? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            vad_ok = download_vad_model()
    
    # Offer to download tiny model
    if not tiny_ok:
        print("\n💡 Recommendation: Download tiny model for 3x faster English processing!")
        response = input("Download tiny model now? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            tiny_ok = download_tiny_model()
    
    # Missing models recommendations
    if not base_ok:
        print("\n❌ Missing required base model!")
        print("💡 Download with: cd whisper.cpp && bash ./models/download-ggml-model.sh base")
    
    # Final speed assessment
    print("\n🚀 FINAL SPEED ASSESSMENT:")
    if tiny_ok and vad_ok:
        print("🎯 MAXIMUM SPEED: Both optimizations available!")
        print("   → Tiny model: 3x faster English processing")
        print("   → VAD model: 40-60% speed boost by skipping silence")
        print("   → Combined: Up to 5x faster for English meetings with silence!")
    elif vad_ok:
        print("🔥 GOOD SPEED: VAD model provides 40-60% improvement!")
        print("   → Consider downloading tiny model for additional 3x English speedup")
    elif tiny_ok:
        print("⚡ DECENT SPEED: Tiny model provides 3x faster English processing!")
        print("   → Consider downloading VAD model for additional 40-60% speedup")
    else:
        print("🐌 SLOW: No optimizations - processing will be slow")
        print("   → Recommend downloading both models for maximum speed")
    
    print("\n✅ Model check complete!")

if __name__ == "__main__":
    main() 