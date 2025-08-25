"""
Unit tests for the ProjectPersistenceService class.
"""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import pytest

from medical_analyzer.services.project_persistence import ProjectPersistenceService
from medical_analyzer.services.ingestion import IngestionService
from medical_analyzer.models import ProjectStructure, FileMetadata


class TestProjectPersistenceService:
    """Test cases for ProjectPersistenceService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.persistence_service = ProjectPersistenceService(self.db_path)
        self.ingestion_service = IngestionService()
        
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_file(self, relative_path: str, content: str) -> str:
        """Create a test file with given content."""
        file_path = os.path.join(self.temp_dir, relative_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def create_test_project(self) -> ProjectStructure:
        """Create a test project structure."""
        # Create test files
        self.create_test_file('src/main.c', '#include <stdio.h>\nint main() { return 0; }')
        self.create_test_file('src/utils.h', '#ifndef UTILS_H\n#define UTILS_H\nvoid helper();\n#endif')
        self.create_test_file('js/app.js', 'function main() { console.log("hello"); }')
        
        # Create project using ingestion service
        project_root = os.path.join(self.temp_dir, 'test_project')
        os.makedirs(project_root, exist_ok=True)
        
        # Move files to project root
        src_dir = os.path.join(project_root, 'src')
        js_dir = os.path.join(project_root, 'js')
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(js_dir, exist_ok=True)
        
        shutil.copy(os.path.join(self.temp_dir, 'src/main.c'), src_dir)
        shutil.copy(os.path.join(self.temp_dir, 'src/utils.h'), src_dir)
        shutil.copy(os.path.join(self.temp_dir, 'js/app.js'), js_dir)
        
        return self.ingestion_service.scan_project(project_root, "Test project for persistence")
    
    def test_save_and_load_project(self):
        """Test saving and loading a project."""
        # Create test project
        project = self.create_test_project()
        
        # Save project
        project_id = self.persistence_service.save_project(project)
        assert isinstance(project_id, int)
        assert project_id > 0
        
        # Load project
        loaded_project = self.persistence_service.load_project(project_id)
        assert loaded_project is not None
        assert isinstance(loaded_project, ProjectStructure)
        
        # Verify project data
        assert loaded_project.root_path == project.root_path
        assert loaded_project.description == project.description
        assert len(loaded_project.selected_files) == len(project.selected_files)
        assert len(loaded_project.file_metadata) == len(project.file_metadata)
        
        # Verify file metadata
        for original, loaded in zip(project.file_metadata, loaded_project.file_metadata):
            assert loaded.file_path == original.file_path
            assert loaded.file_type == original.file_type
            assert loaded.line_count == original.line_count
    
    def test_save_project_twice_updates(self):
        """Test that saving the same project twice updates instead of creating duplicate."""
        project = self.create_test_project()
        
        # Save project first time
        project_id1 = self.persistence_service.save_project(project)
        
        # Modify project and save again
        project.description = "Updated description"
        project_id2 = self.persistence_service.save_project(project)
        
        # Should be the same project ID
        assert project_id1 == project_id2
        
        # Load and verify update
        loaded_project = self.persistence_service.load_project(project_id1)
        assert loaded_project.description == "Updated description"
    
    def test_load_project_by_path(self):
        """Test loading project by root path."""
        project = self.create_test_project()
        
        # Save project
        project_id = self.persistence_service.save_project(project)
        
        # Load by path
        loaded_project = self.persistence_service.load_project_by_path(project.root_path)
        assert loaded_project is not None
        assert loaded_project.root_path == project.root_path
        assert loaded_project.description == project.description
    
    def test_load_nonexistent_project(self):
        """Test loading non-existent project returns None."""
        result = self.persistence_service.load_project(99999)
        assert result is None
        
        result = self.persistence_service.load_project_by_path("/nonexistent/path")
        assert result is None
    
    def test_list_projects(self):
        """Test listing all projects."""
        # Initially empty
        projects = self.persistence_service.list_projects()
        assert len(projects) == 0
        
        # Create and save multiple projects
        project1 = self.create_test_project()
        project1.description = "First project"
        
        # Create second project in different location
        project2_root = os.path.join(self.temp_dir, 'project2')
        os.makedirs(project2_root, exist_ok=True)
        self.create_test_file('project2/test.c', 'int test() { return 1; }')
        project2 = self.ingestion_service.scan_project(project2_root, "Second project")
        
        # Save both projects
        id1 = self.persistence_service.save_project(project1)
        id2 = self.persistence_service.save_project(project2)
        
        # List projects
        projects = self.persistence_service.list_projects()
        assert len(projects) == 2
        
        # Verify project summaries
        project_ids = [p['id'] for p in projects]
        assert id1 in project_ids
        assert id2 in project_ids
        
        # Check project data
        for project_summary in projects:
            assert 'name' in project_summary
            assert 'root_path' in project_summary
            assert 'description' in project_summary
            assert 'selected_files_count' in project_summary
    
    def test_delete_project(self):
        """Test deleting a project."""
        project = self.create_test_project()
        project_id = self.persistence_service.save_project(project)
        
        # Verify project exists
        loaded_project = self.persistence_service.load_project(project_id)
        assert loaded_project is not None
        
        # Delete project
        result = self.persistence_service.delete_project(project_id)
        assert result is True
        
        # Verify project is gone
        loaded_project = self.persistence_service.load_project(project_id)
        assert loaded_project is None
        
        # Try to delete again
        result = self.persistence_service.delete_project(project_id)
        assert result is False
    
    def test_create_analysis_run(self):
        """Test creating analysis runs for a project."""
        project = self.create_test_project()
        project_id = self.persistence_service.save_project(project)
        
        # Create analysis run
        run_id = self.persistence_service.create_analysis_run(
            project_id, 
            artifacts_path="/path/to/artifacts",
            metadata={"test": "data"}
        )
        
        assert isinstance(run_id, int)
        assert run_id > 0
        
        # Get analysis runs
        runs = self.persistence_service.get_project_analysis_runs(project_id)
        assert len(runs) == 1
        assert runs[0]['id'] == run_id
        assert runs[0]['project_id'] == project_id
        assert runs[0]['artifacts_path'] == "/path/to/artifacts"
        assert runs[0]['metadata']['test'] == "data"
    
    def test_validate_project_structure_valid(self):
        """Test validation of valid project structure."""
        project = self.create_test_project()
        errors = self.persistence_service.validate_project_structure(project)
        assert len(errors) == 0
    
    def test_validate_project_structure_invalid(self):
        """Test validation of invalid project structures."""
        # Test empty root path
        project = ProjectStructure(
            root_path="",
            selected_files=[],
            description="Test"
        )
        errors = self.persistence_service.validate_project_structure(project)
        assert len(errors) > 0
        assert any("Root path is required" in error for error in errors)
        
        # Test non-existent root path
        project = ProjectStructure(
            root_path="/nonexistent/path",
            selected_files=[],
            description="Test"
        )
        errors = self.persistence_service.validate_project_structure(project)
        assert len(errors) > 0
        assert any("does not exist" in error for error in errors)
        
        # Test no selected files
        project = ProjectStructure(
            root_path=self.temp_dir,
            selected_files=[],
            description="Test"
        )
        errors = self.persistence_service.validate_project_structure(project)
        assert len(errors) > 0
        assert any("No files selected" in error for error in errors)
    
    def test_save_invalid_project_raises_error(self):
        """Test that saving invalid project raises ValueError."""
        # Test empty root path
        project = ProjectStructure(
            root_path="",
            selected_files=[],
            description="Test"
        )
        
        with pytest.raises(ValueError, match="root_path cannot be empty"):
            self.persistence_service.save_project(project)
        
        # Test non-existent root path
        project = ProjectStructure(
            root_path="/nonexistent/path",
            selected_files=[],
            description="Test"
        )
        
        with pytest.raises(ValueError, match="does not exist"):
            self.persistence_service.save_project(project)
    
    def test_file_metadata_serialization(self):
        """Test that file metadata is properly serialized and deserialized."""
        project = self.create_test_project()
        
        # Verify we have file metadata
        assert len(project.file_metadata) > 0
        original_metadata = project.file_metadata[0]
        
        # Save and load project
        project_id = self.persistence_service.save_project(project)
        loaded_project = self.persistence_service.load_project(project_id)
        
        # Verify file metadata is preserved
        loaded_metadata = loaded_project.file_metadata[0]
        assert loaded_metadata.file_path == original_metadata.file_path
        assert loaded_metadata.file_size == original_metadata.file_size
        assert loaded_metadata.file_type == original_metadata.file_type
        assert loaded_metadata.encoding == original_metadata.encoding
        assert loaded_metadata.line_count == original_metadata.line_count
        assert loaded_metadata.function_count == original_metadata.function_count
        
        # Verify datetime is preserved (within reasonable tolerance)
        time_diff = abs((loaded_metadata.last_modified - original_metadata.last_modified).total_seconds())
        assert time_diff < 1.0  # Should be very close


if __name__ == '__main__':
    pytest.main([__file__])