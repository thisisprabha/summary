from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import subprocess
import openai
import os
import logging
from werkzeug.utils import secure_filename
import tempfile
import time

# Set up logging
logging.basicConfig(level=logging.DEBUG, filename='app.log')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='')

# Get OpenAI API key from environment variable (more secure)
openai.api_key = os.getenv('OPENAI_API_KEY', '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')

# Set up SQLite
conn = sqlite3.connect('meetings.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS summaries
             (id INTEGER PRIMARY KEY, transcription TEXT, summary TEXT, tag TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/upload', methods=['POST'])
def upload_audio():
    try:
        # Ensure Uploads folder exists with correct permissions
        uploads_dir = os.path.join(os.getcwd(), 'Uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        os.chmod(uploads_dir, 0o755)
        logger.debug(f"Uploads directory: {uploads_dir} with permissions: {oct(os.stat(uploads_dir).st_mode)[-3:]}")

        # Save uploaded audio file
        audio_file = request.files.get('audio')
        if not audio_file:
            return jsonify({'error': 'No audio file provided'}), 400
        
        # Secure the filename
        audio_filename = secure_filename(audio_file.filename)
        if not audio_filename:
            audio_filename = f"audio_{int(time.time())}.webm"
        
        audio_path = os.path.join(uploads_dir, audio_filename)
        audio_file.save(audio_path)
        logger.debug(f"Saved audio file to: {audio_path}")

        # Verify file exists and is readable
        if not os.path.exists(audio_path) or not os.access(audio_path, os.R_OK):
            return jsonify({'error': f'Failed to access audio file: {audio_path}'}), 500

        # Check if file has audio content
        if os.path.getsize(audio_path) == 0:
            return jsonify({'error': 'Audio file is empty'}), 400

        # Convert to WAV format for whisper.cpp (handle various input formats)
        wav_filename = os.path.splitext(audio_filename)[0] + '.wav'
        wav_path = os.path.join(uploads_dir, wav_filename)
        
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
            return jsonify({'error': f'Audio conversion failed: {result.stderr}'}), 500
        
        audio_path = wav_path  # Use converted file
        logger.debug(f"Converted to WAV: {audio_path}")

        # Clear old transcription file
        transcription_file = os.path.join(os.getcwd(), 'whisper.cpp/transcription.txt')
        if os.path.exists(transcription_file):
            os.remove(transcription_file)
            logger.debug(f"Removed old transcription file: {transcription_file}")

        # Check if whisper.cpp executable exists
        whisper_exe = "./whisper.cpp/build/bin/whisper-cli"
        if not os.path.exists(whisper_exe):
            return jsonify({'error': f'Whisper executable not found at {whisper_exe}. Please build whisper.cpp first.'}), 500

        # Check if model exists
        model_path = "./whisper.cpp/models/for-tests-ggml-base.bin"
        if not os.path.exists(model_path):
            return jsonify({'error': f'Whisper model not found at {model_path}. Please download the model first.'}), 500

        # Transcribe with whisper-cli
        logger.debug(f"Running whisper-cli with file: {audio_path}")
        whisper_cmd = [
            whisper_exe,
            "-m", model_path,
            "-f", audio_path,
            "-l", "auto",  # Auto-detect language (change to "ta" for Tamil, "en" for English)
            "--output-txt",
            "--output-file", transcription_file.replace('.txt', '')  # whisper adds .txt automatically
        ]
        
        result = subprocess.run(whisper_cmd, capture_output=True, text=True, check=False)
        logger.debug(f"Whisper-cli stdout: {result.stdout}")
        
        if result.returncode != 0:
            logger.error(f"Whisper-cli stderr: {result.stderr}")
            return jsonify({'error': f'Whisper transcription failed: {result.stderr}'}), 500

        # Read transcription
        if not os.path.exists(transcription_file):
            return jsonify({'error': f'Transcription file not created: {transcription_file}'}), 500
        
        with open(transcription_file, 'r', encoding='utf-8') as f:
            transcription = f.read().strip()
        logger.debug(f"Transcription content: {transcription}")

        if not transcription:
            return jsonify({'error': 'Transcription is empty. The audio might be too quiet or contain no speech.'}), 400

        # Summarize with GPT-4o-mini
        try:
            summary_response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Summarize the following meeting transcript into 2-3 sentences highlighting the key points and decisions:"},
                    {"role": "user", "content": transcription}
                ],
                max_tokens=150,
                temperature=0.7
            )
            summary = summary_response.choices[0].message.content.strip()
            logger.debug(f"Summary: {summary}")
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return jsonify({'error': f'Failed to generate summary: {str(e)}'}), 500

        # Save to database
        c.execute("INSERT INTO summaries (transcription, summary) VALUES (?, ?)", 
                  (transcription, summary))
        conn.commit()

        # Clean up temporary files
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
            if audio_path != os.path.join(uploads_dir, audio_filename) and os.path.exists(os.path.join(uploads_dir, audio_filename)):
                os.remove(os.path.join(uploads_dir, audio_filename))
        except Exception as e:
            logger.warning(f"Failed to clean up temporary files: {e}")

        return jsonify({
            'id': c.lastrowid, 
            'summary': summary,
            'transcription': transcription[:200] + '...' if len(transcription) > 200 else transcription
        })

    except subprocess.CalledProcessError as e:
        logger.error(f"Subprocess failed: {e.stderr}")
        return jsonify({'error': f'Processing failed: {e.stderr}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

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
        'model_available': os.path.exists("./whisper.cpp/models/for-tests-ggml-base.bin"),
        'ffmpeg_available': subprocess.run(['which', 'ffmpeg'], capture_output=True).returncode == 0
    })

if __name__ == '__main__':
    # Ensure required directories exist
    os.makedirs('Uploads', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🎤 Meeting Recorder & Summarizer Server Starting...")
    print("📁 Make sure you have:")
    print("   - whisper.cpp built at ./whisper.cpp/build/bin/whisper-cli")
    print("   - Model file at ./whisper.cpp/models/for-tests-ggml-base.bin")
    print("   - ffmpeg installed and accessible")
    print("   - OpenAI API key set (either in environment or in code)")
    print(f"🌐 Server will be available at: http://localhost:9000")
    
    app.run(host='0.0.0.0', port=9000, debug=True)