"""
Document processor for handling different file types and extracting content.
"""
import os
import json
import logging
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd

from config import ALLOWED_EXTENSIONS, UPLOAD_FOLDER, SCREENSHOT_FOLDER, OUTPUT_FOLDER
from utils.pdf_processor import PDFProcessor
from utils.image_processor import ImageProcessor
from utils.llm_client import OllamaClient
from utils.output_formatter import format_text_output, format_table_output

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        """Initialize the document processor."""
        self.pdf_processor = PDFProcessor()
        self.image_processor = ImageProcessor()
        self.llm_client = OllamaClient()
        
    def get_file_type(self, file_path: Union[str, Path]) -> Tuple[str, str]:
        """Determine the file type based on extension and mimetype.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (file_extension, mimetype)
        """
        file_path = Path(file_path)
        file_extension = file_path.suffix.lower()[1:]  # Remove the leading dot
        
        # Get mimetype
        mimetype, _ = mimetypes.guess_type(str(file_path))
        
        logger.info(f"File {file_path.name} has extension: {file_extension}, mimetype: {mimetype}")
        return file_extension, mimetype
        
    def process_document(self, file_path: Union[str, Path]) -> Dict:
        """Process a document based on its file type.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with processing results
        """
        file_path = Path(file_path)
        file_extension, mimetype = self.get_file_type(file_path)
        
        # Validate if file type is supported
        if file_extension not in ALLOWED_EXTENSIONS:
            return {
                "success": False,
                "error": f"Unsupported file type: {file_extension}"
            }
            
        # Process based on file type
        if file_extension == "pdf":
            return self._process_pdf(file_path)
        elif file_extension in ["jpg", "jpeg", "png", "tiff"]:
            return self._process_image(file_path)
        elif file_extension == "docx":
            return self._process_docx(file_path)
        else:
            return {
                "success": False,
                "error": f"Unsupported file type: {file_extension}"
            }
            
    def _process_pdf(self, file_path: Path) -> Dict:
        """Process a PDF document by converting to images and extracting content.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing PDF: {file_path.name}")
        
        # Create folder for screenshots
        doc_name = file_path.stem
        screenshot_folder = SCREENSHOT_FOLDER / doc_name
        screenshot_folder.mkdir(exist_ok=True)
        
        # Convert PDF to images
        image_paths = self.pdf_processor.pdf_to_images(file_path, screenshot_folder)
        
        if not image_paths:
            return {
                "success": False,
                "error": "Failed to convert PDF to images"
            }
            
        # Process each page image with LLM
        results = []
        table_data = []
        text_data = {"headers": [], "content": []}
        
        for i, img_path in enumerate(image_paths):
            # Analyze document type first
            analysis = self.llm_client.analyze_document_type(img_path)
            
            # Extract text content
            text_result = self.llm_client.extract_text(img_path)
            
            # Check if the page contains a table
            if "table" in analysis.get("raw_response", "").lower():
                table_result = self.llm_client.extract_table(img_path)
                if table_result["success"]:
                    table_data.append({
                        "page": i + 1,
                        "data": table_result["data"]
                    })
            
            # Store text extraction results
            if text_result["success"]:
                results.append({
                    "page": i + 1,
                    "text_data": text_result["data"],
                    "table_detected": "table" in analysis.get("raw_response", "").lower()
                })
                
                # Aggregate text data
                if isinstance(text_result["data"], dict):
                    if "headers" in text_result["data"]:
                        text_data["headers"].extend(text_result["data"]["headers"])
                    if "content" in text_result["data"]:
                        text_data["content"].extend(text_result["data"]["content"])
                    elif "text" in text_result["data"]:
                        text_data["content"].append(text_result["data"]["text"])
        
        # Format and save results
        output_base_path = OUTPUT_FOLDER / doc_name
        
        # Save text output as JSON
        text_output_path = output_base_path.with_suffix('.json')
        with open(text_output_path, 'w') as f:
            json.dump(text_data, f, indent=2)
            
        # If tables detected, save to Excel
        if table_data:
            table_output_path = output_base_path.with_suffix('.xlsx')
            # Convert table data to DataFrame and save
            format_table_output(table_data, table_output_path)
            
        return {
            "success": True,
            "document_type": "pdf",
            "pages_processed": len(image_paths),
            "text_output_path": str(text_output_path),
            "table_output_path": str(table_output_path) if table_data else None,
            "screenshot_folder": str(screenshot_folder),
            "results": results
        }
    
    def _process_image(self, file_path: Path) -> Dict:
        """Process an image document and extract content.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing image: {file_path.name}")
        
        # Preprocess image if needed (resize, enhance, etc.)
        processed_image = self.image_processor.preprocess_image(file_path)
        
        # Analyze document type first
        analysis = self.llm_client.analyze_document_type(processed_image)
        
        # Extract text content
        text_result = self.llm_client.extract_text(processed_image)
        
        # Check if the image contains a table
        table_output_path = None
        if "table" in analysis.get("raw_response", "").lower():
            table_result = self.llm_client.extract_table(processed_image)
            if table_result["success"]:
                # Format and save table data
                doc_name = file_path.stem
                table_output_path = OUTPUT_FOLDER / f"{doc_name}.xlsx"
                format_table_output([{"page": 1, "data": table_result["data"]}], table_output_path)
        
        # Format and save text output
        doc_name = file_path.stem
        text_output_path = OUTPUT_FOLDER / f"{doc_name}.json"
        
        with open(text_output_path, 'w') as f:
            json.dump(text_result["data"], f, indent=2)
            
        return {
            "success": True,
            "document_type": "image",
            "text_output_path": str(text_output_path),
            "table_output_path": str(table_output_path) if table_output_path else None,
            "analysis": analysis.get("data", {})
        }
        
    def _process_docx(self, file_path: Path) -> Dict:
        """Process a DOCX document by converting to images and extracting content.
        
        Args:
            file_path: Path to the DOCX file
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing DOCX: {file_path.name}")
        
        # Create folder for screenshots
        doc_name = file_path.stem
        screenshot_folder = SCREENSHOT_FOLDER / doc_name
        screenshot_folder.mkdir(exist_ok=True)
        
        # Convert DOCX to images
        image_paths = self.pdf_processor.docx_to_images(file_path, screenshot_folder)
        
        if not image_paths:
            return {
                "success": False,
                "error": "Failed to convert DOCX to images"
            }
            
        # Process images similar to PDF
        # This is simplified; actual implementation would be similar to _process_pdf
        results = []
        text_data = {"headers": [], "content": []}
        table_data = []
        
        for i, img_path in enumerate(image_paths):
            # Similar processing to PDF pages
            analysis = self.llm_client.analyze_document_type(img_path)
            text_result = self.llm_client.extract_text(img_path)
            
            if "table" in analysis.get("raw_response", "").lower():
                table_result = self.llm_client.extract_table(img_path)
                if table_result["success"]:
                    table_data.append({
                        "page": i + 1,
                        "data": table_result["data"]
                    })
            
            # Store text extraction results
            if text_result["success"]:
                results.append({
                    "page": i + 1,
                    "text_data": text_result["data"],
                    "table_detected": "table" in analysis.get("raw_response", "").lower()
                })
                
                # Aggregate text data
                if isinstance(text_result["data"], dict):
                    if "headers" in text_result["data"]:
                        text_data["headers"].extend(text_result["data"]["headers"])
                    if "content" in text_result["data"]:
                        text_data["content"].extend(text_result["data"]["content"])
                    elif "text" in text_result["data"]:
                        text_data["content"].append(text_result["data"]["text"])
        
        # Format and save results
        output_base_path = OUTPUT_FOLDER / doc_name
        
        # Save text output as JSON
        text_output_path = output_base_path.with_suffix('.json')
        with open(text_output_path, 'w') as f:
            json.dump(text_data, f, indent=2)
            
        # If tables detected, save to Excel
        table_output_path = None
        if table_data:
            table_output_path = output_base_path.with_suffix('.xlsx')
            format_table_output(table_data, table_output_path)
            
        return {
            "success": True,
            "document_type": "docx",
            "pages_processed": len(image_paths),
            "text_output_path": str(text_output_path),
            "table_output_path": str(table_output_path) if table_data else None,
            "screenshot_folder": str(screenshot_folder),
            "results": results
        }