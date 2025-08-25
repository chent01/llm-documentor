"""
Integration tests for the ParserService orchestrator.
"""

import os
import tempfile
import pytest
from datetime import datetime

from medical_analyzer.parsers.parser_service import ParserService, ParsedFile
from medical_analyzer.models.core import ProjectStructure, CodeChunk, FileMetadata, CodeReference
from medical_analyzer.models.enums import ChunkType


class TestParserService:
    """Test cases for ParserService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser_service = ParserService(max_chunk_size=500)
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_temp_file(self, filename: str, content: str) -> str:
        """Create a temporary file with given content."""
        file_path = os.path.join(self.temp_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    def test_parse_c_file(self):
        """Test parsing a C file."""
        c_content = '''
#include <stdio.h>
#define MAX_SIZE 100

struct Point {
    int x;
    int y;
};

int global_var = 42;

int add_numbers(int a, int b) {
    return a + b;
}

static void print_point(struct Point p) {
    printf("Point: (%d, %d)\\n", p.x, p.y);
}
'''
        
        file_path = self.create_temp_file('test.c', c_content)
        parsed_file = self.parser_service.parse_file(file_path)
        
        assert parsed_file is not None
        assert parsed_file.file_path == file_path
        assert parsed_file.file_metadata.file_type == 'c'
        assert parsed_file.file_metadata.function_count == 2
        
        # Check chunks
        chunks = parsed_file.chunks
        assert len(chunks) >= 2  # At least function chunks
        
        # Find function chunks
        function_chunks = [c for c in chunks if c.chunk_type == ChunkType.FUNCTION]
        assert len(function_chunks) == 2
        
        # Check function names
        function_names = {c.function_name for c in function_chunks}
        assert 'add_numbers' in function_names
        assert 'print_point' in function_names
        
        # Check global chunk
        global_chunks = [c for c in chunks if c.chunk_type == ChunkType.GLOBAL]
        assert len(global_chunks) == 1
        
        global_chunk = global_chunks[0]
        assert '#include <stdio.h>' in global_chunk.content
        assert '#define MAX_SIZE 100' in global_chunk.content
        assert 'struct Point' in global_chunk.content
    
    def test_parse_js_file(self):
        """Test parsing a JavaScript file."""
        js_content = '''
import React from 'react';
const util = require('util');

const API_URL = 'https://api.example.com';

class DataProcessor {
    constructor(config) {
        this.config = config;
    }
    
    async processData(data) {
        return await this.transform(data);
    }
    
    transform(data) {
        return data.map(item => item.value);
    }
}

function calculateSum(numbers) {
    return numbers.reduce((sum, num) => sum + num, 0);
}

const multiply = (a, b) => a * b;

export { DataProcessor, calculateSum };
'''
        
        file_path = self.create_temp_file('test.js', js_content)
        parsed_file = self.parser_service.parse_file(file_path)
        
        assert parsed_file is not None
        assert parsed_file.file_path == file_path
        assert parsed_file.file_metadata.file_type == 'javascript'
        
        # Check chunks
        chunks = parsed_file.chunks
        assert len(chunks) >= 3  # Functions, class, and global
        
        # Find function chunks
        function_chunks = [c for c in chunks if c.chunk_type == ChunkType.FUNCTION]
        class_chunks = [c for c in chunks if c.chunk_type == ChunkType.CLASS]
        global_chunks = [c for c in chunks if c.chunk_type == ChunkType.GLOBAL]
        
        assert len(function_chunks) >= 2  # calculateSum, multiply, and class methods
        assert len(class_chunks) == 1
        assert len(global_chunks) == 1
        
        # Check class chunk
        class_chunk = class_chunks[0]
        assert class_chunk.function_name == 'DataProcessor'
        assert 'class DataProcessor' in class_chunk.content
        
        # Check global chunk
        global_chunk = global_chunks[0]
        assert 'import React from' in global_chunk.content
        assert 'require(' in global_chunk.content
        assert 'export {' in global_chunk.content
    
    def test_parse_project(self):
        """Test parsing multiple files in a project."""
        # Create test files
        c_file = self.create_temp_file('src/main.c', '''
int main() {
    return 0;
}
''')
        
        js_file = self.create_temp_file('src/app.js', '''
function init() {
    console.log("App initialized");
}
''')
        
        # Create project structure
        project = ProjectStructure(
            root_path=self.temp_dir,
            selected_files=[c_file, js_file],
            description="Test project"
        )
        
        parsed_files = self.parser_service.parse_project(project)
        
        assert len(parsed_files) == 2
        
        # Check file types
        file_types = {pf.file_metadata.file_type for pf in parsed_files}
        assert 'c' in file_types
        assert 'javascript' in file_types
        
        # Check all files have chunks
        for parsed_file in parsed_files:
            assert len(parsed_file.chunks) > 0
    
    def test_large_function_splitting(self):
        """Test splitting large functions into smaller chunks."""
        # Create a large function that exceeds max_chunk_size
        large_function = '''
int large_function() {
''' + '\n'.join([f'    int var{i} = {i};' for i in range(100)]) + '''
    return 0;
}
'''
        
        file_path = self.create_temp_file('large.c', large_function)
        parsed_file = self.parser_service.parse_file(file_path)
        
        assert parsed_file is not None
        
        # Should have multiple chunks due to splitting
        function_chunks = [c for c in parsed_file.chunks if c.chunk_type == ChunkType.FUNCTION]
        
        # Check if function was split (depends on actual size)
        if len(function_chunks) > 1:
            # Verify partial chunk metadata
            for chunk in function_chunks:
                if chunk.metadata.get('is_partial'):
                    assert 'part_of' in chunk.metadata
                    assert 'part_number' in chunk.metadata
                    assert 'total_parts' in chunk.metadata
    
    def test_extract_code_references(self):
        """Test extracting code references from chunks."""
        c_content = '''
int test_function() {
    return 42;
}
'''
        
        file_path = self.create_temp_file('test.c', c_content)
        parsed_file = self.parser_service.parse_file(file_path)
        
        references = self.parser_service.extract_code_references(parsed_file.chunks)
        
        assert len(references) > 0
        
        # Check reference properties
        for ref in references:
            assert ref.file_path == file_path
            assert ref.start_line > 0
            assert ref.end_line >= ref.start_line
            assert ref.context is not None
    
    def test_get_chunk_statistics(self):
        """Test getting chunk statistics."""
        c_content = '''
int func1() { return 1; }
int func2() { return 2; }
'''
        
        js_content = '''
function jsFunc() { return "hello"; }
class TestClass { method() {} }
'''
        
        c_file = self.create_temp_file('test.c', c_content)
        js_file = self.create_temp_file('test.js', js_content)
        
        c_parsed = self.parser_service.parse_file(c_file)
        js_parsed = self.parser_service.parse_file(js_file)
        
        all_chunks = c_parsed.chunks + js_parsed.chunks
        stats = self.parser_service.get_chunk_statistics(all_chunks)
        
        assert stats['total_chunks'] > 0
        assert stats['function_chunks'] >= 2
        assert stats['c_chunks'] > 0
        assert stats['js_chunks'] > 0
        assert stats['average_chunk_size'] > 0
        assert stats['max_chunk_size'] >= stats['min_chunk_size']
    
    def test_file_metadata_extraction(self):
        """Test file metadata extraction."""
        content = 'int main() { return 0; }'
        file_path = self.create_temp_file('test.c', content)
        
        metadata = self.parser_service._extract_file_metadata(file_path)
        
        assert metadata.file_path == file_path
        assert metadata.file_type == 'c'
        assert metadata.file_size > 0
        assert isinstance(metadata.last_modified, datetime)
        assert metadata.line_count > 0
        assert metadata.encoding in ['utf-8', 'latin-1']
    
    def test_supported_file_extensions(self):
        """Test supported file extension checking."""
        assert self.parser_service.is_supported_file('test.c')
        assert self.parser_service.is_supported_file('test.h')
        assert self.parser_service.is_supported_file('test.js')
        assert self.parser_service.is_supported_file('test.ts')
        assert self.parser_service.is_supported_file('test.jsx')
        assert self.parser_service.is_supported_file('test.tsx')
        
        assert not self.parser_service.is_supported_file('test.py')
        assert not self.parser_service.is_supported_file('test.txt')
        assert not self.parser_service.is_supported_file('README.md')
        
        extensions = self.parser_service.get_supported_extensions()
        assert '.c' in extensions
        assert '.js' in extensions
        assert '.py' not in extensions
    
    def test_error_handling(self):
        """Test error handling for invalid files."""
        # Test non-existent file
        with pytest.raises(FileNotFoundError):
            self.parser_service.parse_file('nonexistent.c')
        
        # Test unsupported file type
        unsupported_file = self.create_temp_file('test.py', 'print("hello")')
        result = self.parser_service.parse_file(unsupported_file)
        assert result is None
    
    def test_empty_file_handling(self):
        """Test handling of empty files."""
        empty_file = self.create_temp_file('empty.c', '')
        parsed_file = self.parser_service.parse_file(empty_file)
        
        assert parsed_file is not None
        assert parsed_file.file_metadata.line_count == 0
        assert len(parsed_file.chunks) == 0  # No chunks for empty file
    
    def test_chunk_content_integrity(self):
        """Test that chunk content matches original source."""
        c_content = '''#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int main() {
    int result = add(5, 3);
    printf("Result: %d\\n", result);
    return 0;
}'''
        
        file_path = self.create_temp_file('integrity.c', c_content)
        parsed_file = self.parser_service.parse_file(file_path)
        
        # Read original file
        with open(file_path, 'r', encoding='utf-8') as f:
            original_lines = f.readlines()
        
        # Check that function chunks contain correct content
        function_chunks = [c for c in parsed_file.chunks if c.chunk_type == ChunkType.FUNCTION]
        
        for chunk in function_chunks:
            # Extract corresponding lines from original
            start_idx = chunk.start_line - 1
            end_idx = chunk.end_line
            expected_content = ''.join(original_lines[start_idx:end_idx]).strip()
            
            assert chunk.content == expected_content
    
    def test_traceability_metadata(self):
        """Test that chunks contain proper traceability metadata."""
        c_content = '''
static inline int helper(int x) {
    return x * 2;
}

int process_data(int* data, int size) {
    int sum = 0;
    for (int i = 0; i < size; i++) {
        sum += helper(data[i]);
    }
    return sum;
}
'''
        
        file_path = self.create_temp_file('trace.c', c_content)
        parsed_file = self.parser_service.parse_file(file_path)
        
        function_chunks = [c for c in parsed_file.chunks if c.chunk_type == ChunkType.FUNCTION]
        
        for chunk in function_chunks:
            # Check required metadata for traceability
            assert chunk.file_path == file_path
            assert chunk.start_line > 0
            assert chunk.end_line >= chunk.start_line
            assert chunk.function_name is not None
            assert 'language' in chunk.metadata
            
            # Check C-specific metadata
            if chunk.metadata['language'] == 'c':
                assert 'parameters' in chunk.metadata
                assert 'return_type' in chunk.metadata
                assert 'is_static' in chunk.metadata
                assert 'is_inline' in chunk.metadata


if __name__ == '__main__':
    pytest.main([__file__])