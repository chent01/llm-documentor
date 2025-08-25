"""
Interactive file tree widget with checkbox selection for the Medical Software Analysis Tool.
"""

import os
from pathlib import Path
from typing import List, Set, Dict, Optional
from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, 
    QHBoxLayout, QPushButton, QLabel, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal


class FileTreeWidget(QWidget):
    """Interactive file tree widget with checkbox selection for supported file types."""
    
    # Signals
    selection_changed = pyqtSignal(list)  # Emits list of selected file paths
    
    # Supported file extensions for medical device software analysis
    SUPPORTED_EXTENSIONS = {'.c', '.h', '.js', '.ts', '.jsx', '.tsx'}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_path: Optional[str] = None
        self.selected_files: Set[str] = set()
        self.file_items: Dict[str, QTreeWidgetItem] = {}  # Maps file paths to tree items
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Initialize the user interface components."""
        layout = QVBoxLayout(self)
        
        # Header with selection controls
        header_layout = QHBoxLayout()
        
        self.file_count_label = QLabel("No files loaded")
        self.select_all_button = QPushButton("Select All")
        self.select_none_button = QPushButton("Select None")
        self.supported_only_checkbox = QCheckBox("Show supported files only")
        self.supported_only_checkbox.setChecked(True)
        
        header_layout.addWidget(self.file_count_label)
        header_layout.addStretch()
        header_layout.addWidget(self.supported_only_checkbox)
        header_layout.addWidget(self.select_all_button)
        header_layout.addWidget(self.select_none_button)
        
        layout.addLayout(header_layout)
        
        # File tree
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("Project Files")
        self.tree_widget.setRootIsDecorated(True)
        layout.addWidget(self.tree_widget)
        
        # Initially disable controls
        self.select_all_button.setEnabled(False)
        self.select_none_button.setEnabled(False)
        self.supported_only_checkbox.setEnabled(False)
        
    def setup_connections(self):
        """Set up signal-slot connections."""
        self.select_all_button.clicked.connect(self.select_all_files)
        self.select_none_button.clicked.connect(self.select_no_files)
        self.supported_only_checkbox.toggled.connect(self.refresh_tree)
        self.tree_widget.itemChanged.connect(self.on_item_changed)
        
    def load_directory_structure(self, root_path: str):
        """Load and display the directory structure."""
        if not os.path.exists(root_path):
            self.file_count_label.setText("Invalid directory path")
            return
            
        self.root_path = root_path
        self.selected_files.clear()
        self.file_items.clear()
        
        # Clear existing tree
        self.tree_widget.clear()
        
        # Build tree structure
        self._build_tree_recursive(root_path, None)
        
        # Update UI state
        self._update_file_count()
        self.select_all_button.setEnabled(True)
        self.select_none_button.setEnabled(True)
        self.supported_only_checkbox.setEnabled(True)
        
        # Expand the root level
        self.tree_widget.expandToDepth(0)
        
    def _build_tree_recursive(self, dir_path: str, parent_item: Optional[QTreeWidgetItem]):
        """Recursively build the tree structure."""
        try:
            # Get directory contents
            entries = []
            for entry in os.listdir(dir_path):
                entry_path = os.path.join(dir_path, entry)
                if self._should_include_entry(entry, entry_path):
                    entries.append((entry, entry_path))
                    
            # Sort entries: directories first, then files
            entries.sort(key=lambda x: (not os.path.isdir(x[1]), x[0].lower()))
            
            for entry_name, entry_path in entries:
                if os.path.isdir(entry_path):
                    # Create directory item
                    dir_item = QTreeWidgetItem([entry_name])
                    dir_item.setData(0, Qt.ItemDataRole.UserRole, entry_path)
                    
                    if parent_item is None:
                        self.tree_widget.addTopLevelItem(dir_item)
                    else:
                        parent_item.addChild(dir_item)
                        
                    # Recursively add subdirectories and files
                    self._build_tree_recursive(entry_path, dir_item)
                    
                    # Set directory checkbox state based on children
                    self._update_directory_checkbox_state(dir_item)
                    
                else:
                    # Create file item
                    file_item = QTreeWidgetItem([entry_name])
                    file_item.setData(0, Qt.ItemDataRole.UserRole, entry_path)
                    file_item.setFlags(file_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    file_item.setCheckState(0, Qt.CheckState.Unchecked)
                    
                    # Store reference for quick access
                    self.file_items[entry_path] = file_item
                    
                    if parent_item is None:
                        self.tree_widget.addTopLevelItem(file_item)
                    else:
                        parent_item.addChild(file_item)
                        
        except PermissionError:
            # Skip directories we can't access
            pass
        except Exception as e:
            print(f"Error processing directory {dir_path}: {e}")
            
    def _should_include_entry(self, entry_name: str, entry_path: str) -> bool:
        """Determine if an entry should be included in the tree."""
        # Skip hidden files and directories
        if entry_name.startswith('.'):
            return False
            
        # Skip common build/dependency directories
        skip_dirs = {'node_modules', '__pycache__', 'build', 'dist', 'target', 'bin', 'obj'}
        if os.path.isdir(entry_path) and entry_name in skip_dirs:
            return False
            
        # If showing supported files only, filter files by extension
        if self.supported_only_checkbox.isChecked() and os.path.isfile(entry_path):
            file_ext = Path(entry_path).suffix.lower()
            return file_ext in self.SUPPORTED_EXTENSIONS
            
        return True
        
    def _update_directory_checkbox_state(self, dir_item: QTreeWidgetItem):
        """Update directory checkbox state based on its children."""
        if dir_item.childCount() == 0:
            return
            
        # Make directory checkable
        dir_item.setFlags(dir_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        
        # Count checked children
        checked_count = 0
        total_files = 0
        
        for i in range(dir_item.childCount()):
            child = dir_item.child(i)
            child_path = child.data(0, Qt.ItemDataRole.UserRole)
            
            if os.path.isfile(child_path):
                total_files += 1
                if child.checkState(0) == Qt.CheckState.Checked:
                    checked_count += 1
            elif os.path.isdir(child_path):
                # Recursively check subdirectories
                self._update_directory_checkbox_state(child)
                
        # Set directory checkbox state
        if total_files == 0:
            dir_item.setCheckState(0, Qt.CheckState.Unchecked)
        elif checked_count == 0:
            dir_item.setCheckState(0, Qt.CheckState.Unchecked)
        elif checked_count == total_files:
            dir_item.setCheckState(0, Qt.CheckState.Checked)
        else:
            dir_item.setCheckState(0, Qt.CheckState.PartiallyChecked)
            
    def on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle item checkbox state changes."""
        if column != 0:
            return
            
        item_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_path:
            return
            
        # Temporarily disconnect to avoid recursion
        self.tree_widget.itemChanged.disconnect()
        
        try:
            if os.path.isdir(item_path):
                # Directory checkbox changed - update all children
                self._set_children_check_state(item, item.checkState(0))
            else:
                # File checkbox changed - update selection set
                if item.checkState(0) == Qt.CheckState.Checked:
                    self.selected_files.add(item_path)
                else:
                    self.selected_files.discard(item_path)
                    
            # Update parent directory states
            self._update_parent_states(item)
            
            # Update file count and emit signal
            self._update_file_count()
            self.selection_changed.emit(list(self.selected_files))
            
        finally:
            # Reconnect the signal
            self.tree_widget.itemChanged.connect(self.on_item_changed)
            
    def _set_children_check_state(self, parent_item: QTreeWidgetItem, state: Qt.CheckState):
        """Recursively set check state for all children."""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            child_path = child.data(0, Qt.ItemDataRole.UserRole)
            
            if os.path.isfile(child_path):
                child.setCheckState(0, state)
                if state == Qt.CheckState.Checked:
                    self.selected_files.add(child_path)
                else:
                    self.selected_files.discard(child_path)
            elif os.path.isdir(child_path):
                child.setCheckState(0, state)
                self._set_children_check_state(child, state)
                
    def _update_parent_states(self, item: QTreeWidgetItem):
        """Update parent directory checkbox states."""
        parent = item.parent()
        if parent is not None:
            self._update_directory_checkbox_state(parent)
            self._update_parent_states(parent)
            
    def _update_file_count(self):
        """Update the file count label."""
        total_supported = len([f for f in self.file_items.keys() 
                              if Path(f).suffix.lower() in self.SUPPORTED_EXTENSIONS])
        selected_count = len(self.selected_files)
        
        self.file_count_label.setText(
            f"Selected: {selected_count} / {total_supported} supported files"
        )
        
    def select_all_files(self):
        """Select all supported files."""
        if not self.root_path:
            return
            
        self.tree_widget.itemChanged.disconnect()
        
        try:
            for file_path, item in self.file_items.items():
                if Path(file_path).suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    item.setCheckState(0, Qt.CheckState.Checked)
                    self.selected_files.add(file_path)
                    
            # Update all directory states
            self._update_all_directory_states()
            self._update_file_count()
            self.selection_changed.emit(list(self.selected_files))
            
        finally:
            self.tree_widget.itemChanged.connect(self.on_item_changed)
            
    def select_no_files(self):
        """Deselect all files."""
        if not self.root_path:
            return
            
        self.tree_widget.itemChanged.disconnect()
        
        try:
            # Clear all file selections
            for item in self.file_items.values():
                item.setCheckState(0, Qt.CheckState.Unchecked)
                
            self.selected_files.clear()
            
            # Update all directory states
            self._update_all_directory_states()
            self._update_file_count()
            self.selection_changed.emit(list(self.selected_files))
            
        finally:
            self.tree_widget.itemChanged.connect(self.on_item_changed)
            
    def _update_all_directory_states(self):
        """Update checkbox states for all directory items."""
        def update_item_recursive(item: QTreeWidgetItem):
            item_path = item.data(0, Qt.ItemDataRole.UserRole)
            if item_path and os.path.isdir(item_path):
                self._update_directory_checkbox_state(item)
                
            for i in range(item.childCount()):
                update_item_recursive(item.child(i))
                
        for i in range(self.tree_widget.topLevelItemCount()):
            update_item_recursive(self.tree_widget.topLevelItem(i))
            
    def refresh_tree(self):
        """Refresh the tree display based on current filter settings."""
        if self.root_path:
            # Save current selection
            current_selection = self.selected_files.copy()
            
            # Reload tree
            self.load_directory_structure(self.root_path)
            
            # Restore selection for files that are still visible
            self.tree_widget.itemChanged.disconnect()
            try:
                for file_path in current_selection:
                    if file_path in self.file_items:
                        self.file_items[file_path].setCheckState(0, Qt.CheckState.Checked)
                        self.selected_files.add(file_path)
                        
                self._update_all_directory_states()
                self._update_file_count()
                self.selection_changed.emit(list(self.selected_files))
                
            finally:
                self.tree_widget.itemChanged.connect(self.on_item_changed)
                
    def get_selected_files(self) -> List[str]:
        """Get the list of currently selected file paths."""
        return list(self.selected_files)
        
    def set_selected_files(self, file_paths: List[str]):
        """Set the selected files programmatically."""
        if not self.root_path:
            return
            
        self.tree_widget.itemChanged.disconnect()
        
        try:
            # Clear current selection
            self.selected_files.clear()
            for item in self.file_items.values():
                item.setCheckState(0, Qt.CheckState.Unchecked)
                
            # Set new selection
            for file_path in file_paths:
                if file_path in self.file_items:
                    self.file_items[file_path].setCheckState(0, Qt.CheckState.Checked)
                    self.selected_files.add(file_path)
                    
            self._update_all_directory_states()
            self._update_file_count()
            self.selection_changed.emit(list(self.selected_files))
            
        finally:
            self.tree_widget.itemChanged.connect(self.on_item_changed)
            
    def filter_supported_files(self, file_paths: List[str]) -> List[str]:
        """Filter a list of file paths to include only supported file types."""
        return [
            path for path in file_paths 
            if Path(path).suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]
        
    def validate_selection(self) -> Dict[str, any]:
        """Validate the current file selection."""
        if not self.selected_files:
            return {
                "valid": False,
                "message": "No files selected for analysis",
                "selected_count": 0,
                "supported_count": 0
            }
            
        supported_files = self.filter_supported_files(list(self.selected_files))
        
        if not supported_files:
            return {
                "valid": False,
                "message": "No supported files selected (C, JavaScript, TypeScript files)",
                "selected_count": len(self.selected_files),
                "supported_count": 0
            }
            
        return {
            "valid": True,
            "message": f"{len(supported_files)} supported files selected for analysis",
            "selected_count": len(self.selected_files),
            "supported_count": len(supported_files)
        }