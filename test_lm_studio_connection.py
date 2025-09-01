#!/usr/bin/env python3
"""
Test script to verify LM Studio connection and endpoint compatibility.
"""

import requests
import json
import time
from urllib.parse import urljoin

# LM Studio default configuration
LM_STUDIO_BASE_URL = "http://localhost:1234"
TIMEOUT = 30

def test_lm_studio_endpoints():
    """Test LM Studio endpoints to identify working ones."""
    
    print("Testing LM Studio connection...")
    print(f"Base URL: {LM_STUDIO_BASE_URL}")
    print("-" * 50)
    
    # Configure session with proper headers
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json',
        'Connection': 'keep-alive',
        'Keep-Alive': 'timeout=30, max=100'
    })
    
    # Test health/availability endpoints
    health_endpoints = [
        "/v1/models",
        "/health", 
        "/",
        "/api/health"
    ]
    
    print("1. Testing health/availability endpoints:")
    working_health = None
    for endpoint in health_endpoints:
        try:
            url = urljoin(LM_STUDIO_BASE_URL, endpoint)
            print(f"   Testing {endpoint}...", end=" ")
            
            response = session.get(url, timeout=5)
            print(f"Status: {response.status_code}")
            
            if response.status_code < 500:
                working_health = endpoint
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"      Response: {json.dumps(data, indent=2)[:200]}...")
                    except:
                        print(f"      Response: {response.text[:100]}...")
                break
                
        except Exception as e:
            print(f"Failed: {e}")
    
    if not working_health:
        print("❌ No working health endpoints found. Is LM Studio running?")
        return False
    
    print(f"✅ Working health endpoint: {working_health}")
    print()
    
    # Test chat completions endpoint
    print("2. Testing chat completions endpoint:")
    chat_data = {
        "messages": [
            {"role": "user", "content": "Hello, respond with just 'Hi there!'"}
        ],
        "temperature": 0.1,
        "max_tokens": 50,
        "stream": False
    }
    
    try:
        url = urljoin(LM_STUDIO_BASE_URL, "/v1/chat/completions")
        print(f"   Testing /v1/chat/completions...", end=" ")
        
        response = session.post(url, json=chat_data, timeout=TIMEOUT)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"      Response: {content}")
                print("✅ Chat completions working!")
            except Exception as e:
                print(f"      Parse error: {e}")
                print(f"      Raw response: {response.text[:200]}...")
        else:
            print(f"      Error: {response.text[:200]}...")
            
    except Exception as e:
        print(f"Failed: {e}")
    
    print()
    
    # Test completions endpoint
    print("3. Testing completions endpoint:")
    completion_data = {
        "prompt": "Hello, respond with just 'Hi there!'",
        "temperature": 0.1,
        "max_tokens": 50,
        "stream": False
    }
    
    try:
        url = urljoin(LM_STUDIO_BASE_URL, "/v1/completions")
        print(f"   Testing /v1/completions...", end=" ")
        
        response = session.post(url, json=completion_data, timeout=TIMEOUT)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                content = result.get('choices', [{}])[0].get('text', '')
                print(f"      Response: {content}")
                print("✅ Completions working!")
            except Exception as e:
                print(f"      Parse error: {e}")
                print(f"      Raw response: {response.text[:200]}...")
        else:
            print(f"      Error: {response.text[:200]}...")
            
    except Exception as e:
        print(f"Failed: {e}")
    
    print()
    
    # Test unsupported endpoints that might cause errors
    print("4. Testing potentially problematic endpoints:")
    bad_endpoints = [
        "/generate",
        "/completions", 
        "/api/v1/completions",
        "/api/health"
    ]
    
    for endpoint in bad_endpoints:
        try:
            url = urljoin(LM_STUDIO_BASE_URL, endpoint)
            print(f"   Testing {endpoint}...", end=" ")
            
            if endpoint == "/generate":
                response = session.post(url, json={"prompt": "test"}, timeout=5)
            else:
                response = session.get(url, timeout=5)
                
            print(f"Status: {response.status_code}")
            if response.status_code >= 400:
                print(f"      ❌ This endpoint causes errors: {response.text[:100]}...")
                
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    print()
    print("Test completed!")
    return True

if __name__ == "__main__":
    test_lm_studio_endpoints()