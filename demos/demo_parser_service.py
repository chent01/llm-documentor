#!/usr/bin/env python3
"""
Demonstration script for the ParserService orchestrator.
Shows complete parsing pipeline with code chunking and metadata extraction.
"""

import os
import tempfile
from medical_analyzer.parsers.parser_service import ParserService
from medical_analyzer.models.core import ProjectStructure


def create_sample_files():
    """Create sample C and JavaScript files for demonstration."""
    temp_dir = tempfile.mkdtemp()
    
    # Sample C file - medical device sensor code
    c_content = '''
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

#define MAX_READINGS 100
#define SENSOR_THRESHOLD 75.0

typedef struct {
    int sensor_id;
    float value;
    bool is_valid;
} SensorReading;

static SensorReading readings[MAX_READINGS];
static int reading_count = 0;

/**
 * Initialize the sensor system
 */
int init_sensor_system(void) {
    reading_count = 0;
    for (int i = 0; i < MAX_READINGS; i++) {
        readings[i].sensor_id = -1;
        readings[i].value = 0.0;
        readings[i].is_valid = false;
    }
    return 0;
}

/**
 * Read sensor value and validate
 */
bool read_sensor_value(int sensor_id, float* value) {
    if (sensor_id < 0 || value == NULL) {
        return false;
    }
    
    // Simulate sensor reading
    *value = (float)(rand() % 100);
    
    // Store reading if space available
    if (reading_count < MAX_READINGS) {
        readings[reading_count].sensor_id = sensor_id;
        readings[reading_count].value = *value;
        readings[reading_count].is_valid = (*value < SENSOR_THRESHOLD);
        reading_count++;
    }
    
    return true;
}

/**
 * Check if sensor reading is within safe limits
 */
bool is_reading_safe(float value) {
    return value < SENSOR_THRESHOLD;
}

/**
 * Get average of all valid readings
 */
float get_average_reading(void) {
    float sum = 0.0;
    int valid_count = 0;
    
    for (int i = 0; i < reading_count; i++) {
        if (readings[i].is_valid) {
            sum += readings[i].value;
            valid_count++;
        }
    }
    
    return (valid_count > 0) ? (sum / valid_count) : 0.0;
}
'''
    
    # Sample JavaScript file - medical device UI
    js_content = '''
import React, { useState, useEffect } from 'react';
import { ipcRenderer } from 'electron';

const ALERT_THRESHOLD = 80;
const UPDATE_INTERVAL = 1000;

class SensorMonitor {
    constructor(sensorId) {
        this.sensorId = sensorId;
        this.isActive = false;
        this.callbacks = [];
    }
    
    start() {
        this.isActive = true;
        this.monitorLoop();
    }
    
    stop() {
        this.isActive = false;
    }
    
    async monitorLoop() {
        while (this.isActive) {
            try {
                const reading = await this.getSensorReading();
                this.notifyCallbacks(reading);
                
                if (reading.value > ALERT_THRESHOLD) {
                    this.triggerAlert(reading);
                }
                
                await this.delay(UPDATE_INTERVAL);
            } catch (error) {
                console.error('Sensor monitoring error:', error);
                this.handleError(error);
            }
        }
    }
    
    async getSensorReading() {
        return new Promise((resolve, reject) => {
            ipcRenderer.invoke('read-sensor', this.sensorId)
                .then(resolve)
                .catch(reject);
        });
    }
    
    triggerAlert(reading) {
        const alertData = {
            sensorId: this.sensorId,
            value: reading.value,
            timestamp: new Date().toISOString(),
            severity: reading.value > 90 ? 'critical' : 'warning'
        };
        
        ipcRenderer.send('sensor-alert', alertData);
    }
    
    handleError(error) {
        ipcRenderer.send('sensor-error', {
            sensorId: this.sensorId,
            error: error.message,
            timestamp: new Date().toISOString()
        });
    }
    
    onReading(callback) {
        this.callbacks.push(callback);
    }
    
    notifyCallbacks(reading) {
        this.callbacks.forEach(callback => {
            try {
                callback(reading);
            } catch (error) {
                console.error('Callback error:', error);
            }
        });
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

function SensorDashboard() {
    const [sensors, setSensors] = useState([]);
    const [alerts, setAlerts] = useState([]);
    const [isMonitoring, setIsMonitoring] = useState(false);
    
    useEffect(() => {
        initializeSensors();
        setupEventListeners();
        
        return () => {
            cleanup();
        };
    }, []);
    
    const initializeSensors = async () => {
        try {
            const sensorList = await ipcRenderer.invoke('get-sensors');
            setSensors(sensorList.map(id => new SensorMonitor(id)));
        } catch (error) {
            console.error('Failed to initialize sensors:', error);
        }
    };
    
    const setupEventListeners = () => {
        ipcRenderer.on('sensor-alert', (event, alertData) => {
            setAlerts(prev => [...prev, alertData]);
        });
    };
    
    const startMonitoring = () => {
        sensors.forEach(sensor => sensor.start());
        setIsMonitoring(true);
    };
    
    const stopMonitoring = () => {
        sensors.forEach(sensor => sensor.stop());
        setIsMonitoring(false);
    };
    
    const cleanup = () => {
        sensors.forEach(sensor => sensor.stop());
        ipcRenderer.removeAllListeners('sensor-alert');
    };
    
    return (
        <div className="sensor-dashboard">
            <h1>Medical Device Sensor Monitor</h1>
            <div className="controls">
                <button 
                    onClick={startMonitoring} 
                    disabled={isMonitoring}
                >
                    Start Monitoring
                </button>
                <button 
                    onClick={stopMonitoring} 
                    disabled={!isMonitoring}
                >
                    Stop Monitoring
                </button>
            </div>
            <div className="sensor-grid">
                {sensors.map(sensor => (
                    <SensorCard key={sensor.sensorId} sensor={sensor} />
                ))}
            </div>
            <AlertPanel alerts={alerts} />
        </div>
    );
}

const validateSensorReading = (reading) => {
    return reading && 
           typeof reading.value === 'number' && 
           reading.value >= 0 && 
           reading.value <= 100;
};

export { SensorMonitor, SensorDashboard, validateSensorReading };
'''
    
    # Create files
    c_file = os.path.join(temp_dir, 'sensor_system.c')
    js_file = os.path.join(temp_dir, 'sensor_ui.js')
    
    with open(c_file, 'w', encoding='utf-8') as f:
        f.write(c_content)
    
    with open(js_file, 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    return temp_dir, [c_file, js_file]


def demonstrate_parser_service():
    """Demonstrate the complete parsing pipeline."""
    print("=== Medical Software Analysis Tool - Parser Service Demo ===\n")
    
    # Create sample files
    temp_dir, files = create_sample_files()
    print(f"Created sample files in: {temp_dir}")
    for file in files:
        print(f"  - {os.path.basename(file)}")
    print()
    
    # Initialize parser service
    parser_service = ParserService(max_chunk_size=800)
    print("Initialized ParserService with max_chunk_size=800\n")
    
    # Create project structure
    project = ProjectStructure(
        root_path=temp_dir,
        selected_files=files,
        description="Medical device sensor monitoring system with C backend and JavaScript UI"
    )
    
    # Parse the project
    print("Parsing project files...")
    parsed_files = parser_service.parse_project(project)
    print(f"Successfully parsed {len(parsed_files)} files\n")
    
    # Display results for each file
    for parsed_file in parsed_files:
        print(f"=== File: {os.path.basename(parsed_file.file_path)} ===")
        
        # File metadata
        metadata = parsed_file.file_metadata
        print(f"File Type: {metadata.file_type}")
        print(f"File Size: {metadata.file_size} bytes")
        print(f"Line Count: {metadata.line_count}")
        print(f"Function Count: {metadata.function_count}")
        print(f"Encoding: {metadata.encoding}")
        print()
        
        # Code structure info
        if hasattr(parsed_file.code_structure, 'functions'):
            functions = parsed_file.code_structure.functions
            print(f"Functions found: {len(functions)}")
            for func in functions[:3]:  # Show first 3 functions
                # Handle different parameter formats (C vs JS)
                if hasattr(func, 'parameters') and func.parameters:
                    if isinstance(func.parameters[0], dict):
                        # C-style parameters with type and name
                        params = ', '.join([f"{p.get('type', '')} {p.get('name', '')}" 
                                          for p in func.parameters])
                    else:
                        # JS-style parameters (just names)
                        params = ', '.join(func.parameters)
                else:
                    params = ''
                
                if hasattr(func, 'return_type'):
                    print(f"  - {func.return_type} {func.name}({params})")
                else:
                    print(f"  - {func.name}({params})")
            if len(functions) > 3:
                print(f"  ... and {len(functions) - 3} more")
        
        if hasattr(parsed_file.code_structure, 'classes'):
            classes = parsed_file.code_structure.classes
            if classes:
                print(f"Classes found: {len(classes)}")
                for cls in classes:
                    extends_info = f" extends {cls.extends}" if cls.extends else ""
                    print(f"  - class {cls.name}{extends_info} ({len(cls.methods)} methods)")
        
        print()
        
        # Chunks analysis
        chunks = parsed_file.chunks
        print(f"Code chunks extracted: {len(chunks)}")
        
        chunk_types = {}
        for chunk in chunks:
            chunk_type = chunk.chunk_type.name
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
        for chunk_type, count in chunk_types.items():
            print(f"  - {chunk_type}: {count}")
        
        print()
        
        # Show sample chunks
        print("Sample chunks:")
        for i, chunk in enumerate(chunks[:2]):  # Show first 2 chunks
            print(f"  Chunk {i+1}: {chunk.chunk_type.name}")
            print(f"    Function: {chunk.function_name or 'N/A'}")
            print(f"    Lines: {chunk.start_line}-{chunk.end_line}")
            print(f"    Size: {len(chunk.content)} characters")
            
            # Show first few lines of content
            content_lines = chunk.content.split('\n')[:3]
            for line in content_lines:
                print(f"    | {line}")
            if len(chunk.content.split('\n')) > 3:
                print("    | ...")
            print()
        
        print("-" * 60)
        print()
    
    # Overall statistics
    all_chunks = []
    for parsed_file in parsed_files:
        all_chunks.extend(parsed_file.chunks)
    
    stats = parser_service.get_chunk_statistics(all_chunks)
    
    print("=== Overall Project Statistics ===")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Function chunks: {stats['function_chunks']}")
    print(f"Class chunks: {stats['class_chunks']}")
    print(f"Global chunks: {stats['global_chunks']}")
    print(f"C chunks: {stats['c_chunks']}")
    print(f"JavaScript chunks: {stats['js_chunks']}")
    print(f"Partial chunks (split): {stats['partial_chunks']}")
    print(f"Average chunk size: {stats['average_chunk_size']} characters")
    print(f"Largest chunk: {stats['max_chunk_size']} characters")
    print(f"Smallest chunk: {stats['min_chunk_size']} characters")
    print()
    
    # Code references for traceability
    references = parser_service.extract_code_references(all_chunks)
    print(f"Code references for traceability: {len(references)}")
    print("Sample references:")
    for ref in references[:3]:
        print(f"  - {os.path.basename(ref.file_path)}:{ref.start_line}-{ref.end_line} "
              f"({ref.function_name or 'global'}) - {ref.context}")
    print()
    
    # Supported file types
    extensions = parser_service.get_supported_extensions()
    print(f"Supported file extensions: {', '.join(sorted(extensions))}")
    print()
    
    print("=== Demo Complete ===")
    print(f"Temporary files created in: {temp_dir}")
    print("You can examine the generated files and run this demo again.")
    
    return temp_dir, parsed_files


if __name__ == '__main__':
    demonstrate_parser_service()