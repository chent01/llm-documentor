#!/usr/bin/env python3
"""
Test script to debug analysis results display issue
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from medical_analyzer.services.analysis_orchestrator import AnalysisOrchestrator
from medical_analyzer.config.config_manager import ConfigManager
from medical_analyzer.config.app_settings import AppSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
import json

class DebugReceiver(QObject):
    """Debug receiver to capture analysis signals"""
    
    def __init__(self):
        super().__init__()
        self.final_results = None
        
    def on_analysis_completed(self, results):
        print(f"Analysis completed! Results structure:")
        self.final_results = results
        
        # Print the structure of results
        if isinstance(results, dict):
            print("Results keys:", list(results.keys()))
            
            # Check risks
            if 'risks' in results:
                risks = results['risks']
                print(f"Risks found: {len(risks) if isinstance(risks, list) else 'Not a list'}")
                if isinstance(risks, list) and len(risks) > 0:
                    print("First risk:", risks[0])
                else:
                    print("No risks in results")
            else:
                print("No 'risks' key in results")
                
            # Check traceability
            if 'traceability' in results:
                traceability = results['traceability']
                print(f"Traceability structure: {type(traceability)}")
                if isinstance(traceability, dict):
                    print("Traceability keys:", list(traceability.keys()))
                    if 'matrix' in traceability:
                        matrix = traceability['matrix']
                        print(f"Matrix type: {type(matrix)}")
                        if isinstance(matrix, dict):
                            print("Matrix keys:", list(matrix.keys()))
                    if 'total_links' in traceability:
                        print(f"Total links: {traceability['total_links']}")
                else:
                    print("Traceability is not a dict")
            else:
                print("No 'traceability' key in results")
        else:
            print(f"Results is not a dict, type: {type(results)}")
        
    def on_analysis_failed(self, error):
        print(f"Analysis failed: {error}")

def test_analysis_results():
    """Test analysis results structure"""
    
    # Create a simple test directory
    test_dir = Path("test_project")
    test_dir.mkdir(exist_ok=True)
    
    # Create a simple test file
    (test_dir / "test.js").write_text("""
function authenticate(username, password) {
    if (!username || !password) {
        throw new Error('Username and password required');
    }
    return validateCredentials(username, password);
}

function validateCredentials(username, password) {
    // Validate against database
    return database.checkUser(username, password);
}
""")
    
    print(f"Created test project at: {test_dir.absolute()}")
    
    # Initialize Qt application
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Initialize configuration and settings
    config_manager = ConfigManager()
    config_manager.load_default_config()
    app_settings = AppSettings(config_manager)
    
    # Create analysis orchestrator
    orchestrator = AnalysisOrchestrator(config_manager, app_settings)
    
    # Create debug receiver
    receiver = DebugReceiver()
    
    # Connect signals
    orchestrator.analysis_completed.connect(receiver.on_analysis_completed)
    orchestrator.analysis_failed.connect(receiver.on_analysis_failed)
    
    # Start analysis
    print("\n=== Starting Analysis ===")
    orchestrator.start_analysis(
        project_path=str(test_dir.absolute()),
        description="Test project for debugging results"
    )
    
    # Process events to let the analysis complete
    app.processEvents()
    
    # Wait for analysis to complete
    import time
    timeout = 30  # 30 seconds timeout
    start_time = time.time()
    
    while receiver.final_results is None and (time.time() - start_time) < timeout:
        app.processEvents()
        time.sleep(0.1)
    
    if receiver.final_results is None:
        print("Analysis did not complete within timeout")
    else:
        print("\n=== Final Results Analysis ===")
        # Save results to file for inspection
        with open("analysis_results_debug.json", "w") as f:
            json.dump(receiver.final_results, f, indent=2, default=str)
        print("Results saved to analysis_results_debug.json")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    print(f"\nCleaned up test directory: {test_dir}")

if __name__ == "__main__":
    test_analysis_results()