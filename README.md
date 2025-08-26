# Medical Software Analysis Tool

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Tests](https://github.com/chent01/llm-documentor/actions/workflows/tests.yml/badge.svg)](https://github.com/chent01/llm-documentor/actions/workflows/tests.yml)

A comprehensive tool for analyzing medical device software, ensuring regulatory compliance, and generating documentation for FDA submissions.

## Features

- **Code Analysis**: Parse and analyze medical device software code for regulatory compliance
- **Hazard Identification**: Automatically identify potential hazards in medical software
- **Risk Assessment**: Generate risk registers and traceability matrices
- **Documentation**: Create regulatory documentation for FDA submissions
- **LLM Integration**: Leverage AI models for enhanced analysis capabilities
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

### Via pip (Recommended)

```bash
pip install medical-analyzer
```

### From Source

```bash
git clone https://github.com/your-organization/medical-analyzer.git
cd medical-analyzer
pip install -e .
```

## Quick Start

### GUI Mode

Launch the graphical user interface:

```bash
medical-analyzer
```

Or use the platform-specific launchers in the `windows`, `macos`, or `linux` directories.

### Headless Mode

Run analysis without the GUI:

```bash
medical-analyzer --headless --input /path/to/source/code --output /path/to/output/dir
```

## Configuration

The tool can be configured via a JSON configuration file. See the [Deployment Guide](docs/DEPLOYMENT.md) for details.

### LLM Integration

The tool supports multiple LLM backends:

- OpenAI (GPT-4, etc.)
- Anthropic (Claude)
- Local models (via llama.cpp)
- Mock backend (for testing)

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install documentation dependencies
pip install -e ".[docs]"
```

### Running Tests

```bash
python -m pytest
```

### Building Documentation

```bash
cd docs
make html
```

## Project Structure

```
medical_analyzer/
├── config/           # Configuration management
├── core/             # Core application logic
├── database/         # Database schema and operations
├── error_handling/   # Error handling and logging
├── llm/              # LLM backend integrations
├── models/           # Data models and enums
├── parsers/          # Code parsing modules
├── services/         # Analysis services
├── tests/            # Test generation
├── ui/               # User interface components
└── utils/            # Utility functions
```

## License

see the LICENSE file for details.

