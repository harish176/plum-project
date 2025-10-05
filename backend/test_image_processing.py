import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.pipeline_service import AmountDetectionPipeline

async def test_image_processing():
    """Test image processing with the uploaded medical bill"""
    
    pipeline = AmountDetectionPipeline()
    
    # Load the test image
    image_path = "test_medical_bill.png"
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    print("🖼️  Testing Image Processing")
    print("=" * 50)
    print(f"Image: {image_path}")
    
    try:
        # Read the image
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        print(f"✅ Image loaded: {len(image_data)} bytes")
        
        # Process the image
        result = await pipeline.process_image(image_data)
        
        print(f"\n📊 Image Processing Results:")
        print(f"Status: {result.status}")
        print(f"Currency: {result.currency}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Total amounts: {len(result.amounts)}")
        
        if result.status == "ok":
            print(f"\n💰 Detected Amounts:")
            expected_amounts = {
                "consultation": 100.0,
                "x_ray": 800.0, 
                "medicine": 400.0,
                "total_bill": 1600.0,
                "paid": 1500.0,
                "due": 200.0,
                "discount": 10.0
            }
            
            for i, amount in enumerate(result.amounts, 1):
                expected_value = expected_amounts.get(amount.type, None)
                status = "✅" if expected_value and abs(amount.value - expected_value) < 1 else "❌"
                note = ""
                if expected_value:
                    if abs(amount.value - expected_value) >= 1:
                        note = f" (should be {expected_value})"
                
                print(f"  {status} {i}. {amount.type}: {amount.value}{note}")
            
            print(f"\n🔍 Analysis:")
            found_values = [amount.value for amount in result.amounts]
            expected_values = list(expected_amounts.values())
            
            missing = []
            partial = []
            correct = []
            
            for exp_val in expected_values:
                if exp_val in found_values:
                    correct.append(exp_val)
                else:
                    # Check if it's a partial match (like 1 instead of 100)
                    partial_matches = [v for v in found_values if str(int(exp_val)).startswith(str(int(v)))]
                    if partial_matches:
                        partial.append((exp_val, partial_matches[0]))
                    else:
                        missing.append(exp_val)
            
            print(f"  ✅ Correct: {len(correct)} amounts")
            print(f"  ⚠️  Partial: {len(partial)} amounts")
            print(f"  ❌ Missing: {len(missing)} amounts")
            
            if partial:
                print(f"\n⚠️  Partial Readings (OCR Issue):")
                for expected, actual in partial:
                    print(f"    Expected: {expected} → Got: {actual}")
                    
        else:
            print(f"❌ Processing failed: {result.reason if hasattr(result, 'reason') else 'Unknown error'}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_image_processing())