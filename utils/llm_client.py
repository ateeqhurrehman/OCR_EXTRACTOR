"""
Client for interacting with the Ollama API to process images and text using LLMs.
"""
import base64
import json
import logging
import requests
from typing import Dict, List, Optional, Union
import time
from pathlib import Path

from config import OLLAMA_API_URL, OLLAMA_MODEL, PROMPTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, model: str = OLLAMA_MODEL, api_url: str = OLLAMA_API_URL):
        """Initialize the Ollama client.
        
        Args:
            model: The model to use for generation
            api_url: The base URL for the Ollama API
        """
        self.model = model
        self.api_url = api_url
        self.generate_endpoint = f"{api_url}/generate"
        
        # Check if Ollama is running
        self._check_ollama_status()
        
    def _check_ollama_status(self) -> None:
        """Check if Ollama server is running."""
        try:
            response = requests.get(f"{self.api_url}/version")
            if response.status_code != 200:
                logger.warning("Ollama server returned status %s", response.status_code)
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama server at %s", self.api_url)
            logger.error("Make sure Ollama is running and accessible")
            
    def encode_image(self, image_path: Union[str, Path]) -> str:
        """Encode an image to base64 format.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded image string
        """
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    
    def process_image(self, image_path: Union[str, Path], prompt_type: str = "text_extraction") -> Dict:
        """Process an image with the LLM to extract text.
        
        Args:
            image_path: Path to the image file
            prompt_type: Type of prompt to use (text_extraction, table_extraction, etc.)
            
        Returns:
            Dictionary containing the LLM's response
        """
        prompt = PROMPTS.get(prompt_type, PROMPTS["text_extraction"])
        
        try:
            # Encode image as base64
            base64_image = self.encode_image(image_path)
            
            # Prepare request for Ollama API with image
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "images": [base64_image]
            }
            
            # Send request to Ollama API
            logger.info(f"Processing image: {image_path}")
            response = requests.post(self.generate_endpoint, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Successfully processed image: {image_path}")
            
            # Try to parse the response as JSON if possible
            try:
                text_content = result.get("response", "")
                
                # Check if response contains JSON
                if "{" in text_content and "}" in text_content:
                    # Extract JSON portion (sometimes LLM adds explanatory text before/after)
                    json_start = text_content.find("{")
                    json_end = text_content.rfind("}") + 1
                    json_str = text_content[json_start:json_end]
                    
                    parsed_data = json.loads(json_str)
                    return {
                        "success": True,
                        "data": parsed_data,
                        "raw_response": text_content
                    }
                else:
                    return {
                        "success": True,
                        "data": {"text": text_content},
                        "raw_response": text_content
                    }
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse response as JSON: {e}")
                return {
                    "success": True,
                    "data": {"text": result.get("response", "")},
                    "raw_response": result.get("response", "")
                }
                
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def analyze_document_type(self, image_path: Union[str, Path]) -> Dict:
        """Analyze a document image to determine its type and content.
        
        Args:
            image_path: Path to the document image
            
        Returns:
            Dictionary with document analysis information
        """
        return self.process_image(image_path, prompt_type="document_analysis")
    
    def extract_text(self, image_path: Union[str, Path]) -> Dict:
        """Extract text from a document image.
        
        Args:
            image_path: Path to the document image
            
        Returns:
            Dictionary with extracted text information
        """
        return self.process_image(image_path, prompt_type="text_extraction")
    
    def extract_table(self, image_path: Union[str, Path]) -> Dict:
        """Extract tables from a document image.
        
        Args:
            image_path: Path to the document image
            
        Returns:
            Dictionary with extracted table information
        """
        return self.process_image(image_path, prompt_type="table_extraction")