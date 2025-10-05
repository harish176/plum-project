import asyncio
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.text_utils import TextProcessor

def debug_percentage_extraction():
    """Test percentage extraction specifically"""
    
    processor = TextProcessor()
    
    # Test with simple percentage text
    test_text = "Discount: 1%"
    
    print("🔍 Percentage Extraction Debug")
    print("=" * 50)
    print(f"Input text: '{test_text}'")
    
    # Test percentage pattern directly
    percentage_pattern = r'\d+(?:\.\d+)?%'
    matches = list(re.finditer(percentage_pattern, test_text))
    print(f"Direct regex matches: {[m.group() for m in matches]}")
    
    # Step 1: Text cleaning
    cleaned = processor.clean_text(test_text)
    print(f"Cleaned text: '{cleaned}'")
    
    # Test percentage pattern on cleaned text
    matches = list(re.finditer(percentage_pattern, cleaned))
    print(f"Matches on cleaned text: {[m.group() for m in matches]}")
    
    # Step 2: OCR correction
    corrected, corrections = processor.correct_ocr_digits(cleaned)
    print(f"OCR corrected text: '{corrected}'")
    
    # Test percentage pattern on corrected text
    matches = list(re.finditer(percentage_pattern, corrected))
    print(f"Matches on corrected text: {[m.group() for m in matches]}")
    
    # Step 3: Extract numeric tokens
    numeric_tokens = processor.extract_numeric_tokens(corrected)
    print(f"Numeric tokens extracted:")
    for token, pos, context in numeric_tokens:
        print(f"  Token: '{token}' at pos {pos}, context: '{context}'")
    
    # Test the full flow
    print("\n" + "=" * 30)
    print("Full flow test with larger text:")
    
    full_text = """
Consultation Rs.l00
X-Ray Rs.800
Medicine Rs.400
Total Bill Rs.1600
Paid Rs.1500
Due Rs.200
Discount: 1%
    """
    
    cleaned_full = processor.clean_text(full_text)
    corrected_full, _ = processor.correct_ocr_digits(cleaned_full)
    
    print(f"Full corrected text: '{corrected_full}'")
    
    # Test percentage pattern on full text
    matches = list(re.finditer(percentage_pattern, corrected_full))
    print(f"Percentage matches in full text: {[m.group() for m in matches]}")
    
    tokens_full = processor.extract_numeric_tokens(corrected_full)
    percentage_tokens = [(t, p, c) for t, p, c in tokens_full if '%' in t]
    print(f"Percentage tokens: {percentage_tokens}")

if __name__ == "__main__":
    debug_percentage_extraction()