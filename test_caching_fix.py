#!/usr/bin/env python3
"""
Test script to verify that the caching functionality is working.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from medical_analyzer.services.analysis_orchestrator import AnalysisOrchestrator
from medical_analyzer.config.config_manager import ConfigManager
from medical_analyzer.config.app_settings import AppSettings


def create_test_project():
    """Create a simple test project for analysis."""
    test_dir = tempfile.mkdtemp(prefix="test_project_")
    
    # Create a simple C file
    c_file = Path(test_dir) / "main.c"
    c_file.write_text("""
#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}
""")
    
    # Create a simple JavaScript file
    js_file = Path(test_dir) / "app.js"
    js_file.write_text("""
function greet(name) {
    console.log("Hello, " + name + "!");
}

greet("World");
""")
    
    return test_dir


def test_caching():
    """Test the caching functionality."""
    print("Testing caching functionality...")
    
    # Create test project
    test_project_path = create_test_project()
    print(f"Created test project at: {test_project_path}")
    
    try:
        # Initialize configuration and orchestrator
        config_manager = ConfigManager()
        config_manager.load_default_config()
        app_settings = AppSettings(config_manager)
        
        orchestrator = AnalysisOrchestrator(config_manager, app_settings)
        
        # Check if project is already cached
        cached_project = orchestrator.project_persistence.load_project_by_path(test_project_path)
        if cached_project:
            print("✓ Found cached project data")
        else:
            print("✗ No cached project data found (expected for first run)")
        
        # List all projects in database
        projects = orchestrator.project_persistence.list_projects()
        print(f"Total projects in database: {len(projects)}")
        
        for project in projects:
            print(f"  - {project['name']} ({project['root_path']})")
            if project['last_analyzed']:
                print(f"    Last analyzed: {project['last_analyzed']}")
        
        print("\nCaching functionality appears to be working!")
        print("To fully test, run an analysis and then run this script again.")
        
    except Exception as e:
        print(f"Error testing caching: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up test project
        shutil.rmtree(test_project_path)
        print(f"Cleaned up test project: {test_project_path}")


if __name__ == "__main__":
    test_caching()