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
    Detect language optimized for Tamil-English bilingual scenarios
    Returns: (model_path, detected_language)
    """
    
    # If user provided language hint, use it
    if user_language_hint and user_language_hint.lower() in ['tamil', 'ta']:
        return "./whisper.cpp/models/ggml-base.bin", "ta"
    elif user_language_hint and user_language_hint.lower() in ['english', 'en']:
        tiny_model = "./whisper.cpp/models/ggml-tiny.bin"
        if os.path.exists(tiny_model):
            return tiny_model, "en"
        return "./whisper.cpp/models/ggml-base.bin", "en"
    
    # Optimized detection for Tamil-English bilingual content
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
    
    # Decision logic optimized for Tamil-English bilingual scenarios
    if tamil_unicode_ratio > 0.1 or tamil_pattern_score > 0:  # Any Tamil detected
        # This is Tamil or mixed Tamil-English
        if english_score > 5 and word_count > 20:
            # Significant English content + Tamil = Mixed language
            logger.debug(f"Mixed Tamil-English detected - Tamil ratio: {tamil_unicode_ratio:.2f}, Tamil patterns: {tamil_pattern_score}, English: {english_score}")
            # Use base model for mixed content (better for code-switching)
            return "./whisper.cpp/models/ggml-base.bin", "ta"  # Tamil model handles mixed better
        else:
            # Predominantly Tamil
            logger.debug(f"Tamil detected - Unicode ratio: {tamil_unicode_ratio:.2f}, Pattern score: {tamil_pattern_score}")
            return "./whisper.cpp/models/ggml-base.bin", "ta"
    
    elif english_score >= 3:  # Clear English content
        # Check for common Tamil-English code-switching patterns in transliterated form
        transliterated_tamil = ['enna', 'eppo', 'anga', 'inga', 'namma', 'avan', 'aval', 'ithu', 'athu']
        transliterated_score = sum(1 for pattern in transliterated_tamil if pattern in text_lower)
        
        if transliterated_score > 0:
            # English with Tamil transliteration = Mixed
            logger.debug(f"Mixed English-Tamil (transliterated) detected - English: {english_score}, Transliterated: {transliterated_score}")
            return "./whisper.cpp/models/ggml-base.bin", "ta"  # Tamil model better for mixed
        else:
            # Pure English
            logger.debug(f"English detected - Pattern score: {english_score}")
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
        
        # Default for Tamil-English bilingual environment
        logger.debug("Language unclear in Tamil-English context, defaulting to Tamil model (better for mixed)")
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

        # Language detection strategy optimized for Tamil-English bilingual environment
        if language_hint:
            # User specified language - use directly
            model_path, detected_language = detect_language_and_select_model("", language_hint)
            logger.debug(f"Using user-specified language: {language_hint} -> {detected_language}")
            emit_progress(session_id, 'language_detection', 55, f'Using specified language: {detected_language}')
        else:
            # Smart detection optimized for Tamil-English bilingual meetings
            quick_model = "./whisper.cpp/models/ggml-tiny.bin"
            if os.path.exists(quick_model):
                logger.debug("Running Tamil-English optimized language detection...")
                emit_progress(session_id, 'language_detection', 50, 'Detecting Tamil vs English content...')
                
                # Quick detection with Tamil bias (better for mixed content)
                quick_whisper_cmd = [
                    whisper_exe,
                    "-m", quick_model,
                    "-f", audio_path,
                    "-l", "ta",  # Start with Tamil model for better mixed detection
                    "--output-txt",
                    "--output-file", transcription_file.replace('.txt', '_quick')
                ]
                
                quick_result = subprocess.run(quick_whisper_cmd, capture_output=True, text=True, check=False)
                
                # Read quick transcription for language analysis
                quick_transcription = ""
                if os.path.exists(transcription_file.replace('.txt', '_quick.txt')):
                    with open(transcription_file.replace('.txt', '_quick.txt'), 'r', encoding='utf-8') as f:
                        quick_transcription = f.read().strip()
                
                # Analyze the Tamil-first transcription
                model_path, detected_language = detect_language_and_select_model(quick_transcription)
                
                # If detected as pure English, verify with English model for comparison
                if detected_language == 'en' and quick_transcription:
                    emit_progress(session_id, 'language_detection', 52, 'Pure English detected, verifying...')
                    
                    # Quick English verification
                    english_test_cmd = [
                        whisper_exe,
                        "-m", quick_model,
                        "-f", audio_path,
                        "-l", "en",
                        "--output-txt",
                        "--output-file", transcription_file.replace('.txt', '_english_test')
                    ]
                    
                    english_result = subprocess.run(english_test_cmd, capture_output=True, text=True, check=False)
                    
                    if english_result.returncode == 0:
                        english_transcription = ""
                        if os.path.exists(transcription_file.replace('.txt', '_english_test.txt')):
                            with open(transcription_file.replace('.txt', '_english_test.txt'), 'r', encoding='utf-8') as f:
                                english_transcription = f.read().strip()
                            
                            # Compare quality: if English version is significantly better, use English
                            if english_transcription and len(english_transcription) > len(quick_transcription) * 1.2:
                                logger.debug("English model gave significantly better results")
                                model_path, detected_language = detect_language_and_select_model(english_transcription, "en")
                            else:
                                # Similar quality or Tamil version better = likely mixed content
                                logger.debug("Similar quality suggests mixed Tamil-English content")
                                model_path, detected_language = "./whisper.cpp/models/ggml-base.bin", "ta"
                
                logger.debug(f"Tamil-English optimized detection result - Model: {model_path}, Language: {detected_language}")
                emit_progress(session_id, 'language_detection', 55, f'Optimized for {detected_language}: {get_language_description(detected_language)}')
            else:
                # No tiny model available - default to Tamil for better mixed language handling
                model_path = base_model_path
                detected_language = "ta"
                logger.debug("Tiny model not available, defaulting to Tamil (better for Tamil-English mixed)")
                emit_progress(session_id, 'language_detection', 55, 'Using Tamil model (optimized for mixed Tamil-English)')

        # Final transcription with optimized model
        emit_progress(session_id, 'transcription', 60, f'Starting transcription with {os.path.basename(model_path)} ({get_language_description(detected_language)})...')
        
        logger.debug(f"Running whisper-cli with file: {audio_path}, language: {detected_language}")
        
        # Enhanced whisper command with optimizations
        whisper_cmd = [
            whisper_exe,
            "-m", model_path,
            "-f", audio_path,
            "-l", detected_language,
            "--output-txt",
            "--output-file", transcription_file.replace('.txt', ''),  # whisper adds .txt automatically
            "--diarize",  # Speaker separation
            "--print-progress",  # Show progress for real-time parsing
            "--print-colors"  # Easier to parse output
        ]
        
        # Try to add VAD if model is available
        vad_model_path = "./whisper.cpp/models/ggml-vad.bin"
        if os.path.exists(vad_model_path):
            whisper_cmd.extend([
                "--vad",  # Voice Activity Detection - skip silent parts
                "--vad-model", vad_model_path,
                "--vad-threshold", "0.3",  # Sensitivity for detecting speech
                "--vad-min-speech-duration-ms", "250",  # Minimum speech duration
                "--vad-min-silence-duration-ms", "500",  # Minimum silence to split
            ])
            emit_progress(session_id, 'transcription', 65, 'Whisper processing with VAD + Speaker Detection...')
            logger.debug("Using VAD model for silence skipping")
        else:
            emit_progress(session_id, 'transcription', 65, 'Whisper processing with Speaker Detection (VAD model not available)...')
            logger.info("VAD model not found, processing without silence skipping")
        
        # Show transcription area immediately when starting
        emit_progress(session_id, 'transcription', 67, 'Whisper starting... Real-time transcription will appear below')
        
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
            return jsonify({'error': f'Whisper transcription failed: {stderr}', 'session_id': session_id}), 500

        emit_progress(session_id, 'transcription', 80, 'Transcription completed! Reading results...')

        # Read transcription
        if not os.path.exists(transcription_file):
            return jsonify({'error': f'Transcription file not created: {transcription_file}', 'session_id': session_id}), 500
        
        with open(transcription_file, 'r', encoding='utf-8') as f:
            transcription = f.read().strip()
        logger.debug(f"Transcription content: {transcription}")

        if not transcription:
            return jsonify({'error': 'Transcription is empty. The audio might be too quiet or contain no speech.', 'session_id': session_id}), 400

        emit_progress(session_id, 'summarization', 85, 'Generating AI summary...')

        # Smart Summarization with backup
        summary = ""
        try:
            summary = create_openai_summary(transcription)
            logger.debug(f"OpenAI Summary: {summary}")
            emit_progress(session_id, 'summarization', 90, 'OpenAI summary generated!')
        except Exception as e:
            logger.warning(f"OpenAI summarization failed: {str(e)}")
            emit_progress(session_id, 'summarization', 87, 'OpenAI failed, trying offline summarization...')
            logger.info("Falling back to offline T5 summarization")
            try:
                summary = create_offline_summary(transcription)
                logger.debug(f"Offline Summary: {summary}")
                emit_progress(session_id, 'summarization', 90, 'Offline summary generated!')
            except Exception as e2:
                logger.error(f"Both summarization methods failed: OpenAI: {str(e)}, Offline: {str(e2)}")
                # Fallback to simple text truncation
                summary = f"Summary unavailable (API error). Transcription preview: {transcription[:200]}..."
                emit_progress(session_id, 'summarization', 90, 'Using fallback summary method')

        emit_progress(session_id, 'saving', 95, 'Saving results to database...')

        # Save to database
        c.execute("INSERT INTO summaries (transcription, summary) VALUES (?, ?)", 
                  (transcription, summary))
        conn.commit()

        emit_progress(session_id, 'cleanup', 98, 'Cleaning up temporary files...')

        # Clean up temporary files
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

        emit_progress(session_id, 'complete', 100, 'Processing completed successfully!')

        return jsonify({
            'id': c.lastrowid, 
            'summary': summary,
            'transcription': transcription[:200] + '...' if len(transcription) > 200 else transcription,
            'session_id': session_id
        })

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
    """Health check endpoint to verify server is running"""
    return jsonify({
        'status': 'healthy',
        'whisper_available': os.path.exists("./whisper.cpp/build/bin/whisper-cli"),
        'model_available': os.path.exists("./whisper.cpp/models/ggml-base.bin"),
        'tiny_model_available': os.path.exists("./whisper.cpp/models/ggml-tiny.bin"),
        'vad_model_available': os.path.exists("./whisper.cpp/models/ggml-vad.bin"),
        'ffmpeg_available': subprocess.run(['which', 'ffmpeg'], capture_output=True).returncode == 0,
        'openai_configured': bool(openai_api_key),
        'offline_summarization_available': OFFLINE_SUMMARIZATION_AVAILABLE,
        'websocket_enabled': True
    })

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
    """Run whisper with real-time output streaming"""
    import subprocess
    import select
    import os
    import fcntl
    import re
    import time
    import threading
    
    try:
        logger.info(f"Starting real-time whisper with command: {' '.join(whisper_cmd)}")
        
        # Extract output file path from command
        output_file = None
        for i, arg in enumerate(whisper_cmd):
            if arg == "--output-file" and i + 1 < len(whisper_cmd):
                output_file = whisper_cmd[i + 1] + ".txt"
                break
        
        # Function to monitor output file for changes
        def monitor_output_file():
            if not output_file:
                return
            
            last_size = 0
            chunk_count = 0
            
            while True:
                try:
                    if os.path.exists(output_file):
                        current_size = os.path.getsize(output_file)
                        if current_size > last_size:
                            # File has grown, read new content
                            with open(output_file, 'r', encoding='utf-8') as f:
                                f.seek(last_size)
                                new_content = f.read()
                                
                                # Parse new content for transcription chunks
                                lines = new_content.strip().split('\n')
                                for line in lines:
                                    if line.strip() and not line.startswith('[') and len(line.strip()) > 10:
                                        chunk_count += 1
                                        # Create simulated timestamp
                                        minutes = (chunk_count - 1) * 5 // 60
                                        seconds = (chunk_count - 1) * 5 % 60
                                        end_minutes = chunk_count * 5 // 60
                                        end_seconds = chunk_count * 5 % 60
                                        
                                        transcription_chunk = {
                                            'timestamp': f'[{minutes:02d}:{seconds:02d}:00.000 --> {end_minutes:02d}:{end_seconds:02d}:00.000]',
                                            'text': line.strip()[:100] + ('...' if len(line.strip()) > 100 else ''),
                                            'chunk_number': chunk_count
                                        }
                                        
                                        emit_progress(session_id, 'transcription', 70 + min(chunk_count * 2, 15), 
                                                    f'Transcribing: {line.strip()[:50]}...', 
                                                    transcription_chunk)
                                        
                            last_size = current_size
                            
                    time.sleep(2)  # Check every 2 seconds
                except Exception as e:
                    logger.debug(f"File monitoring error: {e}")
                    time.sleep(1)
        
        # Start file monitoring in background thread
        if output_file:
            monitor_thread = threading.Thread(target=monitor_output_file, daemon=True)
            monitor_thread.start()
        
        # Run whisper process
        process = subprocess.Popen(
            whisper_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=True,
            bufsize=1
        )
        
        # Make stdout non-blocking for real-time reading
        fd = process.stdout.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        
        output_lines = []
        current_transcription = ""
        chunk_count = 0
        
        # Regex patterns for different whisper output formats
        timestamp_patterns = [
            r'\[(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})\]\s*(.+)',  # Standard format
            r'\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s*(.+)',  # Simple timestamp
            r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})\s*(.+)',  # No brackets
        ]
        
        while True:
            # Check if process is still running
            if process.poll() is not None:
                break
                
            try:
                # Try to read output
                ready, _, _ = select.select([process.stdout], [], [], 0.5)
                if ready:
                    line = process.stdout.readline()
                    if line:
                        line = line.strip()
                        output_lines.append(line)
                        logger.debug(f"Whisper output line: {line}")
                        
                        # Try to parse transcription chunks with multiple patterns
                        transcription_found = False
                        
                        for pattern in timestamp_patterns:
                            match = re.match(pattern, line)
                            if match:
                                transcription_found = True
                                
                                if len(match.groups()) == 3:
                                    # Full timestamp format
                                    start_time, end_time, text = match.groups()
                                    timestamp_display = f"[{start_time} --> {end_time}]"
                                else:
                                    # Simple timestamp format
                                    start_time, text = match.groups()
                                    timestamp_display = f"[{start_time}]"
                                
                                if text.strip():
                                    chunk_count += 1
                                    transcription_chunk = {
                                        'timestamp': timestamp_display,
                                        'text': text.strip(),
                                        'full_line': line,
                                        'chunk_number': chunk_count
                                    }
                                    current_transcription += f"{timestamp_display} {text.strip()}\n"
                                    
                                    logger.info(f"Transcription chunk #{chunk_count}: {text.strip()[:50]}...")
                                    
                                    # Emit real-time transcription update
                                    emit_progress(session_id, 'transcription', 70 + (chunk_count % 10), 
                                                f'Transcribing: {text.strip()[:50]}...', 
                                                transcription_chunk)
                                break
                        
                        # Also check for other whisper progress indicators
                        if not transcription_found:
                            # Look for progress indicators
                            if 'progress' in line.lower() or '%' in line:
                                emit_progress(session_id, 'transcription', 65, f'Whisper: {line[:100]}...')
                            elif 'processing' in line.lower():
                                emit_progress(session_id, 'transcription', 60, f'Whisper: {line[:100]}...')
                
            except Exception as e:
                # Non-blocking read might fail, continue
                logger.debug(f"Non-blocking read exception: {e}")
                continue
        
        # Wait for process to complete and get final output
        stdout, stderr = process.communicate()
        if stdout:
            output_lines.extend(stdout.split('\n'))
            logger.info(f"Final whisper output: {len(output_lines)} lines")
        
        if stderr:
            logger.warning(f"Whisper stderr: {stderr}")
            
        logger.info(f"Real-time whisper completed. Total chunks emitted: {chunk_count}")
        return process.returncode, '\n'.join(output_lines), stderr
        
    except Exception as e:
        logger.error(f"Error in real-time whisper execution: {e}")
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