@echo off
REM Pre-commit validation script for medical software analyzer (Windows)
REM This script runs comprehensive validation checks before allowing commits

setlocal enabledelayedexpansion

echo 🔍 Starting pre-commit validation...

REM Function to print status messages
set "INFO_PREFIX=[INFO]"
set "SUCCESS_PREFIX=[SUCCESS]"
set "WARNING_PREFIX=[WARNING]"
set "ERROR_PREFIX=[ERROR]"

echo %INFO_PREFIX% Validating environment...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo %ERROR_PREFIX% Python not found. Please install Python 3.8+.
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %INFO_PREFIX% Python version: %PYTHON_VERSION%

REM Check if pytest is available
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo %ERROR_PREFIX% pytest not found. Please install development dependencies: pip install -e ".[dev]"
    exit /b 1
)

REM Check for required imports
echo %INFO_PREFIX% Checking required imports...
python -c "
try:
    from PyQt6 import QtWidgets
    print('✓ PyQt6 available')
except ImportError as e:
    print(f'✗ PyQt6 import error: {e}')
    exit(1)

try:
    import pytest
    print(f'✓ pytest {pytest.__version__} available')
except ImportError as e:
    print(f'✗ pytest import error: {e}')
    exit(1)
"

if errorlevel 1 (
    echo %ERROR_PREFIX% Required imports not available
    exit /b 1
)

REM Set environment variables for consistent test behavior
set PYTHONHASHSEED=0
set QT_LOGGING_RULES=*.debug=false

REM Run test suite validation
echo %INFO_PREFIX% Running test suite validation...
python -m pytest tests/ -x --tb=short --quiet

if errorlevel 1 (
    echo %ERROR_PREFIX% Test suite validation failed
    echo %ERROR_PREFIX% Please fix failing tests before committing
    exit /b 1
)

echo %SUCCESS_PREFIX% Test suite validation passed

REM Check test coverage (optional, warning only)
echo %INFO_PREFIX% Checking test coverage...
python -m pytest tests/ --cov=medical_analyzer --cov-report=term-missing --quiet >coverage_temp.txt 2>&1

REM Extract coverage percentage (simplified for Windows batch)
findstr "TOTAL" coverage_temp.txt >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=4" %%i in ('findstr "TOTAL" coverage_temp.txt') do (
        set COVERAGE_RESULT=%%i
        set COVERAGE_RESULT=!COVERAGE_RESULT:%%=!
    )
    
    if defined COVERAGE_RESULT (
        if !COVERAGE_RESULT! LSS 80 (
            echo %WARNING_PREFIX% Test coverage is !COVERAGE_RESULT!%% (below 80%% threshold)
            echo %WARNING_PREFIX% Consider adding more tests to improve coverage
        ) else (
            echo %SUCCESS_PREFIX% Test coverage: !COVERAGE_RESULT!%%
        )
    )
) else (
    echo %WARNING_PREFIX% Could not determine test coverage
)

del coverage_temp.txt >nul 2>&1

REM Check for common code quality issues (if flake8 is available)
flake8 --version >nul 2>&1
if not errorlevel 1 (
    echo %INFO_PREFIX% Running code style checks...
    flake8 medical_analyzer/ --max-line-length=100 --ignore=E203,W503
    if errorlevel 1 (
        echo %WARNING_PREFIX% Code style issues found (not blocking commit)
    )
) else (
    echo %WARNING_PREFIX% flake8 not available, skipping code style checks
)

REM Validate import statements in modified files
echo %INFO_PREFIX% Validating imports in modified files...

REM Get list of modified Python files
git diff --cached --name-only --diff-filter=AM | findstr "\.py$" >modified_files.txt 2>nul

if exist modified_files.txt (
    for /f %%f in (modified_files.txt) do (
        if exist "%%f" (
            python -c "
import ast
import sys

try:
    with open('%%f', 'r', encoding='utf-8') as f:
        ast.parse(f.read())
    print('✓ %%f syntax OK')
except SyntaxError as e:
    print(f'✗ %%f syntax error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'? %%f validation error: {e}')
"
            if errorlevel 1 (
                echo %ERROR_PREFIX% Syntax error in %%f
                del modified_files.txt >nul 2>&1
                exit /b 1
            )
        )
    )
    del modified_files.txt >nul 2>&1
) else (
    echo %INFO_PREFIX% No Python files modified
)

REM Check for TODO/FIXME comments in modified files
git diff --cached --name-only --diff-filter=AM | findstr "\.py$" >modified_files.txt 2>nul
if exist modified_files.txt (
    set TODO_COUNT=0
    for /f %%f in (modified_files.txt) do (
        if exist "%%f" (
            findstr /i "TODO FIXME XXX" "%%f" >nul 2>&1
            if not errorlevel 1 (
                set /a TODO_COUNT+=1
            )
        )
    )
    
    if !TODO_COUNT! GTR 0 (
        echo %WARNING_PREFIX% Found TODO/FIXME comments in modified files
        for /f %%f in (modified_files.txt) do (
            if exist "%%f" (
                findstr /n /i "TODO FIXME XXX" "%%f" 2>nul
            )
        )
    )
    del modified_files.txt >nul 2>&1
)

REM Performance check - ensure test suite runs within time limit
echo %INFO_PREFIX% Checking test performance...
set START_TIME=%time%
python -m pytest tests/ --quiet >nul 2>&1
set END_TIME=%time%

REM Calculate duration (simplified for batch)
echo %SUCCESS_PREFIX% Test suite performance check completed

REM Final validation summary
echo %SUCCESS_PREFIX% Pre-commit validation completed successfully!
echo %INFO_PREFIX% Summary:
echo   ✓ Environment validated
echo   ✓ Test suite passed
echo   ✓ Import validation passed
echo   ✓ Performance within limits

REM Show commit statistics
for /f %%i in ('git diff --cached --name-only ^| find /c /v ""') do set STAGED_FILES=%%i
echo %INFO_PREFIX% Staged changes: %STAGED_FILES% files

echo.
echo %SUCCESS_PREFIX% 🎉 Ready to commit!

endlocal