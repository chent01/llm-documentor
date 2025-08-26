#!/usr/bin/env python3
"""
Demo script for the FileTreeWidget component.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from medical_analyzer.ui.file_tree_widget import FileTreeWidget


class FileTreeDemo(QMainWindow):
    """Demo window for FileTreeWidget."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Tree Widget Demo")
        self.setMinimumSize(600, 500)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add info label
        info_label = QLabel("File Tree Widget Demo - Select files for analysis")
        layout.addWidget(info_label)
        
        # Add file tree widget
        self.file_tree = FileTreeWidget()
        layout.addWidget(self.file_tree)
        
        # Add status label
        self.status_label = QLabel("No files selected")
        layout.addWidget(self.status_label)
        
        # Connect signals
        self.file_tree.selection_changed.connect(self.on_selection_changed)
        
        # Load current directory
        current_dir = os.getcwd()
        self.file_tree.load_directory_structure(current_dir)
        
    def on_selection_changed(self, selected_files):
        """Handle file selection changes."""
        validation = self.file_tree.validate_selection()
        self.status_label.setText(validation["message"])
        
        if validation["valid"]:
            self.status_label.setStyleSheet("color: #4CAF50;")
        else:
            self.status_label.setStyleSheet("color: #f44336;")


def main():
    """Run the demo application."""
    app = QApplication(sys.argv)
    
    demo = FileTreeDemo()
    demo.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()