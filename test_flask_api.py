#!/usr/bin/env python3

import requests
import os
import glob

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        response = requests.get('http://localhost:9000/health')
        data = response.json()
        
        if data.get('status') == 'healthy' and data.get('openai_configured'):
            print("✅ Health endpoint working - OpenAI configured")
            return True
        else:
            print(f"❌ Health endpoint issue: {data}")
            return False
            
    except Exception as e:
        print(f"❌ Health endpoint failed: {e}")
        return False

def test_upload_endpoint():
    """Test the upload endpoint with an audio file"""
    try:
        # Find an audio file
        audio_files = []
        for ext in ['*.mp3', '*.wav', '*.m4a', '*.ogg']:
            audio_files.extend(glob.glob(f"Uploads/{ext}"))
        
        if not audio_files:
            print("⚠️ No audio files found for testing upload")
            return None
        
        audio_file = audio_files[0]
        print(f"🎵 Testing upload with: {audio_file}")
        
        with open(audio_file, 'rb') as f:
            files = {'audio': f}
            response = requests.post('http://localhost:9000/upload', files=files)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                transcription = data.get('transcription', '')
                print(f"✅ Upload successful!")
                print(f"📝 Transcription (first 100 chars): {transcription[:100]}...")
                return transcription
            else:
                print(f"❌ Upload failed: {data.get('error')}")
                return None
        else:
            print(f"❌ Upload failed with status {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        return None

def test_summarize_endpoint(transcription):
    """Test the summarize endpoint"""
    try:
        print("🧠 Testing summarization...")
        
        payload = {'transcription': transcription}
        response = requests.post(
            'http://localhost:9000/summarize',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                summary = data.get('summary', '')
                print(f"✅ Summarization successful!")
                print(f"📋 Summary (first 200 chars): {summary[:200]}...")
                return summary
            else:
                print(f"❌ Summarization failed: {data.get('error')}")
                return None
        else:
            print(f"❌ Summarization failed with status {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Summarization test failed: {e}")
        return None

def main():
    print("🧪 Flask API Test Script")
    print("=" * 40)
    
    # Test health endpoint
    if not test_health_endpoint():
        print("❌ Health check failed - make sure Flask app is running")
        return
    
    # Test upload endpoint
    transcription = test_upload_endpoint()
    if not transcription:
        print("❌ Upload test failed")
        return
    
    # Test summarize endpoint
    summary = test_summarize_endpoint(transcription)
    if not summary:
        print("❌ Summarization test failed")
        return
    
    print("\n🎉 All Flask API tests passed!")
    print("\n📋 Full Test Results:")
    print("-" * 30)
    print(f"Transcription: {transcription}")
    print("-" * 30)
    print(f"Summary: {summary}")

if __name__ == "__main__":
    main() 