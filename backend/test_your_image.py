import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.pipeline_service import AmountDetectionPipeline

async def test_your_image():
    """Test your uploaded screenshot"""
    
    pipeline = AmountDetectionPipeline()
    
    # Use your screenshot
    image_path = "Screenshot 2025-10-05 125922.png"
    
    print("🖼️  Testing Your Medical Bill Image")
    print("=" * 60)
    
    try:
        # Read the image
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        print(f"✅ Image loaded: {len(image_data)} bytes")
        
        # Process the image
        result = await pipeline.process_image(image_data)
        
        print(f"\n📊 Results for Your Image:")
        print(f"Status: {result.status}")
        print(f"Currency: {result.currency}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Total amounts: {len(result.amounts)}")
        
        if result.status == "ok":
            print(f"\n💰 Detected Amounts:")
            
            # Expected based on your image
            expected_results = [
                (100.0, "consultation"),
                (800.0, "x_ray"),
                (400.0, "medicine"), 
                (1600.0, "total_bill"),
                (1500.0, "paid"),
                (200.0, "due"),
                (10.0, "discount")
            ]
            
            found_amounts = {amount.value: amount.type for amount in result.amounts}
            
            all_correct = True
            for expected_value, expected_type in expected_results:
                if expected_value in found_amounts:
                    actual_type = found_amounts[expected_value]
                    if actual_type == expected_type:
                        print(f"  ✅ {expected_type}: Rs.{expected_value}")
                    else:
                        print(f"  ⚠️  Rs.{expected_value}: {actual_type} (expected: {expected_type})")
                else:
                    print(f"  ❌ MISSING: Rs.{expected_value} ({expected_type})")
                    all_correct = False
            
            # Show any extra amounts found
            extra_amounts = []
            expected_values = [exp[0] for exp in expected_results]
            for amount in result.amounts:
                if amount.value not in expected_values:
                    extra_amounts.append(amount)
            
            if extra_amounts:
                print(f"\n🔍 Extra amounts detected:")
                for amount in extra_amounts:
                    print(f"  • {amount.type}: Rs.{amount.value}")
            
            print(f"\n📋 Complete API Response:")
            response_data = {
                "currency": result.currency,
                "amounts": [
                    {
                        "type": amount.type,
                        "value": int(amount.value) if amount.value.is_integer() else amount.value,
                        "source": "image"
                    } for amount in result.amounts
                ],
                "status": result.status
            }
            
            import json
            print(json.dumps(response_data, indent=2))
            
            if all_correct and len(result.amounts) == len(expected_results):
                print(f"\n🎉 PERFECT: All amounts detected correctly!")
            elif len([exp[0] for exp in expected_results if exp[0] in found_amounts]) >= 6:
                print(f"\n✅ GOOD: Most amounts detected correctly!")
            else:
                print(f"\n⚠️  NEEDS IMPROVEMENT: Some amounts missing or incorrect")
                
        else:
            print(f"❌ Processing failed: {result.reason if hasattr(result, 'reason') else 'Unknown error'}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_your_image())