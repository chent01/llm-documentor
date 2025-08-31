#!/usr/bin/env python3
"""
File Selection Diagnostic Tool

This tool helps diagnose file selection issues in the Medical Software Analyzer.
Run this to check if file selection is working correctly in your environment.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_diagnostic():
    """Run comprehensive file selection diagnostic"""
    
    print("=" * 60)
    print("MEDICAL SOFTWARE ANALYZER - FILE SELECTION DIAGNOSTIC")
    print("=" * 60)
    
    try:
        from medical_analyzer.services.ingestion import IngestionService
        from medical_analyzer.ui.file_tree_widget import FileTreeWidget
        from medical_analyzer.ui.main_window import MainWindow
        from medical_analyzer.config.config_manager import ConfigManager
        from medical_analyzer.config.app_settings import AppSettings
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        
        print("✓ All imports successful")
        
        # Initialize Qt application
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        print("✓ Qt application initialized")
        
        # Test with your actual project
        print("\n" + "=" * 40)
        print("TESTING WITH CURRENT PROJECT")
        print("=" * 40)
        
        current_dir = Path.cwd()
        print(f"Current directory: {current_dir}")
        
        # Initialize services
        config_manager = ConfigManager()
        config_manager.load_default_config()
        app_settings = AppSettings(config_manager)
        
        # Test ingestion service
        print("\n1. Testing Ingestion Service...")
        ingestion = IngestionService()
        
        # Scan all files
        project_all = ingestion.scan_project(str(current_dir))
        print(f"   Total supported files found: {len(project_all.selected_files)}")
        
        if len(project_all.selected_files) > 0:
            print("   Sample files:")
            for i, file_path in enumerate(project_all.selected_files[:5]):
                print(f"     {i+1}. {Path(file_path).name}")
            if len(project_all.selected_files) > 5:
                print(f"     ... and {len(project_all.selected_files) - 5} more")
        
        # Test with specific file selection
        if len(project_all.selected_files) >= 2:
            print("\n2. Testing Specific File Selection...")
            selected_files = project_all.selected_files[:2]  # Select first 2 files
            print(f"   Selecting specific files: {[Path(f).name for f in selected_files]}")
            
            project_selected = ingestion.scan_project(str(current_dir), selected_files=selected_files)
            print(f"   Files processed with selection: {len(project_selected.selected_files)}")
            
            if len(project_selected.selected_files) == len(selected_files):
                print("   ✓ File selection working correctly in ingestion service")
            else:
                print("   ✗ File selection NOT working in ingestion service")
                print(f"     Expected: {len(selected_files)}, Got: {len(project_selected.selected_files)}")
        
        # Test file tree widget
        print("\n3. Testing File Tree Widget...")
        file_tree = FileTreeWidget()
        file_tree.load_directory_structure(str(current_dir))
        
        total_files = len(file_tree.file_items)
        print(f"   Files loaded in tree widget: {total_files}")
        
        if total_files > 0:
            # Test select all
            file_tree.select_all_files()
            selected_all = len(file_tree.get_selected_files())
            print(f"   Files selected with 'Select All': {selected_all}")
            
            # Test select none
            file_tree.select_no_files()
            selected_none = len(file_tree.get_selected_files())
            print(f"   Files selected with 'Select None': {selected_none}")
            
            if selected_none == 0:
                print("   ✓ File tree selection controls working correctly")
            else:
                print("   ✗ File tree selection controls NOT working correctly")
        
        # Test main window
        print("\n4. Testing Main Window Integration...")
        main_window = MainWindow(config_manager, app_settings)
        main_window.set_project_folder(str(current_dir))
        
        # Check if files are loaded
        main_window_files = len(main_window.file_tree_widget.file_items)
        print(f"   Files loaded in main window: {main_window_files}")
        
        if main_window_files > 0:
            # Test file selection
            main_window.file_tree_widget.select_all_files()
            main_selected = len(main_window.get_selected_files())
            print(f"   Files selected in main window: {main_selected}")
            
            if main_selected == main_window_files:
                print("   ✓ Main window file selection working correctly")
            else:
                print("   ✗ Main window file selection NOT working correctly")
        
        print("\n" + "=" * 40)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 40)
        
        if len(project_all.selected_files) == 0:
            print("⚠️  No supported files found in current directory")
            print("   Make sure you're running this from a project with C/JS/TS files")
        else:
            print("✓ File selection mechanism appears to be working correctly")
            print("\nIf you're still experiencing issues:")
            print("1. Make sure you're not accidentally selecting directory checkboxes")
            print("2. Check that 'Show supported files only' filter is set correctly")
            print("3. Verify you're clicking individual file checkboxes, not directory ones")
            print("4. Try using 'Select None' then manually selecting specific files")
        
        print(f"\nTotal supported files in current project: {len(project_all.selected_files)}")
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_diagnostic()