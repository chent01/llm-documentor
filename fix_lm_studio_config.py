#!/usr/bin/env python3
"""
Script to fix LM Studio configuration for better endpoint compatibility.
"""

import json
import os
from pathlib import Path

def fix_lm_studio_config():
    """Update LM Studio configuration to use only compatible endpoints."""
    
    # Find and update LLM config
    config_paths = [
        Path.home() / ".medical_analyzer" / "llm_config.json",
        Path("medical_analyzer") / "config" / "llm_config.json",
        Path("config") / "llm_config.json"
    ]
    
    config_found = False
    
    for config_path in config_paths:
        if config_path.exists():
            print(f"Found config at: {config_path}")
            
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Update local-server backend config
                for backend in config.get('backends', []):
                    if backend.get('name') == 'local-server' or backend.get('backend_type') == 'LocalServerBackend':
                        print(f"Updating backend: {backend['name']}")
                        
                        # Ensure proper LM Studio configuration
                        backend['config'].update({
                            'base_url': 'http://localhost:1234',
                            'timeout': 60,  # Longer timeout for LM Studio
                            'max_retries': 3,
                            'use_chat_completions': True,  # Prefer chat completions
                            'connection_pool_size': 5,
                            'keep_alive': True
                        })
                        
                        # Remove any problematic endpoint configurations
                        backend['config'].pop('custom_endpoints', None)
                        backend['config'].pop('fallback_endpoints', None)
                        
                        print(f"Updated config: {json.dumps(backend['config'], indent=2)}")
                
                # Save updated config
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                print(f"✅ Updated config saved to: {config_path}")
                config_found = True
                
            except Exception as e:
                print(f"❌ Error updating config {config_path}: {e}")
    
    if not config_found:
        # Create default config
        default_config_path = Path.home() / ".medical_analyzer" / "llm_config.json"
        default_config_path.parent.mkdir(exist_ok=True)
        
        config = {
            "backends": [
                {
                    "name": "local-server",
                    "backend_type": "LocalServerBackend",
                    "enabled": True,
                    "priority": 2,
                    "config": {
                        "base_url": "http://localhost:1234",
                        "timeout": 60,
                        "max_retries": 3,
                        "use_chat_completions": True,
                        "connection_pool_size": 5,
                        "keep_alive": True
                    }
                }
            ],
            "default_temperature": 0.1,
            "default_max_tokens": 2048,
            "enable_fallback": True,
            "chunk_overlap": 200
        }
        
        with open(default_config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Created default config at: {default_config_path}")
    
    print("\n📋 LM Studio Setup Checklist:")
    print("1. ✅ Configuration updated for LM Studio compatibility")
    print("2. 🔄 Make sure LM Studio is running on http://localhost:1234")
    print("3. 🔄 Load a model in LM Studio")
    print("4. 🔄 Enable CORS in LM Studio (Developer > Settings > Enable CORS)")
    print("5. 🔄 Test connection with: python test_lm_studio_connection.py")

if __name__ == "__main__":
    fix_lm_studio_config()