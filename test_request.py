#!/usr/bin/env python3
"""
test_request.py - Test script for the new request.json format

This script takes a request.json file and executes it using requests library.
"""

import json
import sys
import os
from pathlib import Path
import requests

def test_request(directory):
    """Test a request from a directory containing request.json and auth.txt."""
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"❌ Directory not found: {directory}")
        return False
    
    request_file = dir_path / "request.json"
    auth_file = dir_path / "auth.txt"
    
    if not request_file.exists():
        print(f"❌ No request.json found in: {directory}")
        return False
    
    # Load request data
    with open(request_file, 'r') as f:
        request_data = json.load(f)
    
    # Load auth token if available
    auth_token = ""
    if auth_file.exists():
        try:
            with open(auth_file, 'r') as f:
                auth_token = f.read().strip()
        except:
            pass
    
    # Extract request details
    method = request_data.get('method', 'GET')
    url = request_data.get('url', '')
    headers = request_data.get('headers', {})
    body = request_data.get('body')
    
    # Replace auth token placeholders
    if auth_token:
        for key, value in headers.items():
            if isinstance(value, str) and '{{auth_token}}' in value:
                headers[key] = value.replace('{{auth_token}}', auth_token)
    
    print(f"🚀 Testing {method} {url}")
    print(f"📁 From: {directory}")
    
    if auth_token:
        print(f"🔐 Using auth token: {auth_token[:10]}...")
    else:
        print("🔓 No auth token found")
    
    print(f"📤 Headers: {len(headers)} headers")
    if body:
        print(f"📦 Body: {type(body).__name__}")
    
    try:
        # Make the request
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=body if isinstance(body, dict) else None,
            data=body if isinstance(body, str) else None,
            timeout=30
        )
        
        print(f"\n✅ Response: {response.status_code} {response.reason}")
        print(f"📏 Size: {len(response.content)} bytes")
        
        # Show response preview
        content_type = response.headers.get('content-type', '')
        if 'json' in content_type.lower():
            try:
                json_data = response.json()
                preview = json.dumps(json_data, indent=2)[:500]
                if len(preview) == 500:
                    preview += "..."
                print(f"📄 JSON Response Preview:\n{preview}")
            except:
                print(f"📄 Response: {response.text[:200]}...")
        else:
            print(f"📄 Response: {response.text[:200]}...")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python test_request.py <directory>")
        print("Example: python test_request.py output/airdna.com/post_submarkets_2024-08-02_14-30-15_001")
        sys.exit(1)
    
    directory = sys.argv[1]
    success = test_request(directory)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()