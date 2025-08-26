#!/usr/bin/env python3
"""
Demo script for the Medical Software Analysis Tool MainWindow.
"""

import sys
from PyQt6.QtWidgets import QApplication
from medical_analyzer.ui import MainWindow


def main():
    """Run the MainWindow demo."""
    app = QApplication(sys.argv)
    
    # Create and show the main window
    window = MainWindow()
    
    # Connect signals to show when they're emitted
    def on_project_selected(path):
        print(f"Project selected: {path}")
        
    def on_analysis_requested(path, description):
        print(f"Analysis requested for: {path}")
        print(f"Description: {description}")
        # Simulate analysis completion after a short delay
        from PyQt6.QtCore import QTimer
        timer = QTimer()
        timer.timeout.connect(lambda: window.analysis_completed())
        timer.setSingleShot(True)
        timer.start(3000)  # 3 seconds
        
    window.project_selected.connect(on_project_selected)
    window.analysis_requested.connect(on_analysis_requested)
    
    window.show()
    
    print("MainWindow demo started. Select a project folder to test the functionality.")
    print("The window will show project validation and allow you to start analysis.")
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())