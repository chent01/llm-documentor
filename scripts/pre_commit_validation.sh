#!/bin/bash

# Pre-commit validation script for medical software analyzer
# This script runs comprehensive validation checks before allowing commits

set -e  # Exit on any error

echo "🔍 Starting pre-commit validation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate environment
print_status "Validating environment..."

if ! command_exists python; then
    print_error "Python not found. Please install Python 3.8+."
    exit 1
fi

PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
print_status "Python version: $PYTHON_VERSION"

if ! command_exists pytest; then
    print_error "pytest not found. Please install development dependencies: pip install -e \".[dev]\""
    exit 1
fi

# Check for required imports
print_status "Checking required imports..."
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

if [ $? -ne 0 ]; then
    print_error "Required imports not available"
    exit 1
fi

# Run test suite validation
print_status "Running test suite validation..."

# Set environment variables for consistent test behavior
export PYTHONHASHSEED=0
export QT_LOGGING_RULES="*.debug=false"

# Run tests with timeout to prevent hanging
timeout 600 python -m pytest tests/ -x --tb=short --quiet

if [ $? -ne 0 ]; then
    print_error "Test suite validation failed"
    print_error "Please fix failing tests before committing"
    exit 1
fi

print_success "Test suite validation passed"

# Check test coverage (optional, warning only)
print_status "Checking test coverage..."
COVERAGE_RESULT=$(python -m pytest tests/ --cov=medical_analyzer --cov-report=term-missing --quiet 2>/dev/null | grep "TOTAL" | awk '{print $4}' | sed 's/%//')

if [ ! -z "$COVERAGE_RESULT" ]; then
    if [ "$COVERAGE_RESULT" -lt 80 ]; then
        print_warning "Test coverage is ${COVERAGE_RESULT}% (below 80% threshold)"
        print_warning "Consider adding more tests to improve coverage"
    else
        print_success "Test coverage: ${COVERAGE_RESULT}%"
    fi
else
    print_warning "Could not determine test coverage"
fi

# Check for common code quality issues (if tools are available)
if command_exists flake8; then
    print_status "Running code style checks..."
    flake8 medical_analyzer/ --max-line-length=100 --ignore=E203,W503 || {
        print_warning "Code style issues found (not blocking commit)"
    }
else
    print_warning "flake8 not available, skipping code style checks"
fi

# Check for security issues (if bandit is available)
if command_exists bandit; then
    print_status "Running security checks..."
    bandit -r medical_analyzer/ -f json -o bandit_report.json -q || {
        print_warning "Security issues found (not blocking commit)"
        print_warning "Check bandit_report.json for details"
    }
else
    print_warning "bandit not available, skipping security checks"
fi

# Validate import statements in modified files
print_status "Validating imports in modified files..."
MODIFIED_FILES=$(git diff --cached --name-only --diff-filter=AM | grep "\.py$" || true)

if [ ! -z "$MODIFIED_FILES" ]; then
    for file in $MODIFIED_FILES; do
        if [ -f "$file" ]; then
            python -c "
import ast
import sys

try:
    with open('$file', 'r') as f:
        ast.parse(f.read())
    print('✓ $file syntax OK')
except SyntaxError as e:
    print(f'✗ $file syntax error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'? $file validation error: {e}')
"
            if [ $? -ne 0 ]; then
                print_error "Syntax error in $file"
                exit 1
            fi
        fi
    done
else
    print_status "No Python files modified"
fi

# Check for TODO/FIXME comments in modified files
if [ ! -z "$MODIFIED_FILES" ]; then
    TODO_COUNT=$(grep -n -i "TODO\|FIXME\|XXX" $MODIFIED_FILES 2>/dev/null | wc -l || echo "0")
    if [ "$TODO_COUNT" -gt 0 ]; then
        print_warning "Found $TODO_COUNT TODO/FIXME comments in modified files"
        grep -n -i "TODO\|FIXME\|XXX" $MODIFIED_FILES 2>/dev/null || true
    fi
fi

# Check for large files
print_status "Checking for large files..."
LARGE_FILES=$(git diff --cached --name-only | xargs ls -la 2>/dev/null | awk '$5 > 1048576 {print $9 " (" $5 " bytes)"}' || true)
if [ ! -z "$LARGE_FILES" ]; then
    print_warning "Large files detected:"
    echo "$LARGE_FILES"
    print_warning "Consider if these files should be committed"
fi

# Performance check - ensure test suite runs within time limit
print_status "Checking test performance..."
START_TIME=$(date +%s)
timeout 300 python -m pytest tests/ --quiet >/dev/null 2>&1
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ $DURATION -gt 300 ]; then
    print_warning "Test suite took ${DURATION}s (>5 minutes)"
    print_warning "Consider optimizing slow tests"
else
    print_success "Test suite completed in ${DURATION}s"
fi

# Final validation summary
print_success "Pre-commit validation completed successfully!"
print_status "Summary:"
echo "  ✓ Environment validated"
echo "  ✓ Test suite passed"
echo "  ✓ Import validation passed"
echo "  ✓ Performance within limits"

# Optional: Show commit statistics
STAGED_FILES=$(git diff --cached --name-only | wc -l)
STAGED_LINES=$(git diff --cached --numstat | awk '{add+=$1; del+=$2} END {print add "+" del "-"}')
print_status "Staged changes: $STAGED_FILES files, $STAGED_LINES lines"

echo ""
print_success "🎉 Ready to commit!"