"""
Unit tests for the FileTreeWidget component.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from medical_analyzer.ui.file_tree_widget import FileTreeWidget


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with test files."""
    temp_dir = tempfile.mkdtemp()
    
    # Create directory structure
    os.makedirs(os.path.join(temp_dir, "src"))
    os.makedirs(os.path.join(temp_dir, "include"))
    os.makedirs(os.path.join(temp_dir, "js"))
    os.makedirs(os.path.join(temp_dir, "node_modules"))  # Should be filtered out
    os.makedirs(os.path.join(temp_dir, ".git"))  # Should be filtered out
    
    # Create test files
    test_files = [
        "src/main.c",
        "src/utils.c", 
        "include/main.h",
        "include/utils.h",
        "js/app.js",
        "js/components.jsx",
        "js/types.ts",
        "README.md",  # Unsupported file type
        "Makefile",   # Unsupported file type
        "node_modules/package.json",  # Should be filtered out
        ".git/config"  # Should be filtered out
    ]
    
    for file_path in test_files:
        full_path = os.path.join(temp_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(f"// Test content for {file_path}")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def file_tree_widget(app):
    """Create FileTreeWidget instance for testing."""
    widget = FileTreeWidget()
    return widget


class TestFileTreeWidget:
    """Test cases for FileTreeWidget."""
    
    def test_initialization(self, file_tree_widget):
        """Test widget initialization."""
        assert file_tree_widget.root_path is None
        assert len(file_tree_widget.selected_files) == 0
        assert len(file_tree_widget.file_items) == 0
        assert file_tree_widget.tree_widget.topLevelItemCount() == 0
        
        # Check initial UI state
        assert not file_tree_widget.select_all_button.isEnabled()
        assert not file_tree_widget.select_none_button.isEnabled()
        assert not file_tree_widget.supported_only_checkbox.isEnabled()
        assert file_tree_widget.supported_only_checkbox.isChecked()
        
    def test_supported_extensions(self, file_tree_widget):
        """Test supported file extensions."""
        expected_extensions = {'.c', '.h', '.js', '.ts', '.jsx', '.tsx'}
        assert file_tree_widget.SUPPORTED_EXTENSIONS == expected_extensions
        
    def test_load_directory_structure(self, file_tree_widget, temp_project_dir):
        """Test loading directory structure."""
        file_tree_widget.load_directory_structure(temp_project_dir)
        
        assert file_tree_widget.root_path == temp_project_dir
        assert file_tree_widget.tree_widget.topLevelItemCount() > 0
        assert file_tree_widget.select_all_button.isEnabled()
        assert file_tree_widget.select_none_button.isEnabled()
        assert file_tree_widget.supported_only_checkbox.isEnabled()
        
        # Check that supported files are loaded
        expected_files = [
            os.path.join(temp_project_dir, "src", "main.c"),
            os.path.join(temp_project_dir, "src", "utils.c"),
            os.path.join(temp_project_dir, "include", "main.h"),
            os.path.join(temp_project_dir, "include", "utils.h"),
            os.path.join(temp_project_dir, "js", "app.js"),
            os.path.join(temp_project_dir, "js", "components.jsx"),
            os.path.join(temp_project_dir, "js", "types.ts")
        ]
        
        for file_path in expected_files:
            assert file_path in file_tree_widget.file_items
            
    def test_load_invalid_directory(self, file_tree_widget):
        """Test loading invalid directory."""
        invalid_path = "/nonexistent/path"
        file_tree_widget.load_directory_structure(invalid_path)
        
        assert "Invalid directory path" in file_tree_widget.file_count_label.text()
        
    def test_filter_supported_files(self, file_tree_widget):
        """Test filtering supported files."""
        test_files = [
            "/path/to/main.c",
            "/path/to/app.js", 
            "/path/to/types.ts",
            "/path/to/component.jsx",
            "/path/to/header.h",
            "/path/to/README.md",  # Unsupported
            "/path/to/Makefile"    # Unsupported
        ]
        
        filtered = file_tree_widget.filter_supported_files(test_files)
        
        expected = [
            "/path/to/main.c",
            "/path/to/app.js",
            "/path/to/types.ts", 
            "/path/to/component.jsx",
            "/path/to/header.h"
        ]
        
        assert set(filtered) == set(expected)
        
    def test_select_all_files(self, file_tree_widget, temp_project_dir):
        """Test selecting all files."""
        file_tree_widget.load_directory_structure(temp_project_dir)
        
        # Initially no files selected
        assert len(file_tree_widget.selected_files) == 0
        
        # Select all files
        file_tree_widget.select_all_files()
        
        # Check that all supported files are selected
        supported_files = [
            path for path in file_tree_widget.file_items.keys()
            if Path(path).suffix.lower() in file_tree_widget.SUPPORTED_EXTENSIONS
        ]
        
        assert len(file_tree_widget.selected_files) == len(supported_files)
        assert file_tree_widget.selected_files == set(supported_files)
        
    def test_select_no_files(self, file_tree_widget, temp_project_dir):
        """Test deselecting all files."""
        file_tree_widget.load_directory_structure(temp_project_dir)
        file_tree_widget.select_all_files()
        
        # Verify files are selected
        assert len(file_tree_widget.selected_files) > 0
        
        # Deselect all files
        file_tree_widget.select_no_files()
        
        # Verify no files are selected
        assert len(file_tree_widget.selected_files) == 0
        
    def test_get_selected_files(self, file_tree_widget, temp_project_dir):
        """Test getting selected files."""
        file_tree_widget.load_directory_structure(temp_project_dir)
        
        # Initially empty
        assert file_tree_widget.get_selected_files() == []
        
        # Select some files
        file_tree_widget.select_all_files()
        selected = file_tree_widget.get_selected_files()
        
        assert len(selected) > 0
        assert isinstance(selected, list)
        
    def test_set_selected_files(self, file_tree_widget, temp_project_dir):
        """Test setting selected files programmatically."""
        file_tree_widget.load_directory_structure(temp_project_dir)
        
        # Get some file paths
        available_files = list(file_tree_widget.file_items.keys())[:2]
        
        # Set selection
        file_tree_widget.set_selected_files(available_files)
        
        # Verify selection
        assert set(file_tree_widget.selected_files) == set(available_files)
        assert set(file_tree_widget.get_selected_files()) == set(available_files)
        
    def test_validate_selection_empty(self, file_tree_widget, temp_project_dir):
        """Test validation with no files selected."""
        file_tree_widget.load_directory_structure(temp_project_dir)
        
        validation = file_tree_widget.validate_selection()
        
        assert not validation["valid"]
        assert "No files selected" in validation["message"]
        assert validation["selected_count"] == 0
        assert validation["supported_count"] == 0
        
    def test_validate_selection_valid(self, file_tree_widget, temp_project_dir):
        """Test validation with valid files selected."""
        file_tree_widget.load_directory_structure(temp_project_dir)
        file_tree_widget.select_all_files()
        
        validation = file_tree_widget.validate_selection()
        
        assert validation["valid"]
        assert "supported files selected" in validation["message"]
        assert validation["selected_count"] > 0
        assert validation["supported_count"] > 0
        
    def test_should_include_entry_hidden_files(self, file_tree_widget):
        """Test filtering of hidden files and directories."""
        # Hidden files should be excluded
        assert not file_tree_widget._should_include_entry(".hidden", "/path/.hidden")
        assert not file_tree_widget._should_include_entry(".git", "/path/.git")
        
        # Regular files should be included
        assert file_tree_widget._should_include_entry("main.c", "/path/main.c")
        
    def test_should_include_entry_skip_dirs(self, file_tree_widget):
        """Test filtering of common build directories."""
        skip_dirs = ['node_modules', '__pycache__', 'build', 'dist', 'target', 'bin', 'obj']
        
        for dir_name in skip_dirs:
            with patch('os.path.isdir', return_value=True):
                assert not file_tree_widget._should_include_entry(dir_name, f"/path/{dir_name}")
                
    def test_should_include_entry_supported_files_only(self, file_tree_widget):
        """Test filtering when 'supported files only' is enabled."""
        file_tree_widget.supported_only_checkbox.setChecked(True)
        
        with patch('os.path.isfile', return_value=True):
            # Supported files should be included
            assert file_tree_widget._should_include_entry("main.c", "/path/main.c")
            assert file_tree_widget._should_include_entry("app.js", "/path/app.js")
            
            # Unsupported files should be excluded
            assert not file_tree_widget._should_include_entry("README.md", "/path/README.md")
            assert not file_tree_widget._should_include_entry("Makefile", "/path/Makefile")
            
    def test_should_include_entry_all_files(self, file_tree_widget):
        """Test filtering when 'supported files only' is disabled."""
        file_tree_widget.supported_only_checkbox.setChecked(False)
        
        with patch('os.path.isfile', return_value=True):
            # All files should be included when filter is off
            assert file_tree_widget._should_include_entry("main.c", "/path/main.c")
            assert file_tree_widget._should_include_entry("README.md", "/path/README.md")
            assert file_tree_widget._should_include_entry("Makefile", "/path/Makefile")
            
    def test_refresh_tree(self, file_tree_widget, temp_project_dir):
        """Test refreshing the tree display."""
        file_tree_widget.load_directory_structure(temp_project_dir)
        
        # Select some files
        available_files = list(file_tree_widget.file_items.keys())[:2]
        file_tree_widget.set_selected_files(available_files)
        
        # Refresh tree
        file_tree_widget.refresh_tree()
        
        # Selection should be preserved
        assert set(file_tree_widget.get_selected_files()) == set(available_files)
        
    def test_selection_changed_signal(self, file_tree_widget, temp_project_dir):
        """Test that selection_changed signal is emitted."""
        file_tree_widget.load_directory_structure(temp_project_dir)
        
        # Connect signal to mock
        mock_handler = MagicMock()
        file_tree_widget.selection_changed.connect(mock_handler)
        
        # Select files
        file_tree_widget.select_all_files()
        
        # Verify signal was emitted
        mock_handler.assert_called()
        
    def test_file_count_label_updates(self, file_tree_widget, temp_project_dir):
        """Test that file count label updates correctly."""
        file_tree_widget.load_directory_structure(temp_project_dir)
        
        # Initially no files selected
        assert "Selected: 0" in file_tree_widget.file_count_label.text()
        
        # Select all files
        file_tree_widget.select_all_files()
        
        # Count should update
        label_text = file_tree_widget.file_count_label.text()
        assert "Selected:" in label_text
        assert "supported files" in label_text
        
    def test_directory_checkbox_behavior(self, file_tree_widget, temp_project_dir):
        """Test directory checkbox behavior with children."""
        file_tree_widget.load_directory_structure(temp_project_dir)
        
        # Find a directory item
        root_item = file_tree_widget.tree_widget.topLevelItem(0)
        if root_item and root_item.childCount() > 0:
            # Directory should have checkbox
            assert root_item.flags() & Qt.ItemFlag.ItemIsUserCheckable
            
    def test_empty_directory_handling(self, file_tree_widget):
        """Test handling of empty directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty subdirectory
            empty_dir = os.path.join(temp_dir, "empty")
            os.makedirs(empty_dir)
            
            file_tree_widget.load_directory_structure(temp_dir)
            
            # Should handle empty directory without errors
            assert file_tree_widget.root_path == temp_dir
            
    def test_permission_error_handling(self, file_tree_widget):
        """Test handling of permission errors during directory scanning."""
        with patch('os.listdir', side_effect=PermissionError("Access denied")):
            with tempfile.TemporaryDirectory() as temp_dir:
                # Should not crash on permission errors
                file_tree_widget.load_directory_structure(temp_dir)
                assert file_tree_widget.root_path == temp_dir


class TestFileTreeWidgetIntegration:
    """Integration tests for FileTreeWidget."""
    
    def test_complete_workflow(self, file_tree_widget, temp_project_dir):
        """Test complete workflow from loading to selection."""
        # Load directory
        file_tree_widget.load_directory_structure(temp_project_dir)
        assert file_tree_widget.root_path == temp_project_dir
        
        # Validate initial state
        validation = file_tree_widget.validate_selection()
        assert not validation["valid"]
        
        # Select files
        file_tree_widget.select_all_files()
        
        # Validate selection
        validation = file_tree_widget.validate_selection()
        assert validation["valid"]
        
        # Get selected files
        selected = file_tree_widget.get_selected_files()
        assert len(selected) > 0
        
        # Filter supported files
        supported = file_tree_widget.filter_supported_files(selected)
        assert len(supported) == len(selected)  # All selected should be supported
        
        # Clear selection
        file_tree_widget.select_no_files()
        validation = file_tree_widget.validate_selection()
        assert not validation["valid"]
        
    def test_filter_toggle_workflow(self, file_tree_widget, temp_project_dir):
        """Test toggling the supported files filter."""
        # Load with filter enabled (default)
        file_tree_widget.load_directory_structure(temp_project_dir)
        initial_count = len(file_tree_widget.file_items)
        
        # Disable filter
        file_tree_widget.supported_only_checkbox.setChecked(False)
        file_tree_widget.refresh_tree()
        
        # Should show more files (including unsupported ones)
        new_count = len(file_tree_widget.file_items)
        # Note: This might be equal if temp directory only has supported files
        assert new_count >= initial_count
        
        # Re-enable filter
        file_tree_widget.supported_only_checkbox.setChecked(True)
        file_tree_widget.refresh_tree()
        
        # Should be back to original count
        final_count = len(file_tree_widget.file_items)
        assert final_count == initial_count