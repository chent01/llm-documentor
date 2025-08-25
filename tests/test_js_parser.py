"""
Unit tests for JavaScript code parser.
"""

import pytest
import tempfile
import os
from medical_analyzer.parsers.js_parser import JSParser, FunctionSignature, ClassDefinition, JSCodeStructure
from medical_analyzer.models.enums import ChunkType


class TestJSParser:
    """Test cases for JSParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = JSParser()
    
    def test_parser_initialization(self):
        """Test that parser initializes correctly."""
        # Parser should initialize even if tree-sitter is not available
        assert self.parser is not None
    
    def test_parse_simple_function(self):
        """Test parsing a simple JavaScript function."""
        source_code = """
        function add(a, b) {
            return a + b;
        }
        """
        
        structure = self.parser.parse_source(source_code, "test.js")
        
        assert len(structure.functions) == 1
        func = structure.functions[0]
        assert func.name == "add"
        assert len(func.parameters) == 2
        assert "a" in func.parameters
        assert "b" in func.parameters
        assert func.is_async == False
        assert func.is_arrow == False
    
    def test_parse_arrow_function(self):
        """Test parsing arrow functions."""
        source_code = """
        const multiply = (x, y) => {
            return x * y;
        };
        
        const square = x => x * x;
        """
        
        structure = self.parser.parse_source(source_code, "test.js")
        
        # Should find arrow functions
        assert len(structure.functions) >= 1
        
        # Check if we found the arrow functions
        arrow_funcs = [f for f in structure.functions if f.is_arrow]
        assert len(arrow_funcs) >= 1
    
    def test_parse_async_function(self):
        """Test parsing async functions."""
        source_code = """
        async function fetchData(url) {
            const response = await fetch(url);
            return response.json();
        }
        
        const asyncArrow = async (data) => {
            return await processData(data);
        };
        """
        
        structure = self.parser.parse_source(source_code, "test.js")
        
        # Should find async functions
        async_funcs = [f for f in structure.functions if f.is_async]
        assert len(async_funcs) >= 1
        
        # Check specific function
        fetch_func = next((f for f in structure.functions if f.name == "fetchData"), None)
        assert fetch_func is not None
        assert fetch_func.is_async == True
    
    def test_parse_class(self):
        """Test parsing JavaScript classes."""
        source_code = """
        class Device {
            constructor(name, id) {
                this.name = name;
                this.id = id;
            }
            
            async initialize() {
                return await this.connect();
            }
            
            getData() {
                return this.data;
            }
        }
        """
        
        structure = self.parser.parse_source(source_code, "test.js")
        
        assert len(structure.classes) == 1
        device_class = structure.classes[0]
        assert device_class.name == "Device"
        assert len(device_class.methods) >= 2  # initialize and getData (constructor might not be counted)
        
        # Check methods
        method_names = [m.name for m in device_class.methods]
        assert "initialize" in method_names or "getData" in method_names
    
    def test_parse_class_inheritance(self):
        """Test parsing class inheritance."""
        source_code = """
        class MedicalDevice extends Device {
            constructor(name, id, type) {
                super(name, id);
                this.type = type;
            }
            
            calibrate() {
                return this.performCalibration();
            }
        }
        """
        
        structure = self.parser.parse_source(source_code, "test.js")
        
        assert len(structure.classes) == 1
        medical_device = structure.classes[0]
        assert medical_device.name == "MedicalDevice"
        assert medical_device.extends == "Device"
    
    def test_parse_imports_exports(self):
        """Test parsing import and export statements."""
        source_code = """
        import { Component } from 'react';
        import fs from 'fs';
        import * as utils from './utils';
        
        export default class App extends Component {
            render() {
                return null;
            }
        }
        
        export const helper = () => {};
        export { utils };
        """
        
        structure = self.parser.parse_source(source_code, "test.js")
        
        # Should find imports and exports
        assert len(structure.imports) >= 2
        assert len(structure.exports) >= 2
        
        # Check import details
        import_statements = [imp['statement'] for imp in structure.imports]
        assert any('react' in stmt for stmt in import_statements)
        assert any('fs' in stmt for stmt in import_statements)
    
    def test_parse_commonjs_requires(self):
        """Test parsing CommonJS require statements."""
        source_code = """
        const fs = require('fs');
        const path = require('path');
        const { EventEmitter } = require('events');
        
        function processFile(filename) {
            const data = fs.readFileSync(filename);
            return data;
        }
        
        module.exports = { processFile };
        """
        
        structure = self.parser.parse_source(source_code, "test.js")
        
        # Should find require statements
        assert len(structure.requires) >= 2
        assert 'fs' in structure.requires
        assert 'path' in structure.requires
    
    def test_parse_variable_declarations(self):
        """Test parsing variable declarations."""
        source_code = """
        const API_URL = 'https://api.example.com';
        let currentUser = null;
        var globalConfig = {};
        
        function initialize() {
            const localVar = 'test';
            let counter = 0;
        }
        """
        
        structure = self.parser.parse_source(source_code, "test.js")
        
        # Should find variable declarations
        assert len(structure.variables) >= 3
        
        var_names = [var['name'] for var in structure.variables]
        assert 'API_URL' in var_names
        assert 'currentUser' in var_names
        assert 'globalConfig' in var_names
    
    def test_extract_code_chunks(self):
        """Test extracting code chunks from parsed structure."""
        source_code = """
        import { Device } from './device';
        
        class MedicalMonitor extends Device {
            constructor(config) {
                super(config);
                this.readings = [];
            }
            
            async startMonitoring() {
                while (this.isActive) {
                    const reading = await this.readSensor();
                    this.readings.push(reading);
                }
            }
        }
        
        function validateReading(reading) {
            return reading.value > 0 && reading.timestamp;
        }
        
        export { MedicalMonitor, validateReading };
        """
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(source_code)
            temp_file = f.name
        
        try:
            structure = self.parser.parse_file(temp_file)
            chunks = self.parser.extract_code_chunks(structure)
            
            # Should have chunks for class, function, and possibly module-level code
            assert len(chunks) >= 2
            
            # Check for class chunk
            class_chunks = [c for c in chunks if c.chunk_type == ChunkType.CLASS]
            assert len(class_chunks) >= 1
            
            # Check for function chunk
            function_chunks = [c for c in chunks if c.chunk_type == ChunkType.FUNCTION]
            assert len(function_chunks) >= 1
            
            # Verify chunk content
            validate_chunk = next((c for c in function_chunks if c.function_name == 'validateReading'), None)
            if validate_chunk:
                assert 'validateReading' in validate_chunk.content
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_electron_specific_code(self):
        """Test parsing Electron-specific JavaScript code."""
        source_code = """
        const { app, BrowserWindow, ipcMain } = require('electron');
        const path = require('path');
        
        class ElectronApp {
            constructor() {
                this.mainWindow = null;
            }
            
            createWindow() {
                this.mainWindow = new BrowserWindow({
                    width: 1200,
                    height: 800,
                    webPreferences: {
                        nodeIntegration: true,
                        contextIsolation: false
                    }
                });
                
                this.mainWindow.loadFile('index.html');
            }
            
            setupIPC() {
                ipcMain.handle('get-device-data', async () => {
                    return await this.getDeviceData();
                });
            }
        }
        
        app.whenReady().then(() => {
            const electronApp = new ElectronApp();
            electronApp.createWindow();
            electronApp.setupIPC();
        });
        """
        
        structure = self.parser.parse_source(source_code, "main.js")
        
        # Should parse Electron code successfully
        assert len(structure.classes) == 1
        assert structure.classes[0].name == "ElectronApp"
        
        # Should find require statements for Electron modules
        assert 'electron' in structure.requires
        assert 'path' in structure.requires
        
        # Should find methods
        electron_class = structure.classes[0]
        method_names = [m.name for m in electron_class.methods]
        assert 'createWindow' in method_names
        assert 'setupIPC' in method_names
    
    def test_parse_medical_device_example(self):
        """Test parsing a medical device-like JavaScript code example."""
        source_code = """
        import { EventEmitter } from 'events';
        
        const PRESSURE_LIMITS = {
            MIN: 50,
            MAX: 300,
            CRITICAL: 250
        };
        
        class PressureMonitor extends EventEmitter {
            constructor(deviceId) {
                super();
                this.deviceId = deviceId;
                this.currentPressure = 0;
                this.isCalibrated = false;
            }
            
            async calibrate() {
                try {
                    await this.performCalibration();
                    this.isCalibrated = true;
                    this.emit('calibrated', this.deviceId);
                } catch (error) {
                    this.emit('error', error);
                }
            }
            
            readPressure() {
                if (!this.isCalibrated) {
                    throw new Error('Device not calibrated');
                }
                
                const reading = this.getSensorReading();
                this.currentPressure = reading.value;
                
                if (reading.value > PRESSURE_LIMITS.CRITICAL) {
                    this.emit('critical-pressure', reading);
                } else if (reading.value > PRESSURE_LIMITS.MAX) {
                    this.emit('high-pressure', reading);
                }
                
                return reading;
            }
            
            async performSafetyCheck() {
                const reading = this.readPressure();
                
                if (reading.value > PRESSURE_LIMITS.MAX) {
                    await this.emergencyShutdown();
                    return false;
                }
                
                return true;
            }
        }
        
        function validatePressureReading(reading) {
            return reading && 
                   typeof reading.value === 'number' && 
                   reading.value >= 0 && 
                   reading.timestamp;
        }
        
        export { PressureMonitor, validatePressureReading, PRESSURE_LIMITS };
        """
        
        structure = self.parser.parse_source(source_code, "pressure_monitor.js")
        
        # Verify parsing of medical device code
        assert len(structure.classes) == 1
        assert structure.classes[0].name == "PressureMonitor"
        assert structure.classes[0].extends == "EventEmitter"
        
        # Check methods
        pressure_class = structure.classes[0]
        method_names = [m.name for m in pressure_class.methods]
        assert 'calibrate' in method_names
        assert 'readPressure' in method_names
        assert 'performSafetyCheck' in method_names
        
        # Check for async methods
        async_methods = [m for m in pressure_class.methods if m.is_async]
        assert len(async_methods) >= 2  # calibrate and performSafetyCheck
        
        # Check functions
        function_names = [f.name for f in structure.functions]
        assert 'validatePressureReading' in function_names
        
        # Check imports and exports
        assert len(structure.imports) >= 1
        assert len(structure.exports) >= 1
        
        # Check variables
        var_names = [v['name'] for v in structure.variables]
        assert 'PRESSURE_LIMITS' in var_names
    
    def test_error_handling(self):
        """Test error handling for invalid input."""
        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            self.parser.parse_file("non_existent_file.js")
        
        # Test with invalid JavaScript code (should not crash)
        invalid_code = "this is not valid JavaScript code {"
        structure = self.parser.parse_source(invalid_code, "invalid.js")
        
        # Parser should handle gracefully
        assert isinstance(structure, JSCodeStructure)
        assert structure.file_path == "invalid.js"
    
    def test_get_file_metadata(self):
        """Test extracting file metadata."""
        source_code = """
        function test() {
            return 'test';
        }
        
        class TestClass {
            method() {}
        }
        """
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(source_code)
            temp_file = f.name
        
        try:
            metadata = self.parser.get_file_metadata(temp_file)
            
            assert metadata.file_path == temp_file
            assert metadata.file_type == "javascript"
            assert metadata.file_size > 0
            assert metadata.function_count >= 1
            
        finally:
            os.unlink(temp_file)
    
    def test_fallback_regex_parsing(self):
        """Test that regex fallback parsing works when tree-sitter is not available."""
        # Force fallback mode
        original_parser = self.parser.parser
        original_language = self.parser.language
        
        self.parser.parser = None
        self.parser.language = None
        
        try:
            source_code = """
            function simpleFunction(param1, param2) {
                return param1 + param2;
            }
            
            const arrowFunc = (x, y) => x * y;
            
            class SimpleClass {
                method(arg) {
                    return arg;
                }
            }
            """
            
            structure = self.parser.parse_source(source_code, "test.js")
            
            # Should still parse basic structures
            assert len(structure.functions) >= 1
            assert len(structure.classes) >= 1
            
            # Check function parsing
            simple_func = next((f for f in structure.functions if f.name == "simpleFunction"), None)
            assert simple_func is not None
            assert len(simple_func.parameters) == 2
            
        finally:
            # Restore original parser
            self.parser.parser = original_parser
            self.parser.language = original_language