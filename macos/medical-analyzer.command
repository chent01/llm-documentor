#!/bin/bash
# Medical Software Analysis Tool launcher for macOS

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    osascript -e 'display dialog "Python 3 is not available. Please install Python 3.8 or later and try again." buttons {"OK"} default button "OK" with icon stop with title "Medical Software Analyzer"'
    exit 1
fi

# Launch the application
echo "Launching Medical Software Analysis Tool..."
exec python3 -m medical_analyzer "$@"