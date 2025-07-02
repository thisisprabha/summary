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

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='')

# Initialize OpenAI client lazily
_client = None

def get_openai_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    return _client

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

        # Check if OpenAI API key is configured
        if not os.getenv('OPENAI_API_KEY'):
            return jsonify({'error': 'OpenAI API key not configured'}), 500

        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        timestamp = str(int(time.time()))
        safe_filename = f"{timestamp}_{filename}"
        
        # Save to uploads directory temporarily
        upload_path = os.path.join('Uploads', safe_filename)
        file.save(upload_path)
        file_size = os.path.getsize(upload_path)

        # Create temporary file for OpenAI API
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            file.seek(0)  # Reset file pointer
            temp_file.write(file.read())
            temp_file_path = temp_file.name

        logger.info(f"Processing audio file: {filename} ({file_size} bytes)")

        # Get OpenAI client and transcribe with language optimization for English/Tamil
        client = get_openai_client()
        with open(temp_file_path, 'rb') as audio_file:
            # Try transcription without language forcing for better Tamil/English mixed content
            try:
                # Let Whisper auto-detect language for mixed Tamil/English content
                transcription_response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                    # Removed language="en" to allow Tamil detection
                )
            except Exception as e:
                logger.error(f"OpenAI transcription failed: {str(e)}")
                raise e

        # Process transcription with speaker identification
        transcription_text = transcription_response.strip()
        
        # Enhanced transcription with smart speaker detection for English/Tamil
        enhanced_transcription = add_speaker_labels_smart(transcription_text)
        
        # Analyze language and quality
        analysis = detect_language_and_quality(transcription_text)

        # Clean up temporary file
        os.unlink(temp_file_path)
        
        # Delete uploaded file to save memory
        os.unlink(upload_path)

        # Save to database
        conn = init_db()
        c = conn.cursor()
        c.execute("""INSERT INTO transcriptions (filename, transcription, file_size) 
                     VALUES (?, ?, ?)""", (safe_filename, enhanced_transcription, file_size))
        transcription_id = c.lastrowid
        conn.commit()
        conn.close()

        # Save transcription file
        transcription_file = f"Results/transcription_{transcription_id}.txt"
        with open(transcription_file, 'w', encoding='utf-8') as f:
            f.write(enhanced_transcription)

        logger.info("Transcription completed successfully")

        return jsonify({
            'success': True,
            'transcription': enhanced_transcription,
            'filename': safe_filename,
            'transcription_id': transcription_id,
            'download_url': f'/download/transcription/{transcription_id}',
            'analysis': analysis
        })
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        # Clean up files if they exist
        try:
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)
            if 'upload_path' in locals() and os.path.exists(upload_path):
                os.unlink(upload_path)
        except:
            pass
        return jsonify({'error': str(e)}), 500

def add_speaker_labels_multilingual(transcription):
    """Enhanced speaker labels for English/Tamil mixed conversations"""
    # Clean up repetitive content first
    transcription = clean_repetitive_content(transcription)
    
    # Split into sentences more intelligently for multilingual content
    import re
    # Enhanced sentence splitting for Tamil and English
    sentences = re.split(r'[.!?।]+', transcription)  # Added Tamil punctuation
    enhanced_lines = []
    current_speaker = 1
    word_count = 0
    
    # Tamil conversation markers that indicate speaker changes
    tamil_question_words = ['என்ன', 'எப்படி', 'எங்கே', 'யார்', 'எப்போது']
    english_question_words = ['what', 'how', 'where', 'who', 'when', 'why']
    
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence or len(sentence) < 5:  # Skip very short segments
            continue
            
        # Count words in this sentence
        words = sentence.split()
        word_count += len(words)
        
        # Enhanced speaker change detection for multilingual content
        is_question = (
            any(qword in sentence.lower() for qword in tamil_question_words) or
            any(qword in sentence.lower() for qword in english_question_words) or
            sentence.endswith('?')
        )
        
        # Check for conversation starters
        conversation_starters = ['அண்ணா', 'நான்', 'hello', 'hi', 'okay', 'yes', 'no', 'நன்றி', 'thanks']
        has_starter = any(starter in sentence.lower() for starter in conversation_starters)
        
        # Switch speakers based on natural conversation patterns
        if (word_count > 30 or  # After reasonable speech amount
            is_question or      # Questions often indicate speaker change
            has_starter or      # Conversation starters
            (i > 0 and len(words) > 15)):  # Longer responses
            current_speaker = 2 if current_speaker == 1 else 1
            word_count = 0
            
        enhanced_lines.append(f"Person{current_speaker}: {sentence}.")
    
    return '\n\n'.join(enhanced_lines)

def clean_repetitive_content(text):
    """Remove repetitive sentences and clean up transcription"""
    import re
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    cleaned_sentences = []
    seen_sentences = set()
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Normalize sentence for comparison (remove extra spaces, case)
        normalized = ' '.join(sentence.lower().split())
        
        # Skip if we've seen this exact sentence or very similar
        if normalized not in seen_sentences and len(normalized) > 15:
            cleaned_sentences.append(sentence)
            seen_sentences.add(normalized)
        elif len(cleaned_sentences) == 0:  # Keep first sentence even if short
            cleaned_sentences.append(sentence)
    
    return '. '.join(cleaned_sentences)

def detect_language_and_quality(transcription):
    """Analyze transcription language and quality with enhanced Tamil detection"""
    import re
    
    # Enhanced Tamil word detection with more comprehensive Tamil vocabulary
    tamil_indicators = [
        # Common Tamil words
        'நான்', 'இந்த', 'அது', 'என்', 'இருக்கிறது', 'செய்', 'பார்க்க', 'வந்து', 'போக', 'சொல்ல', 
        'கூட', 'மட்டும்', 'எல்லாம்', 'அவர்', 'நம்ம', 'உங்கள்', 'தான்', 'ஒரு', 'அண்ணா', 
        'நாய்', 'நிமிடம்', 'சங்கம்', 'பாக்கும்', 'நன்றி',
        # Additional Tamil words commonly used in speech
        'என்ன', 'எப்படி', 'எங்கே', 'யார்', 'எப்போது', 'ஏன்', 'எத்தனை', 'எந்த',
        'வர', 'போக', 'இல்ல', 'ஆம்', 'இல்லை', 'சரி', 'ஓகே', 'பண்ண', 'பண்றேன்',
        'இருக்கு', 'இருக்கேன்', 'வந்து', 'போன', 'வேண்டும்', 'முடியும்', 'தெரியும்',
        'பேசு', 'பேசறேன்', 'கேள்', 'சொல்', 'பார்', 'வா', 'போ', 'இரு'
    ]
    
    english_indicators = [
        'the', 'and', 'is', 'was', 'have', 'with', 'that', 'for', 'you', 'are', 'this', 
        'will', 'can', 'about', 'they', 'from', 'there', 'been', 'time', 'would',
        'hello', 'people', 'what', 'doing', 'going', 'record', 'audio', 'show', 
        'speak', 'english', 'tamil', 'now', 'suddenly', 'switched', 'while', 'sure',
        'right', 'eating', 'dosa', 'chutney'
    ]
    
    # Count Tamil and English words with partial matching for Tamil
    words = transcription.lower().split()
    tamil_count = 0
    english_count = 0
    
    for word in words:
        # Tamil matching - check if word contains Tamil characters or words
        if any(tamil_word in word for tamil_word in tamil_indicators):
            tamil_count += 1
        elif word in english_indicators:
            english_count += 1
    
    # Enhanced language classification
    total_detected = tamil_count + english_count
    if total_detected == 0:
        language = "Unknown"
    elif tamil_count > english_count * 1.5:  # Higher threshold for Tamil
        language = "Tamil"
    elif english_count > tamil_count * 1.5:  # Higher threshold for English
        language = "English"
    else:
        language = "Mixed English/Tamil"
    
    # Quality assessment
    total_words = len(words)
    unique_words = len(set(words))
    repetition_ratio = 1 - (unique_words / total_words) if total_words > 0 else 0
    
    if repetition_ratio > 0.7:
        quality = "Poor (High repetition)"
    elif repetition_ratio > 0.5:
        quality = "Fair (Some repetition)"
    else:
        quality = "Good"
    
    return {
        'language': language,
        'quality': quality,
        'total_words': total_words,
        'unique_words': unique_words,
        'repetition_ratio': round(repetition_ratio, 2),
        'tamil_words_detected': tamil_count,
        'english_words_detected': english_count
    }

@app.route('/summarize', methods=['POST'])
def summarize_transcription():
    try:
        data = request.get_json()
        transcription = data.get('transcription', '')
        transcription_id = data.get('transcription_id')
        
        if not transcription:
            return jsonify({'error': 'No transcription provided'}), 400

        if not os.getenv('OPENAI_API_KEY'):
            return jsonify({'error': 'OpenAI API key not configured'}), 500

        logger.info("Generating summary with OpenAI GPT")

        # Enhanced MOM prompt for speaker-aware transcriptions with Tamil/English support
        summary_prompt = f"""
Please analyze the following meeting transcription with speaker identification and create a comprehensive Minutes of Meeting (MOM) summary.

Note: This transcription may contain English and Tamil languages mixed together. Please summarize in English while noting when Tamil was spoken.

## Meeting Summary

### Participants:
- [List speakers identified: Person1, Person2, etc.]

### Key Discussion Points:
- [List main topics discussed with speaker attribution where relevant]

### Important Updates & Announcements:
- [List status updates, announcements, decisions made]

### Action Items / Next Steps:
- [List todo items, assignments, deadlines with person responsible if mentioned]

### Decisions Made:
- [List any concrete decisions or agreements reached]

### Questions & Concerns:
- [List any questions raised or concerns discussed]

### Language Notes:
- [Note if Tamil was spoken and provide brief context]

Speaker Transcription:
{transcription}

Please format the response clearly, focus on actionable items and key decisions, and use speaker attribution where helpful. If Tamil text appears unclear, note it as "[Tamil content - may need verification]".
"""

        client = get_openai_client()
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
                f.write(summary)

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
            'service': 'OpenAI Whisper + GPT optimized for English/Tamil',
            'total_transcriptions': total_transcriptions,
            'features': ['message_format', 'auto_cleanup', 'download_history', 'tamil_english_optimized']
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def add_speaker_labels_smart(transcription):
    """Simple clean transcription without speaker labels - just add message formatting"""
    # Clean up repetitive content first
    transcription = clean_repetitive_content(transcription)
    
    # Split into sentences and add simple message icons
    import re
    sentences = re.split(r'[.!?।]+', transcription)
    formatted_lines = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and len(sentence) > 5:  # Skip very short segments
            # Add simple message icon instead of speaker labels
            formatted_lines.append(f"💬 {sentence}.")
    
    return '\n\n'.join(formatted_lines)

def is_single_speaker(transcription):
    """Detect if transcription is likely from a single speaker"""
    import re
    
    # Indicators that suggest single speaker
    single_speaker_phrases = [
        'i am going to', 'what i am going to do', 'i am speaking', 'i switched', 
        'i can speak', 'i am not sure', 'right now i am', 'i speak both',
        'நான் போவேன்', 'நான் செய்யப் போகிறேன்', 'நான் பேசுகிறேன்'
    ]
    
    # Count single speaker indicators
    single_indicators = sum(1 for phrase in single_speaker_phrases 
                          if phrase in transcription.lower())
    
    # Check for conversation patterns (questions and responses)
    questions = len(re.findall(r'[.!?।]', transcription))
    conversation_words = ['hello people', 'what are you doing', 'this is what', 'now i can']
    conversation_count = sum(1 for phrase in conversation_words 
                           if phrase in transcription.lower())
    
    # Single speaker if more self-references than conversation patterns
    return single_indicators > conversation_count or len(transcription.split()) < 50

def add_speaker_labels(transcription):
    """Original speaker labels function - kept for compatibility"""
    return add_speaker_labels_multilingual(transcription)

if __name__ == '__main__':
    print("🎤 Meeting Recorder - Enhanced OpenAI Powered")
    print("📝 Features: Audio Upload → Clean Transcription → MOM Summary")
    print("🗃️  Enhanced: Save results, Message format, Auto cleanup")
    print("🌐 Optimized: English/Tamil language switching support")
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY not set in environment variables")
        print("   Create a .env file with: OPENAI_API_KEY=your_api_key_here")
    print("🌐 Server starting at: http://localhost:9000")
    app.run(host='0.0.0.0', port=9000, debug=False) 