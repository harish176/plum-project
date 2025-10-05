import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ocr_service import OCRService

async def debug_ocr_extraction():
    """Debug what OCR is actually extracting from images"""
    
    ocr_service = OCRService()
    
    # Check available images
    image_files = [f for f in os.listdir('.') if f.endswith(('.png', '.jpg', '.jpeg'))]
    
    print("🔍 OCR Extraction Debug")
    print("=" * 50)
    print(f"Available images: {image_files}")
    
    # Test with the available image
    if not image_files:
        print("❌ No image files found. Please ensure your medical bill image is in the directory.")
        return
    
    image_path = image_files[0]  # Use first available image
    
    try:
        # Read the image
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        print(f"\n🖼️  Testing: {image_path} ({len(image_data)} bytes)")
        
        # Extract using OCR service
        result = await ocr_service.extract_from_image(image_data)
        
        print(f"\n📊 Raw OCR Results:")
        print(f"Status: {result.status}")
        print(f"Raw tokens: {result.raw_tokens}")
        print(f"Currency hint: {result.currency_hint}")
        print(f"Confidence: {result.confidence}")
        
        if hasattr(result, 'original_text') and result.original_text:
            print(f"\n📝 Raw OCR Text:")
            print("=" * 30)
            print(result.original_text)
            print("=" * 30)
        
        # Show what tokens were extracted
        if result.raw_tokens:
            print(f"\n🔢 Extracted Tokens:")
            for i, token in enumerate(result.raw_tokens, 1):
                print(f"  {i}. '{token}'")
        
        # Expected vs actual analysis
        print(f"\n🎯 Expected vs Actual Analysis:")
        expected_tokens = ['100.0', '800.0', '400.0', '1600.0', '1500.0', '200.0', '10.0']
        actual_tokens = result.raw_tokens
        
        print(f"Expected tokens: {expected_tokens}")
        print(f"Actual tokens: {actual_tokens}")
        
        # Check for partial matches
        partial_issues = []
        for expected in expected_tokens:
            exp_val = float(expected)
            found_exact = expected in actual_tokens
            
            if not found_exact:
                # Check for partial matches
                partial_matches = []
                for actual in actual_tokens:
                    try:
                        act_val = float(actual)
                        # Check if actual is a truncated version of expected
                        if str(int(exp_val)).startswith(str(int(act_val))) and act_val != exp_val:
                            partial_matches.append(actual)
                    except:
                        continue
                
                if partial_matches:
                    partial_issues.append((expected, partial_matches[0]))
                else:
                    partial_issues.append((expected, "MISSING"))
        
        if partial_issues:
            print(f"\n⚠️  Issues Found:")
            for expected, actual in partial_issues:
                if actual == "MISSING":
                    print(f"  ❌ Missing: {expected}")
                else:
                    print(f"  ⚠️  Partial: {expected} → {actual}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_ocr_extraction())