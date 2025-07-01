#!/usr/bin/env python3
"""
Test script for Hybrid OpenAI + Local Meeting Recorder
Verifies all components are working correctly
"""

import os
import sys
import requests
import json
import time

# Configuration
SERVER_URL = "http://192.168.31.58:9000"
TEST_ENDPOINTS = [
    "/health",
    "/cost-tracker", 
    "/summaries"
]

def test_server_connectivity():
    """Test if server is reachable"""
    print("🔗 Testing server connectivity...")
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is reachable")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot reach server: {e}")
        return False

def test_health_endpoint():
    """Test health endpoint and capabilities"""
    print("\n🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{SERVER_URL}/health")
        data = response.json()
        
        print(f"   Status: {data.get('status', 'unknown')}")
        print(f"   Database summaries: {data.get('database_summaries', 'unknown')}")
        print(f"   Whisper available: {'✅' if data.get('whisper_available') else '❌'}")
        print(f"   OpenAI available: {'✅' if data.get('openai_available') else '❌'}")
        print(f"   Audio optimization: {'✅' if data.get('audio_optimization_available') else '❌'}")
        print(f"   Offline summarization: {'✅' if data.get('offline_summarization_available') else '❌'}")
        
        return data.get('status') == 'healthy'
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_cost_tracker():
    """Test cost tracking endpoint"""
    print("\n💰 Testing cost tracker...")
    try:
        response = requests.get(f"{SERVER_URL}/cost-tracker")
        data = response.json()
        
        print(f"   Total cost: ${data.get('total_cost', 0.0):.4f}")
        print(f"   Session count: {data.get('session_count', 0)}")
        print(f"   API available: {'✅' if data.get('api_available') else '❌'}")
        print(f"   Optimization available: {'✅' if data.get('optimization_available') else '❌'}")
        
        if data.get('recent_sessions'):
            print("   Recent sessions:")
            for session_id, cost in list(data['recent_sessions'].items())[-3:]:
                print(f"     {session_id}: ${cost:.4f}")
        
        return True
    except Exception as e:
        print(f"❌ Cost tracker failed: {e}")
        return False

def test_audio_optimization():
    """Test audio optimization capabilities"""
    print("\n🎵 Testing audio optimization...")
    try:
        # Try importing audio optimization libraries
        from pydub import AudioSegment
        from pydub.silence import split_on_silence
        import librosa
        import soundfile as sf
        import webrtcvad
        
        print("✅ All audio optimization libraries available:")
        print("   - pydub: Audio manipulation")
        print("   - librosa: Audio analysis")  
        print("   - soundfile: Audio I/O")
        print("   - webrtcvad: Voice Activity Detection")
        return True
    except ImportError as e:
        print(f"❌ Audio optimization libraries missing: {e}")
        return False

def test_openai_configuration():
    """Test OpenAI configuration"""
    print("\n🤖 Testing OpenAI configuration...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        if api_key.startswith('sk-'):
            print("✅ OpenAI API key format looks correct")
            print(f"   Key preview: {api_key[:20]}...{api_key[-8:]}")
        else:
            print("⚠️  OpenAI API key format looks unusual")
            print(f"   Key preview: {api_key[:20]}...")
    else:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        return False
    
    try:
        import openai
        print("✅ OpenAI library available")
        return True
    except ImportError:
        print("❌ OpenAI library not installed")
        return False

def run_comprehensive_test():
    """Run all tests"""
    print("🚀 Starting Hybrid Meeting Recorder System Test")
    print("=" * 60)
    
    results = {
        'connectivity': test_server_connectivity(),
        'health': test_health_endpoint(),
        'cost_tracker': test_cost_tracker(),
        'audio_optimization': test_audio_optimization(),
        'openai_config': test_openai_configuration()
    }
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n🎯 Overall Score: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Your hybrid system is ready to use!")
        print("\n🌐 Access your system at: http://192.168.31.58:9000")
        print("\n💡 Try these features:")
        print("   🎯 Smart Auto: For automatic best choice")  
        print("   🚀 OpenAI Fast: For ultra-fast processing")
        print("   🆓 Local Free: For cost-free processing")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Please check the setup.")
        print("\n🔧 Common fixes:")
        if not results['connectivity']:
            print("   - Check if DietPi server is running")
            print("   - Verify IP address (192.168.31.58)")
        if not results['openai_config']:
            print("   - Set OPENAI_API_KEY environment variable")
        if not results['audio_optimization']:
            print("   - Install audio libraries: pip install pydub librosa soundfile webrtcvad")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1) 