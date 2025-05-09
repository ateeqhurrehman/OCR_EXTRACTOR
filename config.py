"""
Configuration settings for the OCR extraction system.
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(os.path.abspath(os.path.dirname(__file__)))

# Directory configurations
UPLOAD_FOLDER = BASE_DIR / "data" / "uploads"
SCREENSHOT_FOLDER = BASE_DIR / "data" / "screenshots"
OUTPUT_FOLDER = BASE_DIR / "data" / "outputs"

# Create directories if they don't exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
SCREENSHOT_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# Flask configuration
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000

# Ollama configuration
OLLAMA_API_URL = "http://localhost:11434/api"
OLLAMA_MODEL = "gemma3:4b"

# File type configuration
ALLOWED_EXTENSIONS = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "tiff": "image/tiff",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Prompts for LLM
PROMPTS = {
    "text_extraction": (
        "Extract all text content from this image. Format the output as JSON with headers and content sections. "
        "Identify any sections, titles, or structural elements in the document."
    ),
    "table_extraction": (
        "Extract any tables from this image. For each table, provide the data in a structured format "
        "with column headers and row values. Format as JSON that can be converted to Excel."
    ),
    "document_analysis": (
        "Analyze this document image and determine its type (text document, form, invoice, etc.). "
        "Identify if it contains tables, images with text, or pure text content."
    ),
}

# Extraction settings
MAX_IMAGE_SIZE = (1200, 1200)  # Resize large images to this maximum size
DEFAULT_DPI = 300  # Default DPI for PDF to image conversion