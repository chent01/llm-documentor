#!/usr/bin/env python3
"""
Setup script for the Medical Software Analysis Tool.

This script configures the packaging and distribution of the application
for desktop deployment and installation.
"""

from setuptools import setup, find_packages
from pathlib import Path
import os

# Read the README file
def read_readme():
    readme_path = Path(__file__).parent / "README.md"
    if readme_path.exists():
        return readme_path.read_text(encoding='utf-8')
    return "Medical Software Analysis Tool for medical device software development and regulatory compliance."

# Read requirements
def read_requirements():
    requirements_path = Path(__file__).parent / "requirements.txt"
    if requirements_path.exists():
        return requirements_path.read_text().splitlines()
    return []

# Get version
def get_version():
    version_file = Path(__file__).parent / "medical_analyzer" / "__init__.py"
    if version_file.exists():
        with open(version_file, 'r') as f:
            for line in f:
                if line.startswith('__version__'):
                    return line.split('=')[1].strip().strip('"\'')
    return "1.0.0"

# Package data
def get_package_data():
    return {
        'medical_analyzer': [
            'ui/resources/*.qss',
            'ui/resources/*.png',
            'ui/resources/*.ico',
            'config/templates/*.json',
            'data/*.json',
            'data/*.csv',
        ]
    }

# Entry points
def get_entry_points():
    return {
        'console_scripts': [
            'medical-analyzer=medical_analyzer.__main__:main',
        ],
        'gui_scripts': [
            'medical-analyzer-gui=medical_analyzer.__main__:main',
        ]
    }

# Get platform-specific data files
def get_platform_data_files():
    import platform
    system = platform.system()
    data_files = []
    
    if system == 'Windows':
        # Windows-specific files
        data_files.extend([
            ('icons', ['medical_analyzer/ui/resources/app_icon.ico']),
            ('', ['windows/medical-analyzer.bat']),
        ])
    elif system == 'Darwin':  # macOS
        # macOS-specific files
        data_files.extend([
            ('icons', ['medical_analyzer/ui/resources/app_icon.icns']),
            ('', ['macos/medical-analyzer.command']),
        ])
    else:  # Linux and others
        # Linux-specific files
        data_files.extend([
            ('icons', ['medical_analyzer/ui/resources/app_icon.png']),
            ('applications', ['linux/medical-analyzer.desktop']),
            ('bin', ['linux/medical-analyzer']),
        ])
    
    return data_files

setup(
    name="medical-software-analyzer",
    version=get_version(),
    author="Total Control Pty Ltd",
    author_email="info@tcgindustrial.com.au",
    description="A comprehensive tool for medical device software analysis and regulatory compliance",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/total-control/medical-software-analyzer",
    project_urls={
        "Bug Tracker": "https://github.com/total-control/medical-software-analyzer/issues",
        "Documentation": "https://medical-analyzer.readthedocs.io/",
        "Source Code": "https://github.com/total-control/medical-software-analyzer",
    },
    data_files=get_platform_data_files(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
    ],
    keywords="medical device, software analysis, regulatory compliance, ISO 14971, IEC 62304, risk management, requirements, testing",
    packages=find_packages(include=['medical_analyzer', 'medical_analyzer.*']),
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-qt>=4.0.0',
            'pytest-cov>=4.0.0',
            'black>=22.0.0',
            'flake8>=5.0.0',
            'mypy>=1.0.0',
            'pre-commit>=2.20.0',
        ],
        'docs': [
            'sphinx>=5.0.0',
            'sphinx-rtd-theme>=1.0.0',
            'myst-parser>=0.18.0',
        ],
        'gui': [
            'PyQt6>=6.4.0',
            'PyQt6-Qt6>=6.4.0',
            'PyQt6-sip>=13.4.0',
        ],
        'llm': [
            'openai>=1.0.0',
            'anthropic>=0.5.0',
            'llama-cpp-python>=0.2.0',
        ],
    },
    package_data=get_package_data(),
    include_package_data=True,
    entry_points=get_entry_points(),
    zip_safe=False,
    platforms=["Windows", "macOS", "Linux"],
    license="Proprietary - Non-commercial use only",
    maintainer="Total Control Pty Ltd",
    maintainer_email="info@tcgindustrial.com.au",
)
