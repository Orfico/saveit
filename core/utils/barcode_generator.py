# core/utils/barcode_generator.py

import barcode
from barcode.writer import ImageWriter
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)


class BarcodeGenerator:
    """Generate barcodes in PNG format"""
    
    SUPPORTED_FORMATS = {
        'code128': barcode.Code128,
        'ean13': barcode.EAN13,
        'ean8': barcode.EAN8,
        'upca': barcode.UPCA,
        'code39': barcode.Code39,
        'itf': barcode.ITF,
    }
    
    @staticmethod
    def detect_barcode_type(code):
        """
        Auto-detect barcode type from code format
        
        Args:
            code: The card number string
            
        Returns:
            String with the detected barcode type
        """
        code = str(code).strip().replace(' ', '')
        is_numeric = code.isdigit()
        
        if is_numeric:
            if len(code) == 13: return 'ean13'
            if len(code) == 8:  return 'ean8'
            if len(code) == 12: return 'upca'
            if len(code) % 2 == 0: return 'itf'
        
        # Default for alphanumeric or other lengths
        return 'code128'
    
    @staticmethod
    def generate_barcode(code, barcode_type=None, dpi=300):
        """
        Generate a PNG barcode image
        
        Args:
            code: The code to convert into a barcode
            barcode_type: Type of barcode. If None, auto-detected
            dpi: Image resolution
            
        Returns:
            Tuple (ContentFile with PNG image, detected barcode type)
        """
        try:
            # Clean the code
            code = str(code).strip().replace(' ', '')
            
            # Auto-detect type if not provided
            if not barcode_type:
                barcode_type = BarcodeGenerator.detect_barcode_type(code)
            
            # Validate barcode type
            if barcode_type not in BarcodeGenerator.SUPPORTED_FORMATS:
                barcode_type = 'code128'
            
            # Get barcode class
            barcode_class = BarcodeGenerator.SUPPORTED_FORMATS[barcode_type]
            
            # Configure writer
            writer = ImageWriter()
            writer.set_options({
                'module_width': 0.3,
                'module_height': 15.0,
                'quiet_zone': 6.5,
                'font_size': 10,
                'text_distance': 5.0,
                'dpi': dpi
            })
            
            # Generate barcode
            barcode_instance = barcode_class(code, writer=writer)
            
            # Save to BytesIO
            buffer = BytesIO()
            barcode_instance.write(buffer)
            buffer.seek(0)
            
            # Optimize image with Pillow
            img = Image.open(buffer)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Add white margin
            img_with_margin = Image.new('RGB', 
                                        (img.width + 40, img.height + 40), 
                                        'white')
            img_with_margin.paste(img, (20, 20))
            
            # Save optimized
            output = BytesIO()
            img_with_margin.save(output, format='PNG', optimize=True)
            output.seek(0)
            
            return ContentFile(output.read(), name=f'{code}.png'), barcode_type
            
        except Exception as e:
            logger.error(f"Error generating barcode: {str(e)}")
            raise ValueError(f"Cannot generate barcode: {str(e)}")
    
    @staticmethod
    def validate_code(code, barcode_type):
        """Validate a code for a specific barcode type"""
        try:
            code = str(code).strip().replace(' ', '')
            
            if barcode_type == 'ean13':
                return len(code) == 13 and code.isdigit()
            elif barcode_type == 'ean8':
                return len(code) == 8 and code.isdigit()
            elif barcode_type == 'upca':
                return len(code) == 12 and code.isdigit()
            elif barcode_type == 'code39':
                return len(code) <= 43
            elif barcode_type == 'itf':
                return len(code) % 2 == 0 and code.isdigit()
            else:  # code128
                return len(code) > 0
                
        except:
            return False