from flask import Flask, render_template, request, jsonify
import os
import hashlib
import ollama
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from io import BytesIO

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
CACHE_FOLDER = 'cache'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CACHE_FOLDER'] = CACHE_FOLDER

def get_file_hash(file_stream):
    return hashlib.md5(file_stream.getvalue()).hexdigest()

def get_cache_path(file_hash):
    return os.path.join(app.config['CACHE_FOLDER'], f"{file_hash}.md")

def summarize_text(text):
    response = ollama.chat(model='gemma', messages=[
        {
            'role': 'user',
            'content': f"Summarize the following text in markdown format:\n\n{text}",
        },
    ])
    return response['message']['content']

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'})
        if file and allowed_file(file.filename):
            try:
                file_stream = BytesIO(file.read())
                file_hash = get_file_hash(file_stream)
                cache_path = get_cache_path(file_hash)

                if os.path.exists(cache_path):
                    with open(cache_path, 'r') as cache_file:
                        summary = cache_file.read()
                else:
                    file_stream.seek(0)  # Reset file pointer to beginning
                    pdf_reader = PdfReader(file_stream)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    
                    summary = summarize_text(text)
                    
                    # Save summary to cache
                    with open(cache_path, 'w') as cache_file:
                        cache_file.write(summary)

                return jsonify({'summary': summary})
            except Exception as e:
                app.logger.error(f"Error processing PDF: {str(e)}")
                return jsonify({'error': 'Unable to process the document. Please try a different file.'})
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(CACHE_FOLDER, exist_ok=True)
    app.run(debug=True)
