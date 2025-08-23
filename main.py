#!/usr/bin/env python3
"""
Main entry point for the Medical Software Analysis Tool.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from medical_analyzer.database import init_database


def main():
    """Main application entry point."""
    print("Medical Software Analysis Tool")
    print("==============================")
    
    # Initialize database
    try:
        db_manager = init_database()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return 1
    
    print("\nProject structure created successfully!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run the application: python main.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())