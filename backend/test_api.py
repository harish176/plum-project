"""
HTTP-based test script to test the running API service
"""
import json
import requests
import time

def test_health_endpoint():
    """Test the health check endpoint"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check failed: {e}")
        print("   Make sure the server is running!")
        return False

def test_root_endpoint():
    """Test the root endpoint"""
    print("\n🏠 Testing root endpoint...")
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint passed: {data}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Root endpoint failed: {e}")
        return False

def test_text_processing():
    """Test text processing endpoint"""
    print("\n📝 Testing text processing...")
    
    test_cases = [
        {
            "name": "Basic Medical Bill",
            "text": "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%"
        },
        {
            "name": "USD Hospital Bill", 
            "text": "Hospital charges: $2,500 | Insurance: $2,000 | Patient owes: $500"
        },
        {
            "name": "Simple Receipt",
            "text": "Amount due: $150.75"
        }
    ]
    
    passed_tests = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  Test {i}: {test_case['name']}")
        print(f"  Input: {test_case['text']}")
        
        try:
            payload = {"text": test_case['text']}
            response = requests.post(
                "http://localhost:8000/extract-amounts-text",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Status: {data.get('status', 'unknown')}")
                print(f"  💰 Currency: {data.get('currency', 'none')}")
                print(f"  📊 Confidence: {data.get('confidence', 0):.2f}")
                print(f"  🔢 Amounts found: {len(data.get('amounts', []))}")
                
                for amount in data.get('amounts', [])[:3]:  # Show first 3 amounts
                    print(f"     • {amount.get('type', 'unknown')}: {amount.get('value', 0)}")
                
                passed_tests += 1
            else:
                print(f"  ❌ Failed: HTTP {response.status_code}")
                print(f"     Response: {response.text[:100]}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Request failed: {e}")
    
    print(f"\n📊 Text processing tests: {passed_tests}/{len(test_cases)} passed")
    return passed_tests == len(test_cases)

def check_server_running():
    """Check if server is running"""
    print("🔍 Checking if server is running...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("✅ Server is running!")
            return True
    except:
        pass
    
    print("❌ Server is not running!")
    print("\n🚀 To start the server, run:")
    print("   python -m uvicorn main:app --reload")
    print("   OR")
    print("   .\\start_service.bat")
    return False

def main():
    """Main test function"""
    print("🧪 AI-Powered Amount Detection - HTTP API Test")
    print("=" * 60)
    
    # Check if server is running
    if not check_server_running():
        return False
    
    print("\n🔧 Testing API endpoints...")
    
    # Run tests
    health_ok = test_health_endpoint()
    root_ok = test_root_endpoint()
    text_ok = test_text_processing()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"   Health endpoint: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"   Root endpoint: {'✅ PASS' if root_ok else '❌ FAIL'}")
    print(f"   Text processing: {'✅ PASS' if text_ok else '❌ FAIL'}")
    
    if health_ok and root_ok and text_ok:
        print("\n🎉 ALL API TESTS PASSED!")
        print("\n💡 Service is working correctly!")
        print("   Visit http://localhost:8000/docs for interactive API documentation")
    else:
        print("\n❌ SOME API TESTS FAILED!")
        print("   Check the server logs for errors")
    
    return health_ok and root_ok and text_ok

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)