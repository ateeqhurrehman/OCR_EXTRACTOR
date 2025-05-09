"""
Image processor for handling and preprocessing images.
"""
import os
import logging
from pathlib import Path
from typing import Union
import tempfile

from PIL import Image, ImageEnhance, ImageFilter

from config import MAX_IMAGE_SIZE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self, max_size: tuple = MAX_IMAGE_SIZE):
        """Initialize the image processor.
        
        Args:
            max_size: Maximum dimensions for processed images
        """
        self.max_size = max_size
        
    def preprocess_image(self, image_path: Union[str, Path]) -> Path:
        """Preprocess an image for better OCR results.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Path to the preprocessed image
        """
        image_path = Path(image_path)
        
        try:
            # Open the image
            img = Image.open(image_path)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Resize if the image is too large
            if img.width > self.max_size[0] or img.height > self.max_size[1]:
                img.thumbnail(self.max_size, Image.LANCZOS)
                
            # Apply basic enhancements for OCR
            # 1. Increase contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)
            
            # 2. Increase sharpness
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.5)
            
            # 3. Optional: Apply slight blur to reduce noise
            # img = img.filter(ImageFilter.GaussianBlur(0.5))
            
            # Save the preprocessed image to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                temp_path = Path(tmp.name)
                img.save(temp_path, 'PNG')
                
            logger.info(f"Preprocessed image {image_path.name} and saved to {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            # Return the original image path if preprocessing fails
            return image_path
            
    def enhance_image_quality(self, image_path: Union[str, Path]) -> Path:
        """Enhance image quality for better OCR results.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Path to the enhanced image
        """
        image_path = Path(image_path)
        
        try:
            # Open the image
            img = Image.open(image_path)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Apply more aggressive enhancements for challenging images
            # 1. Increase contrast significantly
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # 2. Increase brightness
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.3)
            
            # 3. Increase sharpness
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(2.0)
            
            # Save the enhanced image to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                temp_path = Path(tmp.name)
                img.save(temp_path, 'PNG')
                
            logger.info(f"Enhanced image {image_path.name} and saved to {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error enhancing image: {e}")
            # Return the original image path if enhancement fails
            return image_path