"""User acceptance tests for the Medical Software Analysis Tool."""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path

import pytest

from medical_analyzer import __version__
from medical_analyzer.config.config_manager import ConfigManager


@pytest.fixture
def sample_project_dir():
    """Create a temporary directory with sample medical software files."""
    temp_dir = tempfile.mkdtemp(prefix="medical_analyzer_sample_")
    
    # Create a simple C file with medical device code patterns
    c_file_path = os.path.join(temp_dir, "medical_device.c")
    with open(c_file_path, "w") as f:
        f.write("""
        #include <stdio.h>
        #include <stdlib.h>
        
        // Medical device control module
        // Safety-critical component for patient monitoring
        
        #define ALARM_THRESHOLD 37.5  // Temperature threshold in Celsius
        #define SAMPLING_RATE 100     // Samples per second
        #define FDA_REGULATED 1       // This is an FDA regulated device
        
        float patient_temperature = 0.0;
        int alarm_status = 0;
        
        // Function to check patient vital signs and trigger alarms
        void check_vital_signs(float temperature, float heart_rate, float blood_pressure) {
            // Log the measurements
            printf("Temperature: %.1f C, Heart Rate: %.1f bpm, BP: %.1f mmHg\n", 
                   temperature, heart_rate, blood_pressure);
            
            // Check if temperature exceeds threshold
            if (temperature > ALARM_THRESHOLD) {
                alarm_status = 1;
                printf("WARNING: High temperature detected!\n");
            } else {
                alarm_status = 0;
            }
            
            // Store the current temperature
            patient_temperature = temperature;
        }
        
        // Main function for the medical monitoring system
        int main() {
            printf("Medical Device Monitoring System v1.0\n");
            printf("FDA Regulated: %s\n", FDA_REGULATED ? "Yes" : "No");
            
            // Simulate patient monitoring
            check_vital_signs(36.5, 75.0, 120.0);
            check_vital_signs(38.2, 90.0, 135.0);
            
            return 0;
        }
        """)
    
    # Create a header file
    h_file_path = os.path.join(temp_dir, "medical_device.h")
    with open(h_file_path, "w") as f:
        f.write("""
        #ifndef MEDICAL_DEVICE_H
        #define MEDICAL_DEVICE_H
        
        // Medical device control module header
        // Contains declarations for safety-critical functions
        
        // Function to check patient vital signs and trigger alarms
        void check_vital_signs(float temperature, float heart_rate, float blood_pressure);
        
        // Function to calibrate sensors (IEC 62304 Class C)
        int calibrate_sensors(void);
        
        // Function to log data to secure storage (21 CFR Part 11 compliant)
        int log_patient_data(float temperature, float heart_rate, float blood_pressure);
        
        #endif // MEDICAL_DEVICE_H
        """)
    
    # Create a README file
    readme_path = os.path.join(temp_dir, "README.md")
    with open(readme_path, "w") as f:
        f.write("""
        # Medical Device Monitoring System
        
        This software is designed for patient monitoring and is regulated by FDA as a Class II medical device.
        
        ## Regulatory Information
        
        - FDA Product Code: MSX
        - Classification: Class II
        - Regulation Number: 21 CFR 870.2300
        
        ## Development Standards
        
        This software is developed following:
        - IEC 62304 - Medical device software life cycle processes
        - ISO 14971 - Application of risk management to medical devices
        - 21 CFR Part 11 - Electronic records and signatures
        """)
    
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_gui_launch():
    """Test that the GUI application launches without errors."""
    # Skip this test if running in a CI environment without display
    if os.environ.get("CI") == "true" or os.environ.get("DISPLAY") is None:
        pytest.skip("Skipping GUI test in headless environment")
    
    # Launch the GUI with a timeout to avoid hanging
    process = subprocess.Popen(
        [sys.executable, "-m", "medical_analyzer"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait a short time to see if the process crashes immediately
    try:
        stdout, stderr = process.communicate(timeout=3)
        # If we get here, the process exited within the timeout
        assert process.returncode == 0, f"GUI failed to start: {stderr.decode()}"
    except subprocess.TimeoutExpired:
        # This is actually good - it means the GUI is still running
        pass
    finally:
        # Clean up the process
        process.kill()


def test_headless_analysis(sample_project_dir):
    """Test that the application can analyze a sample project in headless mode."""
    # Create a temporary output directory
    output_dir = tempfile.mkdtemp(prefix="medical_analyzer_output_")
    
    try:
        # Run the analysis in headless mode
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "medical_analyzer",
                "--headless",
                "--input",
                sample_project_dir,
                "--output",
                output_dir,
                "--verbose",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        
        # Check that the process completed successfully
        assert result.returncode == 0, f"Analysis failed: {result.stderr}"
        
        # Check that output files were created
        assert os.path.exists(output_dir), "Output directory not created"
        
        # Check for expected output files (the exact files will depend on your implementation)
        expected_files = ["analysis_report.json", "regulatory_findings.json"]
        for file in expected_files:
            file_path = os.path.join(output_dir, file)
            assert os.path.exists(file_path), f"Expected output file {file} not found"
            
            # Check that the file contains valid JSON
            with open(file_path, "r") as f:
                data = json.load(f)
                assert isinstance(data, dict), f"Invalid JSON in {file}"
    
    finally:
        # Clean up
        shutil.rmtree(output_dir, ignore_errors=True)


def test_config_file_creation():
    """Test that the application creates a config file if it doesn't exist."""
    # Create a temporary directory for the test
    temp_dir = tempfile.mkdtemp(prefix="medical_analyzer_config_test_")
    
    try:
        # Set the config directory environment variable
        os.environ["MEDICAL_ANALYZER_CONFIG_DIR"] = temp_dir
        
        # Run the application with the --init-config flag
        result = subprocess.run(
            [sys.executable, "-m", "medical_analyzer", "--init-config"],
            capture_output=True,
            text=True,
            check=False,
        )
        
        # Check that the process completed successfully
        assert result.returncode == 0, f"Config initialization failed: {result.stderr}"
        
        # Check that the config file was created
        config_file = os.path.join(temp_dir, "config.json")
        assert os.path.exists(config_file), "Config file not created"
        
        # Check that the config file contains valid JSON
        with open(config_file, "r") as f:
            config_data = json.load(f)
            assert isinstance(config_data, dict), "Invalid JSON in config file"
            
            # Check for required sections
            assert "llm" in config_data, "LLM configuration section missing"
            assert "database" in config_data, "Database configuration section missing"
            assert "export" in config_data, "Export configuration section missing"
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)
        # Reset the environment variable
        if "MEDICAL_ANALYZER_CONFIG_DIR" in os.environ:
            del os.environ["MEDICAL_ANALYZER_CONFIG_DIR"]


def test_version_command():
    """Test that the --version command works correctly."""
    result = subprocess.run(
        [sys.executable, "-m", "medical_analyzer", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    
    # Check that the process completed successfully
    assert result.returncode == 0, f"Version command failed: {result.stderr}"
    
    # Check that the output contains the version number
    assert __version__ in result.stdout, "Version number not found in output"


def test_help_command():
    """Test that the --help command works correctly."""
    result = subprocess.run(
        [sys.executable, "-m", "medical_analyzer", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    
    # Check that the process completed successfully
    assert result.returncode == 0, f"Help command failed: {result.stderr}"
    
    # Check that the output contains expected help text
    assert "usage" in result.stdout.lower(), "Usage information not found in help output"
    assert "--headless" in result.stdout, "--headless option not found in help output"
    assert "--version" in result.stdout, "--version option not found in help output"
    assert "--config" in result.stdout, "--config option not found in help output"