#!/usr/bin/env python3

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openai_import():
    """Test if OpenAI can be imported and initialized"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        print("✅ OpenAI client created successfully")
        return client
    except Exception as e:
        print(f"❌ Error creating OpenAI client: {e}")
        return None

def test_transcription(client, audio_file_path):
    """Test audio transcription"""
    try:
        print(f"🎵 Testing transcription with: {audio_file_path}")
        
        with open(audio_file_path, 'rb') as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        print(f"✅ Transcription successful!")
        print(f"📝 Result: {transcription[:100]}...")
        return transcription
        
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        return None

def test_summarization(client, text):
    """Test text summarization"""
    try:
        print("🧠 Testing summarization...")
        
        summary_prompt = f"""
Please analyze the following meeting transcription and create a comprehensive Minutes of Meeting (MOM) summary with the following structure:

## Meeting Summary

### Key Discussion Points:
- [List main topics discussed]

### Important Updates:
- [List status updates, announcements, decisions made]

### Action Items / Next Steps:
- [List todo items, assignments, deadlines]

Transcription:
{text}

Please format the response clearly and focus on actionable items and key decisions.
"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert meeting secretary who creates clear, actionable meeting summaries in Minutes of Meeting format."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content
        print("✅ Summary successful!")
        print(f"📋 Result: {summary[:200]}...")
        return summary
        
    except Exception as e:
        print(f"❌ Summary failed: {e}")
        return None

def main():
    print("🔧 OpenAI API Test Script")
    print("=" * 40)
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        sys.exit(1)
    
    print(f"🔑 API Key found: {api_key[:20]}...")
    
    # Test OpenAI client creation
    client = test_openai_import()
    if not client:
        sys.exit(1)
    
    # Find an audio file to test with
    audio_files = []
    for ext in ['*.mp3', '*.wav', '*.m4a', '*.ogg']:
        import glob
        audio_files.extend(glob.glob(f"Uploads/{ext}"))
    
    if not audio_files:
        print("⚠️  No audio files found in Uploads/ directory")
        print("💡 You can test summarization with sample text...")
        
        # Test just summarization with sample text
        sample_text = "This is a test meeting where we discussed project updates and next steps."
        summary = test_summarization(client, sample_text)
        
        if summary:
            print("\n🎉 All tests passed! OpenAI API is working correctly.")
        else:
            print("\n❌ Tests failed!")
        return
    
    # Test with first audio file found
    audio_file = audio_files[0]
    print(f"🎵 Found audio file: {audio_file}")
    
    # Test transcription
    transcription = test_transcription(client, audio_file)
    if not transcription:
        sys.exit(1)
    
    # Test summarization
    summary = test_summarization(client, transcription)
    if not summary:
        sys.exit(1)
    
    print("\n🎉 All tests passed! OpenAI API is working correctly.")
    print("\n📄 Full Results:")
    print("-" * 20)
    print(f"Transcription: {transcription}")
    print("-" * 20)
    print(f"Summary: {summary}")

if __name__ == "__main__":
    main() 