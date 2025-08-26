#!/usr/bin/env python3
"""
Main entry point for the Medical Software Analysis Tool.

This script serves as the primary entry point for the application when run directly.
It delegates to the main function in the medical_analyzer package.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the main function from the package
from medical_analyzer.__main__ import main


if __name__ == "__main__":
    # Pass command line arguments to the main function
    sys.exit(main())