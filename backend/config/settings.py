import os
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Configuration settings for the amount detection service."""
    
    # OCR Configuration
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Users\nhari\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
    OCR_CONFIG = "--oem 3 --psm 6"
    MIN_OCR_CONFIDENCE = 0.1  # More lenient - our enhanced test showed low confidence can still work
    
    # Image Processing
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp", "tiff"]
    
    # Amount Detection
    MIN_AMOUNT_CONFIDENCE = 0.3  # More lenient
    MAX_AMOUNT_VALUE = 1000000  # Maximum reasonable amount
    MIN_AMOUNT_VALUE = 0.01     # Minimum reasonable amount
    
    # Currency Patterns
    CURRENCY_PATTERNS = {
        "INR": [r"INR", r"Rs\.?", r"₹", r"Rupees?"],
        "USD": [r"USD", r"\$", r"Dollars?"],
        "EUR": [r"EUR", r"€", r"Euros?"],
        "GBP": [r"GBP", r"£", r"Pounds?"]
    }
    
    # Amount Type Keywords
    AMOUNT_TYPE_KEYWORDS = {
        "total_bill": ["total", "amount", "bill", "invoice", "grand total"],
        "paid": ["paid", "payment", "received", "collected"],
        "due": ["due", "balance", "outstanding", "pending", "owed"],
        "discount": ["discount", "off", "reduction", "concession"],
        "tax": ["tax", "gst", "vat", "service tax"],
        "copay": ["copay", "co-pay", "patient share"],
        "deductible": ["deductible", "excess"],
        "insurance_covered": ["insurance", "covered", "claim", "reimbursed"]
    }
    
    # Normalization Settings
    OCR_DIGIT_CORRECTIONS = {
        "l": "1", "I": "1", "O": "0", "o": "0", "S": "5", "s": "5", "G": "6",
        "T": "7", "B": "8", "b": "6", "g": "9", "Z": "2", "z": "2",
        "¢": "0", "@": "0", "e": "0", "c": "0"  # Common OCR misreads for 0
    }
    
    # Processing Thresholds
    PROCESSING_CONFIDENCE_THRESHOLD = 0.3  # More lenient - allow processing with lower confidence
    CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.4  # More lenient
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Development Settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    @classmethod
    def get_currency_pattern(cls, currency: str) -> List[str]:
        """Get regex patterns for a specific currency."""
        return cls.CURRENCY_PATTERNS.get(currency.upper(), [])
    
    @classmethod
    def get_amount_type_keywords(cls, amount_type: str) -> List[str]:
        """Get keywords for a specific amount type."""
        return cls.AMOUNT_TYPE_KEYWORDS.get(amount_type.lower(), [])

# Global settings instance
settings = Settings()