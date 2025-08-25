"""
Unit tests for data model validation methods.
"""

import pytest
from datetime import datetime
from medical_analyzer.models.core import ProjectStructure, FileMetadata


class TestFileMetadataValidation:
    """Test cases for FileMetadata validation."""
    
    def test_valid_file_metadata(self):
        """Test validation of valid FileMetadata."""
        metadata = FileMetadata(
            file_path="/path/to/file.c",
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c",
            encoding="utf-8",
            line_count=50,
            function_count=5
        )
        
        assert metadata.is_valid()
        assert len(metadata.validate()) == 0
    
    def test_empty_file_path(self):
        """Test validation with empty file_path."""
        metadata = FileMetadata(
            file_path="",
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c"
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("file_path cannot be empty" in error for error in errors)
    
    def test_invalid_file_path_type(self):
        """Test validation with non-string file_path."""
        metadata = FileMetadata(
            file_path=123,  # Invalid type
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c"
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("file_path must be a string" in error for error in errors)
    
    def test_negative_file_size(self):
        """Test validation with negative file_size."""
        metadata = FileMetadata(
            file_path="/path/to/file.c",
            file_size=-1,
            last_modified=datetime.now(),
            file_type="c"
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("file_size cannot be negative" in error for error in errors)
    
    def test_invalid_file_size_type(self):
        """Test validation with non-integer file_size."""
        metadata = FileMetadata(
            file_path="/path/to/file.c",
            file_size="1024",  # Invalid type
            last_modified=datetime.now(),
            file_type="c"
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("file_size must be an integer" in error for error in errors)
    
    def test_invalid_last_modified_type(self):
        """Test validation with non-datetime last_modified."""
        metadata = FileMetadata(
            file_path="/path/to/file.c",
            file_size=1024,
            last_modified="2023-01-01",  # Invalid type
            file_type="c"
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("last_modified must be a datetime instance" in error for error in errors)
    
    def test_invalid_file_type(self):
        """Test validation with invalid file_type."""
        metadata = FileMetadata(
            file_path="/path/to/file.py",
            file_size=1024,
            last_modified=datetime.now(),
            file_type="python"  # Invalid type
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("file_type must be 'c' or 'javascript'" in error for error in errors)
    
    def test_empty_file_type(self):
        """Test validation with empty file_type."""
        metadata = FileMetadata(
            file_path="/path/to/file.c",
            file_size=1024,
            last_modified=datetime.now(),
            file_type=""  # Empty type
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("file_type cannot be empty" in error for error in errors)
    
    def test_invalid_encoding_type(self):
        """Test validation with non-string encoding."""
        metadata = FileMetadata(
            file_path="/path/to/file.c",
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c",
            encoding=123  # Invalid type
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("encoding must be a string" in error for error in errors)
    
    def test_empty_encoding(self):
        """Test validation with empty encoding."""
        metadata = FileMetadata(
            file_path="/path/to/file.c",
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c",
            encoding=""  # Empty encoding
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("encoding cannot be empty" in error for error in errors)
    
    def test_negative_line_count(self):
        """Test validation with negative line_count."""
        metadata = FileMetadata(
            file_path="/path/to/file.c",
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c",
            line_count=-1
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("line_count cannot be negative" in error for error in errors)
    
    def test_invalid_line_count_type(self):
        """Test validation with non-integer line_count."""
        metadata = FileMetadata(
            file_path="/path/to/file.c",
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c",
            line_count="50"  # Invalid type
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("line_count must be an integer" in error for error in errors)
    
    def test_negative_function_count(self):
        """Test validation with negative function_count."""
        metadata = FileMetadata(
            file_path="/path/to/file.c",
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c",
            function_count=-1
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("function_count cannot be negative" in error for error in errors)
    
    def test_invalid_function_count_type(self):
        """Test validation with non-integer function_count."""
        metadata = FileMetadata(
            file_path="/path/to/file.c",
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c",
            function_count="5"  # Invalid type
        )
        
        assert not metadata.is_valid()
        errors = metadata.validate()
        assert any("function_count must be an integer" in error for error in errors)


class TestProjectStructureValidation:
    """Test cases for ProjectStructure validation."""
    
    def create_valid_file_metadata(self) -> FileMetadata:
        """Create a valid FileMetadata instance for testing."""
        return FileMetadata(
            file_path="/path/to/file.c",
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c",
            encoding="utf-8",
            line_count=50,
            function_count=5
        )
    
    def test_valid_project_structure(self):
        """Test validation of valid ProjectStructure."""
        file_metadata = self.create_valid_file_metadata()
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files=["/path/to/file.c"],
            description="Test project",
            metadata={"test": "data"},
            timestamp=datetime.now(),
            file_metadata=[file_metadata]
        )
        
        assert project.is_valid()
        assert len(project.validate()) == 0
    
    def test_empty_root_path(self):
        """Test validation with empty root_path."""
        project = ProjectStructure(
            root_path="",
            selected_files=["/path/to/file.c"],
            description="Test project"
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("root_path cannot be empty" in error for error in errors)
    
    def test_invalid_root_path_type(self):
        """Test validation with non-string root_path."""
        project = ProjectStructure(
            root_path=123,  # Invalid type
            selected_files=["/path/to/file.c"],
            description="Test project"
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("root_path must be a string" in error for error in errors)
    
    def test_invalid_selected_files_type(self):
        """Test validation with non-list selected_files."""
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files="/path/to/file.c",  # Invalid type
            description="Test project"
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("selected_files must be a list" in error for error in errors)
    
    def test_invalid_selected_file_type(self):
        """Test validation with non-string item in selected_files."""
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files=[123, "/path/to/file.c"],  # Invalid item type
            description="Test project"
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("selected_files[0] must be a string" in error for error in errors)
    
    def test_empty_selected_file(self):
        """Test validation with empty string in selected_files."""
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files=["", "/path/to/file.c"],  # Empty string
            description="Test project"
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("selected_files[0] cannot be empty" in error for error in errors)
    
    def test_invalid_description_type(self):
        """Test validation with non-string description."""
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files=["/path/to/file.c"],
            description=123  # Invalid type
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("description must be a string" in error for error in errors)
    
    def test_invalid_metadata_type(self):
        """Test validation with non-dict metadata."""
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files=["/path/to/file.c"],
            description="Test project",
            metadata="invalid"  # Invalid type
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("metadata must be a dictionary" in error for error in errors)
    
    def test_invalid_timestamp_type(self):
        """Test validation with non-datetime timestamp."""
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files=["/path/to/file.c"],
            description="Test project",
            timestamp="2023-01-01"  # Invalid type
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("timestamp must be a datetime instance" in error for error in errors)
    
    def test_invalid_file_metadata_type(self):
        """Test validation with non-list file_metadata."""
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files=["/path/to/file.c"],
            description="Test project",
            file_metadata="invalid"  # Invalid type
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("file_metadata must be a list" in error for error in errors)
    
    def test_invalid_file_metadata_item_type(self):
        """Test validation with non-FileMetadata item in file_metadata."""
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files=["/path/to/file.c"],
            description="Test project",
            file_metadata=["invalid"]  # Invalid item type
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("file_metadata[0] must be a FileMetadata instance" in error for error in errors)
    
    def test_file_metadata_count_mismatch(self):
        """Test validation with mismatched file_metadata and selected_files counts."""
        file_metadata = self.create_valid_file_metadata()
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files=["/path/to/file1.c", "/path/to/file2.c"],  # 2 files
            description="Test project",
            file_metadata=[file_metadata]  # 1 metadata
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("file_metadata count (1) does not match selected_files count (2)" in error for error in errors)
    
    def test_missing_file_metadata(self):
        """Test validation with missing file metadata for selected files."""
        file_metadata = FileMetadata(
            file_path="/path/to/other.c",  # Different path
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c"
        )
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files=["/path/to/file.c"],
            description="Test project",
            file_metadata=[file_metadata]
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("Missing file metadata for: /path/to/file.c" in error for error in errors)
    
    def test_extra_file_metadata(self):
        """Test validation with extra file metadata not in selected files."""
        file_metadata1 = FileMetadata(
            file_path="/path/to/file.c",
            file_size=1024,
            last_modified=datetime.now(),
            file_type="c"
        )
        file_metadata2 = FileMetadata(
            file_path="/path/to/extra.c",  # Not in selected files
            file_size=512,
            last_modified=datetime.now(),
            file_type="c"
        )
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files=["/path/to/file.c"],
            description="Test project",
            file_metadata=[file_metadata1, file_metadata2]
        )
        
        assert not project.is_valid()
        errors = project.validate()
        assert any("Extra file metadata for: /path/to/extra.c" in error for error in errors)
    
    def test_invalid_file_metadata_validation(self):
        """Test validation with invalid FileMetadata instance."""
        invalid_metadata = FileMetadata(
            file_path="",  # Invalid - empty path
            file_size=-1,  # Invalid - negative size
            last_modified=datetime.now(),
            file_type="invalid"  # Invalid - unsupported type
        )
        project = ProjectStructure(
            root_path="/path/to/project",
            selected_files=[""],  # Empty to match invalid metadata
            description="Test project",
            file_metadata=[invalid_metadata]
        )
        
        assert not project.is_valid()
        errors = project.validate()
        
        # Should contain errors from FileMetadata validation
        assert any("file_metadata[0]: file_path cannot be empty" in error for error in errors)
        assert any("file_metadata[0]: file_size cannot be negative" in error for error in errors)
        assert any("file_metadata[0]: file_type must be 'c' or 'javascript'" in error for error in errors)


if __name__ == '__main__':
    pytest.main([__file__])