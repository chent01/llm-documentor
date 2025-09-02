#!/usr/bin/env python3
"""
Demonstration of how Python defaults and JSON configuration work together.
"""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from medical_analyzer.llm.operation_configs import (
    LLMOperationConfigs, 
    get_operation_configs,
    get_operation_params
)


def demo_configuration_system():
    """Demonstrate how Python defaults and JSON config work together."""
    
    print("🔧 LLM Configuration System Demo")
    print("=" * 50)
    
    # 1. Show Python defaults (no JSON file)
    print("\n1️⃣ Python Defaults (no JSON file)")
    print("-" * 30)
    
    configs_no_json = LLMOperationConfigs()  # No JSON file specified
    params = configs_no_json.get_generation_params("user_requirements_generation")
    print(f"User requirements (Python default): {params}")
    
    params = configs_no_json.get_generation_params("soup_classification")
    print(f"SOUP classification (Python default): {params}")
    
    # 2. Show JSON override
    print("\n2️⃣ JSON Configuration Override")
    print("-" * 30)
    
    # Create a custom JSON config that overrides some values
    custom_config = {
        "user_requirements_generation": {
            "temperature": 0.8,  # Override: was 0.7 in Python
            "max_tokens": 5000,  # Override: was 4000 in Python
            "operation_name": "user_requirements_generation",
            "description": "CUSTOM: Higher creativity for user requirements"
        },
        "soup_classification": {
            "temperature": 0.05,  # Override: was 0.1 in Python
            "max_tokens": 1200,   # Override: was 1500 in Python
            "operation_name": "soup_classification", 
            "description": "CUSTOM: Ultra-precise SOUP classification"
        },
        "new_custom_operation": {
            "temperature": 0.4,
            "max_tokens": 1800,
            "operation_name": "new_custom_operation",
            "description": "CUSTOM: New operation not in Python defaults"
        }
    }
    
    # Save custom config to file
    custom_config_path = "custom_llm_config.json"
    with open(custom_config_path, 'w') as f:
        json.dump(custom_config, f, indent=2)
    
    print(f"Created custom config file: {custom_config_path}")
    
    # 3. Load with JSON override
    print("\n3️⃣ Loading with JSON Override")
    print("-" * 30)
    
    configs_with_json = LLMOperationConfigs(config_file=custom_config_path)
    
    # Show overridden values
    params = configs_with_json.get_generation_params("user_requirements_generation")
    print(f"User requirements (JSON override): {params}")
    print("  ↳ Temperature changed from 0.7 → 0.8")
    print("  ↳ Max tokens changed from 4000 → 5000")
    
    params = configs_with_json.get_generation_params("soup_classification")
    print(f"SOUP classification (JSON override): {params}")
    print("  ↳ Temperature changed from 0.1 → 0.05")
    print("  ↳ Max tokens changed from 1500 → 1200")
    
    # Show new operation from JSON
    params = configs_with_json.get_generation_params("new_custom_operation")
    print(f"New custom operation (JSON only): {params}")
    print("  ↳ This operation doesn't exist in Python defaults!")
    
    # Show fallback for operations not in JSON (uses Python default)
    params = configs_with_json.get_generation_params("hazard_identification")
    print(f"Hazard identification (Python fallback): {params}")
    print("  ↳ Not in JSON, so uses Python default")
    
    # 4. Show the hierarchy
    print("\n4️⃣ Configuration Hierarchy")
    print("-" * 30)
    print("Priority order:")
    print("1. JSON file values (highest priority)")
    print("2. Python DEFAULT_CONFIGS")
    print("3. 'default' operation config (fallback)")
    
    # Test with non-existent operation
    params = configs_with_json.get_generation_params("totally_unknown_operation")
    print(f"Unknown operation (ultimate fallback): {params}")
    print("  ↳ Uses 'default' config from Python")
    
    # 5. Show runtime modification
    print("\n5️⃣ Runtime Modification")
    print("-" * 30)
    
    # Modify configuration at runtime
    configs_with_json.update_operation_temperature("soup_classification", 0.02)
    params = configs_with_json.get_generation_params("soup_classification")
    print(f"SOUP classification (runtime modified): {params}")
    print("  ↳ Temperature changed at runtime from 0.05 → 0.02")
    
    # Save the modified configuration
    configs_with_json.save_to_file("modified_config.json")
    print("Saved modified configuration to: modified_config.json")
    
    # 6. Show global instance usage
    print("\n6️⃣ Global Instance Usage (How Code Actually Uses It)")
    print("-" * 30)
    
    # This is how the actual code uses it
    params = get_operation_params("user_requirements_generation")
    print(f"get_operation_params() result: {params}")
    print("  ↳ This is what services actually call")
    
    # Clean up
    Path(custom_config_path).unlink(missing_ok=True)
    Path("modified_config.json").unlink(missing_ok=True)
    
    print("\n✅ Demo complete!")
    print("\n📋 Key Points:")
    print("• Python code provides sensible defaults")
    print("• JSON file can override any/all parameters")
    print("• JSON can add new operations not in Python")
    print("• Missing JSON values fall back to Python defaults")
    print("• Runtime modifications are possible")
    print("• Changes can be saved back to JSON")


if __name__ == "__main__":
    demo_configuration_system()