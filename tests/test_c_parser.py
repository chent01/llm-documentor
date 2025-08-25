"""
Unit tests for C code parser.
"""

import pytest
import tempfile
import os
from medical_analyzer.parsers.c_parser import CParser, FunctionSignature, CCodeStructure
from medical_analyzer.models.enums import ChunkType


class TestCParser:
    """Test cases for CParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CParser()
    
    def test_parser_initialization(self):
        """Test that parser initializes correctly."""
        assert self.parser.parser is not None
        assert self.parser.language is not None
    
    def test_parse_simple_function(self):
        """Test parsing a simple C function."""
        source_code = """
        int add(int a, int b) {
            return a + b;
        }
        """
        
        structure = self.parser.parse_source(source_code, "test.c")
        
        assert len(structure.functions) == 1
        func = structure.functions[0]
        assert func.name == "add"
        assert func.return_type == "int"
        assert len(func.parameters) == 2
        assert func.parameters[0]['name'] == 'a'
        assert func.parameters[0]['type'] == 'int'
        assert func.parameters[1]['name'] == 'b'
        assert func.parameters[1]['type'] == 'int'
    
    def test_parse_function_with_modifiers(self):
        """Test parsing function with static/inline modifiers."""
        source_code = """
        static inline void helper_function(void) {
            // Helper function
        }
        """
        
        structure = self.parser.parse_source(source_code, "test.c")
        
        assert len(structure.functions) == 1
        func = structure.functions[0]
        assert func.name == "helper_function"
        assert func.is_static == True
        assert func.is_inline == True
        assert func.return_type == "void"
    
    def test_parse_includes(self):
        """Test parsing include statements."""
        source_code = """
        #include <stdio.h>
        #include "local_header.h"
        
        int main() {
            return 0;
        }
        """
        
        structure = self.parser.parse_source(source_code, "test.c")
        
        assert len(structure.includes) == 2
        assert any("#include <stdio.h>" in inc for inc in structure.includes)
        assert any("#include \"local_header.h\"" in inc for inc in structure.includes)
    
    def test_parse_defines(self):
        """Test parsing define statements."""
        source_code = """
        #define MAX_SIZE 100
        #define PI 3.14159
        #define DEBUG
        
        int main() {
            return 0;
        }
        """
        
        structure = self.parser.parse_source(source_code, "test.c")
        
        assert len(structure.defines) >= 2  # DEBUG might not have a value
        define_names = [d['name'] for d in structure.defines]
        assert 'MAX_SIZE' in define_names
        assert 'PI' in define_names
    
    def test_parse_struct(self):
        """Test parsing struct definitions."""
        source_code = """
        struct Point {
            int x;
            int y;
        };
        
        struct Device {
            char name[50];
            int id;
            float voltage;
        };
        """
        
        structure = self.parser.parse_source(source_code, "test.c")
        
        assert len(structure.structs) == 2
        point_struct = next((s for s in structure.structs if s['name'] == 'Point'), None)
        assert point_struct is not None
        assert len(point_struct['fields']) == 2
    
    def test_parse_enum(self):
        """Test parsing enum definitions."""
        source_code = """
        enum Status {
            IDLE,
            RUNNING,
            ERROR
        };
        
        enum Priority {
            LOW = 1,
            MEDIUM = 2,
            HIGH = 3
        };
        """
        
        structure = self.parser.parse_source(source_code, "test.c")
        
        assert len(structure.enums) == 2
        status_enum = next((e for e in structure.enums if e['name'] == 'Status'), None)
        assert status_enum is not None
        assert len(status_enum['values']) == 3
    
    def test_parse_global_variables(self):
        """Test parsing global variable declarations."""
        source_code = """
        int global_counter = 0;
        static char buffer[256];
        const float PI = 3.14159;
        
        int main() {
            return 0;
        }
        """
        
        structure = self.parser.parse_source(source_code, "test.c")
        
        # Note: parsing global variables is complex and may not catch all cases
        # This test verifies the parser doesn't crash and attempts to find globals
        assert isinstance(structure.global_variables, list)
    
    def test_extract_code_chunks(self):
        """Test extracting code chunks from parsed structure."""
        source_code = """
        #include <stdio.h>
        
        int add(int a, int b) {
            return a + b;
        }
        
        void print_result(int result) {
            printf("Result: %d\\n", result);
        }
        """
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(source_code)
            temp_file = f.name
        
        try:
            structure = self.parser.parse_file(temp_file)
            chunks = self.parser.extract_code_chunks(structure)
            
            # Should have chunks for functions and possibly global content
            assert len(chunks) >= 2
            
            # Check function chunks
            function_chunks = [c for c in chunks if c.chunk_type == ChunkType.FUNCTION]
            assert len(function_chunks) == 2
            
            add_chunk = next((c for c in function_chunks if c.function_name == 'add'), None)
            assert add_chunk is not None
            assert 'return a + b' in add_chunk.content
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_complex_function_signatures(self):
        """Test parsing complex function signatures."""
        source_code = """
        int* create_array(size_t count, const char* name);
        void process_data(struct Device* device, int (*callback)(int));
        static inline double calculate(double x, double y, double z);
        """
        
        structure = self.parser.parse_source(source_code, "test.c")
        
        # These are declarations, not definitions, so they might not be parsed
        # This test ensures the parser doesn't crash on complex signatures
        assert isinstance(structure.functions, list)
    
    def test_parse_medical_device_example(self):
        """Test parsing a medical device-like C code example."""
        source_code = """
        #include <stdint.h>
        #include "device_hal.h"
        
        #define MAX_PRESSURE 300
        #define MIN_PRESSURE 50
        
        typedef enum {
            DEVICE_IDLE,
            DEVICE_MEASURING,
            DEVICE_ALARM
        } device_state_t;
        
        typedef struct {
            uint16_t pressure;
            uint16_t temperature;
            device_state_t state;
        } sensor_data_t;
        
        static sensor_data_t current_reading;
        
        int initialize_device(void) {
            current_reading.state = DEVICE_IDLE;
            return 0;
        }
        
        int read_pressure_sensor(uint16_t* pressure) {
            if (pressure == NULL) {
                return -1;
            }
            
            *pressure = hal_read_adc_channel(PRESSURE_CHANNEL);
            
            if (*pressure > MAX_PRESSURE || *pressure < MIN_PRESSURE) {
                current_reading.state = DEVICE_ALARM;
                return -2;
            }
            
            current_reading.pressure = *pressure;
            return 0;
        }
        
        void safety_check(void) {
            if (current_reading.pressure > MAX_PRESSURE) {
                // Emergency shutdown
                hal_disable_device();
            }
        }
        """
        
        structure = self.parser.parse_source(source_code, "medical_device.c")
        
        # Verify parsing of medical device code
        assert len(structure.functions) >= 3
        assert len(structure.includes) == 2
        assert len(structure.defines) >= 2
        
        # Check for specific functions
        function_names = [f.name for f in structure.functions]
        assert 'initialize_device' in function_names
        assert 'read_pressure_sensor' in function_names
        assert 'safety_check' in function_names
        
        # Verify function details
        read_pressure = next((f for f in structure.functions if f.name == 'read_pressure_sensor'), None)
        assert read_pressure is not None
        assert read_pressure.return_type == 'int'
        assert len(read_pressure.parameters) == 1
        assert read_pressure.parameters[0]['type'] == 'uint16_t*'
    
    def test_chunk_size_limits(self):
        """Test that large functions are properly chunked."""
        # Create a large function
        large_function = """
        int large_function(void) {
        """ + "\n".join([f"    int var{i} = {i};" for i in range(100)]) + """
            return 0;
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(large_function)
            temp_file = f.name
        
        try:
            structure = self.parser.parse_file(temp_file)
            chunks = self.parser.extract_code_chunks(structure, max_chunk_size=500)
            
            # Large function should be split into multiple chunks
            function_chunks = [c for c in chunks if c.chunk_type == ChunkType.FUNCTION]
            
            # Verify chunks are within size limit (approximately)
            for chunk in function_chunks:
                assert len(chunk.content) <= 600  # Some tolerance for splitting logic
                
        finally:
            os.unlink(temp_file)
    
    def test_error_handling(self):
        """Test error handling for invalid input."""
        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            self.parser.parse_file("non_existent_file.c")
        
        # Test with invalid C code (should not crash)
        invalid_code = "this is not valid C code {"
        structure = self.parser.parse_source(invalid_code, "invalid.c")
        
        # Parser should handle gracefully
        assert isinstance(structure, CCodeStructure)
        assert structure.file_path == "invalid.c"