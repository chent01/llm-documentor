# File Selection Issue Analysis and Fix

## Problem Description
Requirements generation is not properly restricted to selected files. The analysis appears to be gathering requirements from all files in the project instead of only the files selected by the user.

## Root Cause Analysis

### 1. Current File Selection Flow
The file selection flow works correctly through these stages:
- **Ingestion**: `IngestionService.scan_project()` properly handles `selected_files` parameter
- **Parsing**: `ParserService.parse_project()` only processes `project_structure.selected_files`
- **Feature Extraction**: `FeatureExtractor.extract_features()` only processes chunks from parsed files
- **Requirements Generation**: `RequirementsGenerator.generate_requirements_from_features()` only uses features from selected files

### 2. Identified Issues

#### Issue 1: SOUP Detection Scans All Files
The SOUP detector (`SOUPDetector.detect_soup_components()`) uses `project_root.rglob(filename)` to find dependency files like `requirements.txt`, `package.json`, etc. This is actually correct behavior for SOUP detection, as it needs to identify all third-party dependencies regardless of which source files are selected.

#### Issue 2: Potential Cross-Contamination in Analysis Pipeline
While the main analysis pipeline respects file selection, there might be edge cases where:
- Cached results from previous analyses include all files
- Error handling fallbacks might process additional files
- Database persistence might retain results from previous full-project analyses

#### Issue 3: File Type Support Limitation
The current analyzer only supports C and JavaScript/TypeScript files (`.c`, `.h`, `.js`, `.jsx`, `.ts`, `.tsx`, `.json`). Python files (`.py`) are not supported, which explains why the diagnostic showed 0 files.

## Proposed Solutions

### Solution 1: Add File Selection Validation and Logging
Add comprehensive logging to track file selection through the pipeline and validate that only selected files are being processed.

### Solution 2: Enhance SOUP Detection with File Selection Awareness
While SOUP detection should still scan for all dependency files, we can add an option to restrict SOUP analysis to only dependencies that are actually used by the selected source files.

### Solution 3: Add Python File Support
Since this project is itself a Python project, add support for Python files to the analyzer.

### Solution 4: Clear Analysis State Between Runs
Ensure that previous analysis results don't contaminate new analyses with different file selections.

## Implementation Plan

### Phase 1: Diagnostic and Validation Enhancement
1. Enhance the diagnostic script to provide more detailed tracing
2. Add file selection validation at each pipeline stage
3. Add comprehensive logging for file processing

### Phase 2: Pipeline Isolation
1. Ensure each analysis run starts with a clean state
2. Add file selection context to all analysis stages
3. Validate that features, requirements, and other artifacts only reference selected files

### Phase 3: SOUP Detection Enhancement
1. Add option to restrict SOUP analysis to dependencies used by selected files
2. Provide clear separation between project-wide SOUP detection and selected-file analysis

### Phase 4: File Type Support Extension
1. Add Python file support to the analyzer
2. Extend parser service to handle Python files
3. Update supported extensions lists

## Immediate Actions Required

1. **Test with Supported File Types**: Test the analyzer with a C or JavaScript project to see if the file selection issue persists
2. **Clear Analysis Cache**: Clear any cached analysis results that might be contaminating new analyses
3. **Validate File Selection**: Use the diagnostic script with supported file types to confirm the issue
4. **Implement Logging**: Add detailed logging to track file processing through the pipeline

## Files to Modify

1. `medical_analyzer/services/ingestion.py` - Add Python support and enhanced logging
2. `medical_analyzer/parsers/parser_service.py` - Add Python parser and logging
3. `medical_analyzer/services/analysis_orchestrator.py` - Add file selection validation
4. `medical_analyzer/services/soup_detector.py` - Add file selection awareness option
5. `medical_analyzer/services/requirements_generator.py` - Add file selection validation

## Testing Strategy

1. Create test projects with both supported (C/JS) and unsupported (Python) file types
2. Test file selection with various combinations of selected files
3. Verify that requirements generation only uses features from selected files
4. Validate SOUP detection behavior with and without file selection restrictions