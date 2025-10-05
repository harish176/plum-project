import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.text_utils import TextProcessor

def debug_tokenization():
    """Test how text is being tokenized"""
    
    processor = TextProcessor()
    
    # Test with the OCR text that contains "Discount: 1%"
    test_text = """
Consultation Rs.l00
X-Ray Rs.800
Medicine Rs.400
Total Bill Rs.1600
Paid Rs.1500
Due Rs.200
Discount: 1%
    """
    
    print("🔍 Tokenization Debug")
    print("=" * 50)
    print(f"Input text:")
    print(test_text)
    print("-" * 30)
    
    # Step 1: Text cleaning
    cleaned = processor.clean_text(test_text)
    print(f"Cleaned text:")
    print(cleaned)
    print("-" * 30)
    
    # Step 2: OCR correction
    corrected, corrections = processor.correct_ocr_digits(cleaned)
    print(f"OCR corrected text:")
    print(corrected)
    if corrections:
        print(f"Corrections made: {corrections}")
    print("-" * 30)
    
    # Step 3: Extract numeric tokens
    numeric_tokens = processor.extract_numeric_tokens(corrected)
    print(f"Numeric tokens extracted:")
    for token, pos, context in numeric_tokens:
        print(f"  Token: '{token}' at pos {pos}, context: '{context}'")
    print("-" * 30)
    
    # Step 4: Extract amounts from each token
    all_amounts = []
    for token, pos, context in numeric_tokens:
        amounts = processor.extract_amounts_from_token(token)
        if amounts:
            all_amounts.extend(amounts)
            print(f"  '{token}' → {amounts}")
    
    print(f"\nFinal amounts: {all_amounts}")
    print(f"Missing 10.0? {'10.0' not in [str(a) for a in all_amounts]}")

if __name__ == "__main__":
    debug_tokenization()