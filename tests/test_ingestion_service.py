"""
Unit tests for the IngestionService class.
"""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import pytest

from medical_analyzer.services.ingestion import IngestionService
from medical_analyzer.models import ProjectStructure, FileMetadata


class TestIngestionService:
    """Test cases for IngestionService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = IngestionService()
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_file(self, relative_path: str, content) -> str:
        """Create a test file with given content."""
        file_path = os.path.join(self.temp_dir, relative_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Handle both string and bytes content
        if isinstance(content, bytes):
            with open(file_path, 'wb') as f:
                f.write(content)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return file_path
    
    def test_scan_project_basic(self):
        """Test basic project scanning functionality."""
        # Create test files
        self.create_test_file('main.c', '#include <stdio.h>\nint main() { return 0; }')
        self.create_test_file('utils.h', '#ifndef UTILS_H\n#define UTILS_H\nvoid helper();\n#endif')
        self.create_test_file('app.js', 'function main() { console.log("hello"); }')
        
        # Scan project
        project = self.service.scan_project(self.temp_dir, "Test project")
        
        # Verify results
        assert isinstance(project, ProjectStructure)
        assert project.root_path == os.path.abspath(self.temp_dir)
        assert project.description == "Test project"
        assert len(project.selected_files) == 3
        assert len(project.file_metadata) == 3
        
        # Check that all expected files are included
        file_names = [os.path.basename(f) for f in project.selected_files]
        assert 'main.c' in file_names
        assert 'utils.h' in file_names
        assert 'app.js' in file_names
    
    def test_scan_project_nonexistent_path(self):
        """Test scanning a non-existent path raises ValueError."""
        with pytest.raises(ValueError, match="Path does not exist"):
            self.service.scan_project("/nonexistent/path")
    
    def test_scan_project_file_instead_of_directory(self):
        """Test scanning a file instead of directory raises ValueError."""
        test_file = self.create_test_file('test.c', 'int main() { return 0; }')
        
        with pytest.raises(ValueError, match="Path is not a directory"):
            self.service.scan_project(test_file)
    
    def test_filter_files_supported_types(self):
        """Test filtering files to supported types only."""
        # Create various file types
        files = [
            self.create_test_file('main.c', 'int main() {}'),
            self.create_test_file('header.h', '#define TEST'),
            self.create_test_file('script.js', 'function test() {}'),
            self.create_test_file('component.jsx', 'export default function() {}'),
            self.create_test_file('types.ts', 'interface Test {}'),
            self.create_test_file('config.json', '{"name": "test"}'),
            self.create_test_file('readme.txt', 'This is a readme'),  # Should be filtered out
            self.create_test_file('image.png', b'fake image data'),  # Should be filtered out
        ]
        
        supported_files = self.service.filter_files(files)
        
        # Should only include C, JS, TS, and JSON files
        assert len(supported_files) == 6
        
        supported_names = [os.path.basename(f) for f in supported_files]
        assert 'main.c' in supported_names
        assert 'header.h' in supported_names
        assert 'script.js' in supported_names
        assert 'component.jsx' in supported_names
        assert 'types.ts' in supported_names
        assert 'config.json' in supported_names
        assert 'readme.txt' not in supported_names
        assert 'image.png' not in supported_names
    
    def test_filter_files_empty_list(self):
        """Test filtering empty file list."""
        result = self.service.filter_files([])
        assert result == []
    
    def test_get_file_metadata_c_file(self):
        """Test getting metadata for a C file."""
        c_content = '''#include <stdio.h>
#include <stdlib.h>

int global_var = 0;

int add(int a, int b) {
    return a + b;
}

void print_hello() {
    printf("Hello, World!\\n");
}

int main() {
    int result = add(5, 3);
    print_hello();
    return 0;
}'''
        
        file_path = self.create_test_file('test.c', c_content)
        metadata = self.service.get_file_metadata(file_path)
        
        assert isinstance(metadata, FileMetadata)
        assert metadata.file_path == file_path
        assert metadata.file_type == 'c'
        assert metadata.encoding == 'utf-8'
        # Count actual lines in the content (including the leading/trailing newlines from triple quotes)
        expected_lines = len(c_content.strip().split('\n'))
        assert metadata.line_count == expected_lines
        assert metadata.function_count >= 2  # Should detect at least add() and main()
        assert metadata.file_size > 0
        assert isinstance(metadata.last_modified, datetime)
    
    def test_get_file_metadata_javascript_file(self):
        """Test getting metadata for a JavaScript file."""
        js_content = '''const express = require('express');
const app = express();

function startServer(port) {
    app.listen(port, () => {
        console.log(`Server running on port ${port}`);
    });
}

const handleRequest = (req, res) => {
    res.json({ message: 'Hello World' });
};

app.get('/', handleRequest);

startServer(3000);'''
        
        file_path = self.create_test_file('server.js', js_content)
        metadata = self.service.get_file_metadata(file_path)
        
        assert metadata.file_type == 'javascript'
        # Count actual lines in the content
        expected_lines = len(js_content.strip().split('\n'))
        assert metadata.line_count == expected_lines
        assert metadata.function_count >= 2  # Should detect functions
        assert metadata.encoding == 'utf-8'
    
    def test_get_file_metadata_nonexistent_file(self):
        """Test getting metadata for non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            self.service.get_file_metadata('/nonexistent/file.c')
    
    def test_exclude_directories(self):
        """Test that excluded directories are properly filtered out."""
        # Create files in excluded directories
        self.create_test_file('node_modules/package/index.js', 'module.exports = {};')
        self.create_test_file('.git/config', 'git config')
        self.create_test_file('build/output.js', 'compiled code')
        self.create_test_file('src/main.c', 'int main() {}')  # Should be included
        
        project = self.service.scan_project(self.temp_dir)
        
        # Should only include the src/main.c file
        assert len(project.selected_files) == 1
        # Check that the file path ends with src/main.c (since it will be an absolute path)
        assert project.selected_files[0].endswith('src/main.c') or project.selected_files[0].endswith('src\\main.c')
    
    def test_project_summary(self):
        """Test project summary generation."""
        # Create test files
        self.create_test_file('main.c', 'int main() {\n    return 0;\n}')
        self.create_test_file('utils.c', 'void helper() {\n    // helper\n}')
        self.create_test_file('app.js', 'function start() {\n    console.log("start");\n}')
        
        project = self.service.scan_project(self.temp_dir, "Test project")
        summary = self.service.get_project_summary(project)
        
        assert summary['total_files'] == 3
        assert summary['c_files'] == 2
        assert summary['javascript_files'] == 1
        assert summary['total_lines_of_code'] > 0
        assert summary['total_functions'] >= 3
        assert summary['total_size_bytes'] > 0
        assert summary['project_root'] == project.root_path
    
    def test_large_file_handling(self):
        """Test handling of files with various sizes."""
        # Create a moderately sized file
        large_content = '\n'.join([f'// Line {i}' for i in range(1000)])
        file_path = self.create_test_file('large.js', large_content)
        
        metadata = self.service.get_file_metadata(file_path)
        
        assert metadata.line_count == 1000
        assert metadata.file_size > 1000
    
    def test_file_encoding_detection(self):
        """Test file encoding detection and handling."""
        # Create UTF-8 file
        utf8_content = 'function test() { console.log("Hello 世界"); }'
        file_path = self.create_test_file('utf8.js', utf8_content)
        
        metadata = self.service.get_file_metadata(file_path)
        assert metadata.encoding == 'utf-8'
    
    def test_function_counting_heuristics(self):
        """Test function counting heuristics for different languages."""
        # C file with various constructs
        c_content = '''
int global = 0;

int add(int a, int b) {
    return a + b;
}

void process() {
    if (global > 0) {
        // not a function
    }
    for (int i = 0; i < 10; i++) {
        // not a function
    }
}

struct Point {
    int x, y;
};
'''
        
        # JavaScript file with various function styles
        js_content = '''
function regularFunction() {
    return true;
}

const arrowFunction = () => {
    return false;
};

const anotherArrow = (x) => x * 2;

if (true) {
    // not a function
}
'''
        
        c_file = self.create_test_file('functions.c', c_content)
        js_file = self.create_test_file('functions.js', js_content)
        
        c_metadata = self.service.get_file_metadata(c_file)
        js_metadata = self.service.get_file_metadata(js_file)
        
        # Should detect functions but not control structures
        assert c_metadata.function_count >= 2  # add() and process()
        assert js_metadata.function_count >= 3  # regularFunction, arrowFunction, anotherArrow
    
    def test_empty_project_directory(self):
        """Test scanning an empty project directory."""
        project = self.service.scan_project(self.temp_dir, "Empty project")
        
        assert len(project.selected_files) == 0
        assert len(project.file_metadata) == 0
        assert project.metadata['total_files_discovered'] == 0
        assert project.metadata['supported_files_count'] == 0


if __name__ == '__main__':
    pytest.main([__file__])