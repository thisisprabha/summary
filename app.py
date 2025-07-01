from flask import Flask, request, jsonify, send_from_directory, Response
import sqlite3
import subprocess
import openai
import os
import logging
from werkzeug.utils import secure_filename
import tempfile
import time
import json
from flask_socketio import SocketIO, emit
import threading
import select
import fcntl
import re

# Audio optimization imports for cost reduction
try:
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
    import librosa
    import soundfile as sf
    import webrtcvad
    AUDIO_OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Audio optimization libraries not available: {e}")
    AUDIO_OPTIMIZATION_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.DEBUG, filename='app.log')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variable to track current session progress
current_session = {}

def emit_progress(session_id, stage, progress, message, transcription_chunk=None):
    """Emit progress update to connected clients with optional transcription chunk"""
    try:
        progress_data = {
            'session_id': session_id,
            'stage': stage,
            'progress': progress,
            'message': message,
            'timestamp': time.time()
        }
        
        # Add real-time transcription chunk if available
        if transcription_chunk:
            progress_data['transcription_chunk'] = transcription_chunk
            
        socketio.emit('progress_update', progress_data, room=session_id)
        logger.debug(f"Progress update: {stage} - {progress}% - {message}")
    except Exception as e:
        logger.error(f"Failed to emit progress: {e}")

# Cost tracking for OpenAI API usage
class CostTracker:
    def __init__(self):
        self.total_cost = 0.0
        self.session_costs = {}
    
    def add_whisper_cost(self, session_id, duration_minutes):
        """Add Whisper API cost ($0.006/minute)"""
        cost = duration_minutes * 0.006
        self.total_cost += cost
        if session_id not in self.session_costs:
            self.session_costs[session_id] = 0.0
        self.session_costs[session_id] += cost
        logger.info(f"Session {session_id}: Whisper cost ${cost:.4f} for {duration_minutes:.2f} minutes")
        return cost
    
    def get_session_cost(self, session_id):
        return self.session_costs.get(session_id, 0.0)
    
    def get_total_cost(self):
        return self.total_cost

cost_tracker = CostTracker()

# Audio optimization functions for cost reduction
def optimize_audio_for_api(audio_path, session_id):
    """Optimize audio file to reduce OpenAI API costs using your strategy"""
    if not AUDIO_OPTIMIZATION_AVAILABLE:
        return audio_path, "No optimization (libraries missing)"
    
    try:
        emit_progress(session_id, 'optimization', 15, 'Optimizing audio to reduce API costs...')
        
        # Load audio
        audio = AudioSegment.from_file(audio_path)
        original_duration = len(audio) / 1000.0  # seconds
        original_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
        
        optimization_steps = []
        
        # Step 1: Convert to mono (halves data)
        if audio.channels > 1:
            audio = audio.set_channels(1)
            optimization_steps.append("mono conversion")
            emit_progress(session_id, 'optimization', 20, 'Converting to mono (50% size reduction)...')
        
        # Step 2: Downsample to optimal rate (16kHz for Whisper)
        if audio.frame_rate > 16000:
            audio = audio.set_frame_rate(16000)
            optimization_steps.append("downsampled to 16kHz")
            emit_progress(session_id, 'optimization', 25, 'Downsampling to 16kHz...')
        
        # Step 3: Trim silence aggressively (your key cost-saving strategy)
        emit_progress(session_id, 'optimization', 30, 'Removing silence to reduce duration cost...')
        
        # Detect silence and split
        chunks = split_on_silence(
            audio,
            min_silence_len=300,    # 300ms minimum silence
            silence_thresh=-40,     # dB threshold for silence
            keep_silence=100,       # keep 100ms padding
            seek_step=10           # precision
        )
        
        if chunks:
            # Combine non-silent chunks
            optimized_audio = AudioSegment.empty()
            for chunk in chunks:
                optimized_audio += chunk
            
            silence_removed = original_duration - (len(optimized_audio) / 1000.0)
            if silence_removed > 1.0:  # Only apply if significant silence removed
                audio = optimized_audio
                optimization_steps.append(f"removed {silence_removed:.1f}s silence")
                emit_progress(session_id, 'optimization', 35, f'Removed {silence_removed:.1f}s of silence!')
        
        # Step 4: Export as FLAC for better compression
        output_path = audio_path.replace('.wav', '_optimized.flac')
        audio.export(output_path, format="flac", parameters=["-compression_level", "8"])
        
        new_duration = len(audio) / 1000.0
        new_size = os.path.getsize(output_path) / (1024 * 1024)
        
        duration_reduction = ((original_duration - new_duration) / original_duration) * 100
        size_reduction = ((original_size - new_size) / original_size) * 100
        cost_savings = duration_reduction  # Cost is per minute, so duration reduction = cost reduction
        
        optimization_summary = f"Optimized: {', '.join(optimization_steps)}"
        savings_summary = f"Duration: -{duration_reduction:.1f}%, Size: -{size_reduction:.1f}%, Cost: -{cost_savings:.1f}%"
        
        emit_progress(session_id, 'optimization', 40, f'Optimization complete! {savings_summary}')
        logger.info(f"Audio optimization: {optimization_summary} | {savings_summary}")
        
        return output_path, f"{optimization_summary} | {savings_summary}"
        
    except Exception as e:
        logger.warning(f"Audio optimization failed: {e}")
        return audio_path, f"Optimization failed: {str(e)}"

def transcribe_with_openai_api(audio_path, session_id, language_hint=None):
    """Transcribe using OpenAI Whisper API with cost tracking"""
    try:
        emit_progress(session_id, 'openai_transcription', 45, 'Starting OpenAI Whisper API transcription...')
        
        # Calculate duration for cost tracking
        try:
            if AUDIO_OPTIMIZATION_AVAILABLE:
                audio = AudioSegment.from_file(audio_path)
                duration_minutes = len(audio) / (1000.0 * 60.0)
            else:
                # Fallback: use ffprobe
                probe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
                           '-show_entries', 'format=duration', audio_path]
                result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
                duration_seconds = float(json.loads(result.stdout)['format']['duration'])
                duration_minutes = duration_seconds / 60.0
        except Exception as e:
            logger.warning(f"Could not determine audio duration: {e}")
            duration_minutes = 1.0  # Default estimate
        
        # Track expected cost
        expected_cost = cost_tracker.add_whisper_cost(session_id, duration_minutes)
        emit_progress(session_id, 'openai_transcription', 50, 
                     f'Uploading to OpenAI... (Est. cost: ${expected_cost:.3f})')
        
        # Prepare language parameter
        language_param = None
        if language_hint:
            if language_hint.lower() in ['tamil', 'ta']:
                language_param = 'ta'
            elif language_hint.lower() in ['english', 'en']:
                language_param = 'en'
        
        # Call OpenAI Whisper API
        with open(audio_path, 'rb') as audio_file:
            if OPENAI_NEW_CLIENT and openai_client:
                # New OpenAI client (v1.0+)
                transcript_kwargs = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "response_format": "text"
                }
                if language_param:
                    transcript_kwargs["language"] = language_param
                
                transcript = openai_client.audio.transcriptions.create(**transcript_kwargs)
                transcription_text = transcript if isinstance(transcript, str) else transcript.text
            else:
                # Legacy OpenAI client
                transcript_kwargs = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "response_format": "text"
                }
                if language_param:
                    transcript_kwargs["language"] = language_param
                
                transcript = openai.Audio.transcribe(**transcript_kwargs)
                transcription_text = transcript.get('text', '') if isinstance(transcript, dict) else str(transcript)
        
        emit_progress(session_id, 'openai_transcription', 80, 
                     f'OpenAI transcription complete! (Cost: ${expected_cost:.3f})')
        
        if not transcription_text or len(transcription_text.strip()) < 5:
            raise Exception("OpenAI returned empty or very short transcription")
        
        return transcription_text.strip()
        
    except Exception as e:
        logger.error(f"OpenAI Whisper API failed: {e}")
        raise Exception(f"OpenAI Whisper API failed: {str(e)}")

# Initialize OpenAI client with backward compatibility
openai_api_key = os.getenv('OPENAI_API_KEY', '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')

# Try new OpenAI client initialization, fall back to old method
try:
    # New OpenAI >= 1.0 method
    openai_client = openai.OpenAI(api_key=openai_api_key)
    OPENAI_NEW_CLIENT = True
    logger.info("Using new OpenAI client (v1.0+)")
except TypeError:
    # Old OpenAI < 1.0 method
    openai.api_key = openai_api_key
    openai_client = None
    OPENAI_NEW_CLIENT = False
    logger.info("Using legacy OpenAI client (v0.x)")
except Exception as e:
    logger.error(f"OpenAI initialization failed: {e}")
    openai_client = None
    OPENAI_NEW_CLIENT = False

# Try to import transformers for offline summarization backup
try:
    from transformers import pipeline
    offline_summarizer = pipeline("summarization", model="t5-small", device=-1)  # CPU mode
    OFFLINE_SUMMARIZATION_AVAILABLE = True
    logger.info("Offline T5 summarization available as backup")
except ImportError:
    OFFLINE_SUMMARIZATION_AVAILABLE = False
    logger.warning("Transformers not available - only OpenAI summarization will work")

# Set up SQLite
conn = sqlite3.connect('meetings.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS summaries
             (id INTEGER PRIMARY KEY, transcription TEXT, summary TEXT, tag TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

def detect_language_and_select_model(transcription_sample, user_language_hint=None):
    """
    Detect language optimized for Tamil-English bilingual scenarios with speed focus
    Returns: (model_path, detected_language)
    """
    
    # If user provided language hint, use it
    if user_language_hint and user_language_hint.lower() in ['tamil', 'ta']:
        return "./whisper.cpp/models/ggml-base.bin", "ta"
    elif user_language_hint and user_language_hint.lower() in ['english', 'en']:
        # Prefer tiny model for English (3x faster)
        tiny_model = "./whisper.cpp/models/ggml-tiny.bin"
        if os.path.exists(tiny_model):
            return tiny_model, "en"
        return "./whisper.cpp/models/ggml-base.bin", "en"
    
    # Optimized detection for Tamil-English bilingual content with speed priority
    text_lower = transcription_sample.lower()
    
    # Tamil Unicode range detection (comprehensive for all Tamil scripts)
    tamil_char_count = sum(1 for char in transcription_sample if 0x0B80 <= ord(char) <= 0x0BFF)
    total_chars = len([c for c in transcription_sample if c.isalnum()])
    
    # Common Tamil words and patterns (expanded for business/meeting context)
    tamil_patterns = [
        'தமிழ்', 'நான்', 'அது', 'இது', 'என்', 'உங்கள்', 'அவர்', 'இவர்', 
        'எங்கள்', 'நம்', 'அவள்', 'இவள்', 'செய்', 'வந்த', 'போன', 'வரும்',
        'உள்ள', 'இருக்க', 'கூட', 'மட்டும்', 'தான்', 'என்று', 'அன்று',
        'இன்று', 'நாள்', 'மணி', 'நேரம்', 'பேர்', 'விட', 'கொண்ட',
        # Business/meeting specific Tamil words
        'மீட்டிங்', 'வேலை', 'பணி', 'திட்டம்', 'செய்யலாம்', 'முடியும்',
        'ஆகும்', 'வேண்டும்', 'இல்லை', 'உண்டு', 'பார்க்க', 'சொன்ன',
        'கொடுக்க', 'எடுக்க', 'அனுப்ப', 'வாங்க', 'போக', 'வர',
        # Common code-switching markers
        'அப்புறம்', 'இப்ப', 'நம்ம', 'உன்', 'என்ன', 'எப்ப', 'எங்க'
    ]
    
    # English words common in business/technical contexts
    english_patterns = [
        'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'is', 'are', 'was', 'were',
        'meeting', 'project', 'work', 'team', 'call', 'email', 'update', 'status', 'task',
        'client', 'customer', 'business', 'process', 'system', 'data', 'report', 'analysis',
        'we', 'they', 'our', 'their', 'this', 'that', 'can', 'will', 'should', 'need'
    ]
    
    # Calculate Tamil presence score
    tamil_pattern_score = sum(1 for pattern in tamil_patterns if pattern in transcription_sample)
    tamil_unicode_ratio = tamil_char_count / max(total_chars, 1)
    
    # Calculate English presence score
    english_score = sum(1 for pattern in english_patterns if pattern in text_lower)
    
    # Total word count for ratio calculations
    words = transcription_sample.split()
    word_count = len(words)
    
    # Speed-optimized decision logic for Tamil-English bilingual scenarios
    if tamil_unicode_ratio > 0.2 or tamil_pattern_score > 1:  # Strong Tamil detected
        # Clear Tamil content - use base model
        logger.debug(f"Strong Tamil detected - Unicode ratio: {tamil_unicode_ratio:.2f}, Pattern score: {tamil_pattern_score}")
        return "./whisper.cpp/models/ggml-base.bin", "ta"
    
    elif tamil_unicode_ratio > 0.05 or tamil_pattern_score > 0:  # Light Tamil detected
        # Some Tamil but might be mixed
        if english_score > 8 and word_count > 20:
            # Heavy English with some Tamil = probably mixed but English-heavy
            logger.debug(f"English-heavy mixed content - Tamil ratio: {tamil_unicode_ratio:.2f}, English: {english_score}")
            # Use tiny model for speed (English model handles some Tamil)
            tiny_model = "./whisper.cpp/models/ggml-tiny.bin"
            if os.path.exists(tiny_model):
                return tiny_model, "en"
            return "./whisper.cpp/models/ggml-base.bin", "en"
        else:
            # Tamil-leaning mixed content
            logger.debug(f"Tamil-leaning mixed content - Tamil ratio: {tamil_unicode_ratio:.2f}, Tamil patterns: {tamil_pattern_score}")
            return "./whisper.cpp/models/ggml-base.bin", "ta"
    
    elif english_score >= 3:  # Clear English content
        # Check for common Tamil-English code-switching patterns in transliterated form
        transliterated_tamil = ['enna', 'eppo', 'anga', 'inga', 'namma', 'avan', 'aval', 'ithu', 'athu']
        transliterated_score = sum(1 for pattern in transliterated_tamil if pattern in text_lower)
        
        if transliterated_score > 0:
            # English with Tamil transliteration = Mixed but English model might work
            logger.debug(f"English with transliterated Tamil - English: {english_score}, Transliterated: {transliterated_score}")
            # Try tiny model first for speed
            tiny_model = "./whisper.cpp/models/ggml-tiny.bin"
            if os.path.exists(tiny_model):
                return tiny_model, "en"  # English model often handles transliterated Tamil
            return "./whisper.cpp/models/ggml-base.bin", "ta"
        else:
            # Pure English - use tiny model for speed
            logger.debug(f"Pure English detected - Pattern score: {english_score}")
            tiny_model = "./whisper.cpp/models/ggml-tiny.bin"
            if os.path.exists(tiny_model):
                return tiny_model, "en"
            return "./whisper.cpp/models/ggml-base.bin", "en"
    
    else:
        # Unclear content - use heuristics for Tamil-English environment
        # Check for non-ASCII characters (likely Tamil)
        non_ascii_ratio = sum(1 for char in transcription_sample if ord(char) > 127) / max(len(transcription_sample), 1)
        
        if non_ascii_ratio > 0.05:  # Any significant non-ASCII = likely Tamil
            logger.debug(f"Non-ASCII characters detected ({non_ascii_ratio:.2f}), defaulting to Tamil")
            return "./whisper.cpp/models/ggml-base.bin", "ta"
        
        # When truly unclear, prefer speed for Tamil-English bilingual environment
        logger.debug("Language unclear in Tamil-English context, using tiny model for speed")
        tiny_model = "./whisper.cpp/models/ggml-tiny.bin"
        if os.path.exists(tiny_model):
            return tiny_model, "en"  # Try English first for speed
        return "./whisper.cpp/models/ggml-base.bin", "ta"

def get_language_description(language_code):
    """Get user-friendly description for language codes"""
    descriptions = {
        'ta': 'Tamil/Mixed Tamil-English',
        'en': 'Pure English',
        'auto': 'Auto-detect'
    }
    return descriptions.get(language_code, language_code)

def create_offline_summary(text):
    """Create summary using offline T5 model"""
    try:
        if not OFFLINE_SUMMARIZATION_AVAILABLE:
            return "Offline summarization not available. Install transformers: pip install transformers torch"
        
        # T5 has input length limits, so truncate if necessary
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]
        
        # Generate summary
        summary = offline_summarizer(text, max_length=100, min_length=30, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        logger.error(f"Offline summarization error: {str(e)}")
        return f"Offline summarization failed: {str(e)}"

def create_openai_summary(text):
    """Create summary using OpenAI API (compatible with both old and new clients)"""
    try:
        if OPENAI_NEW_CLIENT and openai_client:
            # New OpenAI >= 1.0 method
            summary_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Summarize the following meeting transcript into 2-3 sentences highlighting the key points and decisions:"},
                    {"role": "user", "content": text}
                ],
                max_tokens=150,
                temperature=0.7
            )
            return summary_response.choices[0].message.content.strip()
        else:
            # Legacy OpenAI < 1.0 method
            summary_response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Summarize the following meeting transcript into 2-3 sentences highlighting the key points and decisions:"},
                    {"role": "user", "content": text}
                ],
                max_tokens=150,
                temperature=0.7
            )
            return summary_response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise e

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/upload', methods=['POST'])
def upload_audio():
    try:
        # Generate session ID for progress tracking
        session_id = f"session_{int(time.time() * 1000)}"
        current_session[session_id] = {'status': 'starting'}
        
        emit_progress(session_id, 'upload', 5, 'Processing uploaded file...')
        
        # Get language hint from request (from Mac app or web form)
        language_hint = request.form.get('language') or request.json.get('language') if request.is_json else None
        logger.debug(f"Language hint provided: {language_hint}")
        
        # Ensure Uploads folder exists with correct permissions
        uploads_dir = os.path.join(os.getcwd(), 'Uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        os.chmod(uploads_dir, 0o755)
        logger.debug(f"Uploads directory: {uploads_dir} with permissions: {oct(os.stat(uploads_dir).st_mode)[-3:]}")

        # Save uploaded audio file
        audio_file = request.files.get('audio')
        if not audio_file:
            return jsonify({'error': 'No audio file provided', 'session_id': session_id}), 400
        
        emit_progress(session_id, 'upload', 10, 'Saving uploaded file...')
        
        # Secure the filename
        audio_filename = secure_filename(audio_file.filename)
        if not audio_filename:
            audio_filename = f"audio_{int(time.time())}.webm"
        
        audio_path = os.path.join(uploads_dir, audio_filename)
        audio_file.save(audio_path)
        logger.debug(f"Saved audio file to: {audio_path}")

        emit_progress(session_id, 'validation', 15, 'Validating audio file...')

        # Verify file exists and is readable
        if not os.path.exists(audio_path) or not os.access(audio_path, os.R_OK):
            return jsonify({'error': f'Failed to access audio file: {audio_path}', 'session_id': session_id}), 500

        # Check if file has audio content
        if os.path.getsize(audio_path) == 0:
            return jsonify({'error': 'Audio file is empty', 'session_id': session_id}), 400

        emit_progress(session_id, 'conversion', 20, 'Converting audio format...')

        # Convert to WAV format for whisper.cpp (handle various input formats)
        wav_filename = os.path.splitext(audio_filename)[0] + '_converted.wav'
        wav_path = os.path.join(uploads_dir, wav_filename)
        
        # Check if the input file is already in WAV format with correct specs
        input_ext = os.path.splitext(audio_filename)[1].lower()
        needs_conversion = True
        
        if input_ext == '.wav':
            emit_progress(session_id, 'conversion', 25, 'Checking WAV format compatibility...')
            # Check if WAV file already has correct format (16kHz, mono, PCM)
            probe_cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', audio_path
            ]
            try:
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
                import json
                probe_data = json.loads(probe_result.stdout)
                audio_stream = probe_data['streams'][0]
                
                if (audio_stream.get('sample_rate') == '16000' and 
                    audio_stream.get('channels') == 1 and 
                    audio_stream.get('codec_name') == 'pcm_s16le'):
                    # File is already in correct format, no conversion needed
                    wav_path = audio_path
                    needs_conversion = False
                    logger.debug(f"WAV file already in correct format, skipping conversion")
                    emit_progress(session_id, 'conversion', 30, 'Audio already in correct format!')
            except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
                logger.debug(f"Could not probe audio format, will convert: {e}")
        
        if needs_conversion:
            emit_progress(session_id, 'conversion', 25, 'Converting to WAV format...')
            # Use ffmpeg to convert to the format whisper.cpp expects
            ffmpeg_cmd = [
                'ffmpeg', '-y',  # -y to overwrite output file
                '-i', audio_path,
                '-ar', '16000',  # Sample rate for whisper
                '-ac', '1',      # Mono channel
                '-c:a', 'pcm_s16le',  # PCM 16-bit little-endian
                wav_path
            ]
            
            logger.debug(f"Running ffmpeg: {' '.join(ffmpeg_cmd)}")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return jsonify({'error': f'Audio conversion failed: {result.stderr}', 'session_id': session_id}), 500
            
            logger.debug(f"Converted to WAV: {wav_path}")
            emit_progress(session_id, 'conversion', 35, 'Audio conversion completed!')
        
        # Use the final wav file (either converted or original)
        audio_path = wav_path

        emit_progress(session_id, 'preparation', 40, 'Preparing transcription...')

        # Clear old transcription file
        transcription_file = os.path.join(os.getcwd(), 'whisper.cpp/transcription.txt')
        if os.path.exists(transcription_file):
            os.remove(transcription_file)
            logger.debug(f"Removed old transcription file: {transcription_file}")

        # Check if whisper.cpp executable exists
        whisper_exe = "./whisper.cpp/build/bin/whisper-cli"
        if not os.path.exists(whisper_exe):
            return jsonify({'error': f'Whisper executable not found at {whisper_exe}. Please build whisper.cpp first.', 'session_id': session_id}), 500

        # Check if model exists
        base_model_path = "./whisper.cpp/models/ggml-base.bin"
        if not os.path.exists(base_model_path):
            return jsonify({'error': f'Base whisper model not found at {base_model_path}. Please download the model first.', 'session_id': session_id}), 500

        emit_progress(session_id, 'language_detection', 45, 'Detecting language...')

        # Get transcription method choice from user
        transcription_method = request.form.get('transcription_method', 'auto').lower()
        logger.debug(f"Transcription method requested: {transcription_method}")
        
        # User Choice Logic: Fast/Free/Auto
        if transcription_method == 'openai_fast':
            # Option 1: Pure OpenAI API (fastest, small cost)
            emit_progress(session_id, 'method_selection', 47, '🚀 Using OpenAI API (Fast & Accurate)')
            use_openai = True
            use_optimization = True
        elif transcription_method == 'local_free':
            # Option 2: Pure Local (free, slower)
            emit_progress(session_id, 'method_selection', 47, '🆓 Using Local Processing (Free)')
            use_openai = False
            use_optimization = False
        else:
            # Option 3: Auto Smart Choice (recommended)
            emit_progress(session_id, 'method_selection', 47, '🎯 Smart Auto Selection...')
            
            # Smart decision based on audio duration and Tamil content
            try:
                # Get audio duration for smart choice
                if AUDIO_OPTIMIZATION_AVAILABLE:
                    audio_segment = AudioSegment.from_file(audio_path)
                    duration_minutes = len(audio_segment) / (1000.0 * 60.0)
                else:
                    probe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
                               '-show_entries', 'format=duration', audio_path]
                    result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
                    duration_seconds = float(json.loads(result.stdout)['format']['duration'])
                    duration_minutes = duration_seconds / 60.0
                
                # Calculate expected OpenAI cost
                expected_cost = duration_minutes * 0.006
                
                # Smart choice criteria
                if duration_minutes <= 2.0:
                    # Short audio: Use OpenAI (cost < 1.2 cents)
                    use_openai = True
                    use_optimization = True
                    emit_progress(session_id, 'method_selection', 48, 
                                f'Short audio ({duration_minutes:.1f}min, ${expected_cost:.3f}) → OpenAI')
                elif duration_minutes <= 10.0 and expected_cost <= 0.06:
                    # Medium audio under 6 cents: Use OpenAI with optimization
                    use_openai = True
                    use_optimization = True
                    emit_progress(session_id, 'method_selection', 48, 
                                f'Medium audio ({duration_minutes:.1f}min, ${expected_cost:.3f}) → Optimized OpenAI')
                else:
                    # Long audio or high cost: Use local
                    use_openai = False
                    use_optimization = False
                    emit_progress(session_id, 'method_selection', 48, 
                                f'Long audio ({duration_minutes:.1f}min, ${expected_cost:.3f}) → Local (free)')
                    
            except Exception as e:
                logger.warning(f"Smart choice analysis failed: {e}, defaulting to local")
                use_openai = False
                use_optimization = False
                emit_progress(session_id, 'method_selection', 48, 'Analysis failed → Local (safe)')

        # Hybrid Transcription Execution: OpenAI API vs Local Processing
        transcription = ""
        optimization_info = ""
        detected_language = language_hint or "auto"  # Initialize with user hint or auto
        
        if use_openai:
            # OpenAI API Path with Cost Optimization
            try:
                # Step 1: Audio optimization for cost reduction (if enabled)
                final_audio_path = audio_path
                if use_optimization:
                    final_audio_path, optimization_info = optimize_audio_for_api(audio_path, session_id)
                
                # Step 2: OpenAI Whisper API transcription
                transcription = transcribe_with_openai_api(final_audio_path, session_id, detected_language)
                
                # Add cost info to response
                session_cost = cost_tracker.get_session_cost(session_id)
                total_cost = cost_tracker.get_total_cost()
                
                emit_progress(session_id, 'transcription', 80, 
                            f'OpenAI transcription complete! Session: ${session_cost:.3f}, Total: ${total_cost:.3f}')
                
                logger.info(f"OpenAI transcription success. {optimization_info}")
                
            except Exception as openai_error:
                logger.warning(f"OpenAI API failed: {openai_error}")
                emit_progress(session_id, 'fallback', 45, 'OpenAI failed, falling back to local processing...')
                
                # Fallback to local processing
                use_openai = False
                
        if not use_openai:
            # Local Processing Path (Free but slower)
            emit_progress(session_id, 'transcription', 60, 'Starting local Whisper processing...')
            
            # Language detection for local processing
            if not language_hint:
                # Use the existing language detection logic for local
                quick_model = "./whisper.cpp/models/ggml-tiny.bin"
                if os.path.exists(quick_model):
                    logger.debug("Running Tamil-English optimized language detection...")
                    emit_progress(session_id, 'language_detection', 50, 'Quick language detection (15 seconds max)...')
                    
                    # Quick detection with timeout and Tamil bias
                    quick_whisper_cmd = [
                        whisper_exe,
                        "-m", quick_model,
                        "-f", audio_path,
                        "-l", "auto",  # Let whisper auto-detect first
                        "--output-txt",
                        "--output-file", transcription_file.replace('.txt', '_quick'),
                        "--threads", "4",  # Limit threads for speed
                        "--duration", "30000",  # Only process first 30 seconds for detection
                        "--no-timestamps"  # Skip timestamps for speed
                    ]
                    
                    try:
                        # Run with timeout to prevent hanging
                        quick_result = subprocess.run(
                            quick_whisper_cmd, 
                            capture_output=True, 
                            text=True, 
                            timeout=25,  # 25 second timeout
                            check=False
                        )
                        
                        emit_progress(session_id, 'language_detection', 52, 'Analyzing detected language...')
                        
                        # Read quick transcription for language analysis
                        quick_transcription = ""
                        quick_file_path = transcription_file.replace('.txt', '_quick.txt')
                        if os.path.exists(quick_file_path):
                            with open(quick_file_path, 'r', encoding='utf-8') as f:
                                quick_transcription = f.read().strip()
                            # Clean up temp file
                            os.remove(quick_file_path)
                        
                        # If no transcription or very short, likely Tamil - whisper auto-detect struggles with Tamil
                        if not quick_transcription or len(quick_transcription) < 10:
                            logger.debug("Very short/empty auto-detection output - likely Tamil or poor audio")
                            model_path, detected_language = "./whisper.cpp/models/ggml-base.bin", "ta"
                            emit_progress(session_id, 'language_detection', 55, 'Short output detected - using Tamil model')
                        else:
                            # Analyze the auto-detected transcription
                            model_path, detected_language = detect_language_and_select_model(quick_transcription)
                            
                            # Additional heuristic: if auto-detection gave nonsensical English, likely Tamil
                            nonsense_patterns = ['hello hello hello', 'testing testing', 'the the the', 
                                               'and and and', 'this this this', 'is is is']
                            quick_lower = quick_transcription.lower()
                            if any(pattern in quick_lower for pattern in nonsense_patterns):
                                logger.debug("Repetitive/nonsensical English detected - likely Tamil misclassified")
                                model_path, detected_language = "./whisper.cpp/models/ggml-base.bin", "ta"
                                emit_progress(session_id, 'language_detection', 55, 'Nonsensical English detected - switching to Tamil')
                            else:
                                emit_progress(session_id, 'language_detection', 55, f'Language detected: {get_language_description(detected_language)}')
                        
                    except subprocess.TimeoutExpired:
                        logger.warning("Language detection timed out - defaulting to Tamil for safety")
                        emit_progress(session_id, 'language_detection', 55, 'Detection timeout - using Tamil model (safer for mixed)')
                        model_path, detected_language = "./whisper.cpp/models/ggml-base.bin", "ta"
                    except Exception as e:
                        logger.warning(f"Language detection failed: {e} - defaulting to Tamil")
                        emit_progress(session_id, 'language_detection', 55, 'Detection failed - using Tamil model')
                        model_path, detected_language = "./whisper.cpp/models/ggml-base.bin", "ta"
                    
                    logger.debug(f"Final language choice - Model: {model_path}, Language: {detected_language}")
                else:
                    # No tiny model available - default to Tamil for better mixed language handling
                    model_path = base_model_path
                    detected_language = "ta"
                    logger.debug("Tiny model not available, defaulting to Tamil (better for Tamil-English mixed)")
                    emit_progress(session_id, 'language_detection', 55, 'Using Tamil model (tiny model unavailable)')
            else:
                # User provided language hint
                model_path, detected_language = detect_language_and_select_model("", language_hint)
                emit_progress(session_id, 'language_detection', 55, f'Using specified language: {detected_language}')

            # Local transcription with optimized model
            emit_progress(session_id, 'transcription', 60, f'Starting local transcription with {os.path.basename(model_path)} ({get_language_description(detected_language)})...')
            
            logger.debug(f"Running whisper-cli with file: {audio_path}, language: {detected_language}")
            
            # Enhanced whisper command with aggressive performance optimizations
            whisper_cmd = [
                whisper_exe,
                "-m", model_path,
                "-f", audio_path,
                "-l", detected_language,
                "--output-txt",
                "--output-file", transcription_file.replace('.txt', ''),  # whisper adds .txt automatically
                "--diarize",  # Speaker separation
                "--print-progress",  # Show progress for real-time parsing
                "--print-colors",  # Easier to parse output
                # Performance optimizations
                "--threads", str(min(8, os.cpu_count())),  # Use optimal thread count
                "--processors", "1",  # Single processor for stability
                "--max-len", "0",  # No length limit for better performance
                "--word-thold", "0.01",  # Lower word threshold for speed
                "--entropy-thold", "2.40",  # Lower entropy threshold
                "--logprob-thold", "-1.00",  # Lower log probability threshold
                "--beam-size", "1",  # Reduce beam size for speed (quality vs speed tradeoff)
                "--best-of", "1",  # Use only best candidate for speed
                "--audio-ctx", "512"  # Reduce audio context for speed
            ]
            
            # Additional optimizations based on audio length
            try:
                # Get audio duration for optimization
                probe_cmd = [
                    'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                    '-show_entries', 'format=duration', audio_path
                ]
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
                probe_data = json.loads(probe_result.stdout)
                duration = float(probe_data['format']['duration'])
                logger.debug(f"Audio duration: {duration:.2f} seconds")
                
                # Aggressive optimizations for longer audio
                if duration > 180:  # 3+ minutes
                    whisper_cmd.extend([
                        "--speed-up", "true",  # Enable speed-up for long audio
                        "--no-timestamps"  # Disable timestamps for speed (can add later)
                    ])
                    emit_progress(session_id, 'transcription', 65, f'Long audio detected ({duration:.0f}s), using speed optimizations...')
                elif duration > 60:  # 1+ minutes  
                    whisper_cmd.extend([
                        "--speed-up", "true"
                    ])
                    emit_progress(session_id, 'transcription', 65, f'Medium audio ({duration:.0f}s), optimizing for speed...')
                else:
                    emit_progress(session_id, 'transcription', 65, f'Short audio ({duration:.0f}s), using standard processing...')
                    
            except Exception as e:
                logger.warning(f"Could not determine audio duration: {e}")
                emit_progress(session_id, 'transcription', 65, 'Processing with standard optimizations...')
            
            # Try to add VAD if model is available (major speed boost)
            vad_model_path = "./whisper.cpp/models/ggml-silero-v5.1.2.bin"
            if os.path.exists(vad_model_path):
                whisper_cmd.extend([
                    "--vad",  # Voice Activity Detection - skip silent parts
                    "--vad-model", vad_model_path,
                    "--vad-threshold", "0.4",  # Higher threshold for more aggressive silence skipping
                    "--vad-min-speech-duration-ms", "200",  # Shorter minimum speech
                    "--vad-min-silence-duration-ms", "300",  # Shorter minimum silence
                ])
                emit_progress(session_id, 'transcription', 67, 'Using VAD for 40-60% speed boost by skipping silence...')
                logger.debug("Using VAD model with aggressive silence skipping")
            else:
                emit_progress(session_id, 'transcription', 67, 'Processing without VAD (silence detection unavailable)...')
                logger.info("VAD model not found - consider downloading for 40-60% speed improvement")
            
            # Show transcription area immediately when starting
            emit_progress(session_id, 'transcription', 67, 'Local Whisper starting... Real-time transcription will appear below')
            
            # Use real-time whisper execution for streaming updates
            try:
                result_code, stdout, stderr = run_whisper_with_realtime_output(whisper_cmd, session_id)
            except Exception as e:
                logger.warning(f"Real-time whisper failed, falling back to standard mode: {e}")
                # Fallback to standard execution with progress simulation
                emit_progress(session_id, 'transcription', 70, 'Processing audio in segments...', {
                    'timestamp': '[00:00:00.000 --> 00:00:05.000]',
                    'text': 'Audio processing started...',
                    'chunk_number': 1
                })
                result = subprocess.run(whisper_cmd, capture_output=True, text=True, check=False)
                result_code, stdout, stderr = result.returncode, result.stdout, result.stderr
            
            logger.debug(f"Whisper-cli stdout: {stdout}")
            
            if result_code != 0:
                logger.error(f"Whisper-cli stderr: {stderr}")
                return jsonify({'error': f'Local whisper transcription failed: {stderr}', 'session_id': session_id}), 500

            emit_progress(session_id, 'transcription', 80, 'Local transcription completed! Reading results...')

            # Read transcription from local processing
            if not os.path.exists(transcription_file):
                return jsonify({'error': f'Transcription file not created: {transcription_file}', 'session_id': session_id}), 500
            
            with open(transcription_file, 'r', encoding='utf-8') as f:
                transcription = f.read().strip()
            logger.debug(f"Local transcription content: {transcription}")

        # Validate transcription result (common for both OpenAI and local)
        if not transcription:
            return jsonify({'error': 'Transcription is empty. The audio might be too quiet or contain no speech.', 'session_id': session_id}), 400

        # Save transcription to database immediately (before summarization)
        c.execute("INSERT INTO summaries (transcription, summary) VALUES (?, ?)", 
                  (transcription, "Summarization in progress..."))
        conn.commit()
        transcription_id = c.lastrowid
        
        # Prepare response with cost information if applicable
        response_message = 'Transcription completed! Download available. Summary being generated...'
        if use_openai:
            session_cost = cost_tracker.get_session_cost(session_id)
            response_message += f' (Cost: ${session_cost:.3f})'
            if optimization_info:
                response_message += f' {optimization_info}'
        
        emit_progress(session_id, 'transcription_ready', 85, 'Transcription ready for download! Starting summarization...')

        # Continue summarization in background thread
        def background_summarization():
            try:
                emit_progress(session_id, 'summarization', 87, 'Generating AI summary in background...')
                
                summary = ""
                try:
                    summary = create_openai_summary(transcription)
                    logger.debug(f"OpenAI Summary: {summary}")
                    emit_progress(session_id, 'summarization', 95, 'OpenAI summary generated!')
                except Exception as e:
                    logger.warning(f"OpenAI summarization failed: {str(e)}")
                    emit_progress(session_id, 'summarization', 90, 'OpenAI failed, trying offline summarization...')
                    logger.info("Falling back to offline T5 summarization")
                    try:
                        summary = create_offline_summary(transcription)
                        logger.debug(f"Offline Summary: {summary}")
                        emit_progress(session_id, 'summarization', 95, 'Offline summary generated!')
                    except Exception as e2:
                        logger.error(f"Both summarization methods failed: OpenAI: {str(e)}, Offline: {str(e2)}")
                        summary = f"Summary generation failed. Transcription available for download."
                        emit_progress(session_id, 'summarization', 95, 'Summary generation failed, transcription available')

                # Update database with final summary
                c.execute("UPDATE summaries SET summary = ? WHERE id = ?", (summary, transcription_id))
                conn.commit()
                
                emit_progress(session_id, 'complete', 100, 'Processing completed successfully!')
                
                # Emit final summary to connected clients
                socketio.emit('summary_ready', {
                    'session_id': session_id,
                    'id': transcription_id,
                    'summary': summary
                }, room=session_id)
                
            except Exception as e:
                logger.error(f"Background summarization error: {e}")
                c.execute("UPDATE summaries SET summary = ? WHERE id = ?", 
                         (f"Summary generation failed: {str(e)}", transcription_id))
                conn.commit()
            finally:
                # Clean up temporary files in background
                try:
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                    if audio_path != os.path.join(uploads_dir, audio_filename) and os.path.exists(os.path.join(uploads_dir, audio_filename)):
                        os.remove(os.path.join(uploads_dir, audio_filename))
                    # Clean up language detection test files
                    for suffix in ['_quick.txt', '_english_test.txt']:
                        test_file = transcription_file.replace('.txt', suffix)
                        if os.path.exists(test_file):
                            os.remove(test_file)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary files: {e}")
        
        # Start background summarization
        bg_thread = threading.Thread(target=background_summarization)
        bg_thread.daemon = True
        bg_thread.start()
        
        return jsonify({'id': transcription_id, 'transcription': transcription[:200] + '...' if len(transcription) > 200 else transcription, 'session_id': session_id, 'transcription_ready': True, 'message': response_message})

    except subprocess.CalledProcessError as e:
        logger.error(f"Subprocess failed: {e.stderr}")
        return jsonify({'error': f'Processing failed: {e.stderr}', 'session_id': session_id}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': f'Unexpected error: {str(e)}', 'session_id': session_id}), 500

@app.route('/summaries', methods=['GET'])
def get_summaries():
    try:
        c.execute("SELECT id, summary, tag, created_at FROM summaries ORDER BY id DESC LIMIT 10")
        summaries = c.fetchall()
        return jsonify([{
            'id': s[0], 
            'summary': s[1], 
            'tag': s[2], 
            'created_at': s[3]
        } for s in summaries])
    except Exception as e:
        logger.error(f"Error fetching summaries: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/tag', methods=['POST'])
def tag_summary():
    try:
        data = request.json
        if not data or 'id' not in data or 'tag' not in data:
            return jsonify({'error': 'Missing id or tag in request'}), 400
        
        c.execute("UPDATE summaries SET tag = ? WHERE id = ?", (data['tag'], data['id']))
        conn.commit()
        
        if c.rowcount == 0:
            return jsonify({'error': 'Summary not found'}), 404
        
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error tagging summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    try:
        # Check database connection
        c.execute("SELECT COUNT(*) FROM summaries")
        summary_count = c.fetchone()[0]
        
        # Check whisper executable
        whisper_exe = "./whisper.cpp/build/bin/whisper-cli"
        whisper_available = os.path.exists(whisper_exe)
        
        # Check OpenAI status
        openai_available = bool(openai_client and openai_api_key)
        
        return jsonify({
            'status': 'healthy',
            'database_summaries': summary_count,
            'whisper_available': whisper_available,
            'openai_available': openai_available,
            'audio_optimization_available': AUDIO_OPTIMIZATION_AVAILABLE,
            'offline_summarization_available': OFFLINE_SUMMARIZATION_AVAILABLE
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/cost-tracker', methods=['GET'])
def get_cost_tracker():
    """Get current cost tracking information"""
    try:
        return jsonify({
            'total_cost': cost_tracker.get_total_cost(),
            'session_count': len(cost_tracker.session_costs),
            'recent_sessions': dict(list(cost_tracker.session_costs.items())[-10:]),  # Last 10 sessions
            'api_available': bool(openai_client and openai_api_key),
            'optimization_available': AUDIO_OPTIMIZATION_AVAILABLE
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket event handlers
@socketio.on('connect')
def on_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Successfully connected to progress updates'})

@socketio.on('disconnect')
def on_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('join_session')
def on_join_session(data):
    """Join a session room for progress updates"""
    session_id = data.get('session_id')
    if session_id:
        from flask_socketio import join_room
        join_room(session_id)
        logger.info(f"Client {request.sid} joined session {session_id}")
        emit('joined_session', {'session_id': session_id})

@app.route('/download/<int:summary_id>')
def download_transcription(summary_id):
    """Download full transcription as text file"""
    try:
        c.execute("SELECT transcription, created_at FROM summaries WHERE id = ?", (summary_id,))
        result = c.fetchone()
        
        if not result:
            return jsonify({'error': 'Transcription not found'}), 404
            
        transcription, created_at = result
        
        # Create filename with timestamp
        filename = f"transcription_{summary_id}_{created_at.replace(':', '-').replace(' ', '_')}.txt"
        
        # Create response with file download
        return Response(
            transcription,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        logger.error(f"Error downloading transcription: {str(e)}")
        return jsonify({'error': str(e)}), 500

def run_whisper_with_realtime_output(whisper_cmd, session_id, audio_duration_estimate=None):
    """Run whisper with optimized real-time output streaming"""
    import subprocess
    import select
    import os
    import fcntl
    import re
    import time
    import threading
    
    try:
        logger.info(f"Starting optimized whisper with command: {' '.join(whisper_cmd)}")
        
        # Extract output file path from command
        output_file = None
        for i, arg in enumerate(whisper_cmd):
            if arg == "--output-file" and i + 1 < len(whisper_cmd):
                output_file = whisper_cmd[i + 1] + ".txt"
                break
        
        # Optimized function to monitor output file for changes
        def monitor_output_file():
            if not output_file:
                return
            
            last_size = 0
            chunk_count = 0
            last_check = time.time()
            monitoring_active = True
            
            while monitoring_active:
                try:
                    current_time = time.time()
                    
                    # Adaptive polling based on activity
                    if current_time - last_check < 10:
                        # First 10 seconds: check every 3 seconds
                        poll_interval = 3
                    elif current_time - last_check < 30:
                        # Next 20 seconds: check every 5 seconds  
                        poll_interval = 5
                    else:
                        # After 30 seconds: check every 8 seconds (reduce overhead)
                        poll_interval = 8
                    
                    if os.path.exists(output_file):
                        current_size = os.path.getsize(output_file)
                        if current_size > last_size:
                            # File has grown, read new content
                            try:
                                with open(output_file, 'r', encoding='utf-8') as f:
                                    f.seek(last_size)
                                    new_content = f.read()
                                    
                                    # Parse new content for transcription chunks (optimized)
                                    lines = [line.strip() for line in new_content.split('\n') if line.strip()]
                                    for line in lines:
                                        # Only process substantial lines
                                        if len(line) > 15 and not line.startswith('[') and not line.startswith('whisper'):
                                            chunk_count += 1
                                            # Create simulated timestamp (reduced overhead)
                                            minutes = (chunk_count - 1) * 3 // 60
                                            seconds = (chunk_count - 1) * 3 % 60
                                            end_minutes = chunk_count * 3 // 60
                                            end_seconds = chunk_count * 3 % 60
                                            
                                            transcription_chunk = {
                                                'timestamp': f'[{minutes:02d}:{seconds:02d}:00 --> {end_minutes:02d}:{end_seconds:02d}:00]',
                                                'text': line[:80] + ('...' if len(line) > 80 else ''),  # Shorter preview
                                                'chunk_number': chunk_count
                                            }
                                            
                                            # Less frequent progress updates to reduce overhead
                                            if chunk_count % 2 == 0:  # Every 2nd chunk
                                                progress = min(70 + chunk_count, 85)
                                                emit_progress(session_id, 'transcription', progress, 
                                                            f'Processing: {line[:40]}...', 
                                                            transcription_chunk)
                                        
                                last_size = current_size
                                
                            except (IOError, UnicodeDecodeError) as e:
                                logger.debug(f"File read error (normal): {e}")
                                
                    time.sleep(poll_interval)  # Adaptive polling interval
                    
                except Exception as e:
                    logger.debug(f"File monitoring error: {e}")
                    time.sleep(poll_interval)
                    
                # Check if we should stop monitoring
                if current_time - last_check > 300:  # Stop after 5 minutes max
                    logger.debug("Stopping file monitoring after 5 minutes")
                    monitoring_active = False
        
        # Start optimized file monitoring in background thread
        if output_file:
            monitor_thread = threading.Thread(target=monitor_output_file, daemon=True)
            monitor_thread.start()
        
        # Run whisper process with optimized settings
        process = subprocess.Popen(
            whisper_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=True,
            bufsize=0  # Unbuffered for real-time output
        )
        
        # Simplified real-time reading (reduced overhead)
        output_lines = []
        chunk_count = 0
        
        # Use more efficient polling
        while True:
            # Check if process is still running
            if process.poll() is not None:
                break
                
            try:
                # Reduced frequency polling to minimize CPU usage
                ready, _, _ = select.select([process.stdout], [], [], 1.0)  # Increased timeout
                if ready:
                    line = process.stdout.readline()
                    if line:
                        line = line.strip()
                        output_lines.append(line)
                        
                        # Only log important lines to reduce overhead
                        if 'progress' in line.lower() or 'processing' in line.lower():
                            logger.debug(f"Whisper: {line[:100]}")
                        
                        # Parse for meaningful progress updates (less frequent)
                        if chunk_count % 5 == 0 and ('progress' in line.lower() or '%' in line):
                            chunk_count += 1
                            emit_progress(session_id, 'transcription', 68, f'Whisper progress: {line[:50]}...')
                
            except Exception as e:
                # Reduced error logging frequency
                if chunk_count % 10 == 0:
                    logger.debug(f"Read exception: {e}")
                continue
        
        # Wait for process to complete and get final output
        stdout, stderr = process.communicate()
        if stdout:
            output_lines.extend(stdout.split('\n'))
            
        if stderr and len(stderr) > 100:  # Only log substantial errors
            logger.warning(f"Whisper stderr: {stderr[:200]}...")
            
        logger.info(f"Optimized whisper completed. Return code: {process.returncode}")
        return process.returncode, '\n'.join(output_lines), stderr
        
    except Exception as e:
        logger.error(f"Error in optimized whisper execution: {e}")
        return -1, "", str(e)

if __name__ == '__main__':
    # Ensure required directories exist
    os.makedirs('Uploads', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🎤 Meeting Recorder & Summarizer Server Starting...")
    print("📁 Make sure you have:")
    print("   - whisper.cpp built at ./whisper.cpp/build/bin/whisper-cli")
    print("   - Model file at ./whisper.cpp/models/ggml-base.bin")
    print("   - ffmpeg installed and accessible")
    print("   - OpenAI API key set (either in environment or in code)")
    print("🔗 WebSocket support enabled for real-time progress updates")
    print(f"🌐 Server will be available at: http://localhost:9000")
    
    # Use SocketIO run instead of app.run for WebSocket support
    socketio.run(app, host='0.0.0.0', port=9000, debug=True, allow_unsafe_werkzeug=True)