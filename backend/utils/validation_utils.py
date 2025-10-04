from typing import Optional, List, Dict, Any
import re
from config.settings import settings

class ValidationUtils:
    """Utility class for input validation and data sanitization."""
    
    @staticmethod
    def validate_text_input(text: str) -> tuple[bool, Optional[str]]:
        """
        Validate text input for processing.
        
        Args:
            text: Input text to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text:
            return False, "Text input cannot be empty"
        
        if not isinstance(text, str):
            return False, "Text input must be a string"
        
        if len(text.strip()) == 0:
            return False, "Text input cannot be only whitespace"
        
        if len(text) > 10000:  # Reasonable limit for processing
            return False, "Text input too long (maximum 10,000 characters)"
        
        return True, None
    
    @staticmethod
    def validate_image_data(image_data: bytes, filename: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Validate image data for processing.
        
        Args:
            image_data: Image bytes
            filename: Optional filename for format validation
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not image_data:
            return False, "Image data cannot be empty"
        
        if len(image_data) > settings.MAX_IMAGE_SIZE:
            return False, f"Image too large (maximum {settings.MAX_IMAGE_SIZE / (1024*1024):.1f}MB)"
        
        if len(image_data) < 100:  # Minimum reasonable image size
            return False, "Image file appears to be too small or corrupted"
        
        # Check for common image file signatures
        image_signatures = [
            b'\xff\xd8\xff',  # JPEG
            b'\x89PNG\r\n\x1a\n',  # PNG
            b'BM',  # BMP
            b'II*\x00',  # TIFF (Intel)
            b'MM\x00*',  # TIFF (Motorola)
        ]
        
        has_valid_signature = any(image_data.startswith(sig) for sig in image_signatures)
        if not has_valid_signature:
            return False, "Invalid image format. Supported formats: JPEG, PNG, BMP, TIFF"
        
        return True, None
    
    @staticmethod
    def validate_amount_value(amount: float) -> tuple[bool, Optional[str]]:
        """
        Validate an extracted amount value.
        
        Args:
            amount: Amount to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(amount, (int, float)):
            return False, "Amount must be a number"
        
        if amount < 0:
            return False, "Amount cannot be negative"
        
        if amount < settings.MIN_AMOUNT_VALUE:
            return False, f"Amount too small (minimum {settings.MIN_AMOUNT_VALUE})"
        
        if amount > settings.MAX_AMOUNT_VALUE:
            return False, f"Amount too large (maximum {settings.MAX_AMOUNT_VALUE})"
        
        return True, None
    
    @staticmethod
    def validate_confidence_score(confidence: float) -> tuple[bool, Optional[str]]:
        """
        Validate a confidence score.
        
        Args:
            confidence: Confidence score to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(confidence, (int, float)):
            return False, "Confidence must be a number"
        
        if not 0.0 <= confidence <= 1.0:
            return False, "Confidence must be between 0.0 and 1.0"
        
        return True, None
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Sanitize text input by removing potentially harmful content.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove potential script injection attempts
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized.strip())
        
        return sanitized
    
    @staticmethod
    def validate_processing_result(result: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a processing result structure.
        
        Args:
            result: Processing result to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ['status']
        
        for field in required_fields:
            if field not in result:
                return False, f"Missing required field: {field}"
        
        if result['status'] not in ['ok', 'no_amounts_found', 'error']:
            return False, "Invalid status value"
        
        if result['status'] == 'ok':
            if 'amounts' not in result:
                return False, "Missing 'amounts' field for successful processing"
            
            if not isinstance(result['amounts'], list):
                return False, "'amounts' must be a list"
        
        return True, None
    
    @staticmethod
    def is_reasonable_medical_amount(amount: float) -> bool:
        """
        Check if an amount is reasonable for a medical bill/receipt.
        
        Args:
            amount: Amount to check
            
        Returns:
            True if amount seems reasonable for medical context
        """
        # Medical bills typically range from a few dollars to thousands
        # This is a heuristic and can be adjusted based on requirements
        return 1.0 <= amount <= 50000.0
    
    @staticmethod
    def validate_currency_code(currency: str) -> tuple[bool, Optional[str]]:
        """
        Validate a currency code.
        
        Args:
            currency: Currency code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not currency:
            return False, "Currency code cannot be empty"
        
        if not isinstance(currency, str):
            return False, "Currency code must be a string"
        
        # Check if it's a supported currency
        supported_currencies = list(settings.CURRENCY_PATTERNS.keys()) + ['UNKNOWN']
        if currency.upper() not in supported_currencies:
            return False, f"Unsupported currency: {currency}"
        
        return True, None

# Global validation utils instance
validation_utils = ValidationUtils()