# Command Line Error Handling Improvements

## Overview
Enhanced the command line interface with comprehensive error handling for configuration files, project paths, output directories, and other command line arguments. The improvements provide clear error messages with actionable suggestions to help users resolve issues quickly.

## Key Improvements

### 1. **Configuration File Error Handling**

#### **File Not Found**
```bash
$ python -m medical_analyzer --config /non/existent/config.json
Error: File does not exist: /non/existent/config.json

Suggestions:
  1. Check that the file path is correct
  2. Verify file permissions (should be readable)
  3. Use --init-config to create a default configuration file
  4. Example: python -m medical_analyzer --init-config
```

#### **Permission Denied**
- Detects when config files exist but are not readable
- Provides specific suggestions for fixing permissions
- Includes example commands for fixing permissions

#### **Invalid Configuration Format**
- Catches JSON parsing errors and invalid configuration structure
- Suggests using --init-config to create a valid configuration
- Provides guidance on checking configuration format

### 2. **Project Path Validation**

#### **Directory Not Found**
```bash
$ python -m medical_analyzer --headless --project-path /non/existent/project
Error: Directory does not exist: /non/existent/project

Suggestions:
  1. Check that the directory path is correct
  2. Verify directory permissions (should be readable)
  3. Ensure the path points to a directory, not a file
  4. Try: ls -la /non/existent (to check if directory exists)
```

#### **Path is Not a Directory**
- Detects when project path points to a file instead of directory
- Provides clear guidance on what's expected

#### **Permission Issues**
- Validates directory read permissions
- Suggests permission fixes with example commands

### 3. **Output Directory Handling**

#### **Automatic Directory Creation**
- Attempts to create output directories if they don't exist
- Provides detailed error messages if creation fails

#### **Permission Validation**
- Checks write permissions on output directories
- Suggests permission fixes and alternative locations

#### **Path Conflicts**
- Detects when output path exists but is not a directory
- Suggests alternative solutions

### 4. **Headless Mode Requirements**

#### **Missing Project Path**
```bash
$ python -m medical_analyzer --headless
Error: Project path is required for headless mode.
Use --project-path to specify the project directory to analyze.
Example: python -m medical_analyzer --headless --project-path /path/to/project
```

### 5. **Configuration Initialization**

#### **Enhanced --init-config**
```bash
$ python -m medical_analyzer --init-config
✅ Configuration file created successfully at: /home/user/.medical_analyzer/config.json
You can now use --config /home/user/.medical_analyzer/config.json to use this configuration.
```

#### **Overwrite Protection**
- Asks for confirmation before overwriting existing configuration files
- Provides clear feedback on what was created

## Technical Implementation

### **Helper Functions**

#### **Error Message Formatting**
```python
def print_error_with_suggestions(error_type: str, message: str, suggestions: list = None):
    """Print error message with helpful suggestions."""
    print(f"Error: {message}")
    
    if suggestions:
        print("\nSuggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    
    print()  # Add blank line for readability
```

#### **File Access Validation**
```python
def validate_file_access(file_path: Path, operation: str = "read") -> tuple[bool, str]:
    """Validate file access and return detailed error information."""
    if not file_path.exists():
        return False, f"File does not exist: {file_path}"
    
    if operation == "read" and not os.access(file_path, os.R_OK):
        return False, f"File is not readable: {file_path}"
    
    return True, ""
```

#### **Directory Access Validation**
```python
def validate_directory_access(dir_path: Path, operation: str = "read") -> tuple[bool, str]:
    """Validate directory access and return detailed error information."""
    if not dir_path.exists():
        return False, f"Directory does not exist: {dir_path}"
    
    if not dir_path.is_dir():
        return False, f"Path exists but is not a directory: {dir_path}"
    
    return True, ""
```

### **Error Categories Handled**

1. **File System Errors**
   - File/directory not found
   - Permission denied
   - Path type mismatches (file vs directory)

2. **Configuration Errors**
   - Invalid JSON format
   - Missing required configuration keys
   - Configuration loading failures

3. **Command Line Argument Errors**
   - Missing required arguments
   - Invalid argument combinations
   - Path validation failures

4. **Application Initialization Errors**
   - Logging setup failures
   - Service initialization failures
   - Dependency import errors

## Error Message Design Principles

### **1. Clear and Specific**
- Error messages clearly state what went wrong
- Include specific file paths and error details
- Avoid technical jargon when possible

### **2. Actionable Suggestions**
- Every error includes numbered suggestions
- Suggestions are specific and actionable
- Include example commands when helpful

### **3. Progressive Disclosure**
- Basic error message first
- Detailed suggestions follow
- Additional context in logs

### **4. User-Friendly**
- Use plain language
- Provide examples
- Guide users toward solutions

## Benefits

### **1. Improved User Experience**
- Users can quickly understand and fix issues
- Reduced frustration with clear guidance
- Self-service problem resolution

### **2. Reduced Support Burden**
- Common issues are self-explanatory
- Users can resolve problems independently
- Clear documentation of requirements

### **3. Better Error Recovery**
- Graceful handling of common scenarios
- Fallback options when possible
- Clear exit codes for scripting

### **4. Development Efficiency**
- Easier debugging during development
- Clear validation of inputs
- Consistent error handling patterns

## Usage Examples

### **Successful Configuration Creation**
```bash
$ python -m medical_analyzer --init-config
✅ Configuration file created successfully at: ~/.medical_analyzer/config.json
You can now use --config ~/.medical_analyzer/config.json to use this configuration.
```

### **Successful Analysis with Custom Config**
```bash
$ python -m medical_analyzer --config ~/.medical_analyzer/config.json --project-path ./my_project
# Application starts with custom configuration
```

### **Headless Mode Analysis**
```bash
$ python -m medical_analyzer --headless --project-path ./my_project --output-dir ./results
# Runs analysis in headless mode with specified paths
```

## Files Modified
- `medical_analyzer/__main__.py` - Enhanced error handling throughout
- Added helper functions for validation and error reporting
- Improved error messages with actionable suggestions
- Better handling of edge cases and permission issues

The command line interface now provides a much more user-friendly experience with comprehensive error handling and helpful guidance for resolving common issues.