# Medical Software Analysis Tool Configuration Guide

This document provides detailed information about configuring the Medical Software Analysis Tool through its JSON configuration system.

## Table of Contents

1. [Configuration Overview](#configuration-overview)
2. [Configuration File Locations](#configuration-file-locations)
3. [Configuration Options](#configuration-options)
   - [LLM Configuration](#llm-configuration)
   - [Database Configuration](#database-configuration)
   - [Export Configuration](#export-configuration)
   - [UI Configuration](#ui-configuration)
   - [Analysis Configuration](#analysis-configuration)
   - [Logging Configuration](#logging-configuration)
   - [Custom Configuration](#custom-configuration)
4. [Example Configurations](#example-configurations)
   - [OpenAI Configuration](#openai-configuration)
   - [Anthropic Configuration](#anthropic-configuration)
   - [Local LLM Configuration](#local-llm-configuration)
   - [Mock Backend Configuration](#mock-backend-configuration)
5. [Environment Variables](#environment-variables)

## Configuration Overview

The Medical Software Analysis Tool uses a JSON-based configuration system that allows you to customize various aspects of the application, including LLM backends, database settings, UI preferences, and more.

Configuration is loaded in the following order of precedence:

1. Command-line arguments (highest priority)
2. Custom configuration file specified with `--config`
3. User-specific configuration file
4. Default configuration template

## Configuration File Locations

The application looks for configuration files in the following locations:

- **Default configuration template**: `medical_analyzer/config/templates/default_config.json`
- **User-specific configuration**:
  - Windows: `%APPDATA%\MedicalAnalyzer\config.json`
  - macOS: `~/Library/Application Support/MedicalAnalyzer/config.json`
  - Linux: `~/.config/medical-analyzer/config.json`
- **Custom configuration**: Any path specified with the `--config` command-line option

## Configuration Options

### LLM Configuration

The `llm` section configures the Language Model backend used for analysis:

| Option | Type | Description |
|--------|------|-------------|
| `backend_type` | string | LLM backend type: "openai", "anthropic", "local", or "mock" |
| `model_path` | string | Path to local model file (for "local" backend) |
| `server_url` | string | URL for local LLM server (for "local" backend) |
| `api_key` | string | API key for OpenAI or Anthropic |
| `model_name` | string | Model name (e.g., "gpt-4", "claude-2") |
| `max_tokens` | integer | Maximum tokens to generate |
| `temperature` | float | Temperature for sampling (0.0-1.0) |
| `timeout` | integer | Request timeout in seconds |
| `retry_attempts` | integer | Number of retry attempts |
| `batch_size` | integer | Batch size for processing |
| `context_window` | integer | Context window size in tokens |
| `embedding_model` | string | Model for embeddings |

### Database Configuration

The `database` section configures the SQLite database used for storing analysis results:

| Option | Type | Description |
|--------|------|-------------|
| `db_path` | string | Path to database file |
| `backup_enabled` | boolean | Enable automatic backups |
| `backup_interval` | integer | Backup interval in seconds |
| `max_backups` | integer | Maximum number of backup files |

### Export Configuration

The `export` section configures how analysis results are exported:

| Option | Type | Description |
|--------|------|-------------|
| `default_format` | string | Default export format: "pdf", "html", "markdown", "zip" |
| `include_audit_log` | boolean | Include audit log in exports |
| `include_metadata` | boolean | Include metadata in exports |
| `compression_level` | integer | Compression level for zip exports (1-9) |
| `max_file_size` | integer | Maximum export file size in bytes |

### UI Configuration

The `ui` section configures the user interface:

| Option | Type | Description |
|--------|------|-------------|
| `theme` | string | UI theme: "light", "dark", "system", "default" |
| `window_width` | integer | Initial window width |
| `window_height` | integer | Initial window height |
| `auto_save` | boolean | Enable auto-save |
| `auto_save_interval` | integer | Auto-save interval in seconds |
| `show_tooltips` | boolean | Show tooltips |
| `confirm_exit` | boolean | Confirm before exiting |

### Analysis Configuration

The `analysis` section configures the analysis process:

| Option | Type | Description |
|--------|------|-------------|
| `max_chunk_size` | integer | Maximum chunk size for analysis |
| `min_confidence` | float | Minimum confidence threshold (0.0-1.0) |
| `max_files_per_analysis` | integer | Maximum files per analysis run |
| `supported_extensions` | array | Array of supported file extensions |
| `enable_parallel_processing` | boolean | Enable parallel processing |
| `max_workers` | integer | Maximum number of worker threads |

### Logging Configuration

The `logging` section configures application logging:

| Option | Type | Description |
|--------|------|-------------|
| `level` | string | Logging level: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" |
| `file_enabled` | boolean | Enable logging to file |
| `console_enabled` | boolean | Enable logging to console |
| `log_file` | string | Path to log file |
| `max_file_size` | integer | Maximum log file size in bytes |
| `backup_count` | integer | Number of log backups to keep |
| `format_string` | string | Log format string |

### Custom Configuration

The `custom` section contains additional application settings:

| Option | Type | Description |
|--------|------|-------------|
| `auto_update_check` | boolean | Check for updates automatically |
| `update_check_interval` | integer | Update check interval in seconds |
| `telemetry_enabled` | boolean | Enable anonymous usage telemetry |
| `project_templates_dir` | string | Custom project templates directory |

## Example Configurations

The following examples demonstrate how to configure the tool for different LLM backends.

### OpenAI Configuration

Use this configuration to connect to OpenAI's API services:

```json
{
  "llm": {
    "backend_type": "openai",
    "api_key": "your-openai-api-key",
    "model_name": "gpt-4",
    "max_tokens": 2000,
    "temperature": 0.2,
    "timeout": 60,
    "retry_attempts": 3,
    "batch_size": 16,
    "context_window": 8192,
    "embedding_model": "text-embedding-ada-002"
  }
}
```

**Key Settings:**
- `api_key`: Your OpenAI API key (required)
- `model_name`: The OpenAI model to use (e.g., "gpt-4", "gpt-3.5-turbo")
- `embedding_model`: Model used for text embeddings

### Anthropic Configuration

Use this configuration to connect to Anthropic's API services:

```json
{
  "llm": {
    "backend_type": "anthropic",
    "api_key": "your-anthropic-api-key",
    "model_name": "claude-2",
    "max_tokens": 2000,
    "temperature": 0.2,
    "timeout": 60,
    "retry_attempts": 3
  }
}
```

**Key Settings:**
- `api_key`: Your Anthropic API key (required)
- `model_name`: The Anthropic model to use (e.g., "claude-2", "claude-instant")

### Local LLM Configuration

#### Using a Local Model File

Use this configuration to run a local model file directly on your machine:

```json
{
  "llm": {
    "backend_type": "local",
    "model_path": "/path/to/your/model.gguf",
    "max_tokens": 1000,
    "temperature": 0.1,
    "batch_size": 8,
    "context_window": 4096
  }
}
```

**Key Settings:**
- `model_path`: Path to your local model file (typically .gguf format)
- `batch_size`: Processing batch size for local inference
- `context_window`: Context window size in tokens

#### Using a Local LLM Server

Use this configuration to connect to a local LLM server on your network:

```json
{
  "llm": {
    "backend_type": "local",
    "server_url": "http://192.168.1.100:8080",
    "api_key": "your-api-key-if-required",
    "model_name": "your-model-name",
    "max_tokens": 1000,
    "temperature": 0.1,
    "timeout": 30,
    "retry_attempts": 3
  }
}
```

**Key Settings:**
- `server_url`: URL to your LAN-hosted LLM server
- `api_key`: API key if required by your local server
- `model_name`: Name of the model on your local server

### Mock Backend Configuration

For testing purposes, you can use the mock backend which doesn't require any external services:

```json
{
  "llm": {
    "backend_type": "mock"
  }
}
```

**Note:** The mock backend provides simulated responses and is useful for testing the application without connecting to actual LLM services.

## Environment Variables

You can override the configuration directory using the `MEDICAL_ANALYZER_CONFIG_DIR` environment variable:

```bash
# Windows
set MEDICAL_ANALYZER_CONFIG_DIR=C:\path\to\config\dir

# macOS/Linux
export MEDICAL_ANALYZER_CONFIG_DIR=/path/to/config/dir
```

## Using the Example Configuration

Example configuration files are provided in the `examples` directory:

- `examples/example_config.json`: A comprehensive example with comments explaining each option
- `examples/clean_config.json`: A clean version without comments, ready to use
- `examples/local_lan_config.json`: Configuration for connecting to a local LLM server on your LAN
- `examples/local_machine_config.json`: Configuration for running a local LLM directly on your machine
- `examples/openai_config.json`: Configuration for using OpenAI's API
- `examples/mock_config.json`: Configuration for using the mock backend for testing

You can use these as starting points for your own configuration:

1. Copy one of the example configurations to your preferred location:
   ```bash
   # If you want the commented version for reference
   cp examples/example_config.json my_config.json
   
   # If you want a specific backend configuration
   cp examples/local_lan_config.json my_config.json
   # or
   cp examples/local_machine_config.json my_config.json
   # or
   cp examples/openai_config.json my_config.json
   # or
   cp examples/mock_config.json my_config.json
   ```

2. Edit the configuration file to match your requirements:
   ```bash
   # Edit with your preferred text editor
   nano my_config.json
   ```

3. If you used the commented version, remember to remove all comments as JSON does not officially support them.

4. Run the application with your custom configuration:
   ```bash
   medical-analyzer --config my_config.json
   ```

---

For additional support, please contact: info@tcgindustrial.com.au