from flask import Flask, request, jsonify, send_from_directory, send_file
import os
import logging
from werkzeug.utils import secure_filename
import tempfile
import time
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import re
import subprocess
import shutil

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='')

# Configuration for transcription modes
TRANSCRIPTION_MODE = os.getenv('TRANSCRIPTION_MODE', 'hybrid')  # 'online', 'offline', 'hybrid'
WHISPER_CPP_PATH = os.getenv('WHISPER_CPP_PATH', './whisper.cpp/build/bin/whisper-cli')
WHISPER_MODEL_PATH = os.getenv('WHISPER_MODEL_PATH', './whisper.cpp/models/ggml-base.bin')

# Initialize OpenAI client lazily
_openai_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    return _openai_client

def check_offline_availability():
    """Check if offline transcription is available"""
    try:
        return (os.path.exists(WHISPER_CPP_PATH) and 
                os.path.exists(WHISPER_MODEL_PATH) and
                os.access(WHISPER_CPP_PATH, os.X_OK))
    except Exception:
        return False

def check_online_availability():
    """Check if online transcription is available"""
    return bool(os.getenv('OPENAI_API_KEY'))

def transcribe_offline(audio_file_path, language="en"):
    """Transcribe audio using local whisper.cpp"""
    try:
        logger.info(f"OFFLINE MODE: Using local whisper.cpp for transcription")
        
        # Check if audio format conversion is needed
        supported_formats = ['.flac', '.mp3', '.ogg', '.wav']
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        
        working_file = audio_file_path
        converted_file = None
        
        if file_ext not in supported_formats:
            logger.info(f"Converting {file_ext} to WAV format for whisper.cpp compatibility")
            try:
                # Convert to WAV using ffmpeg if available
                converted_file = audio_file_path + '.wav'
                result = subprocess.run([
                    'ffmpeg', '-i', audio_file_path, '-ar', '16000', '-ac', '1', '-y', converted_file
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    working_file = converted_file
                    logger.info(f"Successfully converted to WAV: {working_file}")
                else:
                    logger.warning(f"Format conversion failed: {result.stderr}")
                    raise Exception(f"Unsupported format {file_ext} and conversion failed")
                    
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                logger.warning(f"ffmpeg not available or conversion failed: {str(e)}")
                raise Exception(f"Unsupported format {file_ext} and no ffmpeg available for conversion")
        
        # Prepare whisper-cli command (updated syntax)
        cmd = [
            WHISPER_CPP_PATH,
            '-m', WHISPER_MODEL_PATH,
            '-f', working_file,
            '-l', language,
            '-t', '4',  # Use 4 threads
            '--output-txt',  # Output text format
            '--no-prints'    # Suppress verbose output
        ]
        
        logger.info(f"Running whisper-cli: {' '.join(cmd)}")
        
        # Run whisper-cli
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise Exception(f"Whisper-cli failed: {result.stderr}")
        
        # Read the output text file
        output_txt = working_file + '.txt'
        if os.path.exists(output_txt):
            with open(output_txt, 'r', encoding='utf-8') as f:
                transcription = f.read().strip()
            
            # Clean up the output file
            os.remove(output_txt)
            
            # Clean up converted file if it was created
            if converted_file and os.path.exists(converted_file):
                os.remove(converted_file)
            
            logger.info(f"Offline transcription completed: {transcription[:100]}...")
            return transcription
        else:
            raise Exception("Whisper-cli output file not found")
            
    except subprocess.TimeoutExpired:
        # Clean up converted file if it exists
        if converted_file and os.path.exists(converted_file):
            os.remove(converted_file)
        raise Exception("Offline transcription timed out")
    except Exception as e:
        # Clean up converted file if it exists
        if converted_file and os.path.exists(converted_file):
            os.remove(converted_file)
        logger.error(f"Offline transcription failed: {str(e)}")
        raise

def transcribe_online(audio_file_path, language="en"):
    """Transcribe audio using OpenAI Whisper API"""
    try:
        logger.info("ONLINE MODE: Using OpenAI Whisper API for transcription")
        
        client = get_openai_client()
        with open(audio_file_path, 'rb') as audio_file:
            logger.info("ENGLISH-DIRECT TRANSCRIPTION: Using English model for Tamil-English mixed speech")
            
            transcription_response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                prompt="Mixed conversation with Tamil and English words",
                response_format="text"
            )
            
            transcription = transcription_response.strip()
            logger.info(f"Online transcription completed: {transcription[:100]}...")
            return transcription
            
    except Exception as e:
        logger.error(f"Online transcription failed: {str(e)}")
        raise

def transcribe_audio(audio_file_path, language="en"):
    """Main transcription function with mode selection and fallback"""
    offline_available = check_offline_availability()
    online_available = check_online_availability()
    
    logger.info(f"Transcription mode: {TRANSCRIPTION_MODE}")
    logger.info(f"Offline available: {offline_available}, Online available: {online_available}")
    
    if TRANSCRIPTION_MODE == 'offline':
        if not offline_available:
            raise Exception("Offline mode requested but whisper.cpp not available")
        return transcribe_offline(audio_file_path, language), "offline"
        
    elif TRANSCRIPTION_MODE == 'online':
        if not online_available:
            raise Exception("Online mode requested but OpenAI API key not available")
        return transcribe_online(audio_file_path, language), "online"
        
    elif TRANSCRIPTION_MODE == 'hybrid':
        # Try offline first, fallback to online
        if offline_available:
            try:
                return transcribe_offline(audio_file_path, language), "offline"
            except Exception as e:
                logger.warning(f"Offline transcription failed, trying online: {str(e)}")
                
        if online_available:
            try:
                return transcribe_online(audio_file_path, language), "online"
            except Exception as e:
                logger.error(f"Online transcription also failed: {str(e)}")
                raise Exception("Both offline and online transcription failed")
        else:
            raise Exception("No transcription method available")
    
    else:
        raise Exception(f"Invalid transcription mode: {TRANSCRIPTION_MODE}")

# Database setup for saving results
def init_db():
    conn = sqlite3.connect('transcriptions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transcriptions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT,
                  transcription TEXT,
                  summary TEXT,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  file_size INTEGER)''')
    conn.commit()
    return conn

def clean_transcription_artifacts(transcription):
    """Remove transcription artifacts and repetitive content"""
    if not transcription:
        return transcription
    
    # Split into lines
    lines = transcription.split('\n')
    cleaned_lines = []
    seen_lines = set()
    
    for line in lines:
        # Clean up each line
        line = line.strip()
        
        # Remove excessive trailing punctuation (3+ dots to single dot)
        line = re.sub(r'\.{3,}', '.', line)
        line = re.sub(r'[.!?]{2,}', '.', line)
        
        # Skip very short fragments (less than 3 characters)
        if len(line) < 3:
            continue
            
        # Skip standalone punctuation lines
        if re.match(r'^[.!?•\-\s]*$', line):
            continue
        
        # Remove consecutive duplicate lines
        if line not in seen_lines:
            cleaned_lines.append(line)
            seen_lines.add(line)
    
    # Join back and ensure proper sentence endings
    result = '\n'.join(cleaned_lines)
    
    # Fix sentence endings
    result = re.sub(r'([^.!?])\s*$', r'\1.', result)
    
    return result

# Ensure directories exist
os.makedirs('Uploads', exist_ok=True)
os.makedirs('Results', exist_ok=True)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_audio():
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400

        file = request.files['audio']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Check if any transcription method is available
        offline_available = check_offline_availability()
        online_available = check_online_availability()
        
        if not offline_available and not online_available:
            return jsonify({'error': 'No transcription method available. Need either OpenAI API key or whisper.cpp setup.'}), 500

        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        timestamp = str(int(time.time()))
        safe_filename = f"{timestamp}_{filename}"
        
        upload_path = os.path.join('Uploads', safe_filename)
        file.save(upload_path)
        file_size = os.path.getsize(upload_path)

        # Create temporary file for transcription
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            file.seek(0)
            temp_file.write(file.read())
            temp_file_path = temp_file.name

        logger.info(f"Processing audio file: {filename} ({file_size} bytes)")

        # Use the new transcription function
        transcription, used_mode = transcribe_audio(temp_file_path, "en")
        logger.info(f"Transcription completed using {used_mode} mode: {transcription[:100]}...")

        # Format transcription with bullet points
        if transcription and len(transcription.strip()) > 0:
            sentences = []
            current_sentence = ""
            
            for char in transcription:
                current_sentence += char
                if char in '.!?' or (char == '\n' and current_sentence.strip()):
                    if current_sentence.strip():
                        sentences.append(current_sentence.strip())
                        current_sentence = ""
            
            if current_sentence.strip():
                sentences.append(current_sentence.strip())
            
            if len(sentences) > 1:
                formatted_sentences = []
                for sentence in sentences:
                    if sentence.strip():
                        formatted_sentences.append(f"• {sentence.strip()}")
                transcription = "\n".join(formatted_sentences)
            
            # Apply post-processing cleanup
            logger.info("Applying post-processing cleanup...")
            transcription = clean_transcription_artifacts(transcription)
            logger.info(f"Cleaned transcription: {transcription[:100]}...")

        # Store in database
        conn = init_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transcriptions (filename, transcription, created_at, file_size)
            VALUES (?, ?, datetime('now'), ?)
        ''', (safe_filename, transcription, file_size))
        
        transcription_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Save transcription file
        transcription_file = f"Results/transcription_{transcription_id}.txt"
        with open(transcription_file, 'w', encoding='utf-8') as f:
            f.write(transcription)

        # Clean up temporary files
        try:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary files: {str(e)}")

        return jsonify({
            'success': True,
            'transcription': transcription,
            'transcription_id': transcription_id,
            'filename': safe_filename,
            'transcription_mode': used_mode,
            'download_url': f'/download/transcription/{transcription_id}'
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        # Clean up files if they exist
        try:
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            if 'upload_path' in locals() and os.path.exists(upload_path):
                os.unlink(upload_path)
        except:
            pass
        return jsonify({'error': str(e)}), 500

@app.route('/summarize', methods=['POST'])
def summarize_transcription():
    try:
        data = request.get_json()
        transcription = data.get('transcription', '')
        transcription_id = data.get('transcription_id')
        
        if not transcription:
            return jsonify({'error': 'No transcription provided'}), 400

        # Check if OpenAI API key is configured
        if not os.getenv('OPENAI_API_KEY'):
            return jsonify({'error': 'OpenAI API key required for summarization'}), 500

        client = get_openai_client()
        logger.info("Generating summary with OpenAI GPT")

        summary_prompt = f"""
Create a clear, accurate meeting summary based ONLY on the content provided. Do not add information that is not explicitly mentioned in the transcription.

STRICT INSTRUCTIONS:
- Only summarize what is actually said in the transcription
- Do not invent or assume details not present
- If speakers are not clearly identifiable, use "Speaker" or "Participant" 
- Focus on factual content and actual decisions mentioned
- Keep language natural and concise

TRANSCRIPTION TO SUMMARIZE:
{transcription}

Please provide a summary in this format:

## Meeting Summary

### Main Topics Discussed:
[List only topics actually mentioned in the transcription]

### Key Points:
[Bullet points of important information actually discussed]

### Decisions or Actions Mentioned:
[Only list decisions/actions explicitly stated in the conversation]

### Technical Details:
[Any technical information, features, or implementation details mentioned]

### Questions or Issues Raised:
[Questions or concerns actually voiced in the discussion]

Important: Base this summary strictly on the provided transcription content. Do not extrapolate or add context not present in the original text.
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert meeting secretary who creates clear, actionable meeting summaries in Minutes of Meeting format with awareness of English/Tamil mixed conversations."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )

        summary = response.choices[0].message.content

        # Update database with summary
        if transcription_id:
            conn = init_db()
            c = conn.cursor()
            c.execute("UPDATE transcriptions SET summary = ? WHERE id = ?", (summary, transcription_id))
            conn.commit()
            conn.close()

            # Save summary file
            summary_file = f"Results/summary_{transcription_id}.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"Generated using: OpenAI GPT-3.5\n\n{summary}")

        logger.info("Summary generated successfully")

        return jsonify({
            'success': True,
            'summary': summary,
            'download_url': f'/download/summary/{transcription_id}' if transcription_id else None
        })

    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/transcription/<int:transcription_id>')
def download_transcription(transcription_id):
    """Download transcription file"""
    try:
        transcription_file = f"Results/transcription_{transcription_id}.txt"
        if os.path.exists(transcription_file):
            return send_file(transcription_file, as_attachment=True, download_name=f"transcription_{transcription_id}.txt")
        else:
            return jsonify({'error': 'Transcription file not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/summary/<int:transcription_id>')
def download_summary(transcription_id):
    """Download summary file"""
    try:
        summary_file = f"Results/summary_{transcription_id}.txt"
        if os.path.exists(summary_file):
            return send_file(summary_file, as_attachment=True, download_name=f"summary_{transcription_id}.txt")
        else:
            return jsonify({'error': 'Summary file not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def get_history():
    """Get list of all processed transcriptions"""
    try:
        conn = init_db()
        c = conn.cursor()
        c.execute("""SELECT id, filename, created_at, file_size,
                     CASE WHEN summary IS NOT NULL THEN 1 ELSE 0 END as has_summary
                     FROM transcriptions ORDER BY created_at DESC""")
        
        history = []
        for row in c.fetchall():
            history.append({
                'id': row[0],
                'filename': row[1],
                'created_at': row[2],
                'file_size': row[3],
                'has_summary': bool(row[4]),
                'transcription_url': f'/download/transcription/{row[0]}',
                'summary_url': f'/download/summary/{row[0]}' if row[4] else None
            })
        
        conn.close()
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    try:
        openai_configured = bool(os.getenv('OPENAI_API_KEY'))
        
        # Check database
        conn = init_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM transcriptions")
        total_transcriptions = c.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'openai_configured': openai_configured,
            'service': 'OpenAI Whisper direct English transcription for Tamil-English mixed speech',
            'total_transcriptions': total_transcriptions,
            'features': [
                'direct_english_transcription',
                'tamil_english_mixed_support',
                'clean_formatting',
                'no_hallucination',
                'download_history',
                'post_processing_cleanup',
                'enhanced_summary_accuracy',
                'repetition_removal'
            ]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/set-transcription-mode', methods=['POST'])
def set_transcription_mode():
    """Set transcription mode dynamically"""
    try:
        data = request.get_json()
        new_mode = data.get('mode')
        
        if new_mode not in ['online', 'offline', 'hybrid']:
            return jsonify({'error': 'Invalid mode. Must be: online, offline, or hybrid'}), 400
        
        global TRANSCRIPTION_MODE
        TRANSCRIPTION_MODE = new_mode
        
        # Check availability with new mode
        offline_available = check_offline_availability()
        online_available = check_online_availability()
        
        return jsonify({
            'success': True,
            'transcription_mode': TRANSCRIPTION_MODE,
            'offline_available': offline_available,
            'online_available': online_available,
            'message': f'Transcription mode set to {new_mode.upper()}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/transcription-status', methods=['GET'])
def transcription_status():
    """Get current transcription capabilities and mode"""
    try:
        offline_available = check_offline_availability()
        online_available = check_online_availability()
        
        return jsonify({
            'transcription_mode': TRANSCRIPTION_MODE,
            'offline_available': offline_available,
            'online_available': online_available,
            'whisper_cpp_path': WHISPER_CPP_PATH if offline_available else None,
            'whisper_model_path': WHISPER_MODEL_PATH if offline_available else None,
            'capabilities': {
                'can_transcribe': offline_available or online_available,
                'preferred_mode': 'offline' if offline_available and TRANSCRIPTION_MODE in ['offline', 'hybrid'] else 'online',
                'fallback_available': offline_available and online_available and TRANSCRIPTION_MODE == 'hybrid'
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Check transcription capabilities
    offline_available = check_offline_availability()
    online_available = check_online_availability()
    
    # Print startup information
    mode_str = f"Mode: {TRANSCRIPTION_MODE.upper()}"
    capability_str = []
    
    if offline_available:
        capability_str.append("Offline✓")
    if online_available:
        capability_str.append("Online✓")
    
    if not capability_str:
        capability_str.append("No transcription available")
    
    capabilities = " | ".join(capability_str)
    
    print(f"🎙️ Meeting Recorder: Tamil→English | {mode_str} | {capabilities} | http://localhost:9000")
    
    if not offline_available and not online_available:
        print("⚠️  ERROR: No transcription method available!")
        print("   Set OPENAI_API_KEY or ensure whisper.cpp is built")
    
    app.run(host='0.0.0.0', port=9000, debug=False) 