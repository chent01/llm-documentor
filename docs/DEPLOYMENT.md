# Medical Software Analysis Tool Deployment Guide

This document provides comprehensive instructions for deploying the Medical Software Analysis Tool in various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Methods](#installation-methods)
   - [Standard Installation](#standard-installation)
   - [Development Installation](#development-installation)
3. [Platform-Specific Instructions](#platform-specific-instructions)
   - [Windows](#windows)
   - [macOS](#macos)
   - [Linux](#linux)
4. [Configuration](#configuration)
5. [LLM Backend Setup](#llm-backend-setup)
6. [Troubleshooting](#troubleshooting)
7. [Updating](#updating)

## Prerequisites

Before installing the Medical Software Analysis Tool, ensure your system meets the following requirements:

- Python 3.8 or higher
- Pip package manager
- Git (for development installation)
- 4GB RAM minimum (8GB recommended)
- 500MB free disk space

## Installation Methods

### Standard Installation

The recommended way to install the Medical Software Analysis Tool is via pip:

```bash
pip install medical-analyzer
```

This will install the latest stable version of the tool along with all required dependencies.

### Development Installation

For development purposes or to access the latest features, you can install directly from the repository:

```bash
# Clone the repository
git clone https://github.com/your-organization/medical-analyzer.git
cd medical-analyzer

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

## Platform-Specific Instructions

### Windows

After installation, you can launch the application using:

1. The installed command-line tool:
   ```
   medical-analyzer
   ```

2. The installed GUI shortcut (Start Menu → Medical Software Analyzer)

3. The batch file in the Windows directory:
   ```
   windows\medical-analyzer.bat
   ```

### macOS

After installation, you can launch the application using:

1. The installed command-line tool:
   ```
   medical-analyzer
   ```

2. The macOS command script:
   ```
   chmod +x macos/medical-analyzer.command
   ./macos/medical-analyzer.command
   ```

### Linux

After installation, you can launch the application using:

1. The installed command-line tool:
   ```
   medical-analyzer
   ```

2. The Linux shell script:
   ```
   chmod +x linux/medical-analyzer
   ./linux/medical-analyzer
   ```

3. The desktop entry (after installation):
   ```
   # Copy the desktop file to the applications directory
   sudo cp linux/medical-analyzer.desktop /usr/share/applications/
   # Copy the icon to the icons directory
   sudo cp resources/icons/medical-analyzer.svg /usr/share/icons/
   ```

## Configuration

The Medical Software Analysis Tool uses a configuration system that can be customized in several ways:

### Default Configuration

On first run, the application creates a default configuration file in the user's home directory:

- Windows: `%APPDATA%\MedicalAnalyzer\config.json`
- macOS: `~/Library/Application Support/MedicalAnalyzer/config.json`
- Linux: `~/.config/medical-analyzer/config.json`

### Custom Configuration

You can specify a custom configuration file using the `--config` command-line option:

```bash
medical-analyzer --config /path/to/your/config.json
```

### Configuration Template

A default configuration template is provided in the package at `medical_analyzer/config/templates/default_config.json`. You can use this as a starting point for creating your own configuration.

### Environment Variables

You can override the configuration directory using the `MEDICAL_ANALYZER_CONFIG_DIR` environment variable:

```bash
# Windows
set MEDICAL_ANALYZER_CONFIG_DIR=C:\path\to\config\dir

# macOS/Linux
export MEDICAL_ANALYZER_CONFIG_DIR=/path/to/config/dir
```

## LLM Backend Setup

The Medical Software Analysis Tool supports multiple LLM backends:

### OpenAI

To use OpenAI's models:

1. Obtain an API key from [OpenAI](https://platform.openai.com/)
2. Configure the LLM settings in your config.json:

```json
{
  "llm": {
    "backend_type": "openai",
    "api_key": "your-api-key",
    "model_name": "gpt-4",
    "max_tokens": 1000,
    "temperature": 0.1
  }
}
```

### Anthropic

To use Anthropic's Claude models:

1. Obtain an API key from [Anthropic](https://www.anthropic.com/)
2. Configure the LLM settings in your config.json:

```json
{
  "llm": {
    "backend_type": "anthropic",
    "api_key": "your-api-key",
    "model_name": "claude-2",
    "max_tokens": 1000,
    "temperature": 0.1
  }
}
```

### Local Models

To use a local LLM model:

1. Download a compatible model (e.g., a GGUF format model for llama.cpp)
2. Configure the LLM settings in your config.json:

```json
{
  "llm": {
    "backend_type": "local",
    "model_path": "/path/to/your/model.gguf",
    "max_tokens": 1000,
    "temperature": 0.1
  }
}
```

### Mock Backend

For testing purposes, you can use the mock backend which doesn't require any external services:

```json
{
  "llm": {
    "backend_type": "mock"
  }
}
```

## Troubleshooting

### Common Issues

1. **Application fails to start**
   - Verify Python version (3.8+)
   - Check for missing dependencies: `pip install -r requirements.txt`
   - Examine log file: `medical_analyzer.log`

2. **LLM backend errors**
   - Verify API key is correct
   - Check network connectivity
   - Ensure model name is valid
   - Increase timeout setting if necessary

3. **Database errors**
   - Check write permissions in the database directory
   - Verify SQLite is properly installed

### Logging

The application logs information to:

- Console (if `console_enabled` is true in config)
- Log file (if `file_enabled` is true in config)

You can adjust the logging level in the configuration:

```json
{
  "logging": {
    "level": "DEBUG",  // Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    "file_enabled": true,
    "console_enabled": true,
    "log_file": "medical_analyzer.log"
  }
}
```

## Updating

To update the Medical Software Analysis Tool to the latest version:

```bash
pip install --upgrade medical-analyzer
```

For development installations:

```bash
cd medical-analyzer
git pull
pip install -e .
```

After updating, it's recommended to run the tests to ensure everything is working correctly:

```bash
python -m pytest
```

---

For additional support, please contact: info@tcgindustrial.com.au