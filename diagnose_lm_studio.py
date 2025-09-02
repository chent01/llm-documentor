#!/usr/bin/env python3
"""
Comprehensive LM Studio diagnostic script.
"""

import requests
import socket
import json
from urllib.parse import urljoin

def check_port_open(host, port, timeout=3):
    """Check if a port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def scan_common_llm_ports():
    """Scan common ports used by local LLM servers."""
    print("🔍 Scanning common LLM server ports...")
    
    common_ports = [
        (1234, "LM Studio default"),
        (8000, "FastAPI/Uvicorn default"),
        (8080, "Alternative web server"),
        (5000, "Flask default"),
        (3000, "Node.js default"),
        (7860, "Gradio default"),
        (11434, "Ollama default"),
        (8001, "Alternative API server"),
        (9000, "Alternative server")
    ]
    
    open_ports = []
    
    for port, description in common_ports:
        if check_port_open('localhost', port):
            print(f"   ✅ Port {port} is open ({description})")
            open_ports.append(port)
        else:
            print(f"   ❌ Port {port} is closed ({description})")
    
    return open_ports

def test_llm_server_on_port(port):
    """Test if there's an LLM server on the given port."""
    base_url = f"http://localhost:{port}"
    
    print(f"\n🧪 Testing LLM server on port {port}...")
    
    # Common LLM server endpoints
    test_endpoints = [
        ("/v1/models", "GET", None),
        ("/v1/chat/completions", "POST", {
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 5
        }),
        ("/health", "GET", None),
        ("/", "GET", None),
        ("/api/v1/generate", "POST", {"prompt": "test", "max_tokens": 5}),
        ("/generate", "POST", {"prompt": "test", "max_tokens": 5})
    ]
    
    session = requests.Session()
    session.headers.update({'Content-Type': 'application/json'})
    
    working_endpoints = []
    
    for endpoint, method, data in test_endpoints:
        try:
            url = urljoin(base_url, endpoint)
            
            if method == "GET":
                response = session.get(url, timeout=10)
            else:
                response = session.post(url, json=data, timeout=10)
            
            status = response.status_code
            print(f"   {endpoint} ({method}): Status {status}")
            
            if status < 500:  # Not a server error
                working_endpoints.append((endpoint, method, status))
                
                if status == 200:
                    try:
                        result = response.json()
                        if endpoint == "/v1/models" and "data" in result:
                            models = [model.get("id", "unknown") for model in result["data"]]
                            print(f"      Available models: {models}")
                        elif "choices" in result:
                            print(f"      Response working: {len(result['choices'])} choices")
                        elif "response" in result:
                            print(f"      Response working: {result['response'][:50]}...")
                    except:
                        print(f"      Response: {response.text[:100]}...")
        
        except requests.exceptions.Timeout:
            print(f"   {endpoint} ({method}): ⏱️ Timeout")
        except requests.exceptions.ConnectionError:
            print(f"   {endpoint} ({method}): 🔌 Connection refused")
        except Exception as e:
            print(f"   {endpoint} ({method}): ❌ Error: {e}")
    
    return working_endpoints

def provide_lm_studio_guidance():
    """Provide guidance for setting up LM Studio."""
    print("\n📚 LM Studio Setup Guide:")
    print("=" * 50)
    
    print("\n1. 📥 Download and Install LM Studio:")
    print("   - Go to https://lmstudio.ai/")
    print("   - Download for Windows")
    print("   - Install and launch LM Studio")
    
    print("\n2. 📦 Download a Model:")
    print("   - In LM Studio, go to the 'Discover' tab")
    print("   - Search for models like:")
    print("     • microsoft/DialoGPT-medium")
    print("     • microsoft/Phi-3-mini-4k-instruct")
    print("     • Meta-Llama-3-8B-Instruct")
    print("   - Click download on a model that fits your system")
    
    print("\n3. 🚀 Start the Local Server:")
    print("   - Go to the 'Local Server' tab in LM Studio")
    print("   - Select your downloaded model")
    print("   - Click 'Start Server'")
    print("   - Default address should be: http://localhost:1234")
    
    print("\n4. ⚙️ Configure Server Settings:")
    print("   - In LM Studio, go to Settings (gear icon)")
    print("   - Under 'Developer', enable:")
    print("     • Enable CORS")
    print("     • Enable local network access (if needed)")
    
    print("\n5. 🧪 Test the Connection:")
    print("   - Run: python test_lm_studio_connection.py")
    print("   - Or check in browser: http://localhost:1234/v1/models")

def main():
    """Main diagnostic function."""
    print("🏥 Medical Analyzer - LM Studio Diagnostic Tool")
    print("=" * 60)
    print("💡 For comprehensive diagnostics, use: python medical_analyzer/llm/llm_diagnostics.py")
    print()
    
    # Step 1: Scan for open ports
    open_ports = scan_common_llm_ports()
    
    if not open_ports:
        print("\n❌ No LLM servers detected on common ports.")
        provide_lm_studio_guidance()
        return
    
    # Step 2: Test each open port for LLM server
    print(f"\n🔍 Found {len(open_ports)} open ports. Testing for LLM servers...")
    
    llm_servers = []
    for port in open_ports:
        working_endpoints = test_llm_server_on_port(port)
        if working_endpoints:
            llm_servers.append((port, working_endpoints))
    
    # Step 3: Report findings
    if llm_servers:
        print(f"\n✅ Found {len(llm_servers)} working LLM server(s):")
        for port, endpoints in llm_servers:
            print(f"\n   🖥️ Server on port {port}:")
            print(f"      Base URL: http://localhost:{port}")
            print(f"      Working endpoints:")
            for endpoint, method, status in endpoints:
                print(f"        • {method} {endpoint} (Status: {status})")
        
        # Update configuration
        if llm_servers:
            primary_port = llm_servers[0][0]
            print(f"\n🔧 Updating configuration to use port {primary_port}...")
            update_config_for_port(primary_port)
            
        # Suggest enabling debugging
        print(f"\n🔍 For detailed debugging and monitoring:")
        print(f"   • Enable debugging: python enable_llm_debugging.py --verbose")
        print(f"   • Run diagnostics: python medical_analyzer/llm/llm_diagnostics.py")
        print(f"   • Create debug session: python enable_llm_debugging.py --session lm_studio_test")
    else:
        print("\n❌ No working LLM servers found on open ports.")
        provide_lm_studio_guidance()

def update_config_for_port(port):
    """Update the LLM configuration to use the detected port."""
    from pathlib import Path
    
    config_path = Path.home() / ".medical_analyzer" / "llm_config.json"
    
    try:
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {"backends": []}
        
        # Update or create local-server backend
        found_backend = False
        for backend in config.get('backends', []):
            if backend.get('name') == 'local-server':
                backend['config']['base_url'] = f'http://localhost:{port}'
                found_backend = True
                break
        
        if not found_backend:
            config.setdefault('backends', []).append({
                "name": "local-server",
                "backend_type": "LocalServerBackend",
                "enabled": True,
                "priority": 2,
                "config": {
                    "base_url": f"http://localhost:{port}",
                    "timeout": 60,
                    "max_retries": 3
                }
            })
        
        # Ensure directory exists
        config_path.parent.mkdir(exist_ok=True)
        
        # Save updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"   ✅ Updated config: {config_path}")
        print(f"   🔗 Base URL set to: http://localhost:{port}")
        
    except Exception as e:
        print(f"   ❌ Failed to update config: {e}")

if __name__ == "__main__":
    main()