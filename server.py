"""
Flask server for the OCR document extraction system.
"""
import os
import logging
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from config import UPLOAD_FOLDER, OUTPUT_FOLDER, SCREENSHOT_FOLDER, FLASK_HOST, FLASK_PORT, ALLOWED_EXTENSIONS
from utils.document_processor import DocumentProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Initialize document processor
document_processor = DocumentProcessor()

def allowed_file(filename):
    """Check if a file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    """API endpoint for uploading and processing documents."""
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
        
    file = request.files['file']
    
    # If user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = Path(app.config['UPLOAD_FOLDER']) / filename
        
        # Save the uploaded file
        file.save(file_path)
        logger.info(f"Saved uploaded file to {file_path}")
        
        # Process the document
        result = document_processor.process_document(file_path)
        
        # Return processing results
        return jsonify(result)
    else:
        return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

@app.route('/output/<path:filename>')
def get_output(filename):
    """Get a processed output file."""
    return send_from_directory(OUTPUT_FOLDER, filename)

@app.route('/screenshot/<path:filename>')
def get_screenshot(filename):
    """Get a screenshot image."""
    # Extract the document name from the path
    parts = Path(filename).parts
    if len(parts) > 1:
        doc_name = parts[0]
        image_name = parts[-1]
        screenshot_path = SCREENSHOT_FOLDER / doc_name
        return send_from_directory(screenshot_path, image_name)
    else:
        return send_from_directory(SCREENSHOT_FOLDER, filename)

@app.route('/status', methods=['GET'])
def get_status():
    """Get the status of the OCR server."""
    return jsonify({
        'status': 'running',
        'upload_folder': str(UPLOAD_FOLDER),
        'output_folder': str(OUTPUT_FOLDER),
        'screenshot_folder': str(SCREENSHOT_FOLDER),
    })

@app.route('/files', methods=['GET'])
def list_files():
    """List all processed files."""
    uploads = [f.name for f in UPLOAD_FOLDER.iterdir() if f.is_file()]
    outputs = [f.name for f in OUTPUT_FOLDER.iterdir() if f.is_file()]
    
    return jsonify({
        'uploads': uploads,
        'outputs': outputs
    })

@app.route('/files/<filename>', methods=['GET'])
def get_file_info(filename):
    """Get information about a processed file."""
    file_path = Path(UPLOAD_FOLDER) / filename
    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404
        
    # Get file extension
    ext = file_path.suffix.lower()[1:]
    
    # Get output files
    output_base = Path(OUTPUT_FOLDER) / file_path.stem
    json_output = output_base.with_suffix('.json')
    excel_output = output_base.with_suffix('.xlsx')
    
    # Check for screenshots
    screenshot_dir = Path(SCREENSHOT_FOLDER) / file_path.stem
    screenshots = []
    if screenshot_dir.exists() and screenshot_dir.is_dir():
        screenshots = [f.name for f in screenshot_dir.iterdir() if f.is_file()]
    
    return jsonify({
        'filename': filename,
        'type': ext,
        'size': file_path.stat().st_size,
        'outputs': {
            'json': str(json_output) if json_output.exists() else None,
            'excel': str(excel_output) if excel_output.exists() else None,
        },
        'screenshots': screenshots,
    })

if __name__ == '__main__':
    # Ensure required directories exist
    UPLOAD_FOLDER.mkdir(exist_ok=True, parents=True)
    OUTPUT_FOLDER.mkdir(exist_ok=True, parents=True)
    SCREENSHOT_FOLDER.mkdir(exist_ok=True, parents=True)
    
    # Start Flask server
    logger.info(f"Starting Flask server at {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)